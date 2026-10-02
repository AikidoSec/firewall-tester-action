import { Response } from 'express'
import { RequestWithAppData } from '../types.js'
import { captureEvent } from '../zen/events.js'
import { getAppConfig, markAppConfigSent } from '../zen/config.js'

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
  captureEvent(event, appData, {
    'X-Agent-Platform': req.get('X-Agent-Platform') ?? null,
    'X-Agent-Version': req.get('X-Agent-Version') ?? null,
    'X-Agent-Hostname': req.get('X-Agent-Hostname') ?? null,
    'X-Agent-IP-Address': req.get('X-Agent-IP-Address') ?? null,
    'X-Agent-Session-Id': req.get('X-Agent-Session-Id') ?? null
  })

  if (event.type === 'detected_attack') {
    res.json({
      success: true
    })
    return
  }

  const config = getAppConfig(appData)
  res.on('finish', () => markAppConfigSent(appData, config.configUpdatedAt))
  res.json(config)
}
