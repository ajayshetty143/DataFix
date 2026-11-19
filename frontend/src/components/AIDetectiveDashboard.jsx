import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  RotateCw,
  AlertTriangle,
  CheckCircle2,
  Search,
  ShieldAlert,
  ShieldCheck,
  HelpCircle,
  Lightbulb,
  Cpu,
  ChevronRight,
  SlidersHorizontal,
  XCircle,
  Copy,
  Type,
  TrendingUp,
  FileSpreadsheet,
  AlertCircle,
  ExternalLink,
  Wrench
} from 'lucide-react';
import { datasetApi } from '../services/api';

const CATEGORY_META = {
  missing_value: {
    label: 'Missing Value',
    icon: XCircle,
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  },
  duplicate: {
    label: 'Duplicate',
    icon: Copy,
    color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  },
  invalid_format: {
    label: 'Invalid Format',
    icon: Type,
    color: 'text-red-400 bg-red-500/10 border-red-500/20',
  },
  inconsistency: {
    label: 'Inconsistency',
    icon: SlidersHorizontal,
    color: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  },
  statistical_anomaly: {
    label: 'Statistical Anomaly',
    icon: TrendingUp,
    color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  },
};

export default function AIDetectiveDashboard({ datasetId, initialSelectedIssueId, onNavigateToQuality, onNavigateToRepairs }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRec, setSelectedRec] = useState(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState('all');
  const [reviewFilter, setReviewFilter] = useState('all');

  const fetchAIReport = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await datasetApi.getAIDetective(datasetId);
      setReport(data);
      if (data?.recommendations?.length > 0) {
        if (initialSelectedIssueId) {
          const match = data.recommendations.find(r => r.issue_id === initialSelectedIssueId);
          setSelectedRec(match || data.recommendations[0]);
        } else {
          setSelectedRec(data.recommendations[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load AI Detective report:', err);
      setError(err.message || 'Unable to generate Gemini AI Detective report.');
    } finally {
      setLoading(false);
    }
  };

  const rerunAnalysis = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await datasetApi.runAIDetective(datasetId);
      setReport(data);
      if (data?.recommendations?.length > 0) {
        setSelectedRec(data.recommendations[0]);
      }
    } catch (err) {
      console.error('AI Detective re-analysis failed:', err);
      setError(err.message || 'Failed to re-run AI Detective analysis.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAIReport();
  }, [datasetId]);

  // Loading State
  if (loading && !report) {
    return (
      <div className="bg-slate-800/40 border border-slate-800 rounded-3xl p-12 text-center space-y-6 backdrop-blur-sm">
        <div className="relative w-16 h-16 mx-auto">
          <div className="absolute inset-0 rounded-2xl bg-indigo-500/20 animate-ping" />
          <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-xl shadow-indigo-500/30">
            <Sparkles className="w-8 h-8 animate-pulse" />
          </div>
        </div>
        <div className="space-y-2 max-w-lg mx-auto">
          <h3 className="text-xl font-bold text-white tracking-tight">Gemini AI Detective is Investigating...</h3>
          <p className="text-sm text-slate-300 leading-relaxed">
            Formulating root-cause hypotheses, evaluating data capture omissions, and structuring contextual remediation strategies for detected anomalies.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900/80 border border-slate-700/80 text-xs font-mono text-indigo-300">
          <RotateCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
          <span>Synthesizing root cause reasoning with Google Gemini</span>
        </div>
      </div>
    );
  }

  // Error State
  if (error && !report) {
    return (
      <div className="bg-rose-500/10 border border-rose-500/20 rounded-3xl p-8 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-lg font-bold text-rose-300">AI Detective Unavailable</h3>
        <p className="text-xs sm:text-sm text-rose-200/90 max-w-xl mx-auto leading-relaxed">{error}</p>
        <div className="pt-2">
          <button
            onClick={fetchAIReport}
            className="px-5 py-2.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-rose-600/20 inline-flex items-center gap-2 cursor-pointer"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span>Retry AI Analysis</span>
          </button>
        </div>
      </div>
    );
  }

  const recommendations = report?.recommendations || [];

  // Filter recommendations
  const filteredRecs = recommendations.filter((rec) => {
    const matchesConf = confidenceFilter === 'all' || rec.confidence.toLowerCase() === confidenceFilter.toLowerCase();
    const matchesRev =
      reviewFilter === 'all' ||
      (reviewFilter === 'review' && rec.human_review_required) ||
      (reviewFilter === 'automated' && !rec.human_review_required);
    const matchesSearch =
      searchTerm === '' ||
      rec.issue_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rec.explanation.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rec.possible_root_cause.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rec.recommended_action.toLowerCase().includes(searchTerm.toLowerCase());

    return matchesConf && matchesRev && matchesSearch;
  });

  const highConfCount = recommendations.filter(r => r.confidence === 'High').length;
  const reviewNeededCount = recommendations.filter(r => r.human_review_required).length;

  return (
    <div className="space-y-6">
      {/* Top Banner: Advisory Safety Notice */}
      <div className="bg-gradient-to-r from-indigo-950/40 via-purple-950/30 to-slate-900 border border-indigo-500/30 rounded-3xl p-6 sm:p-8 backdrop-blur-sm shadow-xl space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-700/50">
          <div className="flex items-start sm:items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-indigo-600/20 flex-shrink-0">
              <Sparkles className="w-7 h-7" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Gemini AI Detective</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-violet-500/10 text-violet-300 border border-violet-500/20">
                  {report?.model_used ? `Model: ${report.model_used}` : 'Google Gemini Powered'}
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 mt-1 leading-relaxed">
                Autonomous diagnostic intelligence providing root-cause explanations and contextual remediation recommendations.
              </p>
            </div>
          </div>

          <button
            onClick={rerunAnalysis}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/20 cursor-pointer flex-shrink-0"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Consulting Gemini...' : 'Re-run AI Detective'}</span>
          </button>
        </div>

        {/* Advisory Non-Destructive Notice */}
        <div className="flex items-start gap-3 p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-slate-300 text-xs leading-relaxed">
          <ShieldCheck className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
          <div>
            <strong className="text-white font-semibold">Advisory & Non-Destructive: </strong>
            AI recommendations are strategic diagnostic insights for human evaluation. No dataset modifications or automated repairs are applied in this phase; original uploaded files remain strictly preserved.
          </div>
        </div>

        {/* Executive Summary Card */}
        {report?.executive_summary && (
          <div className="p-5 rounded-2xl bg-indigo-950/20 border border-indigo-500/30 space-y-2">
            <div className="flex items-center gap-2 text-indigo-300 text-xs font-bold uppercase tracking-wider">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <span>AI Executive Diagnostic Summary</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-sans">
              {report.executive_summary}
            </p>
          </div>
        )}

        {/* 3 Metric Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Total AI Recommendations</span>
            <div className="mt-2 text-2xl font-bold text-white font-mono">
              {report?.total_recommendations ?? 0}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">Mapped 1:1 to detected issues</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">High Confidence Solutions</span>
            <div className="mt-2 text-2xl font-bold text-emerald-400 font-mono">
              {highConfCount}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">Unambiguous pattern matches</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Human Oversight Recommended</span>
            <div className="mt-2 text-2xl font-bold text-amber-400 font-mono">
              {reviewNeededCount}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">Requires domain stakeholder signoff</span>
          </div>
        </div>
      </div>

      {/* Zero Issues Clean State */}
      {recommendations.length === 0 ? (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-3xl p-12 text-center space-y-4">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
          <h3 className="text-lg font-bold text-emerald-300">Zero Quality Issues Detected</h3>
          <p className="text-xs sm:text-sm text-emerald-200/90 max-w-md mx-auto">
            The dataset has been completely vetted by the deterministic engine and AI Detective. No anomalies were found, and no repair actions are required.
          </p>
        </div>
      ) : (
        /* Main Investigation Interface */
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 border border-slate-800 p-3 rounded-2xl">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search explanations, root causes, or actions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={confidenceFilter}
                onChange={(e) => setConfidenceFilter(e.target.value)}
                className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Confidence Levels</option>
                <option value="high">High Confidence</option>
                <option value="medium">Medium Confidence</option>
                <option value="low">Low Confidence</option>
              </select>

              <select
                value={reviewFilter}
                onChange={(e) => setReviewFilter(e.target.value)}
                className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Review States</option>
                <option value="review">Needs Human Review</option>
                <option value="automated">Standard Candidate</option>
              </select>

              {(confidenceFilter !== 'all' || reviewFilter !== 'all' || searchTerm !== '') && (
                <button
                  onClick={() => {
                    setConfidenceFilter('all');
                    setReviewFilter('all');
                    setSearchTerm('');
                  }}
                  className="text-xs text-indigo-400 hover:text-indigo-300 px-2 py-1 rounded-lg"
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* 2-Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: AI Recommendation Cards (7 Cols) */}
            <div className="lg:col-span-7 space-y-3">
              {filteredRecs.length === 0 ? (
                <div className="bg-slate-800/20 border border-slate-800 rounded-2xl p-8 text-center space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <h4 className="text-sm font-semibold text-white">No Recommendations Match Filter</h4>
                  <p className="text-xs text-slate-400">Try adjusting your search query or filters.</p>
                </div>
              ) : (
                filteredRecs.map((rec) => {
                  const catMeta = CATEGORY_META[rec.issue_category] || {
                    label: rec.issue_category,
                    icon: HelpCircle,
                    color: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
                  };
                  const CatIcon = catMeta.icon;
                  const isSelected = selectedRec?.issue_id === rec.issue_id;

                  const confBadge =
                    rec.confidence === 'High'
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      : rec.confidence === 'Medium'
                      ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                      : 'bg-slate-500/15 text-slate-400 border-slate-500/30';

                  return (
                    <div
                      key={rec.issue_id}
                      onClick={() => setSelectedRec(rec)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-slate-800/90 border-violet-500 shadow-lg shadow-violet-500/10 scale-[1.01]'
                          : 'bg-slate-900/60 hover:bg-slate-800/50 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-[11px] font-bold text-violet-400">{rec.issue_id}</span>
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-semibold ${catMeta.color}`}>
                            <CatIcon className="w-3 h-3" />
                            <span>{catMeta.label}</span>
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border font-mono ${confBadge}`}>
                            {rec.confidence} Confidence
                          </span>
                          {rec.human_review_required ? (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                              <AlertCircle className="w-3 h-3" />
                              <span>Review</span>
                            </span>
                          ) : (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              <span>Standard</span>
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Explanation Teaser */}
                      <p className="text-xs sm:text-sm text-slate-200 mt-2 font-medium leading-relaxed">
                        {rec.explanation}
                      </p>

                      {/* Root Cause & Action Pills */}
                      <div className="mt-3 space-y-1.5 border-t border-slate-800/60 pt-2 text-xs">
                        <div className="flex items-start gap-1.5 text-slate-400">
                          <HelpCircle className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                          <span className="truncate">
                            <strong className="text-slate-300">Root Cause:</strong> {rec.possible_root_cause}
                          </span>
                        </div>
                        <div className="flex items-start gap-1.5 text-indigo-300">
                          <Lightbulb className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                          <span className="truncate">
                            <strong className="text-indigo-200">Recommended:</strong> {rec.recommended_action}
                          </span>
                        </div>
                      </div>

                      <div className="mt-2 text-right">
                        <span className="text-[11px] text-violet-400 inline-flex items-center gap-1 hover:underline">
                          View Full AI Dossier <ChevronRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Right Column: Detailed AI Dossier Inspector (5 Cols) */}
            <div className="lg:col-span-5 sticky top-20">
              {selectedRec ? (
                <div className="bg-slate-800/50 border border-slate-700/80 rounded-3xl p-6 shadow-2xl space-y-5">
                  <div className="flex items-start justify-between border-b border-slate-700/60 pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-violet-400">{selectedRec.issue_id}</span>
                        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border font-mono ${
                          selectedRec.confidence === 'High'
                            ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                            : selectedRec.confidence === 'Medium'
                            ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                            : 'bg-slate-500/15 text-slate-400 border-slate-500/30'
                        }`}>
                          {selectedRec.confidence} Confidence
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-white mt-1">AI Diagnostic Dossier</h3>
                    </div>

                    {selectedRec.human_review_required && (
                      <span className="text-[11px] font-semibold px-2.5 py-1 rounded-xl bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5" />
                        <span>Human Review Required</span>
                      </span>
                    )}
                  </div>

                  {/* 1. Plain-English Explanation */}
                  <div>
                    <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Issue Explanation & Business Impact</span>
                    </h5>
                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3.5 rounded-xl border border-slate-800 font-sans">
                      {selectedRec.explanation}
                    </p>
                  </div>

                  {/* 2. Hypothesized Root Cause */}
                  <div>
                    <h5 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Hypothesized Root Cause</span>
                    </h5>
                    <div className="text-xs text-slate-300 bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl leading-relaxed">
                      {selectedRec.possible_root_cause}
                    </div>
                  </div>

                  {/* 3. Recommended Remediation Action */}
                  <div>
                    <h5 className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                      <span>Recommended Remediation Action</span>
                    </h5>
                    <div className="text-xs text-amber-100/90 bg-gradient-to-r from-amber-500/10 via-indigo-500/10 to-transparent border border-amber-500/30 p-3.5 rounded-xl leading-relaxed font-sans font-medium">
                      {selectedRec.recommended_action}
                    </div>
                  </div>

                  {/* 4. Justification & Reason */}
                  <div>
                    <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Reason for Recommendation</span>
                    </h5>
                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                      {selectedRec.recommendation_reason}
                    </p>
                  </div>

                  {/* 5. Domain Oversight Assessment */}
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800 text-[11px] text-slate-400 leading-relaxed flex items-center gap-2">
                    {selectedRec.human_review_required ? (
                      <>
                        <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        <span>Domain stakeholder review is advised before implementing this repair to avoid unintended business logic side-effects.</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        <span>This remediation follows deterministic standardization rules and is safe to execute as a routine operation.</span>
                      </>
                    )}
                  </div>

                  {/* Navigation Action Buttons */}
                  <div className="space-y-2 pt-1">
                    {onNavigateToRepairs && (
                      <button
                        onClick={onNavigateToRepairs}
                        className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold transition cursor-pointer shadow-lg shadow-emerald-600/20"
                      >
                        <Wrench className="w-3.5 h-3.5" />
                        <span>Open in Safe Repair Center</span>
                      </button>
                    )}

                    {onNavigateToQuality && (
                      <button
                        onClick={() => onNavigateToQuality(selectedRec.issue_id)}
                        className="w-full inline-flex items-center justify-center gap-2 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition cursor-pointer border border-slate-700"
                      >
                        <span>Cross-Reference in Quality Engine</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="bg-slate-800/30 border border-slate-800 rounded-3xl p-8 text-center text-slate-500 text-xs">
                  Select a recommendation from the left to inspect detailed diagnostic dossier.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
