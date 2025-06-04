import { Response } from 'express'
import { RequestWithAppData } from '../types.js'
import {
  updateBlockedIPAddresses,
  updateBlockedUserAgents,
  updateAllowedIPAddresses,
  updateMonitoredUserAgents,
  updateMonitoredIPAddresses,
  updateUserAgentDetails
} from '../zen/config.js'

export function updateListsHandler(req: RequestWithAppData, res: Response) {
  if (!req.appData) {
    res.status(400).json({
      message: 'App is missing'
    })
    return
  }

  // Insecure input validation - but this is only a mock server
  if (
    !req.body ||
    typeof req.body !== 'object' ||
    Array.isArray(req.body) ||
    !Object.keys(req.body).length
  ) {
    res.status(400).json({
      message: 'Request body is missing or invalid'
    })
    return
  }

  if (
    !req.body.blockedIPAddresses ||
    !Array.isArray(req.body.blockedIPAddresses)
  ) {
    res.status(400).json({
      message: 'blockedIPAddresses is missing or invalid'
    })
    return
  }

  updateBlockedIPAddresses(req.appData, req.body.blockedIPAddresses)

  if (
    req.body.blockedUserAgents &&
    typeof req.body.blockedUserAgents === 'string'
  ) {
    updateBlockedUserAgents(req.appData, req.body.blockedUserAgents)
  }

  if (
    req.body.allowedIPAddresses &&
    Array.isArray(req.body.allowedIPAddresses)
  ) {
    updateAllowedIPAddresses(req.appData, req.body.allowedIPAddresses)
  }

  if (
    req.body.monitoredUserAgents &&
    typeof req.body.monitoredUserAgents === 'string'
  ) {
    updateMonitoredUserAgents(req.appData, req.body.monitoredUserAgents)
  }

  if (
    req.body.monitoredIPAddresses &&
    Array.isArray(req.body.monitoredIPAddresses)
  ) {
    updateMonitoredIPAddresses(req.appData, req.body.monitoredIPAddresses)
  }

  if (req.body.userAgentDetails && Array.isArray(req.body.userAgentDetails)) {
    updateUserAgentDetails(req.appData, req.body.userAgentDetails)
  }

  res.json({ success: true })
}
