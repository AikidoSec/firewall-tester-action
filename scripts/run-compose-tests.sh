#!/usr/bin/env bash
set -euo pipefail

command="${1:-run}"
if [ "$command" = "--cleanup" ]; then
  command="cleanup"
fi
if [ "$command" != "run" ] && [ "$command" != "cleanup" ]; then
  echo "Usage: run-compose-tests.sh [run|cleanup]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
action_path="${GITHUB_ACTION_PATH:-$(cd "$script_dir/.." && pwd)}"

dockerfile_path="${DOCKERFILE_PATH:-${INPUT_DOCKERFILE_PATH:-}}"
if [ -z "$dockerfile_path" ]; then
  echo "DOCKERFILE_PATH must point to the demo app Dockerfile" >&2
  exit 2
fi

APP_ENV_FILE="${APP_ENV_FILE:-}"
APP_ENV_FILE_2="${APP_ENV_FILE_2:-}"
APP_PORT="${APP_PORT:-8080}"
BUILD_ARGS="${BUILD_ARGS:-}"
CONFIG_UPDATE_DELAY="${CONFIG_UPDATE_DELAY:-60}"
MAX_PARALLEL_TESTS="${MAX_PARALLEL_TESTS:-${COMPOSE_TEST_PARALLELISM:-10}}"
RUN_TESTS="${RUN_TESTS:-}"
RUNNER_TEMP="${RUNNER_TEMP:-$action_path/.tmp}"
SLEEP_BEFORE_TEST="${SLEEP_BEFORE_TEST:-1}"
SKIP_TESTS="${SKIP_TESTS:-}"
TEST_NAME="${TEST_NAME:-}"
TEST_TYPE="${TEST_TYPE:-server}"

container_os="$(docker info --format '{{.OSType}}')"
if [ "$container_os" = "windows" ]; then
  compose_env_file="${COMPOSE_ENV_FILE:-$action_path/compose.windows.env}"
else
  compose_env_file="${COMPOSE_ENV_FILE:-$action_path/compose.linux.env}"
fi
compose_file="${COMPOSE_FILE:-$action_path/compose.yml}"

compose_path() {
  local path="$1"
  if [ "$container_os" = "windows" ] && command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$path"
  else
    printf '%s\n' "$path"
  fi
}

normalize_env_file() {
  local file_path="$1"
  if [ -n "$file_path" ]; then
    compose_path "$(cd "$(dirname "$file_path")" && pwd)/$(basename "$file_path")"
  else
    compose_path "$action_path/server_tests/empty.env"
  fi
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s\n' "$value"
}

demo_context="$(dirname "$dockerfile_path")"
demo_context_absolute="$(cd "$demo_context" && pwd)"
export DEMO_CONTEXT="$(compose_path "$demo_context_absolute")"
export DEMO_DOCKERFILE="$(basename "$dockerfile_path")"
export APP_ENV_FILE="$(normalize_env_file "$APP_ENV_FILE")"
export APP_ENV_FILE_2="$(normalize_env_file "$APP_ENV_FILE_2")"
export APP_PORT CONFIG_UPDATE_DELAY SLEEP_BEFORE_TEST

if [ -z "${COMPOSE_PROJECT_NAME:-}" ]; then
  if [ -n "$TEST_NAME" ]; then
    export COMPOSE_PROJECT_NAME="$TEST_NAME"
  else
    export COMPOSE_PROJECT_NAME="firewall-tester-action"
  fi
fi
export DEMO_IMAGE="${DEMO_IMAGE:-firewall-tester-action-demo-$COMPOSE_PROJECT_NAME}"

compose=(docker compose --env-file "$compose_env_file" -f "$compose_file")

cleanup_compose_project() {
  "${compose[@]}" down -v --remove-orphans || true
  docker network rm "${COMPOSE_PROJECT_NAME}-default" >/dev/null 2>&1 || true
}

if [ "$command" = "cleanup" ]; then
  cleanup_compose_project
  exit 0
fi

mkdir -p "$RUNNER_TEMP/compose-test-logs"
: > "$RUNNER_TEMP/compose-test-failures"

trap cleanup_compose_project EXIT

build_arg_flags=()
while IFS= read -r build_arg; do
  build_arg="$(trim "$build_arg")"
  if [ -n "$build_arg" ]; then
    build_arg_flags+=(--build-arg "$build_arg")
  fi
done <<< "$BUILD_ARGS"

cleanup_compose_project

"${compose[@]}" --profile build build \
  "${build_arg_flags[@]}" \
  demo-app-image

"${compose[@]}" --profile build build \
  core \
  test-runner-image

"${compose[@]}" up --no-build -d --wait core postgres
all_services="$("${compose[@]}" config --services)"

summary_order=()
declare -A test_started_at=()
declare -A summary_status=()
declare -A summary_duration=()
declare -A summary_error=()

record_selected_test() {
  local test_name="$1"
  summary_order+=("$test_name")
}

duration_for_test() {
  local test_name="$1"
  local started_at="${test_started_at[$test_name]:-}"
  if [ -z "$started_at" ]; then
    printf 'N/A\n'
    return
  fi

  printf '%ss\n' "$(($(date +%s) - started_at))"
}

record_test_result() {
  local test_name="$1"
  local status="$2"
  local duration="$3"
  local error_message="${4:-}"

  summary_status["$test_name"]="$status"
  summary_duration["$test_name"]="$duration"
  summary_error["$test_name"]="$error_message"
}

markdown_escape() {
  local value="$1"
  value="${value//$'\r'/}"
  value="${value//$'\n'/<br>}"
  value="${value//|/\\|}"
  printf '%s\n' "$value"
}

write_test_summary() {
  local total=0
  local passed=0
  local failed=0
  local skipped=0
  local test_name
  local status
  local duration
  local error_message

  for test_name in "${summary_order[@]}"; do
    total=$((total + 1))
    status="${summary_status[$test_name]:-UNKNOWN}"
    case "$status" in
      PASS) passed=$((passed + 1)) ;;
      FAIL) failed=$((failed + 1)) ;;
      SKIP) skipped=$((skipped + 1)) ;;
    esac
  done

  echo
  echo "Test Results Summary"
  echo "===================="
  echo "Total Tests: $total"
  echo "Passed: $passed"
  echo "Skipped: $skipped"
  echo "Failed: $failed"
  echo
  echo "Detailed Results:"
  printf '%-45s %-8s %-10s %s\n' "Test" "Status" "Duration" "Error"
  for test_name in "${summary_order[@]}"; do
    status="${summary_status[$test_name]:-UNKNOWN}"
    duration="${summary_duration[$test_name]:-N/A}"
    error_message="${summary_error[$test_name]:-}"
    printf '%-45s %-8s %-10s %s\n' "$test_name" "$status" "$duration" "$error_message"
  done

  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    {
      echo "## Test Results Summary"
      echo
      echo "### Overview"
      echo
      echo "- **Total Tests:** $total"
      echo "- **Passed:** $passed"
      echo "- **Skipped:** $skipped"
      echo "- **Failed:** $failed"
      echo
      echo "### Detailed Results"
      echo
      echo "| Test | Status | Duration | Error Message |"
      echo "|------|--------|----------|---------------|"
      for test_name in "${summary_order[@]}"; do
        status="${summary_status[$test_name]:-UNKNOWN}"
        duration="${summary_duration[$test_name]:-N/A}"
        error_message="${summary_error[$test_name]:-}"
        printf '| %s | %s | %s | %s |\n' \
          "$(markdown_escape "$test_name")" \
          "$(markdown_escape "$status")" \
          "$(markdown_escape "$duration")" \
          "$(markdown_escape "$error_message")"
      done
      echo
    } >> "$GITHUB_STEP_SUMMARY"
  fi
}

related_services() {
  local test_name="$1"
  printf '%s\n' "$all_services" | awk -v t="$test_name" '
    $0 == t || $0 == "app-" t || $0 == "setup-" t || $0 ~ "-" t "$"
  '
}

cleanup_tests() {
  local services=()
  local service
  local test_name
  for test_name in "$@"; do
    while IFS= read -r service; do
      if [ -n "$service" ]; then
        services+=("$service")
      fi
    done < <(related_services "$test_name")
  done

  if [ "${#services[@]}" -gt 0 ]; then
    "${compose[@]}" kill "${services[@]}" >/dev/null 2>&1 || true
    "${compose[@]}" rm -f -v "${services[@]}" >/dev/null 2>&1 || true
  fi
}

test_container_id() {
  local test_name="$1"
  "${compose[@]}" ps -a -q "$test_name" 2>/dev/null | tail -n 1
}

start_test() {
  local test_name="$1"
  local start_log="$RUNNER_TEMP/compose-test-logs/${test_name}.start.log"
  local services=()
  local service

  echo "START ${test_name}"
  test_started_at["$test_name"]="$(date +%s)"
  if "${compose[@]}" up --no-build -d "$test_name" > "$start_log" 2>&1; then
    running_tests+=("$test_name")
    return
  fi

  echo "FAIL ${test_name}"
  record_test_result "$test_name" "FAIL" "$(duration_for_test "$test_name")" "Startup failed"
  printf '%s\n' "$test_name" >> "$RUNNER_TEMP/compose-test-failures"
  echo "::group::${test_name} startup log"
  cat "$start_log"
  while IFS= read -r service; do
    if [ -n "$service" ]; then
      services+=("$service")
    fi
  done < <(related_services "$test_name")
  if [ "${#services[@]}" -gt 0 ]; then
    "${compose[@]}" logs --no-color "${services[@]}" || true
  fi
  echo "::endgroup::"
  cleanup_tests "$test_name"
}

test_finished() {
  local test_name="$1"
  local container_id
  local state
  container_id="$(test_container_id "$test_name")"
  if [ -z "$container_id" ]; then
    return 1
  fi

  state="$(docker inspect -f '{{.State.Status}}' "$container_id" 2>/dev/null || echo missing)"
  [ "$state" = "exited" ] || [ "$state" = "dead" ]
}

collect_test() {
  local test_name="$1"
  local container_id
  local status=1
  local services=()
  local service
  container_id="$(test_container_id "$test_name")"
  if [ -n "$container_id" ]; then
    status="$(docker inspect -f '{{.State.ExitCode}}' "$container_id" 2>/dev/null || echo 1)"
  fi

  if [ "$status" = "0" ]; then
    echo "PASS ${test_name}"
    record_test_result "$test_name" "PASS" "$(duration_for_test "$test_name")"
  else
    echo "FAIL ${test_name}"
    record_test_result "$test_name" "FAIL" "$(duration_for_test "$test_name")" "Exit code $status"
    printf '%s\n' "$test_name" >> "$RUNNER_TEMP/compose-test-failures"
    while IFS= read -r service; do
      if [ -n "$service" ]; then
        services+=("$service")
      fi
    done < <(related_services "$test_name")
    echo "::group::${test_name} log"
    if [ "${#services[@]}" -gt 0 ]; then
      "${compose[@]}" logs --no-color "${services[@]}" || true
    fi
    echo "::endgroup::"
  fi

  cleanup_tests "$test_name"
}

is_skipped_test() {
  local test_name="$1"
  local skipped_test
  local skipped=()
  IFS=',' read -ra skipped <<< "$SKIP_TESTS"
  for skipped_test in "${skipped[@]}"; do
    skipped_test="$(trim "$skipped_test")"
    if [ "$skipped_test" = "$test_name" ]; then
      return 0
    fi
  done
  return 1
}

add_test_if_selected() {
  local test_name="$1"
  record_selected_test "$test_name"
  if is_skipped_test "$test_name"; then
    echo "SKIP ${test_name}"
    record_test_result "$test_name" "SKIP" "N/A" "Skipped"
    return
  fi
  tests+=("$test_name")
}

tests=()
if [ -n "$TEST_NAME" ]; then
  add_test_if_selected "$TEST_NAME"
elif [ -n "$RUN_TESTS" ]; then
  requested_tests=()
  IFS=',' read -ra requested_tests <<< "$RUN_TESTS"
  for requested_test in "${requested_tests[@]}"; do
    requested_test="$(trim "$requested_test")"
    if [ -n "$requested_test" ]; then
      add_test_if_selected "$requested_test"
    fi
  done
else
  while IFS= read -r test_name; do
    case "$TEST_TYPE:$test_name" in
      server:test-runner-image)
        ;;
      control:control-test-*|server:test-*)
        add_test_if_selected "$test_name"
        ;;
    esac
  done < <(printf '%s\n' "$all_services" | sort)
fi

if ! [[ "$MAX_PARALLEL_TESTS" =~ ^[1-9][0-9]*$ ]]; then
  echo "max_parallel_tests must be a positive integer" >&2
  exit 1
fi

next_test_index=0
running_tests=()

while [ "$next_test_index" -lt "${#tests[@]}" ] || [ "${#running_tests[@]}" -gt 0 ]; do
  while [ "${#running_tests[@]}" -lt "$MAX_PARALLEL_TESTS" ] && [ "$next_test_index" -lt "${#tests[@]}" ]; do
    start_test "${tests[$next_test_index]}"
    next_test_index=$((next_test_index + 1))
  done

  if [ "${#running_tests[@]}" -eq 0 ]; then
    continue
  fi

  next_running_tests=()
  completed_any=0
  for test_name in "${running_tests[@]}"; do
    if test_finished "$test_name"; then
      collect_test "$test_name"
      completed_any=1
    else
      next_running_tests+=("$test_name")
    fi
  done
  running_tests=()
  if [ "${#next_running_tests[@]}" -gt 0 ]; then
    running_tests=("${next_running_tests[@]}")
  fi

  if [ "$completed_any" -eq 0 ]; then
    sleep 2
  fi
done

write_test_summary

if [ -s "$RUNNER_TEMP/compose-test-failures" ]; then
  echo "Failed tests:"
  sort -u "$RUNNER_TEMP/compose-test-failures"
  exit 1
fi
