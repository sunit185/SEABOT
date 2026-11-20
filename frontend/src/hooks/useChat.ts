import { useState, useCallback, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { chatApi, askQuestionStream } from '../api/client';
import { Message, SourceChip } from '../types';
import { useAppStore } from '../store/appStore';

export function useChat(chatId: string | null) {
  const queryClient = useQueryClient();
  const { setPartialAnswer, setIsStreaming } = useAppStore();
  const [streamingText, setStreamingText] = useState<string>('');
  const [streamingSources, setStreamingSources] = useState<SourceChip[]>([]);
  const [streamingLang, setStreamingLang] = useState<{ code: string; name: string } | null>(null);
  const [optimisticUserMsg, setOptimisticUserMsg] = useState<Message | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const isRealChat = Boolean(chatId && chatId !== 'new');

  const {
    data: chatDetail,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['chat', chatId],
    queryFn: () => (isRealChat && chatId ? chatApi.getChat(chatId) : null),
    enabled: isRealChat,
  });

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setOptimisticUserMsg(null);
  }, [setIsStreaming]);

  const ask = useCallback(
    async (question: string, scopeDocIds: string[] | null, targetChatId?: string) => {
      const activeId = targetChatId || chatId;
      if (!activeId || activeId === 'new') return;

      stopStreaming();
      setIsStreaming(true);
      setStreamingText('');
      setStreamingSources([]);
      setStreamingLang(null);
      setPartialAnswer('');

      // Add optimistic user question right away
      setOptimisticUserMsg({
        id: 'opt-user-' + Date.now(),
        chat_id: activeId,
        role: 'user',
        content: question,
        is_partial: 0,
        interrupted: 0,
        created_at: new Date().toISOString(),
        sources: [],
      });

      let accumulated = '';

      const controller = askQuestionStream(activeId, question, scopeDocIds, {
        onToken: (token) => {
          accumulated += token;
          setStreamingText(accumulated);
          setPartialAnswer(accumulated);
        },
        onSources: (sources) => {
          setStreamingSources(sources);
        },
        onLanguage: (code, name) => {
          setStreamingLang({ code, name });
        },
        onDone: async () => {
          try {
            await queryClient.refetchQueries({ queryKey: ['chat', activeId] });
            queryClient.invalidateQueries({ queryKey: ['chats'] });
          } finally {
            setOptimisticUserMsg(null);
            setIsStreaming(false);
            setStreamingText('');
            setPartialAnswer('');
            setStreamingLang(null);
          }
        },
        onError: (err) => {
          console.error('SSE ask error:', err);
          setOptimisticUserMsg(null);
          setIsStreaming(false);
          setStreamingText('');
          setStreamingLang(null);
          queryClient.invalidateQueries({ queryKey: ['chat', activeId] });
        },
      });

      abortControllerRef.current = controller;
    },
    [chatId, queryClient, setIsStreaming, setPartialAnswer, stopStreaming]
  );

  const serverMessages = chatDetail?.messages || [];
  const messages = optimisticUserMsg
    ? [...serverMessages, optimisticUserMsg]
    : serverMessages;

  return {
    chat: chatDetail,
    messages,
    isLoading,
    isStreaming: useAppStore((s) => s.isStreaming),
    streamingText,
    streamingSources,
    streamingLang,
    ask,
    stopStreaming,
    refetch,
  };
}
