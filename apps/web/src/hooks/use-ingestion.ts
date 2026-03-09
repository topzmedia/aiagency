'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getIngestionJobs, getIngestionJob, createIngestionJob } from '@/lib/api';
import type { IngestionJobCreate } from '@/lib/types';

export function useIngestionJobs() {
  return useQuery({
    queryKey: ['ingestion-jobs'],
    queryFn: getIngestionJobs,
  });
}

export function useIngestionJob(id: string) {
  return useQuery({
    queryKey: ['ingestion-jobs', id],
    queryFn: () => getIngestionJob(id),
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

export function useCreateIngestionJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: IngestionJobCreate) => createIngestionJob(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingestion-jobs'] });
    },
  });
}
