export interface StreamChunk {
  content: string;
  sequence: number;
  is_final: boolean;
  correlation_id: string;
  conversation_id?: string;
  error?: string;
  error_type?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming: boolean;
  timestamp: Date;
  error?: string;
  errorType?: string;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  message_preview: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  messages: MessageSummary[];
  created_at: string;
  updated_at: string;
}

export interface MessageSummary {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface UpdateConversationRequest {
  title: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
