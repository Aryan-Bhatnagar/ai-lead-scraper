import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/apiClient';

export default function NewScrapeJob() {
  const navigate = useNavigate();  
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();

    const urls = input
      .split('\n')
      .map((url) => url.trim())
      .filter(Boolean);

    if (urls.length === 0) {
      setError('Please enter at least one URL.');
      setMessage('');
      return;
    }

    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await api.post('/jobs', { urls });

            setMessage(
        `Scrape job ${response.data.job_id} created successfully.`
      );
      setInput('');

      navigate('/jobs');
    } catch (err) {
      setError(
        err.response?.data?.error ||
          'Failed to create scrape job.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <h2>New Scrape Job</h2>
      <p>Enter one website URL per line.</p>

      <form onSubmit={handleSubmit}>
        <textarea
          rows="10"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={'https://example.com\nhttps://another-example.com'}
        />

        <br />

        <button type="submit" disabled={loading}>
          {loading ? 'Creating Job...' : 'Create Scrape Job'}
        </button>
      </form>

      {message && <p>{message}</p>}
      {error && <p>{error}</p>}
    </section>
  );
}