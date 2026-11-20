import React, { useEffect, useState, useRef } from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import { viewerApi } from '../api/client';
import { ViewerPageData } from '../types';

interface Props {
  docId: string;
  initialPage?: number;
  highlightChunkId?: string;
}

export const PDFViewer: React.FC<Props> = ({
  docId,
  initialPage = 1,
  highlightChunkId,
}) => {
  const [page, setPage] = useState<number>(initialPage);
  const [data, setData] = useState<ViewerPageData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [zoom, setZoom] = useState<number>(1.0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isCancelled = false;
    setIsLoading(true);

    viewerApi
      .getPage(docId, page)
      .then((res) => {
        if (!isCancelled) {
          setData(res);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          console.error('Failed to load page:', err);
          setIsLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [docId, page]);

  const totalPages = data?.total_pages || 1;

  const handlePrev = () => setPage((p) => Math.max(1, p - 1));
  const handleNext = () => setPage((p) => Math.min(totalPages, p + 1));

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100">
      {/* Viewer Toolbar */}
      <div className="flex items-center justify-between px-6 py-3 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrev}
            disabled={page <= 1}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800 text-slate-200"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-sm font-medium px-2">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={handleNext}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800 text-slate-200"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom((z) => Math.max(0.6, z - 0.15))}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200"
            title="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="text-xs font-mono px-1">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200"
            title="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={() => setZoom(1.0)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200"
            title="Reset zoom"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Page Canvas Container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-8 flex items-center justify-center bg-slate-950"
      >
        {isLoading ? (
          <div className="text-sm text-slate-400 animate-pulse">Rendering page...</div>
        ) : data?.page_image_base64 ? (
          <div
            className="relative shadow-2xl rounded border border-slate-700 transition-transform origin-top"
            style={{
              transform: `scale(${zoom})`,
              width: `${data.width}px`,
              height: `${data.height}px`,
            }}
          >
            <img
              src={`data:image/png;base64,${data.page_image_base64}`}
              alt={`Page ${page}`}
              className="w-full h-full object-contain select-none"
            />

            {/* Highlight overlays */}
            {data.chunks?.map((chunk) => {
              const isTarget = highlightChunkId && chunk.chunk_id === highlightChunkId;
              if (!chunk.bbox || chunk.bbox.length !== 4) return null;
              const [x0, y0, x1, y1] = chunk.bbox;

              return (
                <div
                  key={chunk.chunk_id}
                  className={`absolute border-2 transition-colors ${
                    isTarget
                      ? 'border-amber-400 bg-amber-400/25 ring-2 ring-amber-400/60'
                      : 'border-cyan-500/50 bg-cyan-500/10 hover:border-cyan-400 hover:bg-cyan-500/20'
                  }`}
                  style={{
                    left: `${x0}px`,
                    top: `${y0}px`,
                    width: `${x1 - x0}px`,
                    height: `${y1 - y0}px`,
                  }}
                  title={chunk.text_preview}
                />
              );
            })}
          </div>
        ) : (
          <div className="text-sm text-slate-500">Page not available</div>
        )}
      </div>
    </div>
  );
};
