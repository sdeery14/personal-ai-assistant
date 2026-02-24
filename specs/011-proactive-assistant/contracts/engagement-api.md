# API Contract: Engagement & Proactiveness

**Prefix**: `/proactive`
**Auth**: All endpoints require `Authorization: Bearer <token>` (JWT)
**Scoping**: All queries filtered by authenticated user's `user_id`

---

## GET /proactive/settings

Get the user's proactiveness settings and calibration state.

**Response 200**:

```json
{
  "global_level": 0.7,
  "suppressed_types": ["weather_briefing"],
  "boosted_types": ["meeting_prep"],
  "user_override": null,
  "is_onboarded": true
}
```

---

## GET /proactive/profile

Get a summary of what the assistant knows about the user (US5: "what do you know about me"). This aggregates data from memory, knowledge graph, patterns, and engagement.

**Response 200**:

```json
{
  "facts": [
    {"content": "Software engineer at Acme Corp", "type": "fact", "confidence": 0.95}
  ],
  "preferences": [
    {"content": "Prefers dark mode", "type": "preference", "confidence": 0.9}
  ],
  "patterns": [
    {"description": "Asks about weather most mornings", "occurrence_count": 7, "acted_on": true}
  ],
  "key_relationships": [
    {"entity": "Sarah", "relationship": "WORKS_WITH", "mentions": 12}
  ],
  "proactiveness": {
    "global_level": 0.7,
    "engaged_categories": ["meeting_prep", "deadline_reminder"],
    "suppressed_categories": ["weather_briefing"]
  }
}
```

---

## Notes

- **No PUT/PATCH endpoints for settings**: Proactiveness adjustments are made through conversation ("be more proactive", "be less proactive") via agent tools. The API is read-only.
- The `GET /proactive/profile` endpoint is also available as an agent tool (`get_user_profile`) so the agent can answer "what do you know about me?" directly in conversation.
- Engagement events are created by agent tools during conversation, not via REST API.
