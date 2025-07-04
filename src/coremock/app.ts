import express, { Express } from 'express'
import * as core from '@actions/core'
import { Server } from 'http'
import createApp from './src/handlers/createApp.js'
import { checkToken } from './src/middleware/checkToken.js'
import { getConfigHandler } from './src/handlers/getConfig.js'
import { updateConfigHandler } from './src/handlers/updateConfig.js'
import { realtimeConfigHandler } from './src/handlers/realtimeConfig.js'
import { listEventsHandler } from './src/handlers/listEvents.js'
import { captureEventHandler } from './src/handlers/captureEvent.js'
import { listsHandler } from './src/handlers/listsHandler.js'
import { updateListsHandler } from './src/handlers/updateListsHandler.js'

const app: Express = express()
const port = process.env.PORT || 3000
let server: Server | undefined

// Middleware
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

// Routes
app.get('/api/runtime/config', checkToken, getConfigHandler)
app.post('/api/runtime/config', checkToken, updateConfigHandler)

app.get('/config', checkToken, realtimeConfigHandler)

app.get('/api/runtime/events', checkToken, listEventsHandler)
app.post('/api/runtime/events', checkToken, captureEventHandler)

app.get('/api/runtime/firewall/lists', checkToken, listsHandler)
app.post('/api/runtime/firewall/lists', checkToken, updateListsHandler)

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
