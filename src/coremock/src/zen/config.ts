import { AppData } from '../types.js'

const configs: {
  success: boolean
  serviceId: number
  configUpdatedAt: number
  heartbeatIntervalInMS: number
  endpoints: unknown[]
  blockedUserIds: number[]
  allowedIPAddresses: string[]
  receivedAnyStats: boolean
  block: boolean
}[] = []

function generateConfig(app: AppData) {
  return {
    success: true,
    serviceId: app.id,
    configUpdatedAt: app.configUpdatedAt,
    heartbeatIntervalInMS: 10 * 60 * 1000,
    endpoints: [],
    blockedUserIds: [],
    allowedIPAddresses: [],
    receivedAnyStats: true,
    block: false
  }
}

export function getAppConfig(app: AppData) {
  const existingConf = configs.find((config) => config.serviceId === app.id)
  if (existingConf) {
    return existingConf
  }
  const newConf = generateConfig(app)
  configs.push(newConf)
  return newConf
}

export function updateAppConfig(
  app: AppData,
  newConfig: any // eslint-disable-line @typescript-eslint/no-explicit-any
) {
  let index = configs.findIndex((config) => config.serviceId === app.id)
  if (index === -1) {
    getAppConfig(app)
    index = configs.length - 1
  }
  configs[index] = {
    ...configs[index],
    ...newConfig,
    configUpdatedAt: Date.now()
  }
  return true
}

const blockedIPAddresses: { serviceId: number; ipAddresses: string[] }[] = []
const allowedIPAddresses: { serviceId: number; ipAddresses: string[] }[] = []
const blockedUserAgents: { serviceId: number; userAgents: string }[] = []

const monitoredUserAgents: { serviceId: number; userAgents: string }[] = []
const monitoredIPAddresses: { serviceId: number; ipAddresses: string[] }[] = []
const userAgentDetails: { serviceId: number; userAgents: string[] }[] = []

export function updateBlockedIPAddresses(app: AppData, ips: string[]) {
  let entry = blockedIPAddresses.find((ip) => ip.serviceId === app.id)

  if (entry) {
    entry.ipAddresses = ips
  } else {
    entry = { serviceId: app.id, ipAddresses: ips }
    blockedIPAddresses.push(entry)
  }

  // Bump lastUpdatedAt
  updateAppConfig(app, {})
}

export function getBlockedIPAddresses(app: AppData) {
  const entry = blockedIPAddresses.find((ip) => ip.serviceId === app.id)

  if (entry) {
    return entry.ipAddresses
  }

  return []
}

export function updateAllowedIPAddresses(app: AppData, ips: string[]) {
  let entry = allowedIPAddresses.find((ip) => ip.serviceId === app.id)

  if (entry) {
    entry.ipAddresses = ips
  } else {
    entry = { serviceId: app.id, ipAddresses: ips }
    allowedIPAddresses.push(entry)
  }

  // Bump lastUpdatedAt
  updateAppConfig(app, {})
}

export function getAllowedIPAddresses(app: AppData) {
  const entry = allowedIPAddresses.find((ip) => ip.serviceId === app.id)

  if (entry) {
    return entry.ipAddresses
  }

  return []
}

export function updateBlockedUserAgents(app: AppData, uas: string) {
  let entry = blockedUserAgents.find((e) => e.serviceId === app.id)

  if (entry) {
    entry.userAgents = uas
  } else {
    entry = { serviceId: app.id, userAgents: uas }
    blockedUserAgents.push(entry)
  }

  // Bump lastUpdatedAt
  updateAppConfig(app, {})
}

export function getBlockedUserAgents(app: AppData) {
  const entry = blockedUserAgents.find((e) => e.serviceId === app.id)

  if (entry) {
    return entry.userAgents
  }

  return ''
}

export function updateMonitoredUserAgents(app: AppData, uas: string) {
  let entry = monitoredUserAgents.find((e) => e.serviceId === app.id)

  if (entry) {
    entry.userAgents = uas
  } else {
    entry = { serviceId: app.id, userAgents: uas }
    monitoredUserAgents.push(entry)
  }

  // Bump lastUpdatedAt
  updateAppConfig(app, {})
}

export function getMonitoredUserAgents(app: AppData) {
  const entry = monitoredUserAgents.find((e) => e.serviceId === app.id)

  if (entry) {
    return entry.userAgents
  }

  return ''
}

export function updateMonitoredIPAddresses(app: AppData, ips: string[]) {
  let entry = monitoredIPAddresses.find((e) => e.serviceId === app.id)

  if (entry) {
    entry.ipAddresses = ips
  } else {
    entry = { serviceId: app.id, ipAddresses: ips }
    monitoredIPAddresses.push(entry)
  }

  // Bump lastUpdatedAt
  updateAppConfig(app, {})
}

export function getMonitoredIPAddresses(app: AppData) {
  const entry = monitoredIPAddresses.find((e) => e.serviceId === app.id)

  if (entry) {
    return entry.ipAddresses
  }

  return []
}

export function updateUserAgentDetails(app: AppData, uas: string[]) {
  let entry = userAgentDetails.find((e) => e.serviceId === app.id)

  if (entry) {
    entry.userAgents = uas
  } else {
    entry = { serviceId: app.id, userAgents: uas }
    userAgentDetails.push(entry)
  }

  // Bump lastUpdatedAt
  updateAppConfig(app, {})
}

export function getUserAgentDetails(app: AppData) {
  const entry = userAgentDetails.find((e) => e.serviceId === app.id)

  if (entry) {
    return entry.userAgents
  }

  return []
}
