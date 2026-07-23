import { Response } from 'express'
import { RequestWithAppData } from '../types.js'
import { getAppConfigDelivery } from '../zen/config.js'

export function getConfigDeliveryHandler(
  req: RequestWithAppData,
  res: Response
): void {
  const appData = req.appData
  if (!appData) {
    res.status(401).json({ message: 'Unauthorized' })
    return
  }

  res.json(getAppConfigDelivery(appData))
}
