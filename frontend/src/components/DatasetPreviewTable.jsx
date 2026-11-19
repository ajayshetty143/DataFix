import React, { useState, useEffect } from 'react';
import { 
  Table, 
  ChevronLeft, 
  ChevronRight, 
  ChevronsLeft, 
  ChevronsRight, 
  Loader2, 
  AlertCircle 
} from 'lucide-react';
import { datasetApi } from '../services/api';

export default function DatasetPreviewTable({ datasetId }) {
  const [previewData, setPreviewData] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPage = async (pageNum, size) => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await datasetApi.getPreview(datasetId, pageNum, size);
      setPreviewData(data);
      setPage(data.page);
    } catch (err) {
      console.error('Failed to load preview page:', err);
      setError(err.message || 'Error loading preview data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchPage(1, pageSize);
  }, [datasetId, pageSize]);

  const handlePageChange = (newPage) => {
    if (previewData && newPage >= 1 && newPage <= previewData.total_pages) {
      fetchPage(newPage, pageSize);
    }
  };

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
  };

  if (error) {
    return (
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center gap-3">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <span>{error}</span>
      </div>
    );
  }

  const columns = previewData?.columns || [];
  const rows = previewData?.rows || [];
  const totalRows = previewData?.total_rows || 0;
  const totalPages = previewData?.total_pages || 1;
  const colTypes = previewData?.column_types || {};

  const startRecord = totalRows === 0 ? 0 : (page - 1) * pageSize + 1;
  const endRecord = Math.min(page * pageSize, totalRows);

  return (
    <div className="bg-slate-800/40 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-sm shadow-xl space-y-4">
      {/* Table Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-700/50">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Table className="w-5 h-5 text-indigo-400" />
            Paginated Dataset Preview
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Displaying real backend records on demand. Large files remain on the server and are streamed by page.
          </p>
        </div>

        {/* Page size selector & record indicator */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">Rows per page:</span>
          <select
            value={pageSize}
            onChange={(e) => handlePageSizeChange(Number(e.target.value))}
            disabled={loading}
            className="px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {/* Grid container with sticky headers */}
      <div className="relative overflow-x-auto rounded-2xl border border-slate-700/60 max-h-[550px] overflow-y-auto">
        {loading && (
          <div className="absolute inset-0 bg-slate-900/70 backdrop-blur-xs flex items-center justify-center z-20">
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 border border-slate-700 text-indigo-400 text-xs font-semibold shadow-xl">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Streaming Page {page}...</span>
            </div>
          </div>
        )}

        <table className="w-full text-left text-xs sm:text-sm border-collapse font-mono">
          <thead className="sticky top-0 z-10 bg-slate-900 shadow-md">
            <tr className="border-b border-slate-700 text-slate-300">
              <th className="py-3 px-4 w-16 text-center text-slate-500 font-semibold bg-slate-900">#</th>
              {columns.map((col) => (
                <th key={col} className="py-3 px-4 font-semibold text-slate-200 whitespace-nowrap bg-slate-900">
                  <div className="flex flex-col">
                    <span>{col}</span>
                    <span className="text-[10px] text-slate-500 font-normal uppercase mt-0.5">
                      {colTypes[col] || 'type'}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/80 bg-slate-950/40">
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={columns.length + 1} className="py-8 text-center text-slate-500">
                  No records to display.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row._row_index} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-2.5 px-4 text-center text-slate-500 text-xs bg-slate-900/30">
                    {row._row_index}
                  </td>
                  {columns.map((col) => {
                    const val = row[col];
                    const isNull = val === null || val === undefined;

                    return (
                      <td key={col} className="py-2.5 px-4 whitespace-nowrap">
                        {isNull ? (
                          <span className="text-slate-600 italic text-[11px] bg-slate-900/80 px-1.5 py-0.5 rounded">
                            null
                          </span>
                        ) : typeof val === 'boolean' ? (
                          <span className={`px-1.5 py-0.5 rounded text-[11px] ${val ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                            {val ? 'TRUE' : 'FALSE'}
                          </span>
                        ) : (
                          <span className="text-slate-200">{String(val)}</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 text-xs text-slate-400">
        <div>
          Showing <span className="font-semibold text-slate-200">{startRecord}</span> to{' '}
          <span className="font-semibold text-slate-200">{endRecord}</span> of{' '}
          <span className="font-semibold text-slate-200">{totalRows.toLocaleString()}</span> rows
        </div>

        <div className="flex items-center space-x-1.5">
          <button
            onClick={() => handlePageChange(1)}
            disabled={page <= 1 || loading}
            title="First page"
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300"
          >
            <ChevronsLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => handlePageChange(page - 1)}
            disabled={page <= 1 || loading}
            title="Previous page"
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="px-3 py-1 rounded-lg bg-slate-900 border border-slate-700 font-mono text-slate-200">
            Page {page} of {totalPages}
          </span>

          <button
            onClick={() => handlePageChange(page + 1)}
            disabled={page >= totalPages || loading}
            title="Next page"
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            onClick={() => handlePageChange(totalPages)}
            disabled={page >= totalPages || loading}
            title="Last page"
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300"
          >
            <ChevronsRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
