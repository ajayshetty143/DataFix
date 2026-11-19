import React, { useState } from 'react';
import {
  Grid,
  Info,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ChevronRight,
  Sparkles,
  Wrench,
  Search,
  Filter,
  SlidersHorizontal,
  X
} from 'lucide-react';

const CATEGORY_COLUMNS = [
  { key: 'missing_value', label: 'Missing Values', icon: XCircle },
  { key: 'invalid_format', label: 'Invalid Formats', icon: AlertTriangle },
  { key: 'inconsistency', label: 'Inconsistencies', icon: SlidersHorizontal },
  { key: 'statistical_anomaly', label: 'Anomalies', icon: Info },
  { key: 'duplicate', label: 'Duplicates', icon: Grid },
];

const SEVERITY_STYLES = {
  healthy: {
    bg: 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    indicator: 'bg-emerald-500',
    badge: 'Healthy (0%)',
  },
  low: {
    bg: 'bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border-amber-500/30',
    indicator: 'bg-amber-400',
    badge: 'Low (≤ 5%)',
  },
  moderate: {
    bg: 'bg-orange-500/15 hover:bg-orange-500/25 text-orange-300 border-orange-500/35',
    indicator: 'bg-orange-400',
    badge: 'Moderate (5-20%)',
  },
  high: {
    bg: 'bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border-rose-500/40',
    indicator: 'bg-rose-500',
    badge: 'High (> 20%)',
  },
  na: {
    bg: 'bg-slate-900/40 text-slate-500 border-slate-800/80 hover:bg-slate-900/60',
    indicator: 'bg-slate-600',
    badge: 'N/A',
  },
};

const STATUS_BADGES = {
  healthy: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  low: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  moderate: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  high: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
};

export default function DataQualityHeatmap({
  heatmap = [],
  totalRows = 0,
  onSelectIssue,
  onConsultAIDetective,
  onNavigateToRepairs
}) {
  const [selectedCell, setSelectedCell] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filteredHeatmap = heatmap.filter((item) => {
    const matchesSearch = item.column_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || item.overall_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleCellClick = (colItem, categoryKey) => {
    const cellData = colItem.cells?.[categoryKey];
    if (!cellData) return;

    setSelectedCell({
      columnName: colItem.column_name,
      dataType: colItem.data_type,
      categoryKey,
      ...cellData,
    });
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xl space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Grid className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base sm:text-lg font-bold text-white">
              Data Quality Heatmap
            </h3>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              Interactive Matrix
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Column-by-column diagnostic health matrix across all 5 quality dimensions. Click any cell to inspect affected rows and sample values.
          </p>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Healthy (0%)</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span>Low (≤5%)</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-orange-500/10 border border-orange-500/20 text-orange-300">
            <span className="w-2 h-2 rounded-full bg-orange-400" />
            <span>Moderate (5-20%)</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300">
            <span className="w-2 h-2 rounded-full bg-rose-400" />
            <span>High (&gt;20%)</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-400">
            <span className="w-2 h-2 rounded-full bg-slate-500" />
            <span>N/A</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search column..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Columns ({heatmap.length})</option>
            <option value="healthy">Healthy Only</option>
            <option value="low">Low Severity</option>
            <option value="moderate">Moderate Severity</option>
            <option value="high">High Severity</option>
          </select>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="overflow-x-auto rounded-2xl border border-slate-800">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold tracking-wider uppercase text-[11px]">
              <th className="py-3 px-4 w-48">Column Name</th>
              <th className="py-3 px-3 w-24">Type</th>
              {CATEGORY_COLUMNS.map((cat) => (
                <th key={cat.key} className="py-3 px-3 text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <span>{cat.label}</span>
                  </div>
                </th>
              ))}
              <th className="py-3 px-4 text-center w-36">Overall Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredHeatmap.length > 0 ? (
              filteredHeatmap.map((colItem) => (
                <tr key={colItem.column_name} className="hover:bg-slate-800/30 transition">
                  {/* Column Name */}
                  <td className="py-3 px-4 font-sans font-semibold text-white">
                    <span className="truncate block max-w-[180px]" title={colItem.column_name}>
                      {colItem.column_name}
                    </span>
                  </td>

                  {/* Data Type */}
                  <td className="py-3 px-3 font-sans">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800 font-mono">
                      {colItem.data_type}
                    </span>
                  </td>

                  {/* 5 Quality Dimension Cells */}
                  {CATEGORY_COLUMNS.map((cat) => {
                    const cell = colItem.cells?.[cat.key];
                    if (!cell) {
                      return (
                        <td key={cat.key} className="py-2 px-2 text-center">
                          <span className="text-slate-600 text-xs">N/A</span>
                        </td>
                      );
                    }

                    const style = SEVERITY_STYLES[cell.severity] || SEVERITY_STYLES.healthy;
                    const isSelected =
                      selectedCell &&
                      selectedCell.columnName === colItem.column_name &&
                      selectedCell.categoryKey === cat.key;

                    return (
                      <td key={cat.key} className="py-2 px-2 text-center">
                        <button
                          onClick={() => handleCellClick(colItem, cat.key)}
                          className={`w-full py-2 px-2.5 rounded-xl border text-xs font-bold transition-all cursor-pointer flex flex-col items-center justify-center gap-0.5 ${style.bg} ${
                            isSelected ? 'ring-2 ring-indigo-400 scale-102 shadow-lg' : ''
                          }`}
                          title={`${colItem.column_name} • ${cell.category_label}: ${cell.description}`}
                        >
                          <span>{cell.percentage !== null ? `${cell.percentage}%` : 'N/A'}</span>
                          {cell.affected_count > 0 && (
                            <span className="text-[10px] opacity-75 font-normal">
                              ({cell.affected_count} row{cell.affected_count > 1 ? 's' : ''})
                            </span>
                          )}
                        </button>
                      </td>
                    );
                  })}

                  {/* Overall Status Badge */}
                  <td className="py-3 px-4 text-center font-sans">
                    <span
                      className={`text-[10px] uppercase font-bold px-2.5 py-1 rounded-full border inline-flex items-center gap-1.5 ${
                        STATUS_BADGES[colItem.overall_status] || STATUS_BADGES.healthy
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          SEVERITY_STYLES[colItem.overall_status]?.indicator || 'bg-emerald-400'
                        }`}
                      />
                      <span>{colItem.overall_label}</span>
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-500 font-sans">
                  No columns match your search criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Interactive Detail Inspector Drawer for Selected Cell */}
      {selectedCell && (
        <div className="p-5 sm:p-6 rounded-2xl bg-slate-950 border border-indigo-500/30 space-y-4 animate-fade-in shadow-2xl">
          <div className="flex items-start justify-between gap-4 border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${
                SEVERITY_STYLES[selectedCell.severity]?.bg || 'bg-indigo-500/10'
              }`}>
                <Grid className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm sm:text-base font-bold text-white">
                    {selectedCell.columnName}
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 font-mono">
                    {selectedCell.dataType}
                  </span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                    SEVERITY_STYLES[selectedCell.severity]?.bg || ''
                  }`}>
                    {selectedCell.severity}
                  </span>
                </div>
                <p className="text-xs text-indigo-300 font-medium mt-0.5">
                  Dimension: {selectedCell.category_label}
                </p>
              </div>
            </div>

            <button
              onClick={() => setSelectedCell(null)}
              className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Description */}
          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {selectedCell.description}
          </p>

          {/* Affected Rows and Sample Values */}
          {selectedCell.affected_count > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {/* Affected Row Numbers */}
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider block font-mono">
                  Affected Row Numbers ({selectedCell.affected_rows?.length || 0})
                </span>
                <div className="max-h-24 overflow-y-auto flex flex-wrap gap-1 font-mono text-[11px] pt-1">
                  {selectedCell.affected_rows?.map((rowNum) => (
                    <span
                      key={rowNum}
                      className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300"
                    >
                      Row {rowNum}
                    </span>
                  ))}
                </div>
              </div>

              {/* Sample Problematic Values */}
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider block font-mono">
                  Sample Problematic Values
                </span>
                <div className="max-h-24 overflow-y-auto flex flex-wrap gap-1 font-mono text-[11px] pt-1">
                  {selectedCell.sample_values?.length > 0 ? (
                    selectedCell.sample_values.map((val, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded bg-rose-950/40 border border-rose-500/20 text-rose-300 truncate max-w-[180px]"
                        title={String(val)}
                      >
                        {String(val)}
                      </span>
                    ))
                  ) : (
                    <span className="text-slate-500 text-xs italic">
                      {selectedCell.categoryKey === 'missing_value' ? '<empty / null>' : 'None recorded'}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Action Links */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
            <span className="text-xs text-slate-400 font-mono">
              Impact: <strong>{selectedCell.percentage !== null ? `${selectedCell.percentage}%` : 'N/A'}</strong> of {totalRows.toLocaleString()} total rows
            </span>

            <div className="flex items-center gap-2">
              {selectedCell.issue_ids?.length > 0 && onSelectIssue && (
                <button
                  onClick={() => {
                    onSelectIssue(selectedCell.issue_ids[0]);
                  }}
                  className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition inline-flex items-center gap-1.5 cursor-pointer shadow-md shadow-indigo-600/20"
                >
                  <span>Inspect Issue in Detail</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              )}

              {onConsultAIDetective && selectedCell.issue_ids?.length > 0 && (
                <button
                  onClick={() => onConsultAIDetective(selectedCell.issue_ids[0])}
                  className="px-3 py-1.5 rounded-xl bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 text-xs font-semibold transition inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                  <span>Ask AI Detective</span>
                </button>
              )}

              {onNavigateToRepairs && selectedCell.issue_ids?.length > 0 && (
                <button
                  onClick={onNavigateToRepairs}
                  className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <Wrench className="w-3.5 h-3.5 text-slate-400" />
                  <span>Fix in Repair Center</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
