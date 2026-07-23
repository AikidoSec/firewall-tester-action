import { Response } from 'express'
import { getAppConfig, markAppConfigSent } from '../zen/config.js'
import { RequestWithAppData } from '../types.js'

export function getConfigHandler(req: RequestWithAppData, res: Response): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'Unauthorized' })
    return
  }

  const config = getAppConfig(appData)
  res.on('finish', () => markAppConfigSent(appData, config.configUpdatedAt))
  res.json(config)
}
