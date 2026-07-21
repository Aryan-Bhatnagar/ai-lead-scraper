import React, { useEffect, useState } from 'react';
import { api } from '../api/apiClient';

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadLeads = async () => {
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
      }
    };

    loadLeads();
  }, []);

  if (loading) {
    return <p>Loading leads...</p>;
  }

  if (error) {
    return <p>{error}</p>;
  }

  return (
    <section>
      <h2>Leads</h2>

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
                <td>{lead.source_url || '-'}</td>
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