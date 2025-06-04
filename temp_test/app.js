require('@aikidosec/firewall')

const express = require('express')
const app = express()
const port = 3001

// Middleware to parse JSON
app.use(express.json())

// Root route
app.get('/', (req, res) => {
  res.send('Welcome to the Express Service!')
})

// Hello route
app.get('/hello', (req, res) => {
  res.json({ message: 'Hello, world!' })
})

// Start the server
const server = app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`)
})

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nReceived SIGINT. Performing graceful shutdown...')
  server.close(() => {
    console.log('Server closed. Exiting process.')
    process.exit(0)
  })
})
