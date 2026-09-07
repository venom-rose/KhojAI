import { apiClient, API_BASE_URL } from "./apiClient";
import { authService } from "./auth";

export type StructuredCardType =
  | "text"
  | "destination"
  | "hotel"
  | "activity"
  | "flight"
  | "itinerary"
  | "map"
  | "error";

export interface DestinationCardData {
  id: string;
  name: string;
  state: string;
  region: string;
  category: string;
  best_season: string;
  budget: string;
  trust_score: number;
  description?: string;
  latitude?: number;
  longitude?: number;
  image?: string;
  explanation?: string;
  match_breakdown?: Record<string, number>;
}

export interface HotelCardData {
  id: string;
  name: string;
  city?: string;
  price_tier?: string;
  price_per_night_inr: number;
  rating?: number;
  stay_type?: string;
  address?: string;
  amenities?: string[];
  latitude?: number;
  longitude?: number;
  explanation?: string;
}

export interface ActivityCardData {
  id: string;
  title: string;
  destination?: string;
  category?: string;
  duration_hours?: number;
  price_inr?: number;
  recommended_timing?: string;
  description?: string;
  requires_guide?: boolean;
  is_attraction?: boolean;
  explanation?: string;
}

export interface FlightCardData {
  airline: string;
  flight_number?: string;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  duration: string;
  stops: number;
  price_inr: number;
  is_estimate?: boolean;
}

export interface ItineraryCardData {
  summary: string;
  destination: string;
  duration_days: number;
  pacing_rating: string;
  estimated_cost?: {
    total_estimated_inr?: number;
    per_person_inr?: number;
    accommodation_inr?: number;
    activities_and_admission_inr?: number;
    local_transport_inr?: number;
    food_and_dining_inr?: number;
    contingency_inr?: number;
  };
  days: Array<{
    day_number: number;
    title: string;
    neighborhood_cluster?: string;
    morning?: { time_window?: string; theme?: string; activities?: any[] };
    afternoon?: { time_window?: string; theme?: string; activities?: any[] };
    evening?: { time_window?: string; theme?: string; activities?: any[] };
  }>;
  curator_notes?: string[];
}

export interface MapCardData {
  title: string;
  latitude: number;
  longitude: number;
  description?: string;
  zoom?: number;
}

export interface ErrorCardData {
  tool?: string;
  message: string;
  warning?: string;
}

export interface StructuredCard {
  type: StructuredCardType;
  data:
    | DestinationCardData
    | HotelCardData
    | ActivityCardData
    | FlightCardData
    | ItineraryCardData
    | MapCardData
    | ErrorCardData
    | any;
}

export interface AgentActivityEvent {
  intent?: string;
  tools_called?: string[];
  tools_count?: number;
  structured_cards?: StructuredCard[];
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender_type: "user" | "assistant" | "system";
  content: string;
  model_name?: string;
  token_count?: number;
  metadata_json?: {
    streamed?: boolean;
    provider?: string;
    intent?: string;
    tools_used?: string[];
    structured_cards?: StructuredCard[];
    citations?: string[];
    [key: string]: any;
  };
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
      onActivity?: (activity: AgentActivityEvent) => void;
      onDone: (data: {
        message_id: string;
        content: string;
        structured_cards?: StructuredCard[];
        tools_used?: string[];
        intent?: string;
      }) => void;
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
          if (line.startsWith("event: agent_activity")) {
            const nextLine = lines[++i]?.trim();
            if (nextLine?.startsWith("data: ")) {
              try {
                const parsed = JSON.parse(nextLine.slice(6));
                if (callbacks.onActivity) callbacks.onActivity(parsed);
              } catch {
                // Ignore
              }
            }
          } else if (line.startsWith("event: token")) {
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
