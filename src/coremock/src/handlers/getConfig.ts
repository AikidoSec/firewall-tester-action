import { Request, Response } from 'express'
import { getAppConfig } from '../zen/config.js'

interface RequestWithAppData extends Request {
  appData?: { id: number; token: string; configUpdatedAt: number }
}

export function getConfig(req: RequestWithAppData, res: Response): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'Unauthorized' })
    return
  }

  res.json(getAppConfig(appData))
}
