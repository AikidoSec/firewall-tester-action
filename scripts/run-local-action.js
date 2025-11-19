#!/usr/bin/env node
/**
 * Wrapper script to run local-action with test name support
 * Usage: node scripts/run-local-action.js <env-file> [test-name]
 * Or via npm: npm run local-action-php -- test_name
 */

import { spawn } from 'child_process'

// Get arguments
// First arg is the env file (passed by npm script)
// Remaining args are test names (passed by user via --)
const envFile = process.argv[2]
const testNames = process.argv.slice(3).join(',')

// Set RUN_TESTS environment variable if test names are provided
const env = { ...process.env }
if (testNames) {
  env.RUN_TESTS = testNames
}

// Run the local-action
const proc = spawn(
  'npx',
  ['@github/local-action', '.', 'src/main.ts', envFile],
  {
    stdio: 'inherit',
    env: env,
    shell: true
  }
)

proc.on('close', (code) => {
  process.exit(code || 0)
})

proc.on('error', (err) => {
  console.error('Error running local-action:', err)
  process.exit(1)
})
