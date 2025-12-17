# dotenv-linter:off IncorrectDelimiter

# Do not commit your actual .env file to Git! This may contain secrets or other
# private information.

# Enable/disable step debug logging (default: `false`). For local debugging, it
# may be useful to set it to `true`.
ACTIONS_STEP_DEBUG=true

# GitHub Actions inputs should follow `INPUT_<name>` format (case-sensitive).
# Hyphens should not be converted to underscores!
INPUT_DOCKERFILE_PATH=zen-demo/zen-demo-php/Dockerfile
INPUT_MAX_PARALLEL_TEST=5
INPUT_CONFIG_UPDATE_DELAY=120
INPUT_SKIP_TESTS=test1
INPUT_TEST_TIMEOUT=900
INPUT_EXTRA_ARGS="--env-file=./zen-demo/zen-demo-php/.env.example -e APP_KEY=base64:W2v6u6VR4lURkxuMT9xZ6pdhXSt5rxsmWTbd1HGqlIM="
INPUT_EXTRA_BUILD_ARGS="--build-arg PHP_FIREWALL_VERSION=1.0.125"
INPUT_APP_PORT=8080
INPUT_SLEEP_BEFORE_TEST=20
INPUT_TEST_TYPE=server


# GitHub Actions default environment variables. These are set for every run of a
# workflow and can be used in your actions. Setting the value here will override
# any value set by the local-action tool.
# https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables

# CI="true"
# GITHUB_ACTION=""
# GITHUB_ACTION_PATH=""
# GITHUB_ACTION_REPOSITORY=""
# GITHUB_ACTIONS=""
# GITHUB_ACTOR=""
# GITHUB_ACTOR_ID=""
# GITHUB_API_URL=""
# GITHUB_BASE_REF=""
# GITHUB_ENV=""
# GITHUB_EVENT_NAME=""
# GITHUB_EVENT_PATH=""
# GITHUB_GRAPHQL_URL=""
# GITHUB_HEAD_REF=""
# GITHUB_JOB=""
# GITHUB_OUTPUT=""
# GITHUB_PATH=""
# GITHUB_REF=""
# GITHUB_REF_NAME=""
# GITHUB_REF_PROTECTED=""
# GITHUB_REF_TYPE=""
# GITHUB_REPOSITORY=""
# GITHUB_REPOSITORY_ID=""
# GITHUB_REPOSITORY_OWNER=""
# GITHUB_REPOSITORY_OWNER_ID=""
# GITHUB_RETENTION_DAYS=""
# GITHUB_RUN_ATTEMPT=""
# GITHUB_RUN_ID=""
# GITHUB_RUN_NUMBER=""
# GITHUB_SERVER_URL=""
# GITHUB_SHA=""
# GITHUB_STEP_SUMMARY=""
# GITHUB_TRIGGERING_ACTOR=""
# GITHUB_WORKFLOW=""
# GITHUB_WORKFLOW_REF=""
# GITHUB_WORKFLOW_SHA=""
# GITHUB_WORKSPACE=""
# RUNNER_ARCH=""
# RUNNER_DEBUG=""
# RUNNER_NAME=""
# RUNNER_OS=""
# RUNNER_TEMP=""
# RUNNER_TOOL_CACHE=""
