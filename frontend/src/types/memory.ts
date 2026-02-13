export type MemoryType = "fact" | "preference" | "decision" | "note" | "episode";

export interface MemoryItem {
  id: string;
  content: string;
  type: MemoryType;
  importance: number;
  confidence: number;
  source_conversation_id: string | null;
  created_at: string;
}
