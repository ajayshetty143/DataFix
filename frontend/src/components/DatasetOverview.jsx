import React from 'react';
import { 
  FileSpreadsheet, 
  Rows, 
  Columns, 
  HardDrive, 
  Calendar, 
  Fingerprint, 
  RotateCcw 
} from 'lucide-react';

export default function DatasetOverview({ dataset, onReset }) {
  if (!dataset) return null;

  return (
    <div className="bg-slate-800/40 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-sm shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white tracking-tight">{dataset.filename}</h2>
              <span className="text-xs uppercase font-mono px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-semibold">
                {dataset.file_type}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-1 font-mono">
              <Fingerprint className="w-3.5 h-3.5 text-slate-500" />
              <span>ID: {dataset.id}</span>
            </div>
          </div>
        </div>

        {onReset && (
          <button
            onClick={onReset}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Upload Another Dataset
          </button>
        )}
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        {/* Total Rows */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Rows</span>
            <Rows className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white font-mono">
            {dataset.total_rows.toLocaleString()}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Data records</span>
        </div>

        {/* Total Columns */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Columns</span>
            <Columns className="w-4 h-4 text-violet-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white font-mono">
            {dataset.total_columns}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Feature dimensions</span>
        </div>

        {/* File Size */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>File Size</span>
            <HardDrive className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white font-mono">
            {dataset.file_size_formatted}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Uncompressed original</span>
        </div>

        {/* Upload Date */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Uploaded At</span>
            <Calendar className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 text-sm font-semibold text-white">
            {new Date(dataset.created_at).toLocaleDateString()}
          </div>
          <span className="text-xs text-slate-500 mt-1 block font-mono">
            {new Date(dataset.created_at).toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  );
}

