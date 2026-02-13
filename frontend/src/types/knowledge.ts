export type EntityType =
  | "person"
  | "project"
  | "tool"
  | "concept"
  | "organization";

export type RelationshipType =
  | "USES"
  | "PREFERS"
  | "DECIDED"
  | "WORKS_ON"
  | "WORKS_WITH"
  | "KNOWS"
  | "DEPENDS_ON"
  | "MENTIONED_IN"
  | "PART_OF";

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  description: string | null;
  aliases: string[];
  confidence: number;
  mention_count: number;
  created_at: string;
  last_mentioned_at: string | null;
}

export interface Relationship {
  id: string;
  source_entity: Entity;
  target_entity: Entity | null;
  relationship_type: RelationshipType;
  context: string | null;
  confidence: number;
  created_at: string;
}
