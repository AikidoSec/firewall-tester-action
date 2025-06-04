import { Response } from 'express'
import { RequestWithAppData } from '../types.js'
import { captureEvent, listEvents } from '../zen/events.js'

export function captureEventHandler(
  req: RequestWithAppData,
  res: Response
): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'App is missing' })
    return
  }
  const event = req.body
  captureEvent(event, appData)

  if (event.type === 'detected_attack') {
    res.json({
      success: true
    })
    return
  }

  res.json(listEvents(appData))
}
