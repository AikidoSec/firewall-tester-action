/* eslint-disable @typescript-eslint/no-explicit-any */
import { AppData } from '../types.js'
import fs from 'fs'

const events = new Map()

function normalizeTypesInApiSpec(schema: any): any {
  if (Array.isArray(schema)) {
    return schema.map(normalizeTypesInApiSpec)
  }

  if (typeof schema === 'object' && schema !== null) {
    const clone: any = {}

    for (const key in schema) {
      if (key === 'type') {
        let value = schema[key]
        if (Array.isArray(value) && value.length === 1) {
          value = value[0]
        }

        clone[key] = value
      } else {
        clone[key] = normalizeTypesInApiSpec(schema[key])
      }
    }

    return clone
  }

  return schema
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function captureEvent(event: any, app: AppData) {
  if (!events.has(app.id)) {
    events.set(app.id, [])
  }
  if (event.type === 'started') {
    events.set(app.id, [])
  }

  if (event.type === 'heartbeat') {
    // save event to file
    fs.writeFileSync('event.json', JSON.stringify(event, null, 2))
    event.routes.forEach((route: any) => {
      route.apispec = normalizeTypesInApiSpec(route.apispec)
    })
  }

  events.get(app.id).push(event)
}

export function listEvents(app: AppData) {
  return events.get(app.id) || []
}
