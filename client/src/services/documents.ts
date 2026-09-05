import { apiClient } from "./apiClient";

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  chunk_content: string;
  token_count?: number;
  chunk_metadata: Record<string, any>;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  user_id?: string;
  title: string;
  source_url?: string;
  document_type: string;
  status: "uploaded" | "processing" | "ready" | "failed";
  error_message?: string;
  original_filename?: string;
  file_size?: number;
  mime_type?: string;
  chunk_count: number;
  metadata_json: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentItem {
  raw_content: string;
  chunks: DocumentChunk[];
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface SearchChunkResult {
  chunk_id: string;
  document_id: string;
  document_title: string;
  content: string;
  similarity: number;
  metadata: Record<string, any>;
}

export interface DocumentAskResponse {
  query: string;
  answer: string;
  model: string;
  sources: SearchChunkResult[];
  token_count?: number;
}

export const documentService = {
  async uploadDocument(
    file: File,
    options?: {
      title?: string;
      documentType?: string;
      destinationId?: string;
      processAsync?: boolean;
      onProgress?: (percent: number) => void;
    }
  ): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append("file", file);
    if (options?.title) formData.append("title", options.title);
    if (options?.documentType) formData.append("document_type", options.documentType);
    if (options?.destinationId) formData.append("destination_id", options.destinationId);

    const processAsync = options?.processAsync ?? false;
    const response = await apiClient.post(`/documents?process_async=${processAsync}`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && options?.onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          options.onProgress(percent);
        }
      },
    });
    return response.data;
  },

  async listDocuments(params?: {
    limit?: number;
    offset?: number;
    status?: string;
    search?: string;
  }): Promise<DocumentListResponse> {
    const response = await apiClient.get("/documents", { params });
    return response.data;
  },

  async getDocument(id: string): Promise<DocumentDetail> {
    const response = await apiClient.get(`/documents/${id}`);
    return response.data;
  },

  async deleteDocument(id: string): Promise<void> {
    await apiClient.delete(`/documents/${id}`);
  },

  async reprocessDocument(id: string, processAsync: boolean = false): Promise<DocumentItem> {
    const response = await apiClient.post(`/documents/${id}/reprocess?process_async=${processAsync}`);
    return response.data;
  },

  async searchDocuments(query: string, topK: number = 4): Promise<{ query: string; results: SearchChunkResult[]; count: number }> {
    const response = await apiClient.post("/documents/search", {
      query,
      top_k: topK,
    });
    return response.data;
  },

  async askDocument(query: string, documentId?: string, topK: number = 4): Promise<DocumentAskResponse> {
    const path = documentId ? `/documents/${documentId}/query` : "/documents/query";
    const response = await apiClient.post(path, {
      query,
      document_id: documentId,
      top_k: topK,
    });
    return response.data;
  },
};
