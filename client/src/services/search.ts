import { apiClient } from "./apiClient";

export interface DestinationSearchResult {
  id: string;
  slug: string;
  name: string;
  state: string;
  region: string;
  category: string;
  best_season: string;
  budget: string;
  trust_score: number;
  description: string;
  image_url: string;
  accent_color: string;
  tags: string[];
  relevance_score: number;
}

export interface DocumentSearchResult {
  chunk_id: string;
  document_id: string;
  document_title: string;
  document_type: string;
  content: string;
  similarity: number;
  relevance_score: number;
  source_url?: string;
  metadata: Record<string, any>;
}

export interface ConversationSearchResult {
  conversation_id: string;
  title: string;
  summary?: string;
  model?: string;
  matched_message?: string;
  is_pinned: boolean;
  is_archived: boolean;
  relevance_score: number;
  updated_at: string;
}

export interface GlobalSearchResponse {
  query: string;
  destinations: DestinationSearchResult[];
  documents: DocumentSearchResult[];
  conversations: ConversationSearchResult[];
  total_hits: number;
}

export interface DestinationSearchParams {
  q?: string;
  region?: string;
  state?: string;
  budget?: string;
  style?: string;
  season?: string;
  experience?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}

export interface PaginatedDestinationResponse {
  items: DestinationSearchResult[];
  total: number;
  limit: number;
  offset: number;
}

export const searchService = {
  async globalSearch(q: string, limit: number = 5): Promise<GlobalSearchResponse> {
    const response = await apiClient.get("/search", {
      params: { q, limit },
    });
    return response.data;
  },

  async searchDestinations(params: DestinationSearchParams): Promise<PaginatedDestinationResponse> {
    const response = await apiClient.get("/search/destinations", {
      params,
    });
    return response.data;
  },

  async searchDocuments(
    q: string,
    params?: { document_type?: string; limit?: number; offset?: number; min_similarity?: number }
  ): Promise<{ items: DocumentSearchResult[]; total: number; limit: number; offset: number }> {
    const response = await apiClient.get("/search/documents", {
      params: { q, ...params },
    });
    return response.data;
  },

  async searchConversations(
    q: string,
    params?: { is_pinned?: boolean; is_archived?: boolean; limit?: number; offset?: number }
  ): Promise<{ items: ConversationSearchResult[]; total: number; limit: number; offset: number }> {
    const response = await apiClient.get("/search/conversations", {
      params: { q, ...params },
    });
    return response.data;
  },
};
