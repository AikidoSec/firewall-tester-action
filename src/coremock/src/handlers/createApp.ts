import { Request, Response } from 'express'
import { createZenApp } from '../zen/apps.js'
import * as core from '@actions/core'

export default function createApp(req: Request, res: Response): void {
  const token = createZenApp(
    typeof req.body?.token === 'string' ? req.body.token : undefined
  )

  core.info(`Created app with token: ${token}`)

  res.json({
    token
  })
}
