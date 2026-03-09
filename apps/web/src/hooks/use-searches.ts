'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSearches,
  getSearch,
  getSearchResults,
  createSearch,
  rerankSearch,
  submitFeedback,
  getResultExplanation,
} from '@/lib/api';
import type { SearchCreate, FeedbackCreate } from '@/lib/types';

export function useSearches() {
  return useQuery({
    queryKey: ['searches'],
    queryFn: getSearches,
  });
}

export function useSearch(id: string) {
  return useQuery({
    queryKey: ['searches', id],
    queryFn: () => getSearch(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === 'completed' || data.status === 'failed')) {
        return false;
      }
      return 3000;
    },
  });
}

export function useSearchResults(id: string, enabled = true) {
  return useQuery({
    queryKey: ['searches', id, 'results'],
    queryFn: () => getSearchResults(id),
    enabled: !!id && enabled,
  });
}

export function useCreateSearch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SearchCreate) => createSearch(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['searches'] });
    },
  });
}

export function useRerankSearch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => rerankSearch(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['searches', id] });
      queryClient.invalidateQueries({ queryKey: ['searches', id, 'results'] });
    },
  });
}

export function useSubmitFeedback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ resultId, data }: { resultId: string; data: FeedbackCreate }) =>
      submitFeedback(resultId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['searches'] });
    },
  });
}

export function useResultExplanation(id: string, enabled = false) {
  return useQuery({
    queryKey: ['results', id, 'explain'],
    queryFn: () => getResultExplanation(id),
    enabled,
  });
}
