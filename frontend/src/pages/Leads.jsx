import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api/apiClient';

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const loadLeads = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    }

    setError('');

    try {
      const response = await api.get('/leads');
      setLeads(response.data.leads || []);
    } catch (err) {
      setError(
        err.response?.data?.error ||
          'Failed to load leads.'
      );
    } finally {
      setLoading(false);

      if (isRefresh) {
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  if (loading) {
    return <p>Loading leads...</p>;
  }

  return (
    <section>
      <h2>Leads</h2>

      <button
        type="button"
        onClick={() => loadLeads(true)}
        disabled={refreshing}
      >
        {refreshing ? 'Refreshing...' : 'Refresh'}
      </button>

      {error && <p>{error}</p>}

      {leads.length === 0 ? (
        <p>No leads found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Company</th>
              <th>Website</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id}>
                <td>{lead.id}</td>
                <td>{lead.company_name || '-'}</td>
                <td>{lead.website || lead.source_url || '-'}</td>
                <td>{lead.email || '-'}</td>
                <td>{lead.phone || '-'}</td>
                <td>{lead.status || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}