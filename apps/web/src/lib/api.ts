import type {
  Search,
  SearchCreate,
  SearchListResponse,
  SearchResultResponse,
  SearchResult,
  ResultExplanation,
  Collection,
  CollectionCreate,
  CollectionItem,
  CollectionItemCreate,
  IngestionJob,
  IngestionJobCreate,
  FeedbackCreate,
  HealthResponse,
} from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api`
  : '/api';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => 'Unknown error');
    throw new ApiError(body, res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

// Searches
export async function getSearches(): Promise<SearchListResponse> {
  return request<SearchListResponse>('/searches');
}

export async function getSearch(id: string): Promise<Search> {
  return request<Search>(`/searches/${id}`);
}

export async function createSearch(data: SearchCreate): Promise<Search> {
  return request<Search>('/searches', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getSearchResults(
  id: string,
  page = 1,
  pageSize = 20
): Promise<SearchResultResponse> {
  return request<SearchResultResponse>(
    `/searches/${id}/results?page=${page}&page_size=${pageSize}`
  );
}

export async function rerankSearch(id: string): Promise<Search> {
  return request<Search>(`/searches/${id}/rerank`, {
    method: 'POST',
  });
}

export function getExportUrl(id: string, format: 'csv' | 'json'): string {
  return `${BASE_URL}/searches/${id}/export.${format}`;
}

// Results
export async function getResult(id: string): Promise<SearchResult> {
  return request<SearchResult>(`/results/${id}`);
}

export async function submitFeedback(
  resultId: string,
  data: FeedbackCreate
): Promise<void> {
  return request<void>(`/results/${resultId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getResultExplanation(
  id: string
): Promise<ResultExplanation> {
  return request<ResultExplanation>(`/results/${id}/explain`);
}

// Collections
export async function getCollections(): Promise<Collection[]> {
  return request<Collection[]>('/collections');
}

export async function getCollection(id: string): Promise<Collection> {
  return request<Collection>(`/collections/${id}`);
}

export async function createCollection(
  data: CollectionCreate
): Promise<Collection> {
  return request<Collection>('/collections', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getCollectionItems(
  collectionId: string
): Promise<CollectionItem[]> {
  return request<CollectionItem[]>(`/collections/${collectionId}/items`);
}

export async function addToCollection(
  collectionId: string,
  data: CollectionItemCreate
): Promise<CollectionItem> {
  return request<CollectionItem>(`/collections/${collectionId}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function removeFromCollection(
  collectionId: string,
  itemId: string
): Promise<void> {
  return request<void>(`/collections/${collectionId}/items/${itemId}`, {
    method: 'DELETE',
  });
}

// Ingestion
export async function getIngestionJobs(): Promise<IngestionJob[]> {
  return request<IngestionJob[]>('/ingestion/jobs');
}

export async function getIngestionJob(id: string): Promise<IngestionJob> {
  return request<IngestionJob>(`/ingestion/jobs/${id}`);
}

export async function createIngestionJob(
  data: IngestionJobCreate
): Promise<IngestionJob> {
  return request<IngestionJob>('/ingestion/jobs', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Health
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}
