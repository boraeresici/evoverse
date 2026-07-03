# Event Payload Schemas

Event payloads are consumed by Chronicle, Replay Lite, Forecast Lite, analytics, and future report surfaces. Every event payload is additive and versioned.

## Envelope

Every payload includes these metadata fields:

- `schemaVersion`: current value is `1`.
- `schema`: `event_payload.<event_type>.v1`.
- `eventType`: mirrors the event row type for downstream consumers.

Consumers should branch on `schemaVersion` and `eventType`. New optional fields may be added inside the same version. Removing or renaming a field requires a new version.

## V1 Contracts

| Event type | Required payload fields | Optional payload fields | Notes |
| --- | --- | --- | --- |
| `species_emerged` | `generation` | `parent_species_id` | New observable species branch. |
| `species_declined` | `decline_percent` |  | Population drop marker. |
| `mutation_detected` |  | `child_species_id`, `trait_deltas` | Bootstrap mutation signals may not create a child species. |
| `region_resource_shift` | `direction` | `from`, `to` | `direction` is `rise` or `fall`; bootstrap events may omit numeric bounds. |
| `region_collapse` |  |  | Collapse state is available through the event row's region reference. |
| `catalyst_action` | `action_type`, `action_id`, `user_id` | `day_key` | `day_key` is added by the store for quota and audit correlation. |

## API Shape

Serialized events expose the payload as-is and repeat the schema markers at the event level for fast consumers:

```json
{
  "eventType": "species_emerged",
  "payload": {
    "generation": 2,
    "parent_species_id": "sp-0001",
    "schemaVersion": 1,
    "schema": "event_payload.species_emerged.v1",
    "eventType": "species_emerged"
  },
  "payloadSchemaVersion": 1,
  "payloadSchema": "event_payload.species_emerged.v1"
}
```

Legacy persisted events without envelope metadata are normalized on load by the backend, so API consumers can rely on the v1 envelope.
