import React, { useState, useRef } from 'react';
import { UploadCloud, FileSpreadsheet, AlertCircle, CheckCircle2, Loader2, ArrowUpRight } from 'lucide-react';
import { datasetApi } from '../services/api';

const MAX_FILE_SIZE_MB = 20;
const MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTS = ['.csv', '.xlsx', '.xls'];

export default function FileUploadZone({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    if (!file) return 'No file chosen.';
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      return `Unsupported file format '${ext}'. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.`;
    }
    if (file.size > MAX_BYTES) {
      return `File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the maximum allowed limit of ${MAX_FILE_SIZE_MB} MB.`;
    }
    if (file.size === 0) {
      return 'The selected file is empty (0 bytes).';
    }
    return null;
  };

  const handleFileProcess = async (file) => {
    setError(null);
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSelectedFile(file);
    setUploading(true);
    setUploadProgress(0);

    try {
      const data = await datasetApi.uploadDataset(file, (progress) => {
        setUploadProgress(progress);
      });
      if (onUploadSuccess) {
        onUploadSuccess(data);
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setError(err.message || 'Failed to upload and process dataset. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileProcess(files[0]);
    }
  };

  const handleFileSelect = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileProcess(files[0]);
    }
  };

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-3xl p-8 sm:p-12 text-center transition-all cursor-pointer select-none ${
          isDragging
            ? 'border-indigo-400 bg-indigo-500/10 scale-[1.01]'
            : 'border-slate-700/80 hover:border-slate-600 bg-slate-900/50 hover:bg-slate-900/80'
        } ${uploading ? 'pointer-events-none opacity-90' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileSelect}
          className="hidden"
          disabled={uploading}
        />

        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-tr from-indigo-500/20 to-violet-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-inner">
            {uploading ? (
              <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
            ) : (
              <UploadCloud className="w-8 h-8 text-indigo-400" />
            )}
          </div>

          <div>
            <h3 className="text-lg font-semibold text-white">
              {uploading
                ? 'Processing & Profiling Dataset...'
                : 'Drop your dataset here, or browse'}
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Supports <strong className="text-slate-200">CSV</strong> (.csv) and{' '}
              <strong className="text-slate-200">Excel</strong> (.xlsx, .xls) files up to 20 MB.
            </p>
          </div>

          {/* Progress bar during upload */}
          {uploading && (
            <div className="space-y-2 pt-2">
              <div className="flex justify-between text-xs text-slate-400">
                <span>{uploadProgress < 100 ? 'Uploading raw file...' : 'Computing column profiles & statistics...'}</span>
                <span className="font-mono text-indigo-400">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700/50">
                <div
                  className="bg-indigo-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {!uploading && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-xs text-slate-300">
              <FileSpreadsheet className="w-3.5 h-3.5 text-indigo-400" />
              <span>Original file preserved without modification</span>
            </div>
          )}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mt-4 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3 text-left">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-rose-300">Upload Validation Error</h4>
            <p className="text-xs text-rose-200/90 mt-0.5">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-xs text-rose-400 hover:text-rose-200 px-2 py-1 rounded"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}

