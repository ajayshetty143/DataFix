import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Info, 
  XCircle, 
  CheckCircle2, 
  Filter, 
  Search, 
  RotateCw, 
  Layers, 
  Copy, 
  Calendar, 
  Type, 
  TrendingUp, 
  FileText, 
  ChevronRight, 
  X,
  ExternalLink,
  SlidersHorizontal,
  HelpCircle
} from 'lucide-react';
import { datasetApi } from '../services/api';

const CATEGORY_META = {
  missing_value: {
    label: 'Missing Values',
    icon: XCircle,
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  },
  duplicate: {
    label: 'Duplicate Records',
    icon: Copy,
    color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  },
  invalid_format: {
    label: 'Invalid Formats',
    icon: Type,
    color: 'text-red-400 bg-red-500/10 border-red-500/20',
  },
  inconsistency: {
    label: 'Categorical Inconsistencies',
    icon: SlidersHorizontal,
    color: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  },
  statistical_anomaly: {
    label: 'Statistical Anomalies',
    icon: TrendingUp,
    color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  },
};

const SEVERITY_META = {
  critical: {
    label: 'Critical',
    badge: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    indicator: 'bg-rose-500',
  },
  warning: {
    label: 'Warning',
    badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    indicator: 'bg-amber-400',
  },
  info: {
    label: 'Informational',
    badge: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    indicator: 'bg-blue-400',
  },
};

export default function QualityDashboard({ datasetId, onNavigateToPreview }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIssue, setSelectedIssue] = useState(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchQuality = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await datasetApi.getQualityReport(datasetId);
      setReport(data);
      if (data?.summary?.issues?.length > 0) {
        setSelectedIssue(data.summary.issues[0]);
      }
    } catch (err) {
      console.error('Failed to load quality report:', err);
      setError(err.message || 'Unable to load data quality report.');
    } finally {
      setLoading(false);
    }
  };

  const reanalyze = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await datasetApi.analyzeQuality(datasetId);
      setReport(data);
      if (data?.summary?.issues?.length > 0) {
        setSelectedIssue(data.summary.issues[0]);
      }
    } catch (err) {
      console.error('Re-analysis failed:', err);
      setError(err.message || 'Failed to re-analyze dataset.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuality();
  }, [datasetId]);

  if (loading && !report) {
    return (
      <div className="bg-slate-800/40 border border-slate-800 rounded-3xl p-12 text-center space-y-4">
        <RotateCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
        <h3 className="text-lg font-bold text-white">Running Intelligent Detection Engine...</h3>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Scanning missing values, identifying exact & potential duplicates, testing formats, clustering categorical inconsistencies, and checking statistical bounds.
        </p>
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="bg-rose-500/10 border border-rose-500/20 rounded-3xl p-8 text-center space-y-4">
        <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto" />
        <h3 className="text-lg font-bold text-rose-300">Analysis Failed</h3>
        <p className="text-xs sm:text-sm text-rose-200/90">{error}</p>
        <button
          onClick={fetchQuality}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-xl transition"
        >
          Retry Analysis
        </button>
      </div>
    );
  }

  const summary = report?.summary;
  const issues = summary?.issues || [];

  // Filter issues
  const filteredIssues = issues.filter((iss) => {
    const matchesCat = categoryFilter === 'all' || iss.category === categoryFilter;
    const matchesSev = severityFilter === 'all' || iss.severity === severityFilter;
    const matchesSearch =
      searchTerm === '' ||
      iss.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      iss.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (iss.column && iss.column.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesCat && matchesSev && matchesSearch;
  });

  const qualityScore = summary?.quality_score ?? 100;
  const scoreColor =
    qualityScore >= 85
      ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
      : qualityScore >= 65
      ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
      : 'text-rose-400 border-rose-500/30 bg-rose-500/10';

  return (
    <div className="space-y-6">
      {/* Top Banner: Quality Score & Metrics Strip */}
      <div className="bg-slate-800/40 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-sm shadow-xl space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-700/50">
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 rounded-2xl border flex flex-col items-center justify-center font-mono ${scoreColor}`}>
              <span className="text-2xl font-black">{qualityScore}</span>
              <span className="text-[10px] uppercase font-bold tracking-wider">Score</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-white tracking-tight">Data Quality Intelligence</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Deterministic Audit
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 mt-1">
                Deterministic detection across 5 dimensions: missing values, duplicates, format violations, inconsistencies, and statistical anomalies.
              </p>
            </div>
          </div>

          <button
            onClick={reanalyze}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/20 cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Analyzing...' : 'Re-run Detection Engine'}
          </button>
        </div>

        {/* 4 Diagnostic Metric Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Issues */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Total Issues</span>
            <div className="mt-2 text-2xl font-bold text-white font-mono">
              {summary?.total_issues ?? 0}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">Identified anomalies</span>
          </div>

          {/* Affected Rows */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Affected Rows</span>
            <div className="mt-2 text-2xl font-bold text-white font-mono">
              {summary?.total_affected_rows ?? 0}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">
              {report?.total_rows
                ? `${Math.round(((summary?.total_affected_rows ?? 0) / report.total_rows) * 100)}% of dataset`
                : '0% of dataset'}
            </span>
          </div>

          {/* Affected Columns */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Affected Columns</span>
            <div className="mt-2 text-2xl font-bold text-white font-mono">
              {summary?.total_affected_columns ?? 0}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">
              {report?.total_columns
                ? `${Math.round(((summary?.total_affected_columns ?? 0) / report.total_columns) * 100)}% of schema`
                : '0% of schema'}
            </span>
          </div>

          {/* Severity Breakdown */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
            <span className="text-xs text-slate-400 font-medium">Severity Distribution</span>
            <div className="mt-2 flex items-center gap-2">
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono font-bold">
                {summary?.by_severity?.critical ?? 0} Crit
              </span>
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono font-bold">
                {summary?.by_severity?.warning ?? 0} Warn
              </span>
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono font-bold">
                {summary?.by_severity?.info ?? 0} Info
              </span>
            </div>
            <span className="text-xs text-slate-500 mt-1 block">Prioritized triage</span>
          </div>
        </div>

        {/* Category Pills Strip */}
        <div className="flex flex-wrap items-center gap-2 pt-2">
          {Object.entries(CATEGORY_META).map(([catKey, catMeta]) => {
            const count = summary?.by_category?.[catKey] ?? 0;
            const Icon = catMeta.icon;
            const isSelected = categoryFilter === catKey;

            return (
              <button
                key={catKey}
                onClick={() => setCategoryFilter(isSelected ? 'all' : catKey)}
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                  isSelected
                    ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-600/20 scale-102'
                    : 'bg-slate-900/80 text-slate-300 border-slate-700/80 hover:bg-slate-800'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{catMeta.label}</span>
                <span className={`px-1.5 py-0.2 rounded-md font-mono text-[11px] ${isSelected ? 'bg-indigo-900 text-white' : 'bg-slate-800 text-indigo-400'}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Analysis Section: Filter Bar + 2-Column Inspector */}
      <div className="space-y-4">
        {/* Filter Controls Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 border border-slate-800 p-3 rounded-2xl">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search issues or columns..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Informational</option>
            </select>

            {(categoryFilter !== 'all' || severityFilter !== 'all' || searchTerm !== '') && (
              <button
                onClick={() => {
                  setCategoryFilter('all');
                  setSeverityFilter('all');
                  setSearchTerm('');
                }}
                className="text-xs text-indigo-400 hover:text-indigo-300 px-2 py-1 rounded-lg"
              >
                Reset Filters
              </button>
            )}
          </div>
        </div>

        {/* 2-Column Layout: Left Issue List, Right Issue Inspector */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Issue Cards List (7 Cols) */}
          <div className="lg:col-span-7 space-y-3">
            {filteredIssues.length === 0 ? (
              <div className="bg-slate-800/20 border border-slate-800 rounded-2xl p-8 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <h4 className="text-sm font-semibold text-white">No Issues Matching Filter</h4>
                <p className="text-xs text-slate-400">Try adjusting your category or severity filters.</p>
              </div>
            ) : (
              filteredIssues.map((issue) => {
                const catMeta = CATEGORY_META[issue.category] || {
                  label: issue.category,
                  icon: HelpCircle,
                  color: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
                };
                const CatIcon = catMeta.icon;
                const sevMeta = SEVERITY_META[issue.severity] || SEVERITY_META.info;
                const isSelected = selectedIssue?.id === issue.id;

                return (
                  <div
                    key={issue.id}
                    onClick={() => setSelectedIssue(issue)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-slate-800/90 border-indigo-500 shadow-lg shadow-indigo-500/10 scale-[1.01]'
                        : 'bg-slate-900/60 hover:bg-slate-800/50 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${sevMeta.indicator}`} />
                        <span className="font-mono text-[11px] font-bold text-slate-400">{issue.id}</span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-semibold ${catMeta.color}`}>
                          <CatIcon className="w-3 h-3" />
                          <span>{catMeta.label}</span>
                        </span>
                        {issue.column && (
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-950 text-indigo-300 border border-slate-800">
                            {issue.column}
                          </span>
                        )}
                      </div>

                      <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border font-mono ${sevMeta.badge}`}>
                        {sevMeta.label}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-white mt-2 group-hover:text-indigo-300">
                      {issue.title}
                    </h4>

                    <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                      {issue.description}
                    </p>

                    <div className="mt-3 flex items-center justify-between text-xs text-slate-500 border-t border-slate-800/60 pt-2 font-mono">
                      <span>Affected rows: <strong className="text-slate-300">{issue.affected_count.toLocaleString()}</strong></span>
                      <span className="text-indigo-400 flex items-center gap-1 hover:underline">
                        Inspect Details <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Right Column: Detailed Issue Inspection Panel (5 Cols) */}
          <div className="lg:col-span-5 sticky top-20">
            {selectedIssue ? (
              <div className="bg-slate-800/50 border border-slate-700/80 rounded-3xl p-6 shadow-2xl space-y-5">
                <div className="flex items-start justify-between border-b border-slate-700/60 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400">{selectedIssue.id}</span>
                      <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border font-mono ${SEVERITY_META[selectedIssue.severity]?.badge}`}>
                        {selectedIssue.severity}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-white mt-1">{selectedIssue.title}</h3>
                  </div>
                </div>

                {/* Description */}
                <div>
                  <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Issue Analysis</h5>
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-xl border border-slate-800 font-sans">
                    {selectedIssue.description}
                  </p>
                </div>

                {/* Suggested Action */}
                {selectedIssue.suggested_action && (
                  <div>
                    <h5 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">Recommendation</h5>
                    <div className="text-xs text-indigo-200/90 bg-indigo-500/10 border border-indigo-500/20 p-3 rounded-xl leading-relaxed">
                      {selectedIssue.suggested_action}
                    </div>
                  </div>
                )}

                {/* Affected Row Indices */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Affected Row Indices ({selectedIssue.row_indices?.length || 0})
                    </h5>
                  </div>
                  <div className="max-h-28 overflow-y-auto p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex flex-wrap gap-1.5 font-mono text-[11px]">
                    {selectedIssue.row_indices?.map((r) => (
                      <span
                        key={r}
                        className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300"
                      >
                        Row {r}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Sample / Raw Values */}
                {selectedIssue.sample_values && selectedIssue.sample_values.length > 0 && (
                  <div>
                    <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                      Flagged Sample Values
                    </h5>
                    <div className="max-h-36 overflow-y-auto p-2.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1 font-mono text-[11px] text-emerald-400">
                      {selectedIssue.sample_values.map((val, i) => (
                        <div key={i} className="truncate">
                          &bull; {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Trigger */}
                {onNavigateToPreview && (
                  <button
                    onClick={() => onNavigateToPreview(selectedIssue)}
                    className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition cursor-pointer shadow-lg shadow-indigo-600/20"
                  >
                    <span>Inspect Records in Data Preview</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ) : (
              <div className="bg-slate-800/30 border border-slate-800 rounded-3xl p-8 text-center text-slate-500 text-xs">
                Select an issue on the left to inspect detailed diagnostic metadata.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
