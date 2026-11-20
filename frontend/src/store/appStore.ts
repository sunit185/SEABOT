import { create } from 'zustand';
import { stateApi } from '../api/client';
import { UserState } from '../types';

interface AppStoreState {
  activeChatId: string | null;
  sidebarCollapsed: boolean;
  sidebarScroll: number;
  viewerDocId: string | null;
  viewerPage: number;
  inputDraft: string;
  scopeDocIds: string[];
  partialAnswer: string;
  isStreaming: boolean;

  setActiveChatId: (id: string | null) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setSidebarScroll: (scroll: number) => void;
  setViewer: (docId: string | null, page?: number) => void;
  setInputDraft: (draft: string) => void;
  setScopeDocIds: (ids: string[]) => void;
  toggleScopeDocId: (id: string) => void;
  setPartialAnswer: (answer: string) => void;
  setIsStreaming: (streaming: boolean) => void;

  restoreState: () => Promise<void>;
  saveStateToServer: () => Promise<void>;
}

const LOCAL_STORAGE_KEY = 'seabot_state';

function loadLocalState(): Partial<UserState> {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveLocalState(state: Partial<UserState>) {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.error('Failed to save local state:', e);
  }
}

let debounceTimer: any = null;

export const useAppStore = create<AppStoreState>((set, get) => {
  const local = loadLocalState();

  const syncState = () => {
    const current = get();
    const payload: Partial<UserState> = {
      active_chat_id: current.activeChatId,
      sidebar_collapsed: current.sidebarCollapsed ? 1 : 0,
      sidebar_scroll: current.sidebarScroll,
      viewer_doc_id: current.viewerDocId,
      viewer_page: current.viewerPage,
      input_draft: current.inputDraft,
    };
    saveLocalState(payload);

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      stateApi.saveState(payload).catch((err) => console.warn('Server state sync failed:', err));
    }, 1000);
  };

  return {
    activeChatId: local.active_chat_id || null,
    sidebarCollapsed: local.sidebar_collapsed === 1,
    sidebarScroll: local.sidebar_scroll || 0,
    viewerDocId: local.viewer_doc_id || null,
    viewerPage: local.viewer_page || 1,
    inputDraft: local.input_draft || '',
    scopeDocIds: [],
    partialAnswer: '',
    isStreaming: false,

    setActiveChatId: (id) => {
      set({ activeChatId: id });
      syncState();
    },

    setSidebarCollapsed: (collapsed) => {
      set({ sidebarCollapsed: collapsed });
      syncState();
    },

    setSidebarScroll: (scroll) => {
      set({ sidebarScroll: scroll });
      syncState();
    },

    setViewer: (docId, page = 1) => {
      set({ viewerDocId: docId, viewerPage: page });
      syncState();
    },

    setInputDraft: (draft) => {
      set({ inputDraft: draft });
      syncState();
    },

    setScopeDocIds: (ids) => set({ scopeDocIds: ids }),

    toggleScopeDocId: (id) => {
      const current = get().scopeDocIds;
      if (current.includes(id)) {
        set({ scopeDocIds: current.filter((x) => x !== id) });
      } else {
        set({ scopeDocIds: [...current, id] });
      }
    },

    setPartialAnswer: (answer) => set({ partialAnswer: answer }),
    setIsStreaming: (streaming) => set({ isStreaming: streaming }),

    restoreState: async () => {
      try {
        const serverState = await stateApi.getState();
        if (serverState) {
          set({
            activeChatId: serverState.active_chat_id || get().activeChatId,
            sidebarCollapsed: serverState.sidebar_collapsed === 1,
            sidebarScroll: serverState.sidebar_scroll || get().sidebarScroll,
            viewerDocId: serverState.viewer_doc_id || get().viewerDocId,
            viewerPage: serverState.viewer_page || get().viewerPage,
            inputDraft: serverState.input_draft !== null && serverState.input_draft !== undefined ? serverState.input_draft : get().inputDraft,
          });
        }
      } catch (err) {
        console.warn('Could not restore state from server, using local state:', err);
      }
    },

    saveStateToServer: async () => {
      syncState();
    },
  };
});
