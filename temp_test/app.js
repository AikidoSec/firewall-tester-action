require('@aikidosec/firewall')
const express = require('express')
const fetch = require('node-fetch')
const app = express()
const port = process.env.PORT
const { exec } = require('child_process')

// Middleware to parse JSON
app.use(express.json())

// Root route
app.get('/', (req, res) => {
  res.send('Welcome to the Express Service!')
})

// Hello route
app.get('/somethingVerySpecific', (req, res) => {
  console.log('Endpoint /somethingVerySpecific called')
  res.json({ message: 'Hello, somethingVerySpecific!' })
})

app.get('/test', (req, res) => {
  res.json({ message: 'Hello, test!' })
})

app.post('/shell_injection', (req, res) => {
  console.log('Endpoint /shell_injection called')
  const command = req.body.command
  const fullCommand = `binary --domain www.example${command}.com`
  const result = exec(fullCommand)
  res.json({ message: 'Shell executed!' })
})

// Start the server
const server = app.listen(port, async () => {
  console.log(
    `Server is running at http://localhost:${port} - AIKIDO_ENDPOINT: ${process.env.AIKIDO_ENDPOINT}`
  )
})

app.post('/api/v1/orders', (req, res) => {
  res.json({ message: 'Hello, orders!' })
})

app.get('/api/pets/', (req, res) => {
  res.json([])
})

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nReceived SIGINT. Performing graceful shutdown...')
  server.close(() => {
    console.log('Server closed. Exiting process.')
    process.exit(0)
  })
})
