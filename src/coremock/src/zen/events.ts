import { AppData } from '../types.js'

const events = new Map()

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function captureEvent(event: any, app: AppData) {
  if (!events.has(app.id)) {
    events.set(app.id, [])
  }

  events.get(app.id).push(event)
}

export function listEvents(app: AppData) {
  return events.get(app.id) || []
}
