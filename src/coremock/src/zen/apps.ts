import { randomInt, timingSafeEqual } from 'crypto'
import { AppData } from '../types.js'

const apps: AppData[] = []

let id = 1
export function createZenApp(token?: string): string {
  const appId = id++
  const appToken = token ?? `AIK_RUNTIME_1_${appId}_${generateRandomString(48)}`
  const app = {
    id: appId,
    token: appToken,
    configUpdatedAt: Date.now()
  }

  apps.push(app)

  return appToken
}

export function getByToken(token: string) {
  return apps.find((app) => {
    if (app.token.length !== token.length) {
      return false
    }

    return timingSafeEqual(Buffer.from(app.token), Buffer.from(token))
  })
}

function generateRandomString(length: number) {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
  const size = chars.length
  let str = ''

  for (let i = 0; i < length; i++) {
    const randomIndex = randomInt(0, size)
    str += chars[randomIndex]
  }

  return str
}
