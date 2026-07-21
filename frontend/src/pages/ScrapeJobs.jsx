import React, { useEffect, useState } from 'react';
import { api } from '../api/apiClient';

export default function ScrapeJobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadJobs = async () => {
      try {
        const response = await api.get('/jobs');
        setJobs(response.data.jobs || []);
      } catch (err) {
        setError(
          err.response?.data?.error ||
            'Failed to load scrape jobs.'
        );
      } finally {
        setLoading(false);
      }
    };

    loadJobs();
  }, []);

  if (loading) {
    return <p>Loading scrape jobs...</p>;
  }

  if (error) {
    return <p>{error}</p>;
  }

  return (
    <section>
      <h2>Scrape Jobs</h2>

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
              <th>Created At</th>
            </tr>
          </thead>

          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.id}</td>
                <td>{job.status}</td>
                <td>{job.total_urls}</td>
                <td>{job.completed_urls}</td>
                <td>{job.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}