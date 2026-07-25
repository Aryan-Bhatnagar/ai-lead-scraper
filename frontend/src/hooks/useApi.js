import { useState, useCallback } from 'react'

/**
 * Generic hook for API calls with loading and error state.
 *
 * Usage:
 *   const { data, loading, error, execute } = useApi(api.get, '/api/leads')
 *   useEffect(() => { execute() }, [])
 */
export default function useApi(apiFn, ...args) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const execute = useCallback(
    async (...overrideArgs) => {
      setLoading(true)
      setError(null)
      try {
        const response = await apiFn(...(overrideArgs.length ? overrideArgs : args))
        setData(response.data)
        return response.data
      } catch (err) {
        setError(err.response?.data?.error || err.message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [apiFn, ...args]
  )

  return { data, loading, error, execute }
}
