import { randomInt, timingSafeEqual } from 'crypto'

const apps: { id: number; token: string; configUpdatedAt: number }[] = []

let id = 1
export function createZenApp(): string {
  const appId = id++
  const token = `AIK_RUNTIME_1_${appId}_${generateRandomString(48)}`
  const app = {
    id: appId,
    token: token,
    configUpdatedAt: Date.now()
  }

  apps.push(app)

  return token
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
