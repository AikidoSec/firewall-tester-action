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
IGNORE_FAILURES="${IGNORE_FAILURES:-false}"
MAX_PARALLEL_TESTS="${MAX_PARALLEL_TESTS:-20}"
RUN_TESTS="${RUN_TESTS:-}"
RUNNER_TEMP="${RUNNER_TEMP:-$action_path/.tmp}"
SKIP_TESTS="${SKIP_TESTS:-}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-600}"
TEST_NAME="${TEST_NAME:-}"
TEST_TYPE="${TEST_TYPE:-server}"

if ! [[ "$MAX_PARALLEL_TESTS" =~ ^[1-9][0-9]*$ ]]; then
  echo "MAX_PARALLEL_TESTS must be a positive integer" >&2
  exit 2
fi

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

join_by_comma() {
  local IFS=,
  printf '%s' "$*"
}

demo_context="$(dirname "$dockerfile_path")"
demo_context_absolute="$(cd "$demo_context" && pwd)"
export DEMO_CONTEXT="$(compose_path "$demo_context_absolute")"
export DEMO_DOCKERFILE="$(basename "$dockerfile_path")"
export APP_ENV_FILE="$(normalize_env_file "$APP_ENV_FILE")"
export APP_ENV_FILE_2="$(normalize_env_file "$APP_ENV_FILE_2")"
export APP_PORT CONFIG_UPDATE_DELAY STARTUP_TIMEOUT

if [ -z "${COMPOSE_PROJECT_NAME:-}" ]; then
  if [ -n "$TEST_NAME" ]; then
    export COMPOSE_PROJECT_NAME="$TEST_NAME"
  else
    export COMPOSE_PROJECT_NAME="firewall-tester-action"
  fi
fi
export DEMO_IMAGE="${DEMO_IMAGE:-firewall-tester-action-demo-$COMPOSE_PROJECT_NAME}"

mkdir -p "$RUNNER_TEMP"
runner_temp_absolute="$(cd "$RUNNER_TEMP" && pwd)"
results_dir="$runner_temp_absolute/compose-suite-results"
export RUNNER_TEMP_COMPOSE="$(compose_path "$results_dir")"

compose=(
  docker compose
  --parallel "$MAX_PARALLEL_TESTS"
  --env-file "$compose_env_file"
  -f "$compose_file"
)

cleanup_compose_project() {
  "${compose[@]}" down --timeout 10 -v --remove-orphans || true
}

print_compose_diagnostics() {
  local container_ids=()
  local network_ids=()

  echo "Compose suite did not complete; collecting container diagnostics" >&2
  "${compose[@]}" ps -a || true
  docker ps -a --no-trunc \
    --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" || true

  mapfile -t container_ids < <("${compose[@]}" ps -a -q 2>/dev/null || true)
  if [ "${#container_ids[@]}" -gt 0 ]; then
    docker inspect \
      --format 'ID={{.Id}} Name={{.Name}} Status={{.State.Status}} ExitCode={{.State.ExitCode}} Error={{json .State.Error}}' \
      "${container_ids[@]}" || true
  fi

  mapfile -t network_ids < <(
    docker network ls -q \
      --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME"
  )
  if [ "${#network_ids[@]}" -gt 0 ]; then
    docker network inspect \
      --format 'ID={{.Id}} Name={{.Name}} Containers={{json .Containers}}' \
      "${network_ids[@]}" || true
  fi
}

if [ "$command" = "cleanup" ]; then
  cleanup_compose_project
  exit 0
fi

if [ "$TEST_TYPE" != "server" ] && [ "$TEST_TYPE" != "control" ]; then
  echo "TEST_TYPE must be either server or control" >&2
  exit 2
fi

rm -rf "$results_dir"
mkdir -p "$results_dir"
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

"${compose[@]}" build core suite-runner

all_services="$("${compose[@]}" config --services)"

service_exists() {
  local expected="$1"
  grep -Fxq "$expected" <<< "$all_services"
}

is_skipped_test() {
  local expected="$1"
  local candidate
  local values=()
  IFS=',' read -ra values <<< "$SKIP_TESTS"
  for candidate in "${values[@]}"; do
    candidate="$(trim "$candidate")"
    if [ "$candidate" = "$expected" ]; then
      return 0
    fi
  done
  return 1
}

selected_tests=()
add_selected_test() {
  local test_name="$1"
  if ! service_exists "app-$test_name"; then
    echo "Unknown test: $test_name" >&2
    exit 2
  fi
  selected_tests+=("$test_name")
}

if [ -n "$TEST_NAME" ]; then
  add_selected_test "$TEST_NAME"
elif [ -n "$RUN_TESTS" ]; then
  requested_tests=()
  IFS=',' read -ra requested_tests <<< "$RUN_TESTS"
  for requested_test in "${requested_tests[@]}"; do
    requested_test="$(trim "$requested_test")"
    if [ -n "$requested_test" ]; then
      add_selected_test "$requested_test"
    fi
  done
else
  while IFS= read -r service; do
    case "$TEST_TYPE:$service" in
      server:app-test-*|control:app-control-test-*)
        selected_tests+=("${service#app-}")
        ;;
    esac
  done < <(printf '%s\n' "$all_services" | sort)
fi

tests_to_run=()
skipped_tests=()
for test_name in "${selected_tests[@]}"; do
  if is_skipped_test "$test_name"; then
    echo "SKIP $test_name"
    skipped_tests+=("$test_name")
  else
    tests_to_run+=("$test_name")
  fi
done

export SUITE_TESTS="$(join_by_comma "${tests_to_run[@]}")"
export SUITE_SKIPPED_TESTS="$(join_by_comma "${skipped_tests[@]}")"
export SUITE_MAX_WORKERS="$MAX_PARALLEL_TESTS"

if ! [[ "$CONFIG_UPDATE_DELAY" =~ ^[0-9]+$ ]]; then
  echo "CONFIG_UPDATE_DELAY must be a non-negative integer" >&2
  exit 2
fi

if [ "$IGNORE_FAILURES" != "true" ] && [ "$IGNORE_FAILURES" != "false" ]; then
  echo "IGNORE_FAILURES must be true or false" >&2
  exit 2
fi

runtime_services=()
for test_name in "${tests_to_run[@]}"; do
  while IFS= read -r service; do
    if [ "$service" = "app-$test_name" ] || [[ "$service" == *-"$test_name" ]]; then
      runtime_services+=("$service")
    fi
  done <<< "$all_services"
done

echo "Selected tests: ${#selected_tests[@]}"
echo "Tests to run: ${#tests_to_run[@]}"
echo "Compose services to start: ${#runtime_services[@]}"

set +e
"${compose[@]}" up \
  --no-build \
  --timeout 10 \
  --exit-code-from suite-runner \
  suite-runner \
  "${runtime_services[@]}"
suite_status=$?
set -e

if [ "$suite_status" -ne 0 ] && [ ! -f "$results_dir/suite-complete" ]; then
  print_compose_diagnostics
fi

if [ -f "$results_dir/summary.md" ]; then
  cat "$results_dir/summary.md"
  cp "$results_dir/summary.md" "$RUNNER_TEMP/compose-suite-summary.md"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    cat "$results_dir/summary.md" >> "$GITHUB_STEP_SUMMARY"
  fi
fi
if [ -f "$results_dir/summary.json" ]; then
  cp "$results_dir/summary.json" "$RUNNER_TEMP/compose-suite-summary.json"
fi
if [ -f "$results_dir/failures.txt" ]; then
  cp "$results_dir/failures.txt" "$RUNNER_TEMP/compose-test-failures"
fi

if [ "$suite_status" -ne 0 ] && [ "$IGNORE_FAILURES" = "true" ] && [ -f "$results_dir/suite-complete" ]; then
  echo "Test failures were reported but are being ignored"
  exit 0
fi

exit "$suite_status"
