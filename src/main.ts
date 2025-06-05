import * as core from '@actions/core'
import { wait } from './wait.js'
import { startServer, stopServer } from './coremock/app.js'

/**
 * The main function for the action.
 *
 * @returns Resolves when the action is complete.
 */
export async function run(): Promise<void> {
  try {
    // Start the Express server
    startServer()

    const dockerfile_path: string = core.getInput('dockerfile_path')

    // Debug logs are only output if the `ACTIONS_STEP_DEBUG` secret is true
    core.debug(`Dockerfile path: ${dockerfile_path}`)

    // Log the current timestamp, wait, then log the new timestamp
    core.debug(new Date().toTimeString())
    await wait(1000)
    core.debug(new Date().toTimeString())

    // Set outputs for other workflow steps to use
    core.setOutput('time', new Date().toTimeString())
    // stop the server
    stopServer()
  } catch (error) {
    // Fail the workflow run if an error occurs
    if (error instanceof Error) core.setFailed(error.message)
  }
}
