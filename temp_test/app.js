require('@aikidosec/firewall')
const express = require('express')
const fetch = require('node-fetch')
const app = express()
const port = 3001

// Function to fetch firewall lists
async function getFirewallLists() {
  try {
    const headers = {
      'Content-Type': 'application/json',
      Authorization: `${process.env.AIKIDO_TOKEN}`
    }

    const response = await fetch(
      `${process.env.AIKIDO_ENDPOINT}/api/runtime/firewall/lists`,
      { headers }
    )
    const data = await response.json()
    console.info('Firewall Lists:', data)
  } catch (error) {
    console.error('Error fetching firewall lists:', error)
  }
}

// Middleware to parse JSON
app.use(express.json())

// Root route
app.get('/', (req, res) => {
  res.send('Welcome to the Express Service!')
})

// Hello route
app.get('/somethingVerySpecific', (req, res) => {
  res.json({ message: 'Hello, somethingVerySpecific!' })
})

app.get('/test', (req, res) => {
  res.json({ message: 'Hello, test!' })
})

// Start the server
const server = app.listen(port, async () => {
  console.log(
    `Server is running at http://localhost:${port} - AIKIDO_ENDPOINT: ${process.env.AIKIDO_ENDPOINT}`
  )
  await getFirewallLists()
})

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nReceived SIGINT. Performing graceful shutdown...')
  server.close(() => {
    console.log('Server closed. Exiting process.')
    process.exit(0)
  })
})
