import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  RotateCw,
  Search,
  FileSpreadsheet,
  FileText,
  FileCode,
  ShieldCheck,
  ArrowRight,
  TrendingUp,
  Clock,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Filter,
  Check,
  Info
} from 'lucide-react';
import { datasetApi } from '../services/api';

export default function ValidationExport({ datasetId, onNavigateToRepairs, onNavigateToPreview }) {
  const [report, setReport] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [revalidating, setRevalidating] = useState(false);
  const [error, setError] = useState(null);

  // Filters for Audit Log
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [exportFormat, setExportFormat] = useState('csv');

  // Accordion toggles
  const [showResolved, setShowResolved] = useState(true);
  const [showRemaining, setShowRemaining] = useState(true);

  const fetchValidationData = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch validation report
      const valData = await datasetApi.getValidation(datasetId);
      setReport(valData);

      // 2. Fetch modification audit log
      const logData = await datasetApi.getAuditLog(datasetId);
      setAuditLog(logData.entries || []);
    } catch (err) {
      console.error('Validation fetch error:', err);
      setError(err.message || 'Unable to retrieve validation and audit log.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevalidate = async () => {
    setRevalidating(true);
    try {
      const updated = await datasetApi.runValidation(datasetId);
      setReport(updated);
      const logData = await datasetApi.getAuditLog(datasetId);
      setAuditLog(logData.entries || []);
    } catch (err) {
      alert(err.message || 'Failed to re-validate dataset.');
    } finally {
      setRevalidating(false);
    }
  };

  useEffect(() => {
    fetchValidationData();
  }, [datasetId]);

  // Filtered audit log
  const filteredAudit = auditLog.filter((entry) => {
    const matchesStatus = statusFilter === 'all' || entry.status === statusFilter;
    const q = searchQuery.toLowerCase().trim();
    if (!q) return matchesStatus;
    const matchesSearch =
      (entry.repair_id && entry.repair_id.toLowerCase().includes(q)) ||
      (entry.issue_id && entry.issue_id.toLowerCase().includes(q)) ||
      (entry.column_name && entry.column_name.toLowerCase().includes(q)) ||
      (entry.action && entry.action.toLowerCase().includes(q)) ||
      (entry.original_value && entry.original_value.toLowerCase().includes(q)) ||
      (entry.new_value && entry.new_value.toLowerCase().includes(q));
    return matchesStatus && matchesSearch;
  });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4 bg-slate-900/60 rounded-3xl border border-slate-800">
        <RotateCw className="w-8 h-8 text-indigo-400 animate-spin" />
        <p className="text-sm font-semibold text-slate-300">Auditing repaired dataset & verifying quality score improvement...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-slate-900/60 rounded-3xl border border-rose-500/30 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-base font-bold text-white">Validation Unavailable</h3>
        <p className="text-sm text-slate-400 max-w-lg mx-auto">{error}</p>
        <div className="flex items-center justify-center gap-3 pt-2">
          {onNavigateToRepairs && (
            <button
              onClick={onNavigateToRepairs}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition"
            >
              Go to Repair Center
            </button>
          )}
          <button
            onClick={fetchValidationData}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const isClean = report?.is_fully_clean;
  const scoreDelta = report?.score_improvement || 0;

  return (
    <div className="space-y-8">
      {/* 1. Header & Re-validate Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xl">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-semibold mb-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Phase 6: Post-Repair Quality Audit & Export</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-white">Validation & Export Center</h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Independent verification comparing original vs. repaired datasets. Cleaned data is isolated in a separate working copy.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRevalidate}
            disabled={revalidating}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 transition disabled:opacity-50"
          >
            <RotateCw className={`w-3.5 h-3.5 ${revalidating ? 'animate-spin text-indigo-400' : ''}`} />
            <span>{revalidating ? 'Re-validating...' : 'Re-run Validation'}</span>
          </button>

          {onNavigateToPreview && (
            <button
              onClick={onNavigateToPreview}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-xs font-semibold text-indigo-300 transition"
            >
              <span>Preview Cleaned Data</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* 2. Validation Status Banner */}
      <div className={`p-6 rounded-3xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-lg ${
        isClean
          ? 'bg-gradient-to-r from-emerald-950/40 via-slate-900 to-emerald-950/40 border-emerald-500/30'
          : 'bg-gradient-to-r from-amber-950/40 via-slate-900 to-slate-900 border-amber-500/30'
      }`}>
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 border ${
            isClean
              ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
              : 'bg-amber-500/20 border-amber-500/40 text-amber-400'
          }`}>
            {isClean ? <CheckCircle2 className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-bold text-white">
              {isClean ? 'Dataset Certified 100% Clean' : 'Repairs Applied — Issues Partially Resolved'}
            </h3>
            <p className="text-xs sm:text-sm text-slate-300 mt-0.5">
              {isClean
                ? 'Deterministic detection engine confirms zero data quality anomalies remain in the working copy.'
                : `${report?.remaining_issues_count || 0} issue(s) still remain in the working dataset. Human review is recommended for unresolved anomalies.`
              }
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6 px-4 py-3 rounded-2xl bg-slate-950/60 border border-slate-800">
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Original Score</p>
            <p className="text-lg font-extrabold text-slate-300 font-mono">{report?.original_quality_score}/100</p>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-500" />
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Repaired Score</p>
            <p className="text-lg font-extrabold text-emerald-400 font-mono">{report?.repaired_quality_score}/100</p>
          </div>
          <div className="pl-2 border-l border-slate-800">
            <span className={`text-xs font-bold font-mono px-2 py-1 rounded-lg ${
              scoreDelta >= 0 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
            }`}>
              {scoreDelta >= 0 ? `+${scoreDelta}` : scoreDelta} pts
            </span>
          </div>
        </div>
      </div>

      {/* 3. Export Packages Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Download className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Export Verified Deliverables</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Original upload remains unchanged</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Cleaned CSV */}
          <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 transition shadow-md flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-white">Cleaned Dataset (CSV)</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Download the fully repaired working copy with all user-approved imputations, deduplications, and standardizations applied.
              </p>
            </div>
            <div className="pt-6">
              <a
                href={datasetApi.getCleanedCsvDownloadUrl(datasetId)}
                download
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shadow-lg shadow-indigo-600/25"
              >
                <Download className="w-4 h-4" />
                <span>Download Cleaned CSV</span>
              </a>
            </div>
          </div>

          {/* Card 2: Full Quality Audit Report */}
          <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 hover:border-violet-500/40 transition shadow-md flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-4">
                <FileCode className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-white">Quality Audit Report (JSON)</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Export comprehensive machine-readable report containing pre/post quality scores, resolved issues, remaining issues, and audit metadata.
              </p>
            </div>
            <div className="pt-6">
              <a
                href={datasetApi.getQualityReportDownloadUrl(datasetId, 'json')}
                download
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition shadow-lg shadow-violet-600/25"
              >
                <Download className="w-4 h-4" />
                <span>Download Report (JSON)</span>
              </a>
            </div>
          </div>

          {/* Card 3: Modification History Log */}
          <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 hover:border-emerald-500/40 transition shadow-md flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-2xl bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4">
                <FileText className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-white">Modification Audit Log</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Export every recorded repair action: row indices, columns, original values, modified values, approvals, and timestamps.
              </p>
            </div>
            <div className="pt-6 flex gap-2">
              <a
                href={datasetApi.getAuditLogDownloadUrl(datasetId, 'csv')}
                download
                className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shadow-lg shadow-emerald-600/25"
              >
                <Download className="w-3.5 h-3.5" />
                <span>CSV</span>
              </a>
              <a
                href={datasetApi.getAuditLogDownloadUrl(datasetId, 'json')}
                download
                className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>JSON</span>
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Resolved vs Remaining Issues Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Resolved Issues Panel */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
          <div
            onClick={() => setShowResolved(!showResolved)}
            className="flex items-center justify-between cursor-pointer select-none"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white">
                Resolved Issues ({report?.resolved_issues_count || 0})
              </h3>
            </div>
            {showResolved ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </div>

          {showResolved && (
            <div className="space-y-3">
              {report?.resolved_issues?.length > 0 ? (
                report.resolved_issues.map((iss, i) => (
                  <div key={i} className="p-3.5 rounded-2xl bg-emerald-950/20 border border-emerald-500/20 flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-900/50 text-emerald-300 font-bold">
                          {iss.issue_id}
                        </span>
                        <span className="text-xs font-semibold text-emerald-200">
                          {iss.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">{iss.description}</p>
                    </div>
                    <span className="text-[11px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 flex-shrink-0">
                      Resolved
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 italic p-4 text-center">No issues were resolved in this run.</p>
              )}
            </div>
          )}
        </div>

        {/* Remaining Issues Panel */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
          <div
            onClick={() => setShowRemaining(!showRemaining)}
            className="flex items-center justify-between cursor-pointer select-none"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-white">
                Remaining Issues ({report?.remaining_issues_count || 0})
              </h3>
            </div>
            {showRemaining ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </div>

          {showRemaining && (
            <div className="space-y-3">
              {report?.remaining_issues?.length > 0 ? (
                report.remaining_issues.map((iss, i) => (
                  <div key={i} className="p-3.5 rounded-2xl bg-amber-950/20 border border-amber-500/20 flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-900/50 text-amber-300 font-bold">
                          {iss.id || `ISS-${i + 1}`}
                        </span>
                        <span className="text-xs font-semibold text-amber-200">
                          {iss.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">{iss.description}</p>
                    </div>
                    <span className="text-[11px] font-mono font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 flex-shrink-0">
                      {iss.severity}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center space-y-2 bg-emerald-950/10 rounded-2xl border border-emerald-500/10">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <p className="text-xs font-semibold text-emerald-300">Zero remaining quality issues!</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 5. Interactive Modification Audit Log Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              <span>Modification Audit Log ({auditLog.length} Records)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic log recording row-level original values, applied changes, and human approval states.
            </p>
          </div>

          {/* Search & Filter Controls */}
          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search repairs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Statuses</option>
              <option value="applied">Applied</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {/* Audit Log Table */}
        <div className="overflow-x-auto rounded-2xl border border-slate-800">
          <table className="min-w-full divide-y divide-slate-800 text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="px-4 py-3">Repair ID</th>
                <th className="px-4 py-3">Issue ID</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Original Value</th>
                <th className="px-4 py-3">Modified Value</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Action Description</th>
                <th className="px-4 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-slate-900/40 text-slate-300 font-mono">
              {filteredAudit.length > 0 ? (
                filteredAudit.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-bold text-indigo-300">{item.repair_id}</td>
                    <td className="px-4 py-3 text-slate-400">{item.issue_id}</td>
                    <td className="px-4 py-3 font-sans text-slate-200">
                      <span className="text-slate-400 text-[11px]">Row {item.row_number}</span>
                      {item.column_name && (
                        <span className="ml-1 text-slate-200 font-semibold">&bull; {item.column_name}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-rose-300/80 max-w-[120px] truncate" title={item.original_value}>
                      {item.original_value || '<empty>'}
                    </td>
                    <td className="px-4 py-3 text-emerald-300 font-semibold max-w-[120px] truncate" title={item.new_value}>
                      {item.new_value || '<none>'}
                    </td>
                    <td className="px-4 py-3 font-sans">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                        item.status === 'applied' ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' :
                        item.status === 'approved' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                        item.status === 'rejected' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                        'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-sans text-[11px] text-slate-400 max-w-[220px] truncate" title={item.action}>
                      {item.action}
                    </td>
                    <td className="px-4 py-3 text-[10px] text-slate-500 font-sans whitespace-nowrap">
                      {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : 'N/A'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-500 font-sans text-xs">
                    No audit records match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
