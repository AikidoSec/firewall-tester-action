import { Response } from 'express'
import { getAppConfig } from '../zen/config.js'
import { RequestWithAppData } from '../types.js'

export function getConfigHandler(req: RequestWithAppData, res: Response): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'Unauthorized' })
    return
  }

  res.json(getAppConfig(appData))
}
