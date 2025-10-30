import * as core from '@actions/core'
import { startServer, stopServer } from './coremock/app.js'
import { spawn } from 'child_process'
import path from 'path'

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
    core.debug(`Test timeout: ${test_timeout}`)
    core.debug(`Extra args: ${extra_args}`)
    core.debug(`Extra build args: ${extra_build_args}`)
    core.debug(`App port: ${app_port}`)
    core.debug(`Sleep before test: ${sleep_before_test}`)
    core.debug(`Ignore failures: ${ignore_failures}`)
    core.debug(`Test type: ${test_type}`)
    // Spawn the Python process
    const this_file_dir = path.dirname(new URL(import.meta.url).pathname)
    await new Promise<void>((resolve, reject) => {
      const proc = spawn(
        'python',
        [
          `${this_file_dir}/../server_tests/run_test.py`,
          '--dockerfile_path',
          dockerfile_path,
          '--max_parallel_tests',
          max_parallel_tests.toString(),
          '--config_update_delay',
          config_update_delay.toString(),
          '--skip_tests',
          skip_tests,
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
  const proc = spawn(
    'docker',
    [
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
      '-d',
      'postgres',
      '-c',
      'max_connections=200'
    ],
    {
      stdio: 'inherit'
    }
  )
  console.log(`Started Postgres: ${proc.pid}`)
  // wait for postgres to be ready
  await new Promise((resolve) => {
    setTimeout(resolve, 10000)
  })
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
