import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * Lightweight query hook with:
 *  - module-level cache with TTL (avoids duplicate requests + refetch storms)
 *  - in-flight request deduplication (multiple components with the same key
 *    share one request)
 *  - manual refetch() that bypasses cache
 *
 * This keeps the project dependency-free (no React Query) while matching the
 * existing hook style (useApi).
 */

const cache = new Map() // key -> { data, timestamp }
const inflight = new Map() // key -> Promise

const DEFAULT_TTL_MS = 60_000

function readCache(key, ttl) {
  const entry = cache.get(key)
  if (!entry) return null
  if (Date.now() - entry.timestamp > ttl) {
    cache.delete(key)
    return null
  }
  return entry.data
}

async function fetchOnce(key, fetcher) {
  if (inflight.has(key)) return inflight.get(key)
  const promise = fetcher()
    .then((data) => {
      cache.set(key, { data, timestamp: Date.now() })
      inflight.delete(key)
      return data
    })
    .catch((err) => {
      inflight.delete(key)
      throw err
    })
  inflight.set(key, promise)
  return promise
}

export function invalidateCache(keys) {
  const list = Array.isArray(keys) ? keys : [keys]
  for (const key of list) {
    if (key == null) continue
    // Exact match or prefix invalidation (e.g. 'analytics' clears all analytics keys)
    for (const cachedKey of cache.keys()) {
      if (cachedKey === key || cachedKey.startsWith(`${key}:`)) {
        cache.delete(cachedKey)
      }
    }
  }
}

export default function useQuery({ queryKey, queryFn, ttl = DEFAULT_TTL_MS, enabled = true }) {
  const keyStr = useRef(JSON.stringify(queryKey)).current
  const cached = enabled ? readCache(keyStr, ttl) : null
  const [data, setData] = useState(cached)
  const [loading, setLoading] = useState(enabled && !cached)
  const [error, setError] = useState(null)
  const queryFnRef = useRef(queryFn)
  queryFnRef.current = queryFn

  const fetchData = useCallback(
    async ({ force = false } = {}) => {
      if (!force) {
        const hit = readCache(keyStr, ttl)
        if (hit !== null) {
          setData(hit)
          setLoading(false)
          setError(null)
          return hit
        }
      }
      setLoading(true)
      setError(null)
      try {
        const result = await fetchOnce(keyStr, () => queryFnRef.current())
        setData(result)
        return result
      } catch (err) {
        setError(err.response?.data?.error || err.message || 'Request failed')
        return null
      } finally {
        setLoading(false)
      }
    },
    [keyStr, ttl]
  )

  useEffect(() => {
    if (!enabled) return
    const controller = { cancelled: false }
    const hit = readCache(keyStr, ttl)
    if (hit !== null) {
      setData(hit)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    fetchOnce(keyStr, () => queryFnRef.current())
      .then((result) => {
        if (!controller.cancelled) setData(result)
      })
      .catch((err) => {
        if (!controller.cancelled) {
          setError(err.response?.data?.error || err.message || 'Request failed')
        }
      })
      .finally(() => {
        if (!controller.cancelled) setLoading(false)
      })
    return () => {
      controller.cancelled = true
    }
  }, [keyStr, ttl, enabled])

  const refetch = useCallback(() => fetchData({ force: true }), [fetchData])

  return { data, loading, error, refetch }
}
