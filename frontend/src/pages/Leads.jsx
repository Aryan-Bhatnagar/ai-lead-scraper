import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/apiClient';

export default function Leads() {
  const [allLeads, setAllLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [leadChannelMap, setLeadChannelMap] = useState({});
  const [filter, setFilter] = useState('ALL');
  const [sortOrder, setSortOrder] = useState('HIGH_TO_LOW');

  const loadLeads = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    }

    setError('');

    try {
      const response = await api.get('/leads');

      const normalized = (response.data.leads || []).map((lead) => ({
        ...lead,
        quality_score: lead.quality_score ?? 0,
        data_quality:
          lead.data_quality && lead.data_quality.trim()
            ? lead.data_quality.toUpperCase()
            : 'NONE',
        // Ensure the CRM lead_status field is always present.
        lead_status: lead.lead_status || 'NEW',
      }));

      setAllLeads(normalized);
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

  const handleLeadStatusChange = async (leadId, newStatus) => {
    try {
      const resp = await api.patch(`/leads/${leadId}/status`, {
        lead_status: newStatus,
      });
      // The API returns the full updated lead object.
      const updatedLead = resp.data;
      setAllLeads((prev) =>
        prev.map((l) => (l.id === leadId ? { ...l, ...updatedLead } : l))
      );
    } catch (err) {
      setError(
        err.response?.data?.error ||
          `Failed to update lead status for lead ${leadId}.`
      );
    }
  };

  const counters = useMemo(() => {
    const high = allLeads.filter(
      (lead) => lead.data_quality === 'HIGH'
    ).length;

    const medium = allLeads.filter(
      (lead) => lead.data_quality === 'MEDIUM'
    ).length;

    const low = allLeads.filter(
      (lead) => lead.data_quality === 'LOW'
    ).length;

    const none = allLeads.filter(
      (lead) => lead.data_quality === 'NONE'
    ).length;

    return {
      total: allLeads.length,
      high,
      medium,
      low,
      none,
    };
  }, [allLeads]);

  const displayLeads = useMemo(() => {
    let filteredLeads = allLeads;

    if (filter !== 'ALL') {
      filteredLeads = filteredLeads.filter(
        (lead) => lead.data_quality === filter
      );
    }

    return [...filteredLeads].sort((a, b) => {
      if (sortOrder === 'HIGH_TO_LOW') {
        return b.quality_score - a.quality_score;
      }

      return a.quality_score - b.quality_score;
    });
  }, [allLeads, filter, sortOrder]);

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

      <div>
        <p>Total Leads: {counters.total}</p>
        <p>High Quality: {counters.high}</p>
        <p>Medium Quality: {counters.medium}</p>
        <p>Low Quality: {counters.low}</p>
        <p>Unscored: {counters.none}</p>
      </div>

      <div>
        <label>
          Data Quality:{' '}
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          >
            <option value="ALL">ALL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
            <option value="NONE">NONE</option>
          </select>
        </label>

        {' '}

        <label>
          Sort:{' '}
          <select
            value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value)}
          >
            <option value="HIGH_TO_LOW">
              Quality Score: High to Low
            </option>
            <option value="LOW_TO_HIGH">
              Quality Score: Low to High
            </option>
          </select>
        </label>
      </div>

      {displayLeads.length === 0 ? (
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
              <th>Quality Score</th>
              <th>Data Quality</th>
              <th>Scrape Status</th>
              <th>Lead Status</th>
            </tr>
          </thead>

          <tbody>
            {displayLeads.map((lead) => {
              const selectedChannel = leadChannelMap[lead.id] || 'EMAIL';
              const isEligible =
                (lead.lead_status === 'QUALIFIED' || lead.lead_status === 'INTERESTED') &&
                ((selectedChannel === 'EMAIL' && lead.email) ||
                  ((selectedChannel === 'WHATSAPP' || selectedChannel === 'CALL') && lead.phone));
              const handleChannelChange = (e) => {
                const newChannel = e.target.value;
                setLeadChannelMap((prev) => ({ ...prev, [lead.id]: newChannel }));
              };
              const handleAddToOutreach = async () => {
                try {
                  await api.post('/outreach', {
                    lead_id: lead.id,
                    outreach_channel: selectedChannel,
                  });
                  // Refresh leads after successful queue creation
                  await loadLeads(true);
                } catch (err) {
                  setError(err.response?.data?.error || 'Failed to add to outreach queue');
                }
              };
              return (
                <tr key={lead.id}>
                  <td>{lead.id}</td>
                  <td>{lead.company_name || '-'}</td>
                  <td>{lead.website || lead.source_url || '-'}</td>
                  <td>{lead.email || '-'}</td>
                  <td>{lead.phone || '-'}</td>
                  <td>{lead.quality_score}</td>
                  <td>{lead.data_quality}</td>
                  <td>{lead.status || '-'}</td>
                  <td>
                    <select
                      value={lead.lead_status || 'NEW'}
                      onChange={(e) =>
                        handleLeadStatusChange(lead.id, e.target.value)
                      }
                    >
                      <option value="NEW">NEW</option>
                      <option value="QUALIFIED">QUALIFIED</option>
                      <option value="CONTACTED">CONTACTED</option>
                      <option value="INTERESTED">INTERESTED</option>
                      <option value="CONVERTED">CONVERTED</option>
                      <option value="REJECTED">REJECTED</option>
                    </select>
                    <br />
                    <select
                      value={selectedChannel}
                      onChange={handleChannelChange}
                    >
                      <option value="EMAIL">EMAIL</option>
                      <option value="WHATSAPP">WHATSAPP</option>
                      <option value="CALL">CALL</option>
                    </select>
                    <button
                      type="button"
                      onClick={handleAddToOutreach}
                      disabled={!isEligible}
                      style={{ marginLeft: '4px' }}
                    >
                      Add to Outreach
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
