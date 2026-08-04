import useQuery, { invalidateCache } from './useQuery'
import { getLead, updateLeadLifecycle } from '../services/leadsService'
import { mapApiLead } from '../services/adapters'

/**
 * useLead
 * -------
 * Fetch a single lead for the details drawer.
 */
export function useLead(id) {
  const query = useQuery({
    queryKey: ['lead', id],
    queryFn: async () => mapApiLead(await getLead(id)),
    ttl: 30_000,
    enabled: id != null,
  })

  return {
    lead: query.data,
    loading: query.loading,
    error: query.error,
    refetch: query.refetch,
    async setLifecycle(leadStatus) {
      const updated = await updateLeadLifecycle(id, leadStatus)
      invalidateCache(['lead', 'leads', 'analytics'])
      return mapApiLead(updated)
    },
  }
}
