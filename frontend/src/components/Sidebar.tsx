import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MessageSquare,
  FileText,
  Plus,
  Trash2,
  Edit2,
  Upload,
  Clock,
  ChevronLeft,
  ChevronRight,
  Check,
  X,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import { chatApi } from '../api/client';
import { useDocuments } from '../hooks/useDocuments';
import { useAppStore } from '../store/appStore';
import { ClearHistoryModal } from './ClearHistoryModal';
import { DocumentUpload } from './DocumentUpload';
import { Chat } from '../types';

interface Props {
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
}

export const Sidebar: React.FC<Props> = ({ onSelectChat, onNewChat }) => {
  const queryClient = useQueryClient();
  const {
    activeChatId,
    sidebarCollapsed,
    setSidebarCollapsed,
    scopeDocIds,
    toggleScopeDocId,
  } = useAppStore();

  const [activeTab, setActiveTab] = useState<'chats' | 'documents'>('chats');
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const { data: groupedChats } = useQuery({
    queryKey: ['chats'],
    queryFn: chatApi.listChats,
  });

  const { documents, deleteDoc } = useDocuments();

  const deleteChatMutation = useMutation({
    mutationFn: (id: string) => chatApi.deleteChat(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      if (activeChatId === deletedId) {
        onNewChat();
      }
    },
  });

  const renameChatMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      chatApi.renameChat(id, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      setEditingChatId(null);
    },
  });

  const startRename = (chat: Chat, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingChatId(chat.id);
    setEditTitle(chat.title || 'New Chat');
  };

  const saveRename = (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      renameChatMutation.mutate({ id: chatId, title: editTitle.trim() });
    } else {
      setEditingChatId(null);
    }
  };

  const renderChatGroup = (title: string, list: Chat[] | undefined) => {
    if (!list || list.length === 0) return null;
    return (
      <div className="mb-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-3 mb-1">
          {title}
        </h4>
        <div className="space-y-1">
          {list.map((c) => {
            const isActive = activeChatId === c.id;
            const isEditing = editingChatId === c.id;

            return (
              <div
                key={c.id}
                onClick={() => onSelectChat(c.id)}
                className={`group flex items-center justify-between px-3 py-2.5 rounded-lg text-sm cursor-pointer transition ${
                  isActive
                    ? 'bg-slate-800 text-cyan-400 font-medium'
                    : 'text-slate-300 hover:bg-slate-800/60 hover:text-slate-100'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <MessageSquare className="h-4 w-4 flex-shrink-0 text-slate-400 group-hover:text-cyan-400" />
                  {isEditing ? (
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      className="bg-slate-900 text-slate-100 px-1 py-0.5 rounded text-xs w-full border border-cyan-500 focus:outline-none"
                      autoFocus
                    />
                  ) : (
                    <span className="truncate">{c.title || 'Untitled conversation'}</span>
                  )}
                </div>

                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {isEditing ? (
                    <>
                      <button
                        onClick={(e) => saveRename(c.id, e)}
                        className="p-1 hover:text-emerald-400"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingChatId(null);
                        }}
                        className="p-1 hover:text-slate-400"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={(e) => startRename(c, e)}
                        className="p-1 text-slate-400 hover:text-cyan-400"
                        title="Rename"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteChatMutation.mutate(c.id);
                        }}
                        className="p-1 text-slate-400 hover:text-rose-400"
                        title="Delete"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <>
      <aside
        className={`relative flex flex-col bg-slate-900 border-r border-slate-800 transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-72'
        }`}
      >
        {/* Toggle Collapse Button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute -right-3 top-5 z-20 flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 border border-slate-700 text-slate-300 shadow hover:bg-slate-700 hover:text-white"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-3.5 w-3.5" />
          ) : (
            <ChevronLeft className="h-3.5 w-3.5" />
          )}
        </button>

        {/* Brand header */}
        <div className={`p-4 border-b border-slate-800 flex items-center ${sidebarCollapsed ? 'justify-center px-2 py-3' : 'gap-4'}`}>
          <div className="relative flex-shrink-0">
            <img
              src="/icons/helm-bot.png"
              alt="Seabot Logo"
              className={`${sidebarCollapsed ? 'h-11 w-11' : 'h-16 w-16'} rounded-full object-contain ring-2 ring-cyan-400/80 shadow-lg shadow-cyan-950/60 transition-transform hover:scale-105`}
            />
          </div>
          {!sidebarCollapsed && (
            <div>
              <h1 className="text-2xl font-black text-slate-100 tracking-wider">SEABOT</h1>
              <p className="text-xs text-cyan-400 font-semibold tracking-wide">Offline Maritime Chatbot</p>
            </div>
          )}
        </div>

        {/* Actions header */}
        <div className="p-3 border-b border-slate-800 space-y-2">
          <button
            onClick={onNewChat}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-3 rounded-lg bg-cyan-700 hover:bg-cyan-600 text-white text-sm font-semibold transition shadow-sm"
          >
            <Plus className="h-4 w-4" />
            {!sidebarCollapsed && <span>New Conversation</span>}
          </button>

          {!sidebarCollapsed && (
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs font-medium">
              <button
                onClick={() => setActiveTab('chats')}
                className={`flex-1 py-1.5 rounded-md transition ${
                  activeTab === 'chats'
                    ? 'bg-slate-800 text-cyan-400 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Chats
              </button>
              <button
                onClick={() => setActiveTab('documents')}
                className={`flex-1 py-1.5 rounded-md transition ${
                  activeTab === 'documents'
                    ? 'bg-slate-800 text-cyan-400 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Docs ({documents.length})
              </button>
            </div>
          )}
        </div>

        {/* Tab content list */}
        <div className="flex-1 overflow-y-auto p-2">
          {!sidebarCollapsed ? (
            activeTab === 'chats' ? (
              <div className="space-y-2">
                {renderChatGroup('Today', groupedChats?.today)}
                {renderChatGroup('Yesterday', groupedChats?.yesterday)}
                {renderChatGroup('Previous 7 Days', groupedChats?.previous_7_days)}
                {renderChatGroup('Older', groupedChats?.older)}

                {(!groupedChats ||
                  (groupedChats.today.length === 0 &&
                    groupedChats.yesterday.length === 0 &&
                    groupedChats.previous_7_days.length === 0 &&
                    groupedChats.older.length === 0)) && (
                  <div className="text-center py-8 text-xs text-slate-500">
                    No chat history yet
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <button
                  onClick={() => setIsUploadModalOpen(true)}
                  className="flex items-center justify-center gap-2 w-full py-2 px-3 mb-3 rounded-lg border border-dashed border-slate-700 hover:border-cyan-500/80 bg-slate-950/40 text-xs font-medium text-slate-300 hover:text-cyan-400 transition"
                >
                  <Upload className="h-3.5 w-3.5" />
                  <span>Upload Documents</span>
                </button>

                {documents.map((doc) => {
                  const isScoped = scopeDocIds.includes(doc.id);
                  return (
                    <div
                      key={doc.id}
                      onClick={() => toggleScopeDocId(doc.id)}
                      className={`group flex items-start justify-between p-2.5 rounded-lg border text-xs cursor-pointer transition ${
                        isScoped
                          ? 'border-cyan-500/80 bg-cyan-950/20 text-cyan-200'
                          : 'border-slate-800 hover:bg-slate-800/40 text-slate-300'
                      }`}
                    >
                      <div className="min-w-0 flex-1 pr-2">
                        <p className="font-medium truncate text-slate-200">{doc.name}</p>
                        <div className="flex items-center gap-2 text-[10px] text-slate-500 mt-1">
                          <span>{doc.pages ? `${doc.pages} pages` : doc.file_type}</span>
                          <span>•</span>
                          <span className="capitalize">{doc.status}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {doc.status === 'ready' && (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        )}
                        {(doc.status === 'uploading' ||
                          doc.status === 'parsing' ||
                          doc.status === 'indexing') && (
                          <RefreshCw className="h-3.5 w-3.5 text-cyan-400 animate-spin" />
                        )}
                        {doc.status === 'failed' && (
                          <AlertCircle className="h-3.5 w-3.5 text-rose-400" />
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteDoc(doc.id);
                          }}
                          className="p-1 opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-400 transition"
                          title="Delete document"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}

                {documents.length === 0 && (
                  <div className="text-center py-8 text-xs text-slate-500">
                    No documents uploaded
                  </div>
                )}
              </div>
            )
          ) : (
            <div className="flex flex-col items-center gap-3 py-2">
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-cyan-400"
                title="Upload Documents"
              >
                <Upload className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-800">
          {!sidebarCollapsed ? (
            <button
              onClick={() => setIsClearModalOpen(true)}
              className="flex items-center gap-2 text-xs text-slate-400 hover:text-rose-400 transition px-2 py-1.5 w-full rounded hover:bg-slate-800"
            >
              <Clock className="h-3.5 w-3.5" />
              <span>Clear History</span>
            </button>
          ) : (
            <button
              onClick={() => setIsClearModalOpen(true)}
              className="p-2 text-slate-400 hover:text-rose-400 transition mx-auto block rounded hover:bg-slate-800"
              title="Clear History"
            >
              <Clock className="h-4 w-4" />
            </button>
          )}
        </div>
      </aside>

      {/* Modals */}
      <ClearHistoryModal
        isOpen={isClearModalOpen}
        onClose={() => setIsClearModalOpen(false)}
      />
      <DocumentUpload
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
    </>
  );
};
