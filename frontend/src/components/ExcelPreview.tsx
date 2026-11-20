import React, { useEffect, useState } from 'react';
import { viewerApi } from '../api/client';
import { ViewerSheetData } from '../types';

interface Props {
  docId: string;
  sheetName?: string;
  rowRange?: [number, number];
}

export const ExcelPreview: React.FC<Props> = ({
  docId,
  sheetName = 'Sheet1',
  rowRange,
}) => {
  const [data, setData] = useState<ViewerSheetData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCancelled = false;
    setIsLoading(true);

    viewerApi
      .getSheet(docId, sheetName)
      .then((res) => {
        if (!isCancelled) {
          setData(res);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          console.error('Failed to load sheet:', err);
          setIsLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [docId, sheetName]);

  const parseMarkdownTable = (md: string) => {
    const lines = md.trim().split('\n');
    if (lines.length < 2) return { headers: [], rows: [] };

    const headers = lines[0]
      .split('|')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const rows = lines
      .slice(2) // Skip header separator
      .map((line) =>
        line
          .split('|')
          .map((s) => s.trim())
          .filter((s, idx, arr) => idx > 0 && idx < arr.length - 1)
      );

    return { headers, rows };
  };

  const { headers, rows } = data?.content_markdown
    ? parseMarkdownTable(data.content_markdown)
    : { headers: [], rows: [] };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 p-6 overflow-hidden">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-cyan-400">Sheet: {sheetName}</h2>
          <p className="text-xs text-slate-400">Total rows: {data?.total_rows || rows.length}</p>
        </div>
        {rowRange && (
          <div className="text-xs px-2.5 py-1 rounded bg-amber-950/60 border border-amber-800 text-amber-300 font-mono">
            Highlighted range: rows {rowRange[0]}–{rowRange[1]}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto mt-4 rounded-xl border border-slate-800">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-sm text-slate-400">
            Loading spreadsheet data...
          </div>
        ) : (
          <table className="w-full border-collapse text-left text-sm">
            <thead className="sticky top-0 bg-slate-900 border-b border-slate-800 text-xs font-semibold uppercase tracking-wider text-slate-300">
              <tr>
                <th className="py-3 px-4 border-r border-slate-800 w-16 text-center text-slate-500">
                  #
                </th>
                {headers.map((h, i) => (
                  <th key={i} className="py-3 px-4 border-r border-slate-800 last:border-r-0">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {rows.map((row, rIdx) => {
                const rowNum = rIdx + 1;
                const isHighlighted =
                  rowRange && rowNum >= rowRange[0] && rowNum <= rowRange[1];

                return (
                  <tr
                    key={rIdx}
                    className={`transition-colors ${
                      isHighlighted
                        ? 'bg-amber-950/30 text-amber-200 font-medium'
                        : 'hover:bg-slate-900/50 text-slate-300'
                    }`}
                  >
                    <td className="py-2 px-4 border-r border-slate-800 text-center text-slate-500 font-sans">
                      {rowNum}
                    </td>
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="py-2 px-4 border-r border-slate-800/40 last:border-r-0">
                        {cell}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
