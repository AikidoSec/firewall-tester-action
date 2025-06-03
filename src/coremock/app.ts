import express, { Express } from 'express'
import * as core from '@actions/core'
import { Server } from 'http'
import createApp from './src/handlers/createApp.js'
import { checkToken } from './src/middleware/checkToken.js'
import { getConfig } from './src/handlers/getConfig.js'
import { updateConfig } from './src/handlers/updateConfig.js'
const app: Express = express()
const port = process.env.PORT || 3000
let server: Server | undefined

// Middleware
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

// Routes
app.get('/api/runtime/config', checkToken, getConfig)

//app.post('/api/runtime/config', checkToken, bumpUpdatedAt)

app.put('/api/runtime/config/update', checkToken, updateConfig)

// app.get('/api/runtime/app/events', checkToken, getEvents)

app.post('/api/runtime/apps', createApp)

// Function to start the server
export const startServer = () => {
  server = app.listen(port, () => {
    core.info(`Server is running on port ${port}`)
  })
}

export const stopServer = () => {
  core.info('Stopping server')
  server?.close()
}

export default app
