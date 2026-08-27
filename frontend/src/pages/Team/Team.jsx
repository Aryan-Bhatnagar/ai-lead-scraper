import { useState, useEffect } from 'react'
import { Users, UserPlus, Code2, Palette, FileText, CheckCircle2, Briefcase, Mail, ShieldAlert } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../../services/api'

export default function Team() {
  const [team, setTeam] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    role: '',
    email: '',
    domains: ['Development'],
    expertise_tags: ''
  })
  const [submitting, setSubmitting] = useState(false)

  const fetchTeam = async () => {
    try {
      setLoading(true)
      const res = await api.get('/team')
      setTeam(res.data.team || [])
    } catch (err) {
      toast.error('Failed to load team members')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTeam()
  }, [])

  const handleDomainToggle = (domain) => {
    setFormData(prev => {
      const current = prev.domains || []
      if (current.includes(domain)) {
        if (current.length === 1) return prev // Keep at least one
        return { ...prev, domains: current.filter(d => d !== domain) }
      } else {
        return { ...prev, domains: [...current, domain] }
      }
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.name.trim()) {
      toast.error('Employee name is required')
      return
    }

    try {
      setSubmitting(true)
      const tags = formData.expertise_tags
        .split(',')
        .map(t => t.strip ? t.strip() : t.trim())
        .filter(Boolean)

      await api.post('/team', {
        name: formData.name.trim(),
        role: formData.role.trim() || 'Specialist',
        email: formData.email.trim(),
        domains: formData.domains,
        expertise_tags: tags
      })

      toast.success(`Team member ${formData.name} added successfully!`)
      setShowAddModal(false)
      setFormData({ name: '', role: '', email: '', domains: ['Development'], expertise_tags: '' })
      fetchTeam()
    } catch (err) {
      toast.error('Failed to add team member')
    } finally {
      setSubmitting(false)
    }
  }

  const getDomainIcon = (domain) => {
    switch (domain) {
      case 'Design': return <Palette className="w-4 h-4 text-purple-500" />
      case 'Content': return <FileText className="w-4 h-4 text-emerald-500" />
      default: return <Code2 className="w-4 h-4 text-blue-500" />
    }
  }

  const designMembers = team.filter(m => (m.domains || []).includes('Design'))
  const devMembers = team.filter(m => (m.domains || []).includes('Development'))
  const contentMembers = team.filter(m => (m.domains || []).includes('Content'))

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Users className="w-7 h-7 text-primary-500" />
            Team & Work Assignment Management
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage company employees by expertise domains (Design, Development, Content) and track assigned project workloads.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white font-medium rounded-xl transition-all shadow-lg shadow-primary-600/25 shrink-0"
        >
          <UserPlus className="w-4 h-4" />
          Add Team Member
        </button>
      </div>

      {/* Domain Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
              <Code2 className="w-4 h-4" /> Development Team
            </span>
            <span className="bg-blue-500/10 text-blue-400 text-xs px-2.5 py-1 rounded-full font-semibold border border-blue-500/20">
              {devMembers.length} Employees
            </span>
          </div>
          <p className="text-2xl font-bold text-white">{devMembers.reduce((acc, m) => acc + (m.assigned_count || 0), 0)} Leads Assigned</p>
          <p className="text-xs text-slate-400 mt-1">React, Python, Node.js, DevOps, Fullstack</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
              <Palette className="w-4 h-4" /> Design Team
            </span>
            <span className="bg-purple-500/10 text-purple-400 text-xs px-2.5 py-1 rounded-full font-semibold border border-purple-500/20">
              {designMembers.length} Employees
            </span>
          </div>
          <p className="text-2xl font-bold text-white">{designMembers.reduce((acc, m) => acc + (m.assigned_count || 0), 0)} Leads Assigned</p>
          <p className="text-xs text-slate-400 mt-1">UI/UX, Logo Design, Figma, Graphic Design</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <FileText className="w-4 h-4" /> Content Team
            </span>
            <span className="bg-emerald-500/10 text-emerald-400 text-xs px-2.5 py-1 rounded-full font-semibold border border-emerald-500/20">
              {contentMembers.length} Employees
            </span>
          </div>
          <p className="text-2xl font-bold text-white">{contentMembers.reduce((acc, m) => acc + (m.assigned_count || 0), 0)} Leads Assigned</p>
          <p className="text-xs text-slate-400 mt-1">Copywriting, SEO Content, Content Strategy</p>
        </div>
      </div>

      {/* Team Roster Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2 border-b border-slate-800 pb-4">
          <Briefcase className="w-5 h-5 text-primary-400" />
          Active Employee Roster ({team.length})
        </h2>

        {loading ? (
          <div className="py-12 text-center text-slate-400 animate-pulse">Loading team members...</div>
        ) : team.length === 0 ? (
          <div className="py-12 text-center text-slate-400">No team members registered yet.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {team.map((member) => (
              <div key={member.id} className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5 hover:border-slate-600 transition-all flex flex-col justify-between space-y-4">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-bold text-white text-base">{member.name}</h3>
                      <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                        <Briefcase className="w-3.5 h-3.5 text-slate-500" /> {member.role}
                      </p>
                    </div>
                    <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] uppercase font-bold px-2 py-0.5 rounded-full shrink-0">
                      {member.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-2">
                    <Mail className="w-3.5 h-3.5 text-slate-500" /> {member.email}
                  </p>

                  {/* Expertise Domains */}
                  <div className="flex items-center gap-1.5 flex-wrap mt-3">
                    {(member.domains || []).map((d) => (
                      <span key={d} className="flex items-center gap-1 bg-slate-900 border border-slate-700 text-slate-300 text-xs px-2.5 py-0.5 rounded-md font-medium">
                        {getDomainIcon(d)} {d}
                      </span>
                    ))}
                  </div>

                  {/* Skill Badges */}
                  {(member.expertise_tags || []).length > 0 && (
                    <div className="flex items-center gap-1 flex-wrap mt-2.5">
                      {member.expertise_tags.map((tag) => (
                        <span key={tag} className="bg-primary-500/10 text-primary-400 border border-primary-500/20 text-[11px] px-2 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Assigned Workload Count */}
                <div className="pt-3 border-t border-slate-700/50 flex items-center justify-between text-xs">
                  <span className="text-slate-400">Assigned Projects:</span>
                  <span className="font-bold text-white bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-700">
                    {member.assigned_count || 0} Leads
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Team Member Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-200">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-primary-400" />
              Add New Team Member
            </h3>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Employee Full Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Rahul Sharma"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Designated Role *</label>
                <input
                  type="text"
                  required
                  value={formData.role}
                  onChange={e => setFormData({ ...formData, role: e.target.value })}
                  placeholder="e.g. Senior Frontend Developer"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={e => setFormData({ ...formData, email: e.target.value })}
                  placeholder="rahul@bilvaleaf.com"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Expertise Domains (Select All That Apply)</label>
                <div className="flex items-center gap-2">
                  {['Development', 'Design', 'Content'].map(domain => {
                    const isSelected = (formData.domains || []).includes(domain)
                    return (
                      <button
                        type="button"
                        key={domain}
                        onClick={() => handleDomainToggle(domain)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                          isSelected
                            ? 'bg-primary-600 text-white border-primary-500 shadow-md'
                            : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
                        }`}
                      >
                        {getDomainIcon(domain)} {domain}
                      </button>
                    )
                  })}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Skills & Tech Stack (Comma separated)</label>
                <input
                  type="text"
                  value={formData.expertise_tags}
                  onChange={e => setFormData({ ...formData, expertise_tags: e.target.value })}
                  placeholder="React.js, Node.js, Python, UI/UX"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium rounded-xl transition-all"
                >
                  {submitting ? 'Adding...' : 'Save Employee'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
