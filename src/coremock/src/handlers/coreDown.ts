import { Request, Response } from 'express'

const downTokens = new Set<string>()
const timeoutTokens = new Set<string>()
const timeoutTimeouts = new Map<string, NodeJS.Timeout>()

export function setTokenDown(token: string) {
  downTokens.add(token)
}

export function setTokenUp(token: string) {
  downTokens.delete(token)
  timeoutTokens.delete(token)
  clearTimeout(timeoutTimeouts.get(token) ?? undefined)
  timeoutTimeouts.delete(token)
}

export function setTokenTimeout(token: string) {
  timeoutTokens.add(token)
}

export function addTokenTimeout(token: string, timeout: NodeJS.Timeout) {
  timeoutTimeouts.set(token, timeout)
}

export function isTokenDown(token: string) {
  return downTokens.has(token)
}

export function isTokenTimeout(token: string) {
  return timeoutTokens.has(token)
}

export function setTokenDownHandler(req: Request, res: Response) {
  setTokenDown(req.headers['authorization'] ?? '')
  res.status(200).json({ message: 'Service is down' })
}

export function clearTokenDownHandler(req: Request, res: Response) {
  setTokenUp(req.headers['authorization'] ?? '')
  res.status(200).json({ message: 'Service is up' })
}

export function setTokenTimeoutHandler(req: Request, res: Response) {
  setTokenTimeout(req.headers['authorization'] ?? '')
  res.status(200).json({ message: 'Service is timeout' })
}
