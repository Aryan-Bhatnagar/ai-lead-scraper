import { useEffect, useState } from 'react'

/**
 * Custom hook for fetching opportunity statistics from the API.
 * @returns {Object} - { statistics, loading, error, refetch }
 */
export function useOpportunityStatistics() {
  const [statistics, setStatistics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStatistics = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/opportunities/statistics')
      if (!response.ok) {
        throw new Error(`Failed to fetch opportunity statistics: ${response.status}`)
      }

      const data = await response.json()
      setStatistics(data)
    } catch (err) {
      setError(err)
      setStatistics(null)
    } finally {
      setLoading(false)
    }
  }

  // Refetch function
  const refetch = fetchStatistics

  // Fetch on mount
  useEffect(() => {
    fetchStatistics()
  }, [])

  return { statistics, loading, error, refetch }
}