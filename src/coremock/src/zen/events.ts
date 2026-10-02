/* eslint-disable @typescript-eslint/no-explicit-any */
import { AppData } from '../types.js'

type AgentRequestHeaders = {
  'X-Agent-Platform': string | null
  'X-Agent-Version': string | null
  'X-Agent-Hostname': string | null
  'X-Agent-IP-Address': string | null
  'X-Agent-Session-Id': string | null
}

type CapturedEvent = {
  event: any
  requestHeaders: AgentRequestHeaders
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
  requestHeaders: AgentRequestHeaders
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
