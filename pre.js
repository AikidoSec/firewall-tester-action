const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

async function run() {
  try {
    // Check if requirements.txt exists
    const requirementsPath = path.join(process.cwd(), 'requirements.txt')
    if (!fs.existsSync(requirementsPath)) {
      console.log('No requirements.txt file found')
      return
    }

    // Install requirements
    console.log('Installing Python requirements...')
    execSync('pip install -r requirements.txt', { stdio: 'inherit' })
    console.log('Requirements installed successfully')
  } catch (error) {
    console.error('Error installing requirements:', error)
    process.exit(1)
  }
}

run()
