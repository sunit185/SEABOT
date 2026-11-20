import React, { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { chatApi } from '../api/client';
import { useQueryClient } from '@tanstack/react-query';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

type RangeOption = 'last_hour' | 'today' | 'last_7_days' | 'all';

export const ClearHistoryModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const queryClient = useQueryClient();
  const [range, setRange] = useState<RangeOption>('today');
  const [deleteDocs, setDeleteDocs] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [step, setStep] = useState<'select' | 'confirm'>('select');

  if (!isOpen) return null;

  const handleClear = async () => {
    try {
      setIsDeleting(true);
      await chatApi.clearHistory(range, deleteDocs);
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      onClose();
      setStep('select');
    } catch (e) {
      console.error('Clear history error:', e);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-700 p-6 text-slate-100 shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2 text-lg font-bold text-amber-400">
            <AlertTriangle className="h-5 w-5" />
            <span>Clear History</span>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {step === 'select' ? (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-slate-300">
              Select time range to clear conversations from Seabot:
            </p>

            <div className="space-y-2">
              {[
                { id: 'last_hour', label: 'Last hour' },
                { id: 'today', label: 'Today' },
                { id: 'last_7_days', label: 'Last 7 days' },
                { id: 'all', label: 'All time' },
              ].map((opt) => (
                <label
                  key={opt.id}
                  className="flex items-center gap-3 p-3 rounded-lg border border-slate-800 bg-slate-800/50 hover:bg-slate-800 cursor-pointer text-sm"
                >
                  <input
                    type="radio"
                    name="clear_range"
                    value={opt.id}
                    checked={range === opt.id}
                    onChange={(e) => setRange(e.target.value as RangeOption)}
                    className="h-4 w-4 text-cyan-600 focus:ring-cyan-500 bg-slate-900 border-slate-700"
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-3 text-sm text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={deleteDocs}
                  onChange={(e) => setDeleteDocs(e.target.checked)}
                  className="h-4 w-4 rounded text-cyan-600 focus:ring-cyan-500 bg-slate-900 border-slate-700"
                />
                <span>Also delete documents uploaded in this range</span>
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => setStep('confirm')}
                className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium"
              >
                Review & Confirm
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-slate-200">
              Are you sure you want to permanently clear chats for{' '}
              <span className="font-semibold text-amber-400">
                {range.replace('_', ' ')}
              </span>
              ?
            </p>
            {deleteDocs && (
              <p className="text-xs text-rose-400">
                ⚠️ Associated documents will also be removed from the index.
              </p>
            )}

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setStep('select')}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm font-medium"
                disabled={isDeleting}
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleClear}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-sm font-medium disabled:opacity-50"
              >
                {isDeleting ? 'Clearing...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
