import { Request, Response, NextFunction } from 'express'
import { getByToken } from '../zen/apps.js'
import * as core from '@actions/core'
// Augment Express Request type
interface RequestWithAppData extends Request {
  appData?: { id: number; token: string; configUpdatedAt: number }
}

export function checkToken(
  req: RequestWithAppData,
  res: Response,
  next: NextFunction
): void {
  const token = req.headers['authorization']
  core.info(`Token: ${token} for ${req.url} method ${req.method}`)
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
