import React, { useRef, useEffect } from 'react';
import { Send, StopCircle, Layers, Globe } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { useDocuments } from '../hooks/useDocuments';

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  streamingLang?: { code: string; name: string } | null;
}

// Language flag emoji via regional indicator letters (works for most langs)
function langFlag(code: string): string {
  const countryMap: Record<string, string> = {
    hi: '🇮🇳', mr: '🇮🇳', gu: '🇮🇳', pa: '🇮🇳', bn: '🇧🇩', ur: '🇵🇰',
    ar: '🇸🇦', fr: '🇫🇷', de: '🇩🇪', es: '🇪🇸', pt: '🇧🇷', ru: '🇷🇺',
    zh: '🇨🇳', 'zh-cn': '🇨🇳', 'zh-tw': '🇹🇼', ja: '🇯🇵', ko: '🇰🇷',
    id: '🇮🇩', ms: '🇲🇾', tr: '🇹🇷', nl: '🇳🇱', pl: '🇵🇱', uk: '🇺🇦',
    vi: '🇻🇳', th: '🇹🇭', sv: '🇸🇪', da: '🇩🇰', fi: '🇫🇮', no: '🇳🇴',
    it: '🇮🇹', el: '🇬🇷', cs: '🇨🇿', ro: '🇷🇴', hu: '🇭🇺', fa: '🇮🇷',
    he: '🇮🇱', sw: '🇰🇪', tl: '🇵🇭', af: '🇿🇦', en: '🇬🇧',
  };
  return countryMap[code] || '🌐';
}

export const MessageInput: React.FC<Props> = ({ onSend, onStop, isStreaming, streamingLang }) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { inputDraft, setInputDraft, scopeDocIds, setScopeDocIds, toggleScopeDocId } =
    useAppStore();
  const { documents } = useDocuments();

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [inputDraft]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || !e.shiftKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = inputDraft.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInputDraft('');
  };

  const isAllDocs = scopeDocIds.length === 0;

  return (
    <div className="p-4 md:p-6 bg-slate-900 border-t border-slate-800">
      <div className="max-w-4xl mx-auto space-y-3">
        {/* Top row: Scope chips + Language badge */}
        <div className="flex items-center justify-between gap-2">
          {/* Scope selector chips */}
          {documents.length > 0 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs flex-1 min-w-0">
              <span className="text-slate-400 font-semibold flex items-center gap-1 flex-shrink-0">
                <Layers className="h-3.5 w-3.5 text-cyan-400" /> Scope:
              </span>
              <button
                onClick={() => setScopeDocIds([])}
                className={`px-2.5 py-1 rounded-full font-medium transition flex-shrink-0 ${
                  isAllDocs
                    ? 'bg-cyan-700 text-white shadow-sm'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                All documents ({documents.length})
              </button>

              {documents.map((doc) => {
                const isSelected = scopeDocIds.includes(doc.id);
                return (
                  <button
                    key={doc.id}
                    onClick={() => toggleScopeDocId(doc.id)}
                    className={`px-2.5 py-1 rounded-full font-medium transition truncate max-w-xs flex-shrink-0 ${
                      isSelected
                        ? 'bg-cyan-700 text-white shadow-sm'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                    title={doc.name}
                  >
                    {doc.name}
                  </button>
                );
              })}
            </div>
          )}

          {/* Language detection badge */}
          {streamingLang && streamingLang.code !== 'en' && (
            <div
              className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-violet-900/60 border border-violet-500/40 text-xs font-semibold text-violet-200 flex-shrink-0 animate-pulse"
              title={`Responding in ${streamingLang.name}`}
            >
              <Globe className="h-3 w-3 text-violet-400" />
              <span>{langFlag(streamingLang.code)}</span>
              <span>Replying in {streamingLang.name}</span>
            </div>
          )}
        </div>

        {/* Text Input area */}
        <div className="relative flex items-end gap-2 bg-slate-950 border border-slate-700 rounded-2xl p-2 focus-within:border-cyan-500 focus-within:ring-1 focus-within:ring-cyan-500 shadow-inner">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputDraft}
            onChange={(e) => setInputDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask in any language — Hindi, Arabic, Spanish, French… Seabot will reply in the same language"
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-base resize-none px-3 py-2 focus:outline-none leading-relaxed max-h-44"
          />

          {isStreaming ? (
            <button
              onClick={onStop}
              className="flex items-center justify-center h-10 w-10 rounded-xl bg-rose-600 hover:bg-rose-500 text-white transition flex-shrink-0 mb-0.5"
              title="Stop generating"
            >
              <StopCircle className="h-5 w-5" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!inputDraft.trim()}
              className="flex items-center justify-center h-10 w-10 rounded-xl bg-cyan-700 hover:bg-cyan-600 disabled:opacity-30 disabled:hover:bg-cyan-700 text-white transition flex-shrink-0 mb-0.5"
              title="Send question (Enter or Ctrl+Enter)"
            >
              <Send className="h-5 w-5" />
            </button>
          )}
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-500 px-2">
          <span>Seabot operates completely offline • Ask in any language • Answers from uploaded documents only</span>
          <span>Press Enter to send, Shift+Enter for newline</span>
        </div>
      </div>
    </div>
  );
};
