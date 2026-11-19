import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  RefreshCw, 
  Database, 
  Server, 
  Clock, 
  Cpu, 
  Code,
  ShieldCheck
} from 'lucide-react';
import { healthApi } from '../services/api';

export default function HealthStatus({ onStatusChange }) {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [latency, setLatency] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);
  const [showRawJson, setShowRawJson] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    const startTime = performance.now();
    try {
      const data = await healthApi.getHealth();
      const endTime = performance.now();
      const ping = Math.round(endTime - startTime);
      setLatency(ping);
      setHealthData(data);
      setLastChecked(new Date().toLocaleTimeString());
      if (onStatusChange) onStatusChange(true);
    } catch (err) {
      console.error('Health check failed:', err);
      setError(err.message || 'Unable to reach backend service');
      setHealthData(null);
      if (onStatusChange) onStatusChange(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const isHealthy = healthData?.status === 'healthy';
  const isDbConnected = healthData?.database_status === 'connected';

  return (
    <div className="space-y-6">
      {/* Top Banner / Status Overview */}
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-700/50">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              System Health & Diagnostics
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Real-time validation of FastAPI services, SQLite database connectivity, and CORS pipelines.
            </p>
          </div>
          <button
            onClick={checkHealth}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-xl transition shadow-lg shadow-indigo-600/20 cursor-pointer disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Testing...' : 'Retest Health'}
          </button>
        </div>

        {error ? (
          <div className="mt-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
            <XCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-rose-300">Backend Unreachable</p>
              <p className="text-xs text-rose-200/80 mt-1">{error}</p>
              <p className="text-xs text-slate-400 mt-2">
                Make sure the FastAPI backend is running at <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300">http://127.0.0.1:8000</code>.
              </p>
            </div>
          </div>
        ) : null}

        {/* Diagnostic Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {/* Card 1: API Status */}
          <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">FastAPI Status</span>
              <Server className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-3 flex items-center gap-2">
              {isHealthy ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : error ? (
                <XCircle className="w-5 h-5 text-rose-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-amber-400" />
              )}
              <span className="text-lg font-bold text-white capitalize">
                {loading ? 'Checking...' : healthData?.status || 'Offline'}
              </span>
            </div>
            <span className="text-xs text-slate-500 mt-2">
              Endpoint: <span className="text-slate-300">/api/v1/health</span>
            </span>
          </div>

          {/* Card 2: Database Status */}
          <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Database (SQLite)</span>
              <Database className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-3 flex items-center gap-2">
              {isDbConnected ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <XCircle className="w-5 h-5 text-rose-400" />
              )}
              <span className="text-lg font-bold text-white capitalize">
                {loading ? 'Checking...' : healthData?.database_status || 'Disconnected'}
              </span>
            </div>
            <span className="text-xs text-slate-500 mt-2">
              Engine: <span className="text-slate-300">SQLAlchemy 2.0</span>
            </span>
          </div>

          {/* Card 3: Latency */}
          <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Ping Latency</span>
              <Clock className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-white">
                {latency !== null ? latency : '--'}
              </span>
              <span className="text-xs text-slate-400">ms</span>
            </div>
            <span className="text-xs text-slate-500 mt-2">
              Last tested: <span className="text-slate-300">{lastChecked || 'Never'}</span>
            </span>
          </div>

          {/* Card 4: Environment */}
          <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Environment</span>
              <Cpu className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-3">
              <span className="text-lg font-bold text-white capitalize">
                {healthData?.environment || 'development'}
              </span>
            </div>
            <span className="text-xs text-slate-500 mt-2">
              Version: <span className="text-indigo-400 font-mono">v{healthData?.version || '0.1.0'}</span>
            </span>
          </div>
        </div>

        {/* Technical Details Accordion */}
        <div className="mt-6 border-t border-slate-700/40 pt-4">
          <button
            onClick={() => setShowRawJson(!showRawJson)}
            className="text-xs font-medium text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition"
          >
            <Code className="w-3.5 h-3.5" />
            {showRawJson ? 'Hide Raw Diagnostic JSON' : 'View Raw Diagnostic JSON'}
          </button>

          {showRawJson && (
            <div className="mt-3 p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-emerald-400 overflow-x-auto">
              <pre>{JSON.stringify(healthData || { error }, null, 2)}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
