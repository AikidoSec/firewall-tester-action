import { Response } from 'express'
import { RequestWithAppData } from '../types.js'
import { getAppConfig } from '../zen/config.js'

export function realtimeConfigHandler(
  req: RequestWithAppData,
  res: Response
): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'Unauthorized' })
    return
  }

  const config = getAppConfig(appData)

  res.json({
    serviceId: appData.id,
    configUpdatedAt: config.configUpdatedAt
  })
}
