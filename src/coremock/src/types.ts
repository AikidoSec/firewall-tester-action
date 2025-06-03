import { Request } from 'express'

export interface AppData {
  id: number
  token: string
  configUpdatedAt: number
}

export interface RequestWithAppData extends Request {
  appData?: AppData
}
