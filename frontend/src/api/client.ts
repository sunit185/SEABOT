import axios from 'axios';
import {
  Chat,
  ChatDetail,
  GroupedChats,
  DocumentItem,
  UserState,
  ViewerPageData,
  ViewerSheetData,
  SourceChip,
} from '../types';

export const api = axios.create({
  baseURL: '/api',
});

export const chatApi = {
  createChat: async (title?: string): Promise<Chat> => {
    const res = await api.post<Chat>('/chats', { title });
    return res.data;
  },

  listChats: async (): Promise<GroupedChats> => {
    const res = await api.get<GroupedChats>('/chats');
    return res.data;
  },

  getChat: async (chatId: string): Promise<ChatDetail> => {
    const res = await api.get<ChatDetail>(`/chats/${chatId}`);
    return res.data;
  },

  renameChat: async (chatId: string, title: string): Promise<Chat> => {
    const res = await api.patch<Chat>(`/chats/${chatId}`, { title });
    return res.data;
  },

  deleteChat: async (chatId: string): Promise<void> => {
    await api.delete(`/chats/${chatId}`);
  },

  clearHistory: async (
    range: 'last_hour' | 'today' | 'last_7_days' | 'all',
    deleteDocuments: boolean = false
  ) => {
    const res = await api.post('/chats/clear', {
      range,
      delete_documents: deleteDocuments,
    });
    return res.data;
  },
};

export const documentApi = {
  listDocuments: async (): Promise<DocumentItem[]> => {
    const res = await api.get<DocumentItem[]>('/documents');
    return res.data;
  },

  uploadDocuments: async (files: File[]): Promise<DocumentItem[]> => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await api.post<DocumentItem[]>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  getDocumentStatus: async (docId: string) => {
    const res = await api.get(`/documents/${docId}/status`);
    return res.data;
  },

  deleteDocument: async (docId: string): Promise<void> => {
    await api.delete(`/documents/${docId}`);
  },
};

export const stateApi = {
  getState: async (): Promise<UserState> => {
    const res = await api.get<UserState>('/state');
    return res.data;
  },

  saveState: async (state: Partial<UserState>): Promise<UserState> => {
    const res = await api.put<UserState>('/state', state);
    return res.data;
  },
};

export const viewerApi = {
  getPage: async (docId: string, pageNum: number): Promise<ViewerPageData> => {
    const res = await api.get<ViewerPageData>(`/viewer/${docId}/page/${pageNum}`);
    return res.data;
  },

  getSheet: async (docId: string, sheetName: string): Promise<ViewerSheetData> => {
    const res = await api.get<ViewerSheetData>(`/viewer/${docId}/sheet/${sheetName}`);
    return res.data;
  },
};

export function askQuestionStream(
  chatId: string,
  question: string,
  scopeDocIds: string[] | null,
  callbacks: {
    onToken: (token: string) => void;
    onSources: (sources: SourceChip[]) => void;
    onLanguage: (code: string, name: string) => void;
    onDone: () => void;
    onError: (err: string) => void;
  }
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`/api/chats/${chatId}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          scope_doc_ids: scopeDocIds && scopeDocIds.length > 0 ? scopeDocIds : null,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No readable stream received');

      const decoder = new TextDecoder();
      let buffer = '';

      let doneCalled = false;
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          const trimmed = block.trim();
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.replace(/^data:\s*/, '');
          try {
            const data = JSON.parse(jsonStr);
            if (data.type === 'token') {
              callbacks.onToken(data.content);
            } else if (data.type === 'sources') {
              callbacks.onSources(data.sources);
            } else if (data.type === 'language') {
              callbacks.onLanguage(data.code, data.name);
            } else if (data.type === 'done') {
              doneCalled = true;
              callbacks.onDone();
            } else if (data.type === 'error') {
              callbacks.onError(data.message || 'Error occurred');
            }
          } catch (e) {
            console.error('Failed to parse SSE payload:', jsonStr, e);
          }
        }
      }
      if (!doneCalled) {
        callbacks.onDone();
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        callbacks.onError(err.message || 'Stream connection failed');
      }
    }
  })();

  return controller;
}
