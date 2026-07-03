# Dynamic Report API

Dynamic Report v1 exposes chart-ready comparison data from Alpha snapshots. It uses summary snapshots for universe trends and entity detail snapshots for selected region, species, or population reports.

## Endpoint

`GET /universes/alpha/reports/dynamic`

Query parameters:

- `scope`: `universe`, `region`, `species`, or `population`. Default: `universe`.
- `limit`: number of snapshots to compare, from `1` to `50`. Default: `12`.
- `fromAge`, `toAge`: optional world-age filter.
- `regionId`: required for `region` and `population` scopes.
- `speciesId`: required for `species` and `population` scopes.

## Response Shape

```json
{
  "model": "dynamic_report_v1",
  "scope": {
    "type": "universe",
    "regionId": null,
    "speciesId": null
  },
  "baseline": {
    "tick": 96,
    "worldAge": 4307,
    "metrics": {
      "populationCount": 141000,
      "speciesCount": 10,
      "stabilityIndex": 0.41
    }
  },
  "current": {
    "tick": 103,
    "worldAge": 4314,
    "metrics": {
      "populationCount": 142091,
      "speciesCount": 11,
      "stabilityIndex": 0.386
    }
  },
  "delta": {
    "populationCount": {
      "from": 141000,
      "to": 142091,
      "absolute": 1091,
      "percent": 0.774
    }
  },
  "series": [
    {
      "tick": 103,
      "worldAge": 4314,
      "metrics": {
        "populationCount": 142091
      }
    }
  ],
  "coverage": {
    "snapshotCount": 1,
    "seriesCount": 1,
    "detailSnapshotCount": 1,
    "totalSnapshots": 1
  }
}
```

## Scope Metrics

`universe` metrics:

- `regionCount`
- `speciesCount`
- `populationCount`
- `eventCount`
- `stabilityIndex`
- `activeCatalystActions`
- `collapsedRegionCount` when detail snapshot coverage is available

`region` metrics:

- `energyLevel`
- `resourceDensity`
- `stability`
- `populationCount`
- `speciesCount`
- `collapsed`

`species` metrics:

- `populationCount`
- `regionCount`
- `generation`
- `traitStrength`

`population` metrics:

- `populationCount`
- `energyConsumption`
- `growthRate`
- `migrationPressure`

The frontend should chart `series[].metrics` and use `baseline`, `current`, and `delta` for summary cards.
