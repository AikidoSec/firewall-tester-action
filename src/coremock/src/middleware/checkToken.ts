import { Request, Response, NextFunction } from 'express'
import { getByToken } from '../zen/apps.js'
import * as core from '@actions/core'
// Augment Express Request type
interface RequestWithAppData extends Request {
  appData?: { id: number; token: string; configUpdatedAt: number }
}

// list of those tokens that are down
const downTokens = new Set<string>()
export function setTokenDown(token: string) {
  downTokens.add(token)
}

export function setTokenUp(token: string) {
  downTokens.delete(token)
}

export function checkToken(
  req: RequestWithAppData,
  res: Response,
  next: NextFunction
): void {
  const token = req.headers['authorization']
  core.info(
    `Token: ${token?.substring(0, 15)}... for ${req.url} method ${req.method} ${downTokens.has(token ?? '') ? 'DOWN' : 'UP'}`
  )
  if (downTokens.has(token ?? '')) {
    res.status(503).json({ message: 'Service is down' })
    return
  }

  if (!token) {
    res.status(401).json({
      message: 'Token is required'
    })
    return
  }

  const app = getByToken(token)
  if (!app) {
    res.status(401).json({ message: 'Invalid token' })
    return
  }

  req.appData = app
  next()
}
