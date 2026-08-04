import { useEffect, useState } from 'react'

/**
 * Custom hook for fetching opportunities from the API.
 * @param {Object} options - Fetch options
 * @param {string} [options.search] - Search query
 * @param {string} [options.provider] - Filter by provider
 * @param {string} [options.category] - Filter by category
 * @param {string} [options.skills] - Comma-separated skills to filter by
 * @param {number} [options.minBudget] - Minimum budget
 * @param {number} [options.maxBudget] - Maximum budget
 * @param {string} [options.sortBy] - Field to sort by
 * @param {boolean} [options.sortDesc] - Sort descending
 * @param {number} [options.limit] - Number of results per page
 * @param {number} [options.offset] - Offset for pagination
 * @param {boolean} [options.enabled] - Whether to fetch (default: true)
 * @returns {Object} - { opportunities, total, loading, error, refetch }
 */
export function useOpportunities({
  search = '',
  provider = null,
  category = null,
  skills = '',
  minBudget = null,
  maxBudget = null,
  sortBy = 'posted_time',
  sortDesc = true,
  limit = 50,
  offset = 0,
  enabled = true,
} = {}) {
  const [opportunities, setOpportunities] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchOpportunities = async () => {
    if (!enabled) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Build query string
      const params = new URLSearchParams()
      if (search) params.append('q', search)
      if (provider) params.append('provider', provider)
      if (category) params.append('category', category)
      if (skills) params.append('skills', skills)
      if (minBudget !== null) params.append('min_budget', minBudget)
      if (maxBudget !== null) params.append('max_budget', maxBudget)
      if (sortBy) params.append('sort_by', sortBy)
      if (sortDesc !== undefined) params.append('sort_desc', sortDesc)
      if (limit) params.append('limit', limit)
      if (offset !== undefined) params.append('offset', offset)

      const queryString = params.toString()
      const url = `/api/opportunities/search?${queryString}`

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Failed to fetch opportunities: ${response.status}`)
      }

      const data = await response.json()
      setOpportunities(data.opportunities || [])
      setTotal(data.count || 0)
    } catch (err) {
      setError(err)
      setOpportunities([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  // Refetch function
  const refetch = fetchOpportunities

  // Fetch on mount and when dependencies change
  useEffect(() => {
    fetchOpportunities()
  }, [search, provider, category, skills, minBudget, maxBudget, sortBy, sortDesc, limit, offset, enabled])

  return { opportunities, total, loading, error, refetch }
}