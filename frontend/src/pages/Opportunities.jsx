import { useEffect, useState } from 'react';
import { RefreshCcw, Database } from 'lucide-react';
import PageHeader from '../components/layout/PageHeader';
import EmptyState from '../components/layout/EmptyState';
import LoadingSpinner from '../components/layout/LoadingSpinner';
import Pagination from '../components/reusable/Pagination';
import api from '../services/api';
import toast from 'react-hot-toast';

export default function Opportunities() {
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [limit] = useState(20); // 20 per page
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchData();
  }, [page, limit]);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      // Fetch opportunities for current page
      const offset = (page - 1) * limit;
      const resp = await api.get('/api/opportunities', {
        params: {
          limit,
          offset,
        },
      });
      const { opportunities: data } = resp.data;
      setOpportunities(data);

      // Fetch total count from statistics
      const statsResp = await api.get('/api/opportunities/statistics');
      setTotal(statsResp.data.total_opportunities ?? 0);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Failed to load opportunities';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  if (loading && opportunities.length === 0 && error === '') {
    return (
      <div className="p-4 lg:p-8">
        <PageHeader title="Opportunities" subtitle="Freelance jobs from Upwork and other sources." />
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner className="h-8 w-8" />
          <span className="ml-2">Loading opportunities...</span>
        </div>
      </div>
    );
  }

  if (error && opportunities.length === 0) {
    return (
      <div className="p-4 lg:p-8">
        <PageHeader title="Opportunities" subtitle="Freelance jobs from Upwork and other sources." />
        <div className="glass-card rounded-2xl p-8 text-center">
          <EmptyState
            icon={Database}
            title="Unable to load opportunities"
            description={error}
          >
            <button
              onClick={fetchData}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <RefreshCcw className="w-4 h-4" />
              Retry
            </button>
          </EmptyState>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8">
      <PageHeader title="Opportunities" subtitle="Freelance jobs from Upwork and other sources." >
        <button
          onClick={fetchData}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </PageHeader>

      {opportunities.length === 0 && !loading && !error && (
        <div className="glass-card rounded-2xl p-8">
          <EmptyState
            icon={Database}
            title="No opportunities found"
            description="Try adjusting your search or check back later."
          />
        </div>
      )}

      {!loading && opportunities.length > 0 && (
        <div className="mt-6">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Title</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Client</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Budget</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Category</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Skills</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Published</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Link</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {opportunities.map((opp) => {
                  const budgetMin = opp.budget_min ?? 0;
                  const budgetMax = opp.budget_max ?? 0;
                  const budgetDisplay = budgetMin === budgetMax
                    ? `$${budgetMin}`
                    : `$${budgetMin} - $${budgetMax}`;
                  const skills = Array.isArray(opp.skills) ? opp.skills.join(', ') : '';
                  const publishedAt = opp.posted_time ? new Date(opp.posted_time).toLocaleDateString() : '';
                  return (
                    <tr key={opp.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{opp.project_title}</td>
                      <td className="px-6 py-4 whitespace-normal text-sm text-slate-600 max-w-[200px]">{opp.description}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{opp.client_country}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{budgetDisplay}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{opp.category}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{skills}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{publishedAt}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <a
                          href={opp.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary-600 hover:underline"
                        >
                          View
                        </a>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{opp.provider}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-6 flex justify-between items-center">
            <span className="text-sm text-slate-500">
              Showing {(page - 1) * limit + 1}-{Math.min(page * limit, total)} of {total} opportunities
            </span>
            <Pagination
              page={page}
              totalPages={Math.ceil(total / limit)}
              onPageChange={setPage}
            />
          </div>
        </div>
      )}
    </div>
  );
}