@echo off
setlocal EnableExtensions

set "CURL_RETRY_OPTIONS=--retry 10 --retry-delay 2 --retry-max-time 60 --retry-all-errors"
set "TEST_DIR=C:\workspace\server_tests\%TEST_NAME%"
set "IS_VALID_TEST_NAME="

if "%TEST_NAME%"=="" (
  echo Invalid TEST_NAME: %TEST_NAME%
  exit /b 1
)

if /I "%TEST_NAME:~0,5%"=="test-" set "IS_VALID_TEST_NAME=1"
if /I "%TEST_NAME:~0,13%"=="control-test-" set "IS_VALID_TEST_NAME=1"
if not defined IS_VALID_TEST_NAME (
  echo Invalid TEST_NAME: %TEST_NAME%
  exit /b 1
)
if not "%TEST_NAME:\=%"=="%TEST_NAME%" (
  echo Invalid TEST_NAME: %TEST_NAME%
  exit /b 1
)
if not "%TEST_NAME:/=%"=="%TEST_NAME%" (
  echo Invalid TEST_NAME: %TEST_NAME%
  exit /b 1
)
if not "%TEST_NAME:..=%"=="%TEST_NAME%" (
  echo Invalid TEST_NAME: %TEST_NAME%
  exit /b 1
)

if not exist "%TEST_DIR%\test.py" (
  echo Unknown test: %TEST_NAME%
  exit /b 1
)

echo %POSTGRES_USER%| findstr /R /C:"^[A-Za-z_][A-Za-z0-9_]*$" >nul
if errorlevel 1 (
  echo Invalid POSTGRES_USER: %POSTGRES_USER%
  exit /b 1
)
if not "%POSTGRES_PASSWORD:'=%"=="%POSTGRES_PASSWORD%" (
  echo POSTGRES_PASSWORD cannot contain single quotes
  exit /b 1
)

set "PGPASSWORD=%POSTGRES_ADMIN_PASSWORD%"

echo Preparing database role %POSTGRES_USER%
psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U %POSTGRES_ADMIN_USER% -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = '%POSTGRES_USER%'" | findstr /R "1" >nul
if errorlevel 1 (
  psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U %POSTGRES_ADMIN_USER% -d postgres -v ON_ERROR_STOP=1 -c "CREATE ROLE %POSTGRES_USER% WITH LOGIN PASSWORD '%POSTGRES_PASSWORD%'"
) else (
  psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U %POSTGRES_ADMIN_USER% -d postgres -v ON_ERROR_STOP=1 -c "ALTER ROLE %POSTGRES_USER% WITH LOGIN PASSWORD '%POSTGRES_PASSWORD%'"
)
if errorlevel 1 (
  echo Failed to prepare database role: %POSTGRES_USER%
  exit /b 1
)

echo Preparing database for %TEST_NAME%
createdb -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U %POSTGRES_ADMIN_USER% -O %POSTGRES_USER% %TEST_NAME%
if errorlevel 1 (
  call :check_database_exists
  if errorlevel 1 exit /b 1
)

call :check_database_exists
if errorlevel 1 exit /b 1

echo Registering core app token
> "%TEMP%\app.json" echo {"token":"%TEST_TOKEN%"}
curl.exe -fsS %CURL_RETRY_OPTIONS% -X POST "%CORE_URL%/api/runtime/apps" -H "Content-Type: application/json" --data-binary "@%TEMP%\app.json" >nul
if errorlevel 1 (
  echo Failed to create core app token
  exit /b 1
)

if exist "%TEST_DIR%\start_config.json" (
  echo Uploading runtime config
  curl.exe -fsS %CURL_RETRY_OPTIONS% -X POST "%CORE_URL%/api/runtime/config" -H "Authorization: %TEST_TOKEN%" -H "Content-Type: application/json" --data-binary "@%TEST_DIR%\start_config.json" >nul
  if errorlevel 1 (
    echo Failed to upload runtime config
    exit /b 1
  )
)

if exist "%TEST_DIR%\start_firewall.json" (
  echo Uploading firewall lists
  curl.exe -fsS %CURL_RETRY_OPTIONS% -X POST "%CORE_URL%/api/runtime/firewall/lists" -H "Authorization: %TEST_TOKEN%" -H "Content-Type: application/json" --data-binary "@%TEST_DIR%\start_firewall.json" >nul
  if errorlevel 1 (
    echo Failed to upload firewall lists
    exit /b 1
  )
)

echo Validating core app token
curl.exe -fsS %CURL_RETRY_OPTIONS% "%CORE_URL%/api/runtime/events" -H "Authorization: %TEST_TOKEN%" >nul
if errorlevel 1 (
  echo Core token validation failed
  exit /b 1
)

echo Setup completed for %TEST_NAME%
exit /b 0

:check_database_exists
psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U %POSTGRES_ADMIN_USER% -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '%TEST_NAME%'" | findstr /R "1" >nul
if errorlevel 1 (
  echo Database was not created: %TEST_NAME%
  exit /b 1
)

exit /b 0
