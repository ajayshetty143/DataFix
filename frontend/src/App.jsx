import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import HealthStatus from './components/HealthStatus';
import FileUploadZone from './components/FileUploadZone';
import DatasetOverview from './components/DatasetOverview';
import ColumnProfilingTable from './components/ColumnProfilingTable';
import DatasetPreviewTable from './components/DatasetPreviewTable';
import QualityDashboard from './components/QualityDashboard';
import { 
  Sparkles, 
  Table, 
  BarChart2, 
  ShieldAlert, 
  Activity, 
  History, 
  FileSpreadsheet, 
  ArrowRight
} from 'lucide-react';
import { datasetApi } from './services/api';

export default function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [activeDataset, setActiveDataset] = useState(null);
  const [activeTab, setActiveTab] = useState('quality'); // 'quality' | 'preview' | 'profiling'
  const [recentDatasets, setRecentDatasets] = useState([]);
  const [showHealthDiagnostics, setShowHealthDiagnostics] = useState(false);

  const fetchRecentDatasets = async () => {
    try {
      const list = await datasetApi.listDatasets(5);
      setRecentDatasets(list);
    } catch (err) {
      console.warn('Could not load recent datasets:', err);
    }
  };

  useEffect(() => {
    fetchRecentDatasets();
  }, []);

  const handleUploadSuccess = (datasetData) => {
    setActiveDataset(datasetData);
    setActiveTab('quality'); // Default to Quality Engine upon upload
    fetchRecentDatasets();
  };

  const handleSelectRecent = async (item) => {
    try {
      const fullDataset = await datasetApi.getDataset(item.id);
      setActiveDataset(fullDataset);
      setActiveTab('quality');
    } catch (err) {
      console.error('Failed to load selected dataset:', err);
    }
  };

  const handleReset = () => {
    setActiveDataset(null);
  };

  const handleNavigateToPreview = (issue) => {
    setActiveTab('preview');
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0f19] text-slate-100 selection:bg-indigo-500 selection:text-white">
      <Navbar isConnected={isConnected} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-8 sm:p-10 shadow-2xl">
          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-4">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Phase 3: Intelligent Data Quality Engine</span>
            </div>
            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white">
              DataFix <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">Quality Engine</span>
            </h1>
            <p className="mt-4 text-base sm:text-lg text-slate-300 leading-relaxed">
              Deterministic detection for missing data, duplicate records, invalid formats, categorical inconsistencies, and statistical anomalies. Zero data alteration — complete analytical visibility.
            </p>
          </div>
        </div>

        {/* View Mode: When No Dataset is active */}
        {!activeDataset ? (
          <div className="space-y-8">
            {/* Upload Zone */}
            <section>
              <FileUploadZone onUploadSuccess={handleUploadSuccess} />
            </section>

            {/* Recent Uploads List (if any exist) */}
            {recentDatasets.length > 0 && (
              <section className="bg-slate-800/30 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-sm">
                <div className="flex items-center gap-2 text-white font-semibold text-sm mb-4">
                  <History className="w-4 h-4 text-indigo-400" />
                  <span>Previously Uploaded Datasets</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {recentDatasets.map((ds) => (
                    <div
                      key={ds.id}
                      onClick={() => handleSelectRecent(ds)}
                      className="group p-4 rounded-2xl bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 hover:border-indigo-500/40 cursor-pointer transition-all shadow-md flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3 overflow-hidden">
                        <div className="w-9 h-9 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 flex-shrink-0">
                          <FileSpreadsheet className="w-4 h-4" />
                        </div>
                        <div className="truncate">
                          <p className="text-xs sm:text-sm font-semibold text-white truncate group-hover:text-indigo-300 transition">
                            {ds.filename}
                          </p>
                          <p className="text-[11px] text-slate-400 font-mono">
                            {ds.total_rows.toLocaleString()} rows &bull; {ds.total_columns} cols &bull; {ds.file_size_formatted}
                          </p>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all flex-shrink-0 ml-2" />
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Toggle Health Diagnostics Drawer */}
            <div className="pt-2">
              <button
                onClick={() => setShowHealthDiagnostics(!showHealthDiagnostics)}
                className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition py-2"
              >
                <Activity className="w-4 h-4 text-indigo-400" />
                {showHealthDiagnostics ? 'Hide System Health Diagnostics' : 'Show System Health Diagnostics'}
              </button>

              {showHealthDiagnostics && (
                <div className="mt-4">
                  <HealthStatus onStatusChange={setIsConnected} />
                </div>
              )}
            </div>
          </div>
        ) : (
          /* View Mode: Dataset Loaded */
          <div className="space-y-6">
            {/* Top Metric Cards Overview */}
            <DatasetOverview dataset={activeDataset} onReset={handleReset} />

            {/* Tab Navigation */}
            <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
              <button
                onClick={() => setActiveTab('quality')}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition ${
                  activeTab === 'quality'
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                    : 'bg-slate-800/60 hover:bg-slate-800 text-slate-300'
                }`}
              >
                <ShieldAlert className="w-4 h-4" />
                <span>Quality Analysis Engine</span>
              </button>

              <button
                onClick={() => setActiveTab('preview')}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition ${
                  activeTab === 'preview'
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                    : 'bg-slate-800/60 hover:bg-slate-800 text-slate-300'
                }`}
              >
                <Table className="w-4 h-4" />
                <span>Dataset Preview</span>
                <span className="text-[11px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-200 font-mono">
                  {activeDataset.total_rows.toLocaleString()}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('profiling')}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition ${
                  activeTab === 'profiling'
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                    : 'bg-slate-800/60 hover:bg-slate-800 text-slate-300'
                }`}
              >
                <BarChart2 className="w-4 h-4" />
                <span>Column Profiling & Stats</span>
                <span className="text-[11px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-200 font-mono">
                  {activeDataset.total_columns}
                </span>
              </button>
            </div>

            {/* Tab 1: Intelligent Quality Engine Dashboard */}
            {activeTab === 'quality' && (
              <QualityDashboard
                datasetId={activeDataset.id}
                onNavigateToPreview={handleNavigateToPreview}
              />
            )}

            {/* Tab 2: Dataset Paginated Preview */}
            {activeTab === 'preview' && (
              <DatasetPreviewTable datasetId={activeDataset.id} />
            )}

            {/* Tab 3: Column Schema & Profiling */}
            {activeTab === 'profiling' && (
              <ColumnProfilingTable profiles={activeDataset.column_profiles} />
            )}

            {/* Collapsible Health Diagnostic footer */}
            <div className="pt-4 border-t border-slate-800/60">
              <button
                onClick={() => setShowHealthDiagnostics(!showHealthDiagnostics)}
                className="inline-flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300 transition"
              >
                <Activity className="w-3.5 h-3.5" />
                <span>{showHealthDiagnostics ? 'Hide Diagnostics' : 'Check API & Database Health'}</span>
              </button>

              {showHealthDiagnostics && (
                <div className="mt-4">
                  <HealthStatus onStatusChange={setIsConnected} />
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-500">
        DataFix Platform &bull; Phase 3 Intelligent Quality Engine &bull; Ready for Evaluation
      </footer>
    </div>
  );
}
