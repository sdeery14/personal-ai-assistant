import { create } from "zustand";
import { ChatMessage } from "@/types/chat";
import { StreamError } from "@/lib/chat-stream";

interface ChatState {
  messages: ChatMessage[];
  conversationId: string | null;
  isStreaming: boolean;
  error: StreamError | null;
  lastFailedMessage: string | null;
  greetingRequested: boolean;

  // Actions
  addUserMessage: (content: string) => string;
  addAssistantMessage: () => string;
  appendStreamChunk: (messageId: string, content: string) => void;
  finalizeStream: (messageId: string, conversationId?: string) => void;
  setStreaming: (streaming: boolean) => void;
  setError: (error: StreamError | null) => void;
  setLastFailedMessage: (message: string | null) => void;
  clearMessages: () => void;
  setConversationId: (id: string | null) => void;
  loadMessages: (messages: ChatMessage[]) => void;
  setGreetingRequested: (value: boolean) => void;
}

let messageCounter = 0;
function generateId(): string {
  return `msg-${Date.now()}-${++messageCounter}`;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  conversationId: null,
  isStreaming: false,
  error: null,
  lastFailedMessage: null,
  greetingRequested: false,

  addUserMessage: (content: string) => {
    const id = generateId();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "user",
          content,
          isStreaming: false,
          timestamp: new Date(),
        },
      ],
      error: null,
    }));
    return id;
  },

  addAssistantMessage: () => {
    const id = generateId();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "assistant",
          content: "",
          isStreaming: true,
          timestamp: new Date(),
        },
      ],
    }));
    return id;
  },

  appendStreamChunk: (messageId: string, content: string) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId
          ? { ...msg, content: msg.content + content }
          : msg,
      ),
    }));
  },

  finalizeStream: (messageId: string, conversationId?: string) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId ? { ...msg, isStreaming: false } : msg,
      ),
      isStreaming: false,
      conversationId: conversationId || state.conversationId,
    }));
  },

  setStreaming: (streaming: boolean) => {
    set({ isStreaming: streaming });
  },

  setError: (error: StreamError | null) => {
    set({ error, isStreaming: false });
  },

  setLastFailedMessage: (message: string | null) => {
    set({ lastFailedMessage: message });
  },

  clearMessages: () => {
    set({
      messages: [],
      conversationId: null,
      isStreaming: false,
      error: null,
      lastFailedMessage: null,
      greetingRequested: false,
    });
  },

  setConversationId: (id: string | null) => {
    set({ conversationId: id });
  },

  loadMessages: (messages: ChatMessage[]) => {
    set({ messages });
  },

  setGreetingRequested: (value: boolean) => {
    set({ greetingRequested: value });
  },
}));
