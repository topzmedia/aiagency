'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getCollections,
  getCollection,
  getCollectionItems,
  createCollection,
  addToCollection,
  removeFromCollection,
} from '@/lib/api';
import type { CollectionCreate, CollectionItemCreate } from '@/lib/types';

export function useCollections() {
  return useQuery({
    queryKey: ['collections'],
    queryFn: getCollections,
  });
}

export function useCollection(id: string) {
  return useQuery({
    queryKey: ['collections', id],
    queryFn: () => getCollection(id),
    enabled: !!id,
  });
}

export function useCollectionItems(id: string) {
  return useQuery({
    queryKey: ['collections', id, 'items'],
    queryFn: () => getCollectionItems(id),
    enabled: !!id,
  });
}

export function useCreateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CollectionCreate) => createCollection(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
    },
  });
}

export function useAddToCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      collectionId,
      data,
    }: {
      collectionId: string;
      data: CollectionItemCreate;
    }) => addToCollection(collectionId, data),
    onSuccess: (_, { collectionId }) => {
      queryClient.invalidateQueries({ queryKey: ['collections', collectionId] });
      queryClient.invalidateQueries({ queryKey: ['collections', collectionId, 'items'] });
    },
  });
}

export function useRemoveFromCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      collectionId,
      itemId,
    }: {
      collectionId: string;
      itemId: string;
    }) => removeFromCollection(collectionId, itemId),
    onSuccess: (_, { collectionId }) => {
      queryClient.invalidateQueries({ queryKey: ['collections', collectionId] });
      queryClient.invalidateQueries({ queryKey: ['collections', collectionId, 'items'] });
    },
  });
}
