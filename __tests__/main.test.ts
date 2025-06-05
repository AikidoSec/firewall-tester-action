/**
 * Unit tests for the action's main functionality, src/main.ts
 *
 * To mock dependencies in ESM, you can create fixtures that export mock
 * functions and objects. For example, the core module is mocked in this test,
 * so that the actual '@actions/core' module is not imported.
 */
import { jest } from '@jest/globals'
import * as core from '../__fixtures__/core.js'
import { wait } from '../__fixtures__/wait.js'
import { stopServer, startServer } from '../src/coremock/app.js'

// Mocks should be declared before the module being tested is imported.
jest.unstable_mockModule('@actions/core', () => core)
jest.unstable_mockModule('../src/wait.js', () => ({ wait }))

// The module being tested should be imported dynamically. This ensures that the
// mocks are used in place of any actual dependencies.
const { run } = await import('../src/main.js')

// Helper functions for API calls
const API_BASE_URL = 'http://localhost:3000/api/runtime'

interface AppResponse {
  token: string
}

interface ConfigResponse {
  serviceId: number
  heartbeatIntervalInMS: number
}

async function createApp(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/apps`, {
    method: 'POST',
    body: JSON.stringify({})
  })
  expect(response.status).toBe(200)
  const data = (await response.json()) as AppResponse
  expect(data.token).toBeDefined()
  return data.token
}

async function getConfig(token: string): Promise<ConfigResponse> {
  const response = await fetch(`${API_BASE_URL}/config`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: token
    }
  })
  expect(response.status).toBe(200)
  return response.json() as Promise<ConfigResponse>
}

async function updateConfig(
  token: string,
  heartbeatInterval: number
): Promise<ConfigResponse> {
  const response = await fetch(`${API_BASE_URL}/config/update`, {
    method: 'PUT',
    body: JSON.stringify({ heartbeatIntervalInMS: heartbeatInterval }),
    headers: {
      'Content-Type': 'application/json',
      Authorization: token
    }
  })
  return response.json() as Promise<ConfigResponse>
}

describe('main.ts', () => {
  beforeEach(() => {
    // Set the action's inputs as return values from core.getInput().
    core.getInput.mockImplementation(() => '500')

    // Mock the wait function so that it does not actually wait.
    wait.mockImplementation(() => Promise.resolve('done!'))
  })

  afterEach(() => {
    jest.resetAllMocks()
    stopServer()
  })

  describe('API Integration', () => {
    it('creates a new app and manages configuration', async () => {
      await run()
      startServer()

      // Wait for server to be ready
      await new Promise((resolve) => setTimeout(resolve, 1000))

      // Create app and get token
      const token = await createApp()

      // Get initial config
      const initialConfig = await getConfig(token)
      expect(initialConfig.serviceId).toBe(1)
      expect(initialConfig.heartbeatIntervalInMS).toBe(10 * 60 * 1000)

      // Update config
      const updatedConfig = await updateConfig(token, 1000)
      expect(updatedConfig.heartbeatIntervalInMS).toBe(1000)
    })

    describe('Invalid Token Scenarios', () => {
      beforeEach(async () => {
        await run()
        startServer()
        await new Promise((resolve) => setTimeout(resolve, 1000))
      })

      it('fails to get config with invalid token', async () => {
        const invalidToken = 'invalid-token'
        const response = await fetch(`${API_BASE_URL}/config`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: invalidToken
          }
        })
        expect(response.status).toBe(401)
      })

      it('fails to update config with invalid token', async () => {
        const invalidToken = 'invalid-token'
        const response = await fetch(`${API_BASE_URL}/config/update`, {
          method: 'PUT',
          body: JSON.stringify({ heartbeatIntervalInMS: 1000 }),
          headers: {
            'Content-Type': 'application/json',
            Authorization: invalidToken
          }
        })
        expect(response.status).toBe(401)
      })
    })
  })

  describe('Core Functionality', () => {
    it('Sets the time output', async () => {
      await run()

      // Verify the time output was set.
      expect(core.setOutput).toHaveBeenNthCalledWith(
        1,
        'time',
        // Simple regex to match a time string in the format HH:MM:SS.
        expect.stringMatching(/^\d{2}:\d{2}:\d{2}/)
      )
    })

    it('Sets a failed status when input is invalid', async () => {
      // Clear the getInput mock and return an invalid value.
      core.getInput.mockClear().mockReturnValueOnce('this is not a number')

      // Clear the wait mock and return a rejected promise.
      wait
        .mockClear()
        .mockRejectedValueOnce(new Error('milliseconds is not a number'))

      await run()

      // Verify that the action was marked as failed.
      expect(core.setFailed).toHaveBeenNthCalledWith(
        1,
        'milliseconds is not a number'
      )
    })
  })
})
