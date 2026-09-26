import { Response } from 'express'
import { getAppConfig, updateAppConfig } from '../zen/config.js'
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

  const success = updateAppConfig(appData, newConfig)
  res.json({
    success,
    configUpdatedAt: getAppConfig(appData).configUpdatedAt
  })
}
