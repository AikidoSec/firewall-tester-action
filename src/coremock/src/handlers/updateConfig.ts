import { Request, Response } from 'express'
import { updateAppConfig } from '../zen/config.js'

interface RequestWithAppData extends Request {
  appData?: { id: number; token: string; configUpdatedAt: number }
}

export function updateConfig(req: RequestWithAppData, res: Response): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'Unauthorized' })
    return
  }

  const newConfig = req.body
  const updatedConfig = updateAppConfig(appData, newConfig)
  res.json(updatedConfig)
}
