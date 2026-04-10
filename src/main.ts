import * as core from '@actions/core'
import { startServer, stopServer } from './coremock/app.js'
import { spawn } from 'child_process'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

// Handle process termination signals
process.on('SIGINT', () => {
  console.log('\nReceived SIGINT. Cleaning up...')
  stopServer()
  stopPostgres()
  process.exit(0)
})

process.on('SIGTERM', () => {
  console.log('\nReceived SIGTERM. Cleaning up...')
  stopServer()
  stopPostgres()
  process.exit(0)
})

export async function run(): Promise<void> {
  try {
    // Start the Express server
    await startPostgres()
    startServer()
    const dockerfile_path: string = core.getInput('dockerfile_path')
    const max_parallel_tests: number = parseInt(
      core.getInput('max_parallel_tests')
    )
    const config_update_delay: number = parseInt(
      core.getInput('config_update_delay')
    )
    const skip_tests: string = core.getInput('skip_tests')
    const run_tests: string =
      core.getInput('run_tests') || process.env.RUN_TESTS || ''
    const test_timeout: number = parseInt(core.getInput('test_timeout'))
    const extra_args: string = core.getInput('extra_args')
    const extra_build_args: string = core.getInput('extra_build_args')
    const app_port: number = parseInt(core.getInput('app_port'))
    const sleep_before_test: number = parseInt(
      core.getInput('sleep_before_test')
    )
    const ignore_failures: boolean = core.getInput('ignore_failures') === 'true'
    const test_type: string = core.getInput('test_type')
    if (!['server', 'control'].includes(test_type)) {
      core.setFailed(
        `Invalid test type: ${test_type} Must be one of: server, control`
      )
      return
    }

    core.debug(`Dockerfile path: ${dockerfile_path}`)
    core.debug(`Max parallel tests: ${max_parallel_tests}`)
    core.debug(`Config update delay: ${config_update_delay}`)
    core.debug(`Skip tests: ${skip_tests}`)
    core.debug(`Run tests: ${run_tests}`)
    core.debug(`Test timeout: ${test_timeout}`)
    core.debug(`Extra args: ${extra_args}`)
    core.debug(`Extra build args: ${extra_build_args}`)
    core.debug(`App port: ${app_port}`)
    core.debug(`Sleep before test: ${sleep_before_test}`)
    core.debug(`Ignore failures: ${ignore_failures}`)
    core.debug(`Test type: ${test_type}`)
    // Spawn the Python process
    const this_file_dir = path.dirname(fileURLToPath(import.meta.url))
    const run_test_path = path.resolve(
      this_file_dir,
      '..',
      'server_tests',
      'run_test.py'
    )
    await new Promise<void>((resolve, reject) => {
      const proc = spawn(
        'python',
        [
          run_test_path,
          '--dockerfile_path',
          dockerfile_path,
          '--max_parallel_tests',
          max_parallel_tests.toString(),
          '--config_update_delay',
          config_update_delay.toString(),
          '--skip_tests',
          skip_tests,
          '--run_tests',
          run_tests,
          '--test_timeout',
          test_timeout.toString(),
          '--extra_args',
          extra_args,
          '--extra_build_args',
          extra_build_args,
          '--app_port',
          app_port.toString(),
          '--sleep_before_test',
          sleep_before_test.toString(),
          '--ignore_failures',
          ignore_failures.toString(),
          '--test_type',
          test_type
        ],
        {
          stdio: 'inherit'
        }
      )

      proc.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`run_test.py exited with code ${code}`))
        } else {
          resolve()
        }
      })

      proc.on('error', (err) => {
        reject(err)
      })
    })
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  } finally {
    stopServer()
    stopPostgres()
  }
}

async function startPostgres() {
  // if os is windows
  // docker run --rm --name postgres -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_USER=myuser -e POSTGRES_DB=mydb -p 5432:5432 -d --isolation process innovesys/postgresql-windows:latest -c max_connections=200
  const dockerArgs = [
    'run',
    '--rm',
    '--name',
    'postgres',
    '-e',
    'POSTGRES_PASSWORD=mysecretpassword',
    '-e',
    'POSTGRES_USER=myuser',
    '-e',
    'POSTGRES_DB=mydb',
    '-p',
    '5432:5432',
    '-d'
  ]

  if (process.platform === 'win32') {
    const thisFileDir = path.dirname(fileURLToPath(import.meta.url))
    const srcDir = path.resolve(thisFileDir, '..', 'src')
    const windowsEntrypointPath = path.join(
      srcDir,
      'windows-postgres-entrypoint.ps1'
    )

    if (!fs.existsSync(windowsEntrypointPath)) {
      throw new Error(
        `Windows Postgres entrypoint not found: ${windowsEntrypointPath}`
      )
    }

    dockerArgs.push(
      '--mount',
      `type=bind,source=${srcDir},target=C:\\action-src,readonly`,
      '--entrypoint',
      'pwsh',
      '--isolation',
      'process',
      'innovesys/postgresql-windows:latest',
      '-NoLogo',
      '-NoProfile',
      '-File',
      'C:\\action-src\\windows-postgres-entrypoint.ps1'
    )
  } else {
    dockerArgs.push('postgres')
    dockerArgs.push('-c', 'max_connections=200')
  }

  const proc = spawn('docker', dockerArgs, {
    stdio: 'inherit'
  })
  console.log(`Started Postgres: ${proc.pid}`)
  await waitForPostgresReady()
  proc.on('close', (code) => {
    if (code !== 0) {
      core.setFailed(`Failed to start Postgres: ${code}`)
    }
  })
  proc.on('error', (err) => {
    core.setFailed(`Failed to start Postgres: ${err}`)
  })
  proc.on('exit', (code) => {
    if (code !== 0) {
      core.setFailed(`Failed to start Postgres: ${code}`)
    }
  })
  proc.on('message', (msg) => {
    console.log(`Postgres: ${msg}`)
  })
}

async function waitForPostgresReady() {
  const readyCommand =
    process.platform === 'win32'
      ? [
          'exec',
          'postgres',
          'C:\\pgsql\\bin\\pg_isready.exe',
          '-U',
          'myuser',
          '-h',
          '127.0.0.1',
          '-p',
          '5432'
        ]
      : ['exec', 'postgres', 'pg_isready', '-U', 'myuser', '-h', '127.0.0.1', '-p', '5432']

  for (let attempt = 0; attempt < 60; attempt += 1) {
    const result = await new Promise<number>((resolve) => {
      const proc = spawn('docker', readyCommand, { stdio: 'ignore' })
      proc.on('close', (code) => resolve(code ?? 1))
      proc.on('error', () => resolve(1))
    })

    if (result === 0) {
      return
    }

    await new Promise((resolve) => {
      setTimeout(resolve, 1000)
    })
  }

  throw new Error('Postgres did not become ready after 60 seconds')
}

function stopPostgres() {
  const proc = spawn('docker', ['stop', 'postgres'], {
    stdio: 'inherit'
  })
  proc.on('close', (code) => {
    if (code !== 0) {
      core.warning(`Failed to stop Postgres: ${code}`)
    }
  })
}
