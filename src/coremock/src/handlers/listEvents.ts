import { Response } from 'express'
import { RequestWithAppData } from '../types.js'
import { listEvents } from '../zen/events.js'

export function listEventsHandler(
  req: RequestWithAppData,
  res: Response
): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'App is missing' })
    return
  }
  const events = listEvents(appData)
  res.json(events)
}
