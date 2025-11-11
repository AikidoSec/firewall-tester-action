import { Request, Response, NextFunction } from 'express'
import { getByToken } from '../zen/apps.js'
import * as core from '@actions/core'
import {
  isTokenDown,
  isTokenTimeout,
  addTokenTimeout
} from '../handlers/coreDown.js'
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
  core.info(
    `Token: ${token?.substring(0, 15)}... for ${req.url} method ${req.method} ${isTokenDown(token ?? '') ? 'DOWN' : 'UP'}`
  )
  if (isTokenDown(token ?? '')) {
    res.status(503).json({ message: 'Service is down' })
    return
  }
  if (isTokenTimeout(token ?? '')) {
    const t = setTimeout(
      () => {
        res.status(500).json({ message: 'Service is timeout' })
      },
      3 * 60 * 1000
    )
    addTokenTimeout(token ?? '', t)
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
