import React, { useState } from 'react';
import { 
  Binary, 
  Hash, 
  Type, 
  Calendar, 
  ToggleLeft, 
  HelpCircle, 
  Search, 
  AlertTriangle,
  BarChart2
} from 'lucide-react';

const TYPE_STYLES = {
  integer: { bg: 'bg-blue-500/10 text-blue-400 border-blue-500/20', icon: Hash },
  float: { bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20', icon: Binary },
  string: { bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', icon: Type },
  datetime: { bg: 'bg-purple-500/10 text-purple-400 border-purple-500/20', icon: Calendar },
  boolean: { bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20', icon: ToggleLeft },
};

export default function ColumnProfilingTable({ profiles }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  if (!profiles || profiles.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
        No column profile data available.
      </div>
    );
  }

  const filtered = profiles.filter((col) => {
    const matchesSearch = col.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === 'all' || col.data_type === typeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <div className="bg-slate-800/40 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-sm shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-indigo-400" />
            Column Schema & Statistical Profiling
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Inferred semantic types, missing value frequencies, and descriptive statistics across all features.
          </p>
        </div>

        {/* Search and Type Filter */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search column..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Types</option>
            <option value="integer">Integer</option>
            <option value="float">Float</option>
            <option value="string">String</option>
            <option value="datetime">Datetime</option>
            <option value="boolean">Boolean</option>
          </select>
        </div>
      </div>

      {/* Profiles Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-700/60">
        <table className="w-full text-left text-xs sm:text-sm border-collapse">
          <thead>
            <tr className="bg-slate-900/90 border-b border-slate-700 text-slate-400 font-medium">
              <th className="py-3 px-4">#</th>
              <th className="py-3 px-4">Column Name</th>
              <th className="py-3 px-4">Inferred Type</th>
              <th className="py-3 px-4">Missing Values</th>
              <th className="py-3 px-4">Distinct</th>
              <th className="py-3 px-4">Mean</th>
              <th className="py-3 px-4">Median</th>
              <th className="py-3 px-4">Min</th>
              <th className="py-3 px-4">Max</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {filtered.map((col, idx) => {
              const typeCfg = TYPE_STYLES[col.data_type] || {
                bg: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
                icon: HelpCircle,
              };
              const TypeIcon = typeCfg.icon;
              const hasNulls = col.null_count > 0;

              return (
                <tr key={col.name} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 text-slate-500 font-mono text-xs">{idx + 1}</td>
                  
                  {/* Name */}
                  <td className="py-3 px-4 font-mono font-semibold text-white">
                    {col.name}
                  </td>

                  {/* Type */}
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium ${typeCfg.bg}`}>
                      <TypeIcon className="w-3.5 h-3.5" />
                      <span className="capitalize">{col.data_type}</span>
                    </span>
                  </td>

                  {/* Missing values & progress bar */}
                  <td className="py-3 px-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5">
                        {hasNulls ? (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                        ) : null}
                        <span className={`font-mono ${hasNulls ? 'text-amber-300 font-semibold' : 'text-slate-400'}`}>
                          {col.null_count.toLocaleString()} ({col.null_percentage}%)
                        </span>
                      </div>
                      <div className="w-24 bg-slate-900 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-1.5 rounded-full ${
                            col.null_percentage > 20
                              ? 'bg-rose-500'
                              : col.null_percentage > 0
                              ? 'bg-amber-400'
                              : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(col.null_percentage, col.null_count > 0 ? 5 : 0))}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Distinct values */}
                  <td className="py-3 px-4 font-mono text-slate-300">
                    {col.unique_count.toLocaleString()}
                  </td>

                  {/* Stats */}
                  <td className="py-3 px-4 font-mono text-slate-300">
                    {col.stats?.mean !== undefined && col.stats?.mean !== null
                      ? col.stats.mean
                      : '--'}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300">
                    {col.stats?.median !== undefined && col.stats?.median !== null
                      ? col.stats.median
                      : '--'}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300">
                    {col.stats?.min !== undefined && col.stats?.min !== null
                      ? col.stats.min
                      : '--'}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300">
                    {col.stats?.max !== undefined && col.stats?.max !== null
                      ? col.stats.max
                      : '--'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
