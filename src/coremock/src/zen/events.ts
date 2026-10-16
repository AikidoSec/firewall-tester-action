/* eslint-disable @typescript-eslint/no-explicit-any */
import { IncomingHttpHeaders } from 'http'
import { AppData } from '../types.js'

type CapturedEvent = {
  event: any
  requestHeaders: IncomingHttpHeaders
}

const events = new Map<number, CapturedEvent[]>()

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

export function captureEvent(
  event: any,
  app: AppData,
  requestHeaders: IncomingHttpHeaders
) {
  if (!events.has(app.id)) {
    events.set(app.id, [])
  }
  if (event.type === 'started') {
    events.set(app.id, [])
  }

  if (event.type === 'heartbeat') {
    event.routes ??= []
    event.routes.forEach((route: any) => {
      route.apispec = normalizeTypesInApiSpec(route.apispec)
    })
  }

  events.get(app.id)!.push({ event, requestHeaders })
}

export function listEvents(app: AppData, includeHeaders = false) {
  const capturedEvents = events.get(app.id) ?? []
  return capturedEvents.map(({ event, requestHeaders }) =>
    includeHeaders ? { ...event, requestHeaders } : event
  )
}
