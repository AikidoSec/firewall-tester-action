import * as core from '@actions/core'
import { startServer, stopServer } from './coremock/app.js'
import { spawn } from 'child_process'

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
    startPostgres()
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

    core.debug(`Dockerfile path: ${dockerfile_path}`)
    core.debug(`Max parallel tests: ${max_parallel_tests}`)
    core.debug(`Skip tests: ${skip_tests}`)
    core.debug(`Test timeout: ${test_timeout}`)
    core.debug(`Extra args: ${extra_args}`)
    core.debug(`Extra build args: ${extra_build_args}`)
    core.debug(`App port: ${app_port}`)
    core.debug(`Sleep before test: ${sleep_before_test}`)
    // Spawn the Python process
    await new Promise<void>((resolve, reject) => {
      const proc = spawn(
        'python',
        [
          './server_tests/run_test.py',
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
          sleep_before_test.toString()
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

    core.setOutput('time', new Date().toTimeString())
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  } finally {
    stopServer()
    stopPostgres()
  }
}

function startPostgres() {
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
      'postgres'
    ],
    {
      stdio: 'inherit'
    }
  )
  proc.on('close', (code) => {
    if (code !== 0) {
      core.setFailed(`Failed to start Postgres: ${code}`)
    }
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
