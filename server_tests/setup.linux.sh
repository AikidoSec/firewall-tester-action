#!/bin/sh
set -eu

case "$TEST_NAME" in
  *[!A-Za-z0-9-]*|""|test|control-test)
    echo "Invalid TEST_NAME: $TEST_NAME" >&2
    exit 1
    ;;
  test-*|control-test-*) ;;
  *)
    echo "Invalid TEST_NAME: $TEST_NAME" >&2
    exit 1
    ;;
esac

test_dir="/workspace/server_tests/$TEST_NAME"
test -f "$test_dir/test.py"

echo "Preparing database for $TEST_NAME"
if ! psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$TEST_NAME'" | grep -q 1; then
  createdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$TEST_NAME"
fi

echo "Registering core app token"
curl -fsS \
  -H "Content-Type: application/json" \
  --data "{\"token\":\"$TEST_TOKEN\"}" \
  "$CORE_URL/api/runtime/apps" >/dev/null

if [ -f "$test_dir/start_config.json" ]; then
  echo "Uploading runtime config"
  curl -fsS \
    -H "Authorization: $TEST_TOKEN" \
    -H "Content-Type: application/json" \
    --data-binary "@$test_dir/start_config.json" \
    "$CORE_URL/api/runtime/config" >/dev/null
fi

if [ -f "$test_dir/start_firewall.json" ]; then
  echo "Uploading firewall lists"
  curl -fsS \
    -H "Authorization: $TEST_TOKEN" \
    -H "Content-Type: application/json" \
    --data-binary "@$test_dir/start_firewall.json" \
    "$CORE_URL/api/runtime/firewall/lists" >/dev/null
fi

echo "Validating core app token"
curl -fsS "$CORE_URL/api/runtime/events" -H "Authorization: $TEST_TOKEN" >/dev/null

echo "Setup completed for $TEST_NAME"
