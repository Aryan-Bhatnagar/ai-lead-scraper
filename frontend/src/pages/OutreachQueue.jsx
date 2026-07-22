import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api/apiClient';

export default function OutreachQueue() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadEntries = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true);
    }
    setError('');
    try {
      const response = await api.get('/outreach');
      setEntries(response.data.outreach || []);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load outreach queue.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const handleDelete = async (id) => {
    try {
      await api.delete(`/outreach/${id}`);
      // Refresh list after deletion
      await loadEntries(true);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete outreach entry.');
    }
  };

  if (loading) {
    return <p>Loading outreach queue...</p>;
  }

  return (
    <section>
      <h2>Outreach Queue</h2>
      {error && <p>{error}</p>}
      <button type="button" onClick={() => loadEntries(true)} disabled={loading}>
        Refresh
      </button>
      {entries.length === 0 ? (
        <p>No outreach entries found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Lead ID</th>
              <th>Company</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Attempts</th>
              <th>Last Contacted</th>
              <th>Next Follow‑up</th>
              <th>Error</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id}>
                <td>{e.id}</td>
                <td>{e.lead_id}</td>
                <td>{e.company_name || '-'}
                </td>
                <td>{e.outreach_channel}</td>
                <td>{e.outreach_status}</td>
                <td>{e.attempt_count}</td>
                <td>{e.last_contacted_at || '-'}</td>
                <td>{e.next_follow_up_at || '-'}</td>
                <td>{e.error_message || '-'}</td>
                <td>
                  {(e.outreach_status === 'PENDING' || e.outreach_status === 'FAILED') && (
                    <button type="button" onClick={() => handleDelete(e.id)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
