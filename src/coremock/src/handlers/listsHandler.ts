import { Response } from 'express'
import { RequestWithAppData } from '../types.js'
import {
  getAllowedIPAddresses,
  getBlockedIPAddresses,
  getBlockedUserAgents,
  getMonitoredIPAddresses,
  getMonitoredUserAgents,
  getUserAgentDetails
} from '../zen/config.js'

export function listsHandler(req: RequestWithAppData, res: Response) {
  if (!req.appData) {
    throw new Error('App is missing')
  }

  const blockedIps = getBlockedIPAddresses(req.appData)
  const blockedUserAgents = getBlockedUserAgents(req.appData)
  const allowedIps = getAllowedIPAddresses(req.appData)
  const monitoredUserAgents = getMonitoredUserAgents(req.appData)
  const monitoredIps = getMonitoredIPAddresses(req.appData)
  const userAgentDetails = getUserAgentDetails(req.appData)

  res.json({
    success: true,
    serviceId: req.appData.id,
    blockedIPAddresses:
      blockedIps.length > 0
        ? [
            {
              key: 'geoip/Belgium;BE',
              source: 'geoip',
              description: 'geo restrictions',
              ips: blockedIps
            }
          ]
        : [],
    blockedUserAgents: blockedUserAgents,
    monitoredUserAgents: monitoredUserAgents,
    userAgentDetails: userAgentDetails,
    allowedIPAddresses:
      allowedIps.length > 0
        ? [
            {
              key: 'geoip/Belgium;BE',
              source: 'geoip',
              description: 'geo restrictions',
              ips: allowedIps
            }
          ]
        : [],
    monitoredIPAddresses:
      monitoredIps.length > 0
        ? monitoredIps
        : [
            {
              key: 'geoip/Belgium;BE',
              source: 'geoip',
              description: 'geo restrictions',
              ips: monitoredIps
            }
          ]
  })
}
