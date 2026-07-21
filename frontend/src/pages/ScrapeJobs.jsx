import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api/apiClient';

const POLL_INTERVAL_MS = 3000;

export default function ScrapeJobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const loadJobs = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    }

    try {
      const response = await api.get('/jobs');

      setJobs(response.data.jobs || []);
      setError('');
    } catch (err) {
      setError(
        err.response?.data?.error ||
          'Failed to load scrape jobs.'
      );
    } finally {
      setLoading(false);

      if (isRefresh) {
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    loadJobs();

    const intervalId = setInterval(() => {
      loadJobs();
    }, POLL_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
    };
  }, [loadJobs]);

  const handleRefresh = () => {
    loadJobs(true);
  };

  if (loading) {
    return <p>Loading scrape jobs...</p>;
  }

  return (
    <section>
      <div>
        <h2>Scrape Jobs</h2>

        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <p>
        Job statuses refresh automatically every 3 seconds.
      </p>

      {error && (
        <p>
          {error}
        </p>
      )}

      {jobs.length === 0 ? (
        <p>No scrape jobs found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Job ID</th>
              <th>Status</th>
              <th>Total URLs</th>
              <th>Completed</th>
              <th>Successful</th>
              <th>Failed</th>
              <th>No Data</th>
              <th>Created At</th>
            </tr>
          </thead>

          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.id}</td>
                <td>{job.status}</td>
                <td>{job.total_urls ?? 0}</td>
                <td>{job.completed_urls ?? 0}</td>
                <td>{job.successful_urls ?? 0}</td>
                <td>{job.failed_urls ?? 0}</td>
                <td>{job.no_data_urls ?? 0}</td>
                <td>
                  {job.created_at
                    ? new Date(job.created_at).toLocaleString()
                    : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}