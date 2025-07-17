/* eslint-disable @typescript-eslint/no-explicit-any */
import { AppData } from '../types.js'

const events = new Map()

function normalizeTypesInApiSpec(schema: any) {
  const clone = { ...schema }

  // Convert single-element array type to string
  if (Array.isArray(clone.type) && clone.type.length === 1) {
    clone.type = clone.type[0]
  }

  // Recurse into properties
  if (clone.properties) {
    const newProps: { [key: string]: any } = {}
    for (const [key, value] of Object.entries(clone.properties)) {
      newProps[key] = normalizeTypesInApiSpec(value)
    }
    clone.properties = newProps
  }

  if (clone.items) {
    clone.items = normalizeTypesInApiSpec(clone.items)
  }

  return clone
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
    event.routes.forEach((route: any) => {
      route.apispec = normalizeTypesInApiSpec(route.apispec)
    })
  }

  events.get(app.id).push(event)
}

export function listEvents(app: AppData) {
  return events.get(app.id) || []
}
