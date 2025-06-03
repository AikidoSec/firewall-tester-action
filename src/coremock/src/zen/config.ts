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
  return configs[index]
}
