import React, { useState } from 'react';
import Navbar from './components/Navbar';
import HealthStatus from './components/HealthStatus';
import { 
  FolderTree, 
  Layers, 
  CheckCircle, 
  Terminal, 
  FileCode, 
  Sparkles,
  ArrowRight
} from 'lucide-react';

export default function App() {
  const [isConnected, setIsConnected] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0f19] text-slate-100 selection:bg-indigo-500 selection:text-white">
      <Navbar isConnected={isConnected} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-8 sm:p-10 shadow-2xl">
          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-4">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Phase 1 Initialized Successfully</span>
            </div>
            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white">
              DataFix <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">Core Foundation</span>
            </h1>
            <p className="mt-4 text-base sm:text-lg text-slate-300 leading-relaxed">
              Modern full-stack architecture powered by React 18, Vite, Tailwind CSS, FastAPI, and SQLite + SQLAlchemy. Ready for intelligent data validation and remediation workflows.
            </p>
          </div>
        </div>

        {/* Diagnostic & Communication Health Check */}
        <section>
          <HealthStatus onStatusChange={setIsConnected} />
        </section>

        {/* Phase 1 Architecture & Modular Structure Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Card: Modular Project Structure */}
          <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
              <FolderTree className="w-5 h-5 text-indigo-400" />
              <h3 className="font-semibold text-white">Modular Architecture</h3>
            </div>
            <ul className="mt-4 space-y-3 text-xs sm:text-sm font-mono text-slate-300">
              <li className="flex items-start gap-2">
                <span className="text-indigo-400 font-bold">backend/</span>
                <span className="text-slate-400">FastAPI, SQLAlchemy ORM, SQLite DB, modular API routers, Pydantic schemas</span>
              </li>
              <li className="flex items-start gap-2 pl-4">
                <span className="text-slate-500">├── app/core/</span>
                <span className="text-slate-400">Pydantic settings, DB session & engine lifecycle</span>
              </li>
              <li className="flex items-start gap-2 pl-4">
                <span className="text-slate-500">├── app/api/v1/</span>
                <span className="text-slate-400">Versioned routing & health diagnostic endpoints</span>
              </li>
              <li className="flex items-start gap-2 pl-4">
                <span className="text-slate-500">└── tests/</span>
                <span className="text-slate-400">Automated Pytest suite verifying all endpoints</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-violet-400 font-bold">frontend/</span>
                <span className="text-slate-400">React 18 + Vite + Tailwind CSS + Axios API integration layer</span>
              </li>
              <li className="flex items-start gap-2 pl-4">
                <span className="text-slate-500">├── src/services/</span>
                <span className="text-slate-400">Axios HTTP client with error interception</span>
              </li>
              <li className="flex items-start gap-2 pl-4">
                <span className="text-slate-500">└── src/components/</span>
                <span className="text-slate-400">Reusable diagnostic cards and status widgets</span>
              </li>
            </ul>
          </div>

          {/* Card: Verification Checklist */}
          <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
              <Layers className="w-5 h-5 text-emerald-400" />
              <h3 className="font-semibold text-white">Phase 1 Checklist</h3>
            </div>
            <div className="mt-4 space-y-3">
              {[
                { label: 'React + Vite + Tailwind CSS setup', done: true },
                { label: 'FastAPI modular application structure', done: true },
                { label: 'SQLite + SQLAlchemy 2.0 configuration', done: true },
                { label: 'Backend & frontend .env.example files', done: true },
                { label: 'Health-check API with DB connectivity verification', done: true },
                { label: 'End-to-end frontend-backend communication', done: isConnected },
              ].map((item, idx) => (
                <div key={idx} className="flex items-center gap-3 p-2.5 rounded-xl bg-slate-900/40 border border-slate-800/50">
                  <CheckCircle className={`w-4 h-4 ${item.done ? 'text-emerald-400' : 'text-slate-600'}`} />
                  <span className={`text-xs sm:text-sm ${item.done ? 'text-slate-200' : 'text-slate-500'}`}>
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-500">
        DataFix Platform &bull; Phase 1 Foundation &bull; Ready for Phase 2 Approval
      </footer>
    </div>
  );
}
