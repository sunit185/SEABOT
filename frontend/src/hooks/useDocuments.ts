import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentApi } from '../api/client';

export function useDocuments() {
  const queryClient = useQueryClient();

  const { data: documents = [], isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: documentApi.listDocuments,
    refetchInterval: (query) => {
      // Poll every 2s if any document is uploading, parsing, or indexing
      const docs = query.state.data;
      const isProcessing = docs?.some(
        (d) => d.status === 'uploading' || d.status === 'parsing' || d.status === 'indexing'
      );
      return isProcessing ? 2000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => documentApi.uploadDocuments(files),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (docId: string) => documentApi.deleteDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  return {
    documents,
    isLoading,
    refetch,
    upload: uploadMutation.mutateAsync,
    isUploading: uploadMutation.isPending,
    deleteDoc: deleteMutation.mutateAsync,
  };
}
