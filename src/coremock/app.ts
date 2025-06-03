import express, { Express, Request, Response } from 'express'
import * as core from '@actions/core'
import { Server } from 'http'
const app: Express = express()
const port = process.env.PORT || 3000
let server: Server | undefined

// Middleware
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

// Routes
app.get('/', (req: Request, res: Response) => {
  res.json({ message: 'Welcome to the Express API' })
})

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok' })
})

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
