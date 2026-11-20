import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Anchor, Sparkles, Layers } from 'lucide-react';
import { Sidebar } from '../components/Sidebar';
import { ChatWindow } from '../components/ChatWindow';
import { MessageInput } from '../components/MessageInput';
import { useChat } from '../hooks/useChat';
import { useDocuments } from '../hooks/useDocuments';
import { useAppStore } from '../store/appStore';
import { chatApi } from '../api/client';

export const ChatPage: React.FC = () => {
  const { chatId } = useParams<{ chatId: string }>();
  const navigate = useNavigate();
  const {
    activeChatId,
    setActiveChatId,
    scopeDocIds,
    setScopeDocIds,
    toggleScopeDocId,
  } = useAppStore();

  const { documents } = useDocuments();
  const {
    messages,
    isStreaming,
    streamingText,
    streamingSources,
    streamingLang,
    ask,
    stopStreaming,
  } = useChat(chatId || null);

  useEffect(() => {
    if (chatId && chatId !== activeChatId) {
      setActiveChatId(chatId);
    }
  }, [chatId, activeChatId, setActiveChatId]);

  const handleNewChat = async () => {
    try {
      const newChat = await chatApi.createChat();
      navigate(`/chat/${newChat.id}`);
    } catch (e) {
      console.error('Failed to create new chat:', e);
    }
  };

  const handleSelectChat = (id: string) => {
    navigate(`/chat/${id}`);
  };

  const handleSend = async (question: string) => {
    let targetChatId = chatId;
    if (!targetChatId || targetChatId === 'new') {
      try {
        const created = await chatApi.createChat();
        targetChatId = created.id;
        navigate(`/chat/${created.id}`, { replace: true });
      } catch (err) {
        console.error('Failed to create new chat:', err);
        return;
      }
    }
    ask(question, scopeDocIds, targetChatId);
  };

  // Extract all starter questions from documents
  const allStarterQuestions = documents
    .flatMap((d) => d.starter_questions || [])
    .slice(0, 6);

  const hasMessages = messages.length > 0 || isStreaming;

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden font-sans text-slate-100">
      <Sidebar onSelectChat={handleSelectChat} onNewChat={handleNewChat} />

      <main className="flex-1 flex flex-col min-w-0 bg-slate-950 relative">
        {hasMessages ? (
          <>
            <ChatWindow
              messages={messages}
              streamingText={streamingText}
              streamingSources={streamingSources}
              isStreaming={isStreaming}
              onRegenerate={() => {
                const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
                if (lastUserMsg) {
                  ask(lastUserMsg.content, scopeDocIds);
                }
              }}
            />
            <MessageInput
              onSend={handleSend}
              onStop={stopStreaming}
              isStreaming={isStreaming}
              streamingLang={streamingLang}
            />
          </>
        ) : (
          <div className="flex-1 flex flex-col justify-between">
            {/* Empty state view */}
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-2xl mx-auto">
              <img
                src="/icons/helm-bot.png"
                alt="Seabot Logo"
                className="h-36 w-36 rounded-full mb-6 ring-4 ring-cyan-400/80 shadow-2xl shadow-cyan-950/90 object-contain hover:scale-105 transition-transform"
              />

              <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
                Ask Seabot about your documents
              </h2>
              <p className="mt-3 text-base text-slate-400 max-w-lg">
                Offline Maritime Chatbot for vessel technical manuals, emergency checklists, and maintenance procedures.
              </p>

              {/* Starter Questions suggestions */}
              {allStarterQuestions.length > 0 && (
                <div className="mt-8 w-full">
                  <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-3">
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Suggested Starter Questions</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                    {allStarterQuestions.map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(q)}
                        className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-cyan-500/60 hover:bg-slate-850 text-sm text-slate-200 transition text-left"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <MessageInput
              onSend={handleSend}
              onStop={stopStreaming}
              isStreaming={isStreaming}
              streamingLang={null}
            />
          </div>
        )}
      </main>
    </div>
  );
};
