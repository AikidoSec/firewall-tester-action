import * as core from '@actions/core'
import { wait } from './wait.js'
import { startServer, stopServer } from './coremock/app.js'
import { spawn } from 'child_process'

export async function run(): Promise<void> {
  try {
    // Start the Express server
    startServer()

    const dockerfile_path: string = core.getInput('dockerfile_path')
    const max_parallel_tests: number = parseInt(
      core.getInput('max_parallel_tests')
    )

    core.debug(`Dockerfile path: ${dockerfile_path}`)
    core.debug(`Max parallel tests: ${max_parallel_tests}`)

    await wait(1000)

    // Spawn the Python process
    await new Promise<void>((resolve, reject) => {
      const proc = spawn(
        'python',
        [
          './server_tests/run_test.py',
          '--dockerfile_path',
          dockerfile_path,
          '--max_parallel_tests',
          max_parallel_tests.toString()
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
  }
}
