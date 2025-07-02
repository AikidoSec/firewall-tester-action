import { Response } from 'express'
import { updateAppConfig } from '../zen/config.js'
import { RequestWithAppData } from '../types.js'

export function updateConfigHandler(
  req: RequestWithAppData,
  res: Response
): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'Unauthorized' })
    return
  }

  const newConfig = req.body

  res.json({ success: updateAppConfig(appData, newConfig) })
}
