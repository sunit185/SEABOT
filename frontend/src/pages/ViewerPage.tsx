import React from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText } from 'lucide-react';
import { PDFViewer } from '../components/PDFViewer';
import { ExcelPreview } from '../components/ExcelPreview';
import { useDocuments } from '../hooks/useDocuments';

export const ViewerPage: React.FC = () => {
  const { docId } = useParams<{ docId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { documents } = useDocuments();

  const page = parseInt(searchParams.get('page') || '1', 10);
  const hl = searchParams.get('hl') || undefined;
  const sheet = searchParams.get('sheet') || 'Sheet1';
  const rowStart = searchParams.get('row_start') ? parseInt(searchParams.get('row_start')!, 10) : undefined;
  const rowEnd = searchParams.get('row_end') ? parseInt(searchParams.get('row_end')!, 10) : undefined;
  const rowRange: [number, number] | undefined = rowStart && rowEnd ? [rowStart, rowEnd] : undefined;

  const currentDoc = documents.find((d) => d.id === docId);
  const isExcel = currentDoc?.file_type === 'xlsx' || currentDoc?.name.endsWith('.xlsx');

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Navbar */}
      <header className="flex items-center justify-between px-6 py-3.5 bg-slate-900 border-b border-slate-800 flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold transition shadow-sm"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Chat</span>
          </button>

          <div className="flex items-center gap-2 border-l border-slate-800 pl-4">
            <FileText className="h-4 w-4 text-cyan-400" />
            <span className="font-semibold text-slate-200 text-sm truncate max-w-md">
              {currentDoc?.name || 'Document Viewer'}
            </span>
          </div>
        </div>
      </header>

      {/* Main viewer body */}
      <main className="flex-1 overflow-hidden relative">
        {docId ? (
          isExcel ? (
            <ExcelPreview docId={docId} sheetName={sheet} rowRange={rowRange} />
          ) : (
            <PDFViewer docId={docId} initialPage={page} highlightChunkId={hl} />
          )
        ) : (
          <div className="flex items-center justify-center h-full text-slate-400 text-sm">
            No document selected
          </div>
        )}
      </main>
    </div>
  );
};
