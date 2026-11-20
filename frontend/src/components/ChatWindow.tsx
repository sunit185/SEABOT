import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  ExternalLink,
  RotateCcw,
  AlertTriangle,
  Bot,
  User,
  Image as ImageIcon,
} from 'lucide-react';
import { Message, SourceChip } from '../types';

interface Props {
  messages: Message[];
  streamingText?: string;
  streamingSources?: SourceChip[];
  isStreaming?: boolean;
  onRegenerate?: () => void;
}

export const ChatWindow: React.FC<Props> = ({
  messages,
  streamingText = '',
  streamingSources = [],
  isStreaming = false,
  onRegenerate,
}) => {
  const navigate = useNavigate();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  const handleSourceClick = (chip: SourceChip) => {
    if (!chip.doc_id) return;
    const page = chip.page || 1;
    const hl = chip.chunk_id || '';
    navigate(`/viewer/${chip.doc_id}?page=${page}&hl=${hl}`);
  };

  const renderContent = (content: string) => {
    // Replace [S1] style citations with interactive badges
    const parts = content.split(/(\[S\d+\])/g);
    return parts.map((part, index) => {
      const match = part.match(/^\[S(\d+)\]$/);
      if (match) {
        return (
          <span
            key={index}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800 select-none align-baseline cursor-pointer hover:bg-cyan-900"
            title={`Source ${part}`}
          >
            {part}
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 space-y-6">
      {messages.map((msg) => {
        const isUser = msg.role === 'user';
        const isSystem = msg.role === 'system';

        if (isSystem) {
          return (
            <div key={msg.id} className="flex justify-center">
              <div className="text-xs text-slate-400 bg-slate-900/60 border border-slate-800 px-3 py-1.5 rounded-full italic">
                {msg.content}
              </div>
            </div>
          );
        }

        return (
          <div
            key={msg.id}
            className={`flex gap-3 max-w-4xl mx-auto ${
              isUser ? 'justify-end' : 'justify-start'
            }`}
          >
            {!isUser && (
              <img
                src="/icons/helm-bot.png"
                alt="Seabot"
                className="h-10 w-10 rounded-full object-contain flex-shrink-0 mt-0.5 ring-2 ring-cyan-400/80 shadow-md"
              />
            )}

            <div
              className={`rounded-2xl p-4 sm:p-5 text-base leading-relaxed max-w-2xl shadow-sm ${
                isUser
                  ? 'bg-cyan-700 text-white font-medium ml-12'
                  : 'bg-slate-900 border border-slate-800 text-slate-100 mr-12'
              }`}
            >
              <div className="whitespace-pre-wrap">{renderContent(msg.content)}</div>

              {/* Interrupted badge */}
              {msg.interrupted === 1 && (
                <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-amber-400">
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Generation interrupted</span>
                  </div>
                  {onRegenerate && (
                    <button
                      onClick={onRegenerate}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-medium transition"
                    >
                      <RotateCcw className="h-3 w-3" />
                      <span>Regenerate</span>
                    </button>
                  )}
                </div>
              )}

              {/* Source Chips */}
              {!isUser && msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-800">
                  <p className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
                    Referenced Sources
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((source, sIdx) => (
                      <button
                        key={sIdx}
                        onClick={() => handleSourceClick(source)}
                        className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-slate-700/80 text-cyan-300 transition"
                      >
                        <FileText className="h-3.5 w-3.5 text-cyan-400" />
                        <span>
                          {source.doc_name} — p.{source.page || 1}
                        </span>
                        <ExternalLink className="h-3 w-3 opacity-60 ml-0.5" />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {isUser && (
              <div className="h-8 w-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 flex-shrink-0 mt-1">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        );
      })}

      {/* Streaming response */}
      {isStreaming && (
        <div className="flex gap-3 max-w-4xl mx-auto justify-start">
          <img
            src="/icons/helm-bot.png"
            alt="Seabot"
            className="h-10 w-10 rounded-full object-contain flex-shrink-0 mt-0.5 ring-2 ring-cyan-400/80 shadow-md animate-pulse"
          />

          <div className="rounded-2xl p-4 sm:p-5 text-base leading-relaxed max-w-2xl bg-slate-900 border border-slate-800 text-slate-100 shadow-sm mr-12">
            <div className="whitespace-pre-wrap">
              {streamingText ? renderContent(streamingText) : 'Analyzing ship manuals...'}
              <span className="inline-block w-2 h-4 ml-1 bg-cyan-400 animate-pulse align-middle" />
            </div>

            {streamingSources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-800">
                <p className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
                  Referenced Sources
                </p>
                <div className="flex flex-wrap gap-2">
                  {streamingSources.map((source, sIdx) => (
                    <button
                      key={sIdx}
                      onClick={() => handleSourceClick(source)}
                      className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-slate-700/80 text-cyan-300 transition"
                    >
                      <FileText className="h-3.5 w-3.5 text-cyan-400" />
                      <span>
                        {source.doc_name} — p.{source.page || 1}
                      </span>
                      <ExternalLink className="h-3 w-3 opacity-60 ml-0.5" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};
