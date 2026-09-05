import { apiClient, API_BASE_URL } from "./apiClient";
import { authService } from "./auth";

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender_type: "user" | "assistant" | "system";
  content: string;
  model_name?: string;
  token_count?: number;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id?: string;
  title: string;
  summary?: string;
  model?: string;
  is_pinned: boolean;
  is_archived: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export interface ConversationListResponse {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

export const chatService = {
  async listConversations(params?: {
    limit?: number;
    offset?: number;
    search?: string;
    include_archived?: boolean;
  }): Promise<ConversationListResponse> {
    const response = await apiClient.get("/chat/conversations", { params });
    return response.data;
  },

  async createConversation(data: {
    title?: string;
    model?: string;
    initial_message?: string;
  }): Promise<ConversationDetail> {
    const response = await apiClient.post("/chat/conversations", data);
    return response.data;
  },

  async getConversation(id: string): Promise<ConversationDetail> {
    const response = await apiClient.get(`/chat/conversations/${id}`);
    return response.data;
  },

  async updateConversation(
    id: string,
    data: { title?: string; is_pinned?: boolean; is_archived?: boolean }
  ): Promise<Conversation> {
    const response = await apiClient.patch(`/chat/conversations/${id}`, data);
    return response.data;
  },

  async deleteConversation(id: string): Promise<void> {
    await apiClient.delete(`/chat/conversations/${id}`);
  },

  async sendMessageSync(
    conversationId: string,
    content: string,
    model?: string
  ): Promise<ChatMessage> {
    const response = await apiClient.post(
      `/chat/conversations/${conversationId}/messages`,
      {
        content,
        model,
        stream: false,
      }
    );
    return response.data;
  },

  async streamMessage(
    conversationId: string,
    content: string,
    callbacks: {
      onToken: (token: string) => void;
      onDone: (data: { message_id: string; content: string }) => void;
      onError: (err: string) => void;
    },
    model?: string
  ): Promise<void> {
    const token = authService.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = `${API_BASE_URL}/chat/conversations/${conversationId}/messages?stream=true`;

    try {
      const response = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify({ content, model, stream: true }),
      });

      if (!response.ok) {
        const errText = await response.text();
        callbacks.onError(errText || `Server responded with ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError("No response stream available.");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i].trim();
          if (line.startsWith("event: token")) {
            const nextLine = lines[++i]?.trim();
            if (nextLine?.startsWith("data: ")) {
              try {
                const parsed = JSON.parse(nextLine.slice(6));
                if (parsed.token) callbacks.onToken(parsed.token);
              } catch {
                // Ignore parse errors
              }
            }
          } else if (line.startsWith("event: done")) {
            const nextLine = lines[++i]?.trim();
            if (nextLine?.startsWith("data: ")) {
              try {
                const parsed = JSON.parse(nextLine.slice(6));
                callbacks.onDone(parsed);
              } catch {
                // Ignore
              }
            }
          } else if (line.startsWith("event: error")) {
            const nextLine = lines[++i]?.trim();
            if (nextLine?.startsWith("data: ")) {
              try {
                const parsed = JSON.parse(nextLine.slice(6));
                callbacks.onError(parsed.error || "Streaming error");
              } catch {
                callbacks.onError("Streaming error occurred.");
              }
            }
          }
        }
      }
    } catch (err: any) {
      callbacks.onError(err.message || "Failed to stream message");
    }
  },

  async regenerateMessage(
    conversationId: string,
    messageId?: string,
    model?: string
  ): Promise<ChatMessage> {
    const path = messageId
      ? `/chat/conversations/${conversationId}/messages/${messageId}/regenerate`
      : `/chat/conversations/${conversationId}/regenerate`;
    const response = await apiClient.post(path, { model });
    return response.data;
  },
};
