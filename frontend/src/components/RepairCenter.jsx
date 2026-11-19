import React, { useState, useEffect } from 'react';
import {
  Wrench,
  RotateCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Edit3,
  Save,
  X,
  Download,
  Eye,
  ShieldCheck,
  ShieldAlert,
  HelpCircle,
  Search,
  ArrowRight,
  Copy,
  Type,
  TrendingUp,
  SlidersHorizontal,
  FileSpreadsheet,
  Check,
  AlertCircle
} from 'lucide-react';
import { datasetApi } from '../services/api';

const REPAIR_TYPE_META = {
  missing_imputation: {
    label: 'Missing Imputation',
    icon: XCircle,
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  },
  deduplication: {
    label: 'Deduplication',
    icon: Copy,
    color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  },
  category_normalization: {
    label: 'Category Normalization',
    icon: SlidersHorizontal,
    color: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  },
  format_correction: {
    label: 'Format Correction',
    icon: Type,
    color: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  },
  anomaly_review: {
    label: 'Anomaly Review',
    icon: TrendingUp,
    color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  },
};

const STATUS_BADGES = {
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  approved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  rejected: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  applied: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
  failed: 'bg-red-500/15 text-red-300 border-red-500/30',
};

export default function RepairCenter({ datasetId, onNavigateToValidation }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  // Inline editing state: { [repairId]: string }
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState('');

  // Confirmation Modal state for applying repairs
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [applyResult, setApplyResult] = useState(null);

  // Repaired Dataset Preview modal state
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewPage, setPreviewPage] = useState(1);

  const fetchRepairs = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await datasetApi.getRepairs(datasetId);
      setData(resp);
    } catch (err) {
      console.error('Failed to load repairs:', err);
      setError(err.message || 'Unable to load repair proposals.');
    } finally {
      setLoading(false);
    }
  };

  const regenerateProposals = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await datasetApi.proposeRepairs(datasetId);
      setData(resp);
    } catch (err) {
      console.error('Failed to regenerate repairs:', err);
      setError(err.message || 'Failed to generate repair proposals.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepairs();
  }, [datasetId]);

  // Actions
  const handleApprove = async (repairId) => {
    setActionLoading(true);
    try {
      const updated = await datasetApi.approveRepair(datasetId, repairId);
      setData((prev) => {
        if (!prev) return prev;
        const newRepairs = prev.repairs.map((r) => (r.repair_id === repairId ? updated : r));
        const approvedCount = newRepairs.filter((r) => r.status === 'approved').length;
        const pendingCount = newRepairs.filter((r) => r.status === 'pending').length;
        const rejectedCount = newRepairs.filter((r) => r.status === 'rejected').length;
        return {
          ...prev,
          summary: {
            ...prev.summary,
            approved: approvedCount,
            pending: pendingCount,
            rejected: rejectedCount,
          },
          repairs: newRepairs,
        };
      });
    } catch (err) {
      alert(err.message || 'Failed to approve repair.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (repairId) => {
    setActionLoading(true);
    try {
      const updated = await datasetApi.rejectRepair(datasetId, repairId);
      setData((prev) => {
        if (!prev) return prev;
        const newRepairs = prev.repairs.map((r) => (r.repair_id === repairId ? updated : r));
        const approvedCount = newRepairs.filter((r) => r.status === 'approved').length;
        const pendingCount = newRepairs.filter((r) => r.status === 'pending').length;
        const rejectedCount = newRepairs.filter((r) => r.status === 'rejected').length;
        return {
          ...prev,
          summary: {
            ...prev.summary,
            approved: approvedCount,
            pending: pendingCount,
            rejected: rejectedCount,
          },
          repairs: newRepairs,
        };
      });
    } catch (err) {
      alert(err.message || 'Failed to reject repair.');
    } finally {
      setActionLoading(false);
    }
  };

  const startEditing = (repair) => {
    setEditingId(repair.repair_id);
    setEditValue(repair.proposed_value || '');
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditValue('');
  };

  const saveEdit = async (repairId) => {
    setActionLoading(true);
    try {
      const updated = await datasetApi.updateRepair(datasetId, repairId, editValue);
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          repairs: prev.repairs.map((r) => (r.repair_id === repairId ? updated : r)),
        };
      });
      setEditingId(null);
    } catch (err) {
      alert(err.message || 'Failed to update proposed value.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleApplyApproved = async () => {
    setActionLoading(true);
    try {
      const result = await datasetApi.applyApprovedRepairs(datasetId);
      setApplyResult(result);
      setShowApplyModal(false);
      // Refresh repair statuses
      await fetchRepairs();
    } catch (err) {
      alert(err.message || 'Failed to apply approved repairs.');
    } finally {
      setActionLoading(false);
    }
  };

  const fetchPreview = async (page = 1) => {
    setPreviewLoading(true);
    try {
      const preview = await datasetApi.getRepairedPreview(datasetId, page, 20);
      setPreviewData(preview);
      setPreviewPage(page);
    } catch (err) {
      console.error('Failed to load preview:', err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const openPreview = () => {
    setShowPreviewModal(true);
    fetchPreview(1);
  };

  if (loading && !data) {
    return (
      <div className="bg-slate-800/40 border border-slate-800 rounded-3xl p-12 text-center space-y-4">
        <RotateCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
        <h3 className="text-lg font-bold text-white">Synthesizing Repair Proposals...</h3>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Converting Phase 3 quality detections and Phase 4 Gemini intelligence into deterministic, reviewable repair actions.
        </p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="bg-rose-500/10 border border-rose-500/20 rounded-3xl p-8 text-center space-y-4">
        <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto" />
        <h3 className="text-lg font-bold text-rose-300">Unable to Load Repairs</h3>
        <p className="text-xs sm:text-sm text-rose-200/90">{error}</p>
        <button
          onClick={fetchRepairs}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-xl transition"
        >
          Retry
        </button>
      </div>
    );
  }

  const summary = data?.summary || { total: 0, pending: 0, approved: 0, rejected: 0, applied: 0 };
  const repairs = data?.repairs || [];

  // Filter repairs
  const filteredRepairs = repairs.filter((r) => {
    const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
    const matchesType = typeFilter === 'all' || r.repair_type === typeFilter;
    const matchesSearch =
      searchTerm === '' ||
      r.repair_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.issue_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.column_name && r.column_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (r.original_value && r.original_value.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (r.proposed_value && r.proposed_value.toLowerCase().includes(searchTerm.toLowerCase())) ||
      r.explanation.toLowerCase().includes(searchTerm.toLowerCase());

    return matchesStatus && matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner: Metrics & Safety Strip */}
      <div className="bg-slate-800/40 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-sm shadow-xl space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-700/50">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-emerald-500 flex items-center justify-center text-white shadow-lg shadow-indigo-600/20 flex-shrink-0">
              <Wrench className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Safe Repair Center</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Human Approval Required
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 mt-1">
                Deterministic remediation proposals for detected data issues. Every change requires individual user sign-off.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={regenerateProposals}
              disabled={loading || actionLoading}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold rounded-xl transition border border-slate-700 cursor-pointer"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Proposals</span>
            </button>

            {data?.has_repaired_dataset && (
              <div className="flex items-center gap-2">
                <button
                  onClick={openPreview}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/20 cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Preview Repaired Data</span>
                </button>

                <a
                  href={datasetApi.getRepairedDownloadUrl(datasetId)}
                  download
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-emerald-600/20"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Cleaned File</span>
                </a>
              </div>
            )}
          </div>
        </div>

        {/* Safety & Non-Destructive Banner */}
        <div className="flex items-start gap-3 p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-slate-300 text-xs leading-relaxed">
          <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          <div>
            <strong className="text-white font-semibold">Strict Data Integrity Guarantee: </strong>
            Repairs are applied strictly to a separate working copy. Your original uploaded file is permanently immutable and cannot be overwritten. Single-click bulk auto-application is prohibited to ensure deliberate human oversight.
          </div>
        </div>

        {/* 5 Summary Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Total Proposals</span>
            <div className="mt-1.5 text-2xl font-bold text-white font-mono">{summary.total}</div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-amber-400 font-medium">Pending Review</span>
            <div className="mt-1.5 text-2xl font-bold text-amber-400 font-mono">{summary.pending}</div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-emerald-400 font-medium">Approved</span>
            <div className="mt-1.5 text-2xl font-bold text-emerald-400 font-mono">{summary.approved}</div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-rose-400 font-medium">Rejected</span>
            <div className="mt-1.5 text-2xl font-bold text-rose-400 font-mono">{summary.rejected}</div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-indigo-400 font-medium">Applied</span>
            <div className="mt-1.5 text-2xl font-bold text-indigo-400 font-mono">{summary.applied}</div>
          </div>
        </div>
      </div>

      {/* Applied Feedback Banner if any */}
      {applyResult && (
        <div className="p-5 rounded-2xl bg-indigo-950/30 border border-indigo-500/40 space-y-2">
          <div className="flex items-center gap-2 text-indigo-300 text-sm font-bold">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span>Repairs Successfully Executed!</span>
          </div>
          <p className="text-xs text-slate-300">
            Applied <strong>{applyResult.applied_count}</strong> approved changes to a new working dataset.
            {applyResult.failed_count > 0 && ` (${applyResult.failed_count} repairs encountered validation warnings).`}
          </p>
          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={openPreview}
              className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
            >
              Inspect Repaired Preview
            </button>
            <a
              href={datasetApi.getRepairedDownloadUrl(datasetId)}
              download
              className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition"
            >
              Download Repaired File
            </a>
            {onNavigateToValidation && (
              <button
                onClick={onNavigateToValidation}
                className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold transition shadow-md shadow-emerald-600/25 inline-flex items-center gap-1.5"
              >
                <span>Proceed to Validation & Export</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Sticky Execution Toolbar if approved repairs exist */}
      {summary.approved > 0 && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-950/40 to-slate-900 border border-emerald-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xl">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-bold text-white">
                {summary.approved} Approved Repair{summary.approved > 1 ? 's' : ''} Ready to Apply
              </p>
              <p className="text-xs text-slate-400">
                Approved changes will be written into a separate working copy.
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowApplyModal(true)}
            disabled={actionLoading}
            className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition shadow-lg shadow-emerald-600/25 flex items-center gap-2 cursor-pointer"
          >
            <Wrench className="w-4 h-4" />
            <span>Apply {summary.approved} Approved Repair{summary.approved > 1 ? 's' : ''}</span>
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 border border-slate-800 p-3 rounded-2xl">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search repairs, columns, or values..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Statuses ({summary.total})</option>
            <option value="pending">Pending ({summary.pending})</option>
            <option value="approved">Approved ({summary.approved})</option>
            <option value="rejected">Rejected ({summary.rejected})</option>
            <option value="applied">Applied ({summary.applied})</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Repair Types</option>
            <option value="missing_imputation">Missing Imputation</option>
            <option value="deduplication">Deduplication</option>
            <option value="category_normalization">Category Normalization</option>
            <option value="format_correction">Format Correction</option>
            <option value="anomaly_review">Anomaly Review</option>
          </select>

          {(statusFilter !== 'all' || typeFilter !== 'all' || searchTerm !== '') && (
            <button
              onClick={() => {
                setStatusFilter('all');
                setTypeFilter('all');
                setSearchTerm('');
              }}
              className="text-xs text-indigo-400 hover:text-indigo-300 px-2 py-1 rounded-lg"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Repair Proposals Cards List */}
      <div className="space-y-3">
        {filteredRepairs.length === 0 ? (
          <div className="bg-slate-800/20 border border-slate-800 rounded-2xl p-8 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
            <h4 className="text-sm font-semibold text-white">No Repairs Matching Criteria</h4>
            <p className="text-xs text-slate-400">Try adjusting your status or type filters.</p>
          </div>
        ) : (
          filteredRepairs.map((repair) => {
            const typeMeta = REPAIR_TYPE_META[repair.repair_type] || {
              label: repair.repair_type,
              icon: HelpCircle,
              color: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
            };
            const TypeIcon = typeMeta.icon;
            const isEditing = editingId === repair.repair_id;

            return (
              <div
                key={repair.repair_id}
                className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 transition-all space-y-4"
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-indigo-400">{repair.repair_id}</span>
                    <span className="text-[11px] font-mono text-slate-400">Issue: {repair.issue_id}</span>
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md border text-[10px] font-semibold ${typeMeta.color}`}>
                      <TypeIcon className="w-3 h-3" />
                      <span>{typeMeta.label}</span>
                    </span>
                    {repair.column_name ? (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-950 text-indigo-300 border border-slate-800">
                        {repair.column_name} (Row {repair.row_index + 1})
                      </span>
                    ) : (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-950 text-rose-300 border border-slate-800">
                        Row {repair.row_index + 1} (Entire Record)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border font-mono ${
                      STATUS_BADGES[repair.status] || STATUS_BADGES.pending
                    }`}>
                      {repair.status}
                    </span>

                    {repair.human_review_required && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        <span>Review Required</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Diff View: Original vs Proposed */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
                  {/* Original Value */}
                  <div className="md:col-span-5 p-3 rounded-xl bg-slate-950 border border-slate-800/90 space-y-1">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider block">
                      Original Value
                    </span>
                    <div className="font-mono text-xs text-rose-300 truncate">
                      {repair.original_value || '<empty/null>'}
                    </div>
                  </div>

                  {/* Transition Arrow */}
                  <div className="md:col-span-1 flex items-center justify-center">
                    <ArrowRight className="w-4 h-4 text-slate-500" />
                  </div>

                  {/* Proposed Value / Editable Input */}
                  <div className="md:col-span-6 p-3 rounded-xl bg-slate-950 border border-slate-800/90 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-semibold text-emerald-400 tracking-wider block">
                        Proposed Value
                      </span>
                      {repair.status !== 'applied' && !isEditing && (
                        <button
                          onClick={() => startEditing(repair)}
                          className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
                        >
                          <Edit3 className="w-3 h-3" />
                          <span>Edit</span>
                        </button>
                      )}
                    </div>

                    {isEditing ? (
                      <div className="flex items-center gap-2 pt-1">
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          placeholder="Enter proposed value..."
                          className="flex-1 px-2.5 py-1 rounded bg-slate-900 border border-indigo-500 text-xs text-white font-mono focus:outline-none"
                        />
                        <button
                          onClick={() => saveEdit(repair.repair_id)}
                          disabled={actionLoading}
                          className="p-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer"
                          title="Save Value"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={cancelEditing}
                          className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
                          title="Cancel"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="font-mono text-xs font-semibold text-emerald-400 truncate">
                        {repair.proposed_value !== null && repair.proposed_value !== '' ? (
                          repair.proposed_value
                        ) : (
                          <span className="text-amber-400/90 italic font-sans text-xs">
                            [Requires Manual Input before Approval]
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Explanation text */}
                <p className="text-xs text-slate-300 leading-relaxed font-sans">
                  {repair.explanation}
                </p>

                {/* Action Buttons */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/80">
                  <div className="text-[11px] text-slate-500 font-mono">
                    Confidence: <strong className="text-slate-300">{repair.confidence}</strong>
                  </div>

                  {repair.status !== 'applied' ? (
                    <div className="flex items-center gap-2">
                      {repair.status !== 'approved' && (
                        <button
                          onClick={() => handleApprove(repair.repair_id)}
                          disabled={actionLoading || !repair.proposed_value}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600/90 hover:bg-emerald-600 disabled:opacity-40 text-white text-xs font-semibold transition cursor-pointer"
                          title={!repair.proposed_value ? 'Please edit and provide a proposed value first.' : 'Approve repair'}
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Approve</span>
                        </button>
                      )}

                      {repair.status !== 'rejected' && (
                        <button
                          onClick={() => handleReject(repair.repair_id)}
                          disabled={actionLoading}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-600/80 hover:bg-rose-600 disabled:opacity-40 text-white text-xs font-semibold transition cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="text-xs text-indigo-400 flex items-center gap-1.5 font-semibold">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>Applied to working dataset</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Confirmation Modal for Applying Approved Repairs */}
      {showApplyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Confirm Repair Application</h3>
                <p className="text-xs text-slate-400">Strict Non-Destructive Execution</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 text-xs text-slate-300 space-y-2 leading-relaxed">
              <p>
                You are about to apply <strong>{summary.approved} approved repairs</strong> to this dataset.
              </p>
              <ul className="list-disc list-inside text-slate-400 space-y-1">
                <li>Changes are written to a <strong>separate working copy</strong>.</li>
                <li>Your original uploaded file remains <strong>permanently untouched</strong>.</li>
                <li>Pending and rejected repairs will not be applied.</li>
              </ul>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowApplyModal(false)}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
              >
                Cancel
              </button>

              <button
                onClick={handleApplyApproved}
                disabled={actionLoading}
                className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold transition shadow-lg shadow-emerald-600/25 flex items-center gap-2"
              >
                {actionLoading ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                <span>{actionLoading ? 'Applying...' : 'Confirm & Apply'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Repaired Dataset Preview Modal */}
      {showPreviewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-5xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                  <span>Repaired Working Dataset Preview</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Live slice of the cleaned working copy ({previewData?.total_rows?.toLocaleString() || 0} total rows)
                </p>
              </div>
              <button
                onClick={() => setShowPreviewModal(false)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-5">
              {previewLoading ? (
                <div className="py-12 text-center text-xs text-slate-400">Loading preview...</div>
              ) : previewData?.rows?.length > 0 ? (
                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-950 border-b border-slate-800 text-slate-400 font-mono">
                        <th className="p-2.5">#</th>
                        {previewData.columns.map((col) => (
                          <th key={col} className="p-2.5 font-semibold text-slate-200">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {previewData.rows.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/30">
                          <td className="p-2.5 text-slate-500">{row._row_index}</td>
                          {previewData.columns.map((col) => (
                            <td key={col} className="p-2.5 text-slate-300 truncate max-w-xs">
                              {row[col] !== null ? String(row[col]) : <span className="text-slate-600 italic">null</span>}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-12 text-center text-xs text-slate-400">No rows available in repaired dataset.</div>
              )}
            </div>

            <div className="p-4 border-t border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-400 font-mono">
                Page {previewData?.page || 1} of {previewData?.total_pages || 1}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => fetchPreview(previewPage - 1)}
                  disabled={previewPage <= 1 || previewLoading}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs text-white"
                >
                  Previous
                </button>
                <button
                  onClick={() => fetchPreview(previewPage + 1)}
                  disabled={previewPage >= (previewData?.total_pages || 1) || previewLoading}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs text-white"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
