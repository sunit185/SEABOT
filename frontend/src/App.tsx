import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ChatPage } from './pages/ChatPage';
import { ViewerPage } from './pages/ViewerPage';
import { useAppStore } from './store/appStore';

export const App: React.FC = () => {
  const { restoreState, activeChatId } = useAppStore();

  useEffect(() => {
    restoreState();
  }, [restoreState]);

  return (
    <Routes>
      <Route
        path="/"
        element={
          activeChatId ? (
            <Navigate to={`/chat/${activeChatId}`} replace />
          ) : (
            <Navigate to="/chat/new" replace />
          )
        }
      />
      <Route path="/chat/new" element={<ChatPage />} />
      <Route path="/chat/:chatId" element={<ChatPage />} />
      <Route path="/viewer/:docId" element={<ViewerPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
