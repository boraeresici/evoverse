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
| `mutation_detected` |  | `child_species_id`, `trait_deltas`, `chiral_flip` | Bootstrap mutation signals may not create a child species. `chiral_flip` marks a rare, usually lethal handedness flip. |
| `region_resource_shift` | `direction` | `from`, `to` | `direction` is `rise` or `fall`; bootstrap events may omit numeric bounds. |
| `region_collapse` |  | `catalyst_action_ids`, `catalyst_user_ids`, `catalyst_action_types` | Collapse state is available through the event row's region reference. Every collapse is organic and aperiodic: depletion drove the region's stability and resource below the collapse thresholds (see `docs/SIMULATION_FLOW_AND_FORMULAS.md` §8). There is no scripted beat and no `synthetic` flag anymore — the whole chronicle is ecology, so nothing needs excluding. The optional catalyst keys attribute the collapse when a user action was acting on the region at the time. |
| `catalyst_action` | `action_type`, `action_id`, `user_id` | `day_key` | `day_key` is added by the store for quota and audit correlation. |
| `symmetry_break` | `scope` | `hand`, `hand_sign`, `homochirality_index` | `scope` is `region` (first molecular break), `lineage` (a species commits a hand), or `universe` (full homochirality). Universe scope carries no `regionId`. See `docs/CHIRALITY_AND_MIND.md`. |
| `era_advanced` | `from_era`, `to_era` | `homochirality_index` | The universe crossed a maturity gate. Carries no `regionId`. See `docs/CHIRALITY_AND_MIND.md` §6.4. |

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
