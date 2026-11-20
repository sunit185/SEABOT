import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, CheckCircle2, AlertCircle, RefreshCw, X, FileText } from 'lucide-react';
import { useDocuments } from '../hooks/useDocuments';
import { DocumentItem } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess?: (docs: DocumentItem[]) => void;
}

export const DocumentUpload: React.FC<Props> = ({ isOpen, onClose, onUploadSuccess }) => {
  const { upload, documents } = useDocuments();
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadingFiles, setUploadingFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    setUploadingFiles(acceptedFiles);
    setUploadError(null);
    setIsSubmitting(true);

    try {
      const res = await upload(acceptedFiles);
      if (onUploadSuccess) {
        onUploadSuccess(res);
      }
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || err.message || 'Upload failed');
    } finally {
      setIsSubmitting(false);
    }
  }, [upload, onUploadSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    maxSize: 200 * 1024 * 1024, // 200 MB
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-xl rounded-xl bg-slate-900 border border-slate-700 p-6 text-slate-100 shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2 text-lg font-bold text-cyan-400">
            <UploadCloud className="h-6 w-6" />
            <span>Upload Ship Documents</span>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-4">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-cyan-500 bg-cyan-950/20'
                : 'border-slate-700 hover:border-slate-500 bg-slate-800/40'
            }`}
          >
            <input {...getInputProps()} />
            <UploadCloud className="mx-auto h-12 w-12 text-slate-400 mb-3" />
            <p className="text-base font-medium text-slate-200">
              Drag and drop manuals, checklists, or spreadsheets here
            </p>
            <p className="text-sm text-slate-400 mt-1">
              Supports .pdf, .docx, .xlsx (max 200 MB per file)
            </p>
          </div>

          {uploadError && (
            <div className="mt-4 flex items-center gap-2 p-3 bg-rose-950/50 border border-rose-800 rounded-lg text-sm text-rose-300">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}

          {isSubmitting && (
            <div className="mt-4 flex items-center justify-center gap-2 text-sm text-cyan-400">
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span>Uploading and initiating background processing...</span>
            </div>
          )}

          {/* Recently uploaded / processing files */}
          {documents.length > 0 && (
            <div className="mt-6">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Document Ingestion Status
              </h4>
              <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                {documents.slice(0, 5).map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-slate-800/70 border border-slate-700/60 text-sm"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                      <span className="truncate text-slate-200">{doc.name}</span>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {doc.status === 'ready' && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/50">
                          <CheckCircle2 className="h-3 w-3" /> Ready
                        </span>
                      )}
                      {(doc.status === 'uploading' ||
                        doc.status === 'parsing' ||
                        doc.status === 'indexing') && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/50">
                          <RefreshCw className="h-3 w-3 animate-spin" />{' '}
                          {doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
                        </span>
                      )}
                      {doc.status === 'failed' && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/50" title={doc.error_msg || ''}>
                          <AlertCircle className="h-3 w-3" /> Failed
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end pt-5 border-t border-slate-800 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-lg bg-cyan-700 hover:bg-cyan-600 text-white text-sm font-semibold transition"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
