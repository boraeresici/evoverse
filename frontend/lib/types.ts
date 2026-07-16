export type UniverseStatus = {
  id: string;
  name: string;
  ageYears: number;
  currentEra: string;
  activeSpecies: number;
  regionCount: number;
  recentEvents: number;
  stabilityIndex: number;
  chiralityEe: number;
  homochiralityIndex: number;
  localOrderIndex: number;
  domainCount: number;
  chiralityLocked: boolean;
};

export type ChronicleEvent = {
  id: string;
  eventType: string;
  eventLabel: string;
  severity: number;
  worldAge: number;
  title: string;
  summary: string;
  regionId: string | null;
  regionName: string | null;
  speciesId: string | null;
  speciesName: string | null;
  payload: Record<string, unknown>;
  payloadSchemaVersion: number;
  payloadSchema: string;
  createdAt: string;
};

export type RegionSummary = {
  id: string;
  x: number;
  y: number;
  biomeType: string;
  energyLevel: number;
  resourceDensity: number;
  stability: number;
  lifeIndex: number;
  chiralityEe: number;
  chiralityLocked: boolean;
  collapsed: boolean;
  dominantSpeciesId: string | null;
  dominantSpeciesName: string | null;
  population: number;
};

export type SpeciesSummary = {
  id: string;
  name: string;
  status: string;
  population: number;
  originRegionId: string;
  emergedAtWorldAge: number;
  generation: number;
  parentSpeciesId: string | null;
  chirality: number;
  heterochiralLoad: number;
  traits: Record<string, number>;
  regions: Array<{ regionId: string; population: number; share: number }>;
  forecast: {
    extinctionRisk: number;
    dominanceProbability: number;
    expansionPressure: number;
    mutationVolatility: number;
  };
};

export type LandingData = {
  universe: UniverseStatus;
  featuredEvents: ChronicleEvent[];
  chroniclePreview: ChronicleEvent[];
  regions: RegionSummary[];
  species: SpeciesSummary[];
};

export type ChronicleData = {
  universe: UniverseStatus;
  timeFilter: string;
  events: ChronicleEvent[];
};

export type RegionDetail = {
  region: RegionSummary;
  populations: Array<{
    speciesId: string;
    speciesName: string;
    status: string;
    population: number;
    growthRate: number;
    migrationPressure: number;
  }>;
  events: ChronicleEvent[];
};

export type SpeciesDetail = {
  species: SpeciesSummary;
  children: SpeciesSummary[];
  events: ChronicleEvent[];
};

export type ObserverUser = {
  id: string;
  mode: string;
  auth: string;
};

export type RoleUser = ObserverUser & {
  role: string;
  status: string;
};

export type IdentityContextData = {
  model: string;
  mode: string;
  auth: {
    provider: string;
    status: string;
    nextProvider: string;
    source: string;
    sessionStrategy: string;
    localFallback: boolean;
    trustedHeaderRequired: boolean;
    googleClientConfigured: boolean;
  };
  users: {
    observer: ObserverUser;
    catalyst: RoleUser;
    admin: RoleUser;
  };
  capabilities: {
    observer: {
      canFollow: boolean;
      canReceiveNotifications: boolean;
    };
    catalyst: {
      permission: {
        canUseCatalyst: boolean;
        reason: string | null;
      };
      quotas: Array<{
        actionType: string;
        dayKey: string;
        limit: number;
        used: number;
        remaining: number;
      }>;
      cooldowns: Array<Record<string, unknown>>;
      regionId: string | null;
    };
    admin: {
      canUseAdmin: boolean;
      reason: string | null;
    };
  };
  roleGate: {
    observerAccess: string;
    catalystAccess: string;
    adminAccess: string;
    subscription: string;
  };
};

export type ObserverFollow = {
  id: string;
  universeId: string;
  userId: string;
  entityType: "region" | "species";
  entityId: string;
  entity: RegionSummary | SpeciesSummary;
  createdAt: string | null;
};

export type ObserverFollowsData = {
  model: string;
  user: ObserverUser;
  follows: {
    regions: ObserverFollow[];
    species: ObserverFollow[];
  };
  counts: {
    regions: number;
    species: number;
    total: number;
  };
};

export type ObserverNotification = {
  id: string;
  model: string;
  userId: string;
  kind:
    | "followed_region_event"
    | "followed_species_event"
    | "catalyst_action"
    | "catalyst_downstream_event";
  title: string;
  summary: string;
  read: boolean;
  readAt: string | null;
  target: {
    type: "region" | "species";
    id: string;
    label: string;
  } | null;
  event: ChronicleEvent;
  createdAt: string;
};

export type ObserverNotificationsData = {
  model: string;
  user: ObserverUser;
  notifications: ObserverNotification[];
  unreadCount: number;
  filters: {
    unreadOnly: boolean;
  };
  pagination: {
    limit: number;
    offset: number;
    total: number;
    hasMore: boolean;
    nextOffset: number | null;
  };
};

export type RulePrimitive = string | number | boolean | null;

export type RuleValue = RulePrimitive | Record<string, RulePrimitive>;

export type RulesSection = Record<string, RuleValue>;

export type RuleReloadStrategy = {
  api: { mode: string; status: string };
  worker: { mode: string; status: string };
  restartRequired: boolean;
};

export type RuleGovernance = {
  validation: string;
  auditLog: string;
  rollback: string;
  writeSurface: string;
  uiEditable: boolean;
  reloadStrategy: RuleReloadStrategy;
};

export type AdminRulesData = {
  model: string;
  mode: string;
  source: string;
  revision?: number;
  rulesHash?: string;
  rules: Record<string, RulesSection>;
  governance?: RuleGovernance;
};

export type RuleIssue = {
  path: string;
  message: string;
};

export type RuleAuditEntry = {
  id: string;
  universeId: string;
  actionType: "validate" | "apply" | "rollback";
  status: "accepted" | "rejected";
  actorId: string;
  reason: string | null;
  currentRulesHash: string | null;
  candidateRulesHash: string | null;
  targetRevision: number | null;
  validationErrors: RuleIssue[] | null;
  reloadStrategy: RuleReloadStrategy | null;
  payload: Record<string, unknown> | null;
  createdAt: string | null;
};

export type RuleRevision = {
  id: string;
  universeId: string;
  revision: number;
  rulesHash: string;
  rules: Record<string, RulesSection>;
  appliedBy: string;
  reason: string | null;
  isActive: boolean;
  createdAt: string | null;
};

export type RuleValidationResponse = {
  valid: boolean;
  rulesHash: string;
  rules: Record<string, RulesSection> | null;
  errors: RuleIssue[];
  warnings: RuleIssue[];
  audit: RuleAuditEntry;
  reloadStrategy: RuleReloadStrategy;
};

export type RuleApplyResponse = {
  applied: boolean;
  revision: number;
  rulesHash: string;
  rules: Record<string, RulesSection>;
  audit: RuleAuditEntry;
  reloadStrategy: RuleReloadStrategy;
};

export type RuleRollbackResponse = {
  rolledBack: boolean;
  restoredFromRevision: number;
  revision: number;
  rulesHash: string;
  rules: Record<string, RulesSection>;
  audit: RuleAuditEntry;
  reloadStrategy: RuleReloadStrategy;
};

export type RuleAuditPage = {
  audit: RuleAuditEntry[];
  pagination: { total: number; limit: number; offset: number };
};

export type RuleRevisionPage = {
  revisions: RuleRevision[];
  pagination: { total: number; limit: number; offset: number };
};

export type DynamicReportScope = "universe" | "region" | "species" | "population";

export type DynamicReportPoint = {
  tick: number;
  worldAge: number;
  metrics: Record<string, number>;
  metadata: Record<string, string | number | boolean | null>;
};

export type DynamicReportDelta = Record<
  string,
  {
    from: number;
    to: number;
    absolute: number;
    percent: number | null;
  }
>;

export type DynamicReportData = {
  model: string;
  scope: {
    type: DynamicReportScope;
    regionId: string | null;
    speciesId: string | null;
  };
  universe: UniverseStatus;
  filters: {
    limit: number;
    fromAge: number | null;
    toAge: number | null;
  };
  baseline: DynamicReportPoint;
  current: DynamicReportPoint;
  delta: DynamicReportDelta;
  series: DynamicReportPoint[];
  coverage: {
    snapshotCount: number;
    seriesCount: number;
    detailSnapshotCount: number;
    totalSnapshots: number;
  };
};

export type SimulationHealthData = {
  status: string;
  persistence: string;
  universe: string;
  ageYears: number;
  tick: number;
  regions: number;
  species: number;
  events: number;
  snapshots?: number;
  workerStaleSeconds: number | null;
  worker: {
    workerId: string;
    status: string;
    lastTick: number;
    lastWorldAge: number;
    lastStep: number;
    lastError: string | null;
    updatedAt: string;
  } | null;
  operations: {
    env: string;
    destructiveOpsAllowed: boolean;
    workerStaleThresholdSeconds: number;
    workerStale: boolean;
    workerState: string;
  };
};

export type SnapshotAggregate = {
  universeId: string;
  tick: number;
  worldAge: number;
  regionCount: number;
  speciesCount: number;
  populationCount: number;
  eventCount: number;
  payload: {
    stability_index?: number;
    [key: string]: unknown;
  };
  createdAt: string | null;
};

export type SnapshotsPage = {
  universe: UniverseStatus;
  snapshots: SnapshotAggregate[];
  pagination: {
    limit: number;
    offset: number;
    total: number;
    hasMore: boolean;
    nextOffset: number | null;
  };
};

export type SnapshotRegionRow = {
  universeId: string;
  tick: number;
  worldAge: number;
  regionId: string;
  x: number;
  y: number;
  biomeType: string;
  energyLevel: number;
  resourceDensity: number;
  stability: number;
  dominantSpeciesId: string | null;
  collapsed: boolean;
  populationCount: number;
  speciesCount: number;
  // Raw snapshot payload — snake_case, passed through from the DB unchanged.
  // Keys are optional: snapshots written before the chirality migrations have none.
  payload: {
    life_index?: number;
    chirality_ee?: number;
    chirality_locked?: boolean;
  };
};

export type SnapshotSpeciesRow = {
  universeId: string;
  tick: number;
  worldAge: number;
  speciesId: string;
  name: string;
  status: string;
  originRegionId: string;
  generation: number;
  parentSpeciesId: string | null;
  populationCount: number;
  regionCount: number;
  traits: Record<string, number>;
  // See SnapshotRegionRow.payload — snake_case, keys absent on older snapshots.
  payload: {
    emerged_at_world_age?: number;
    chirality?: number;
    heterochiral_load?: number;
  };
};

export type SnapshotDetails = {
  universe: UniverseStatus;
  snapshot: SnapshotAggregate;
  coverage: {
    regionSnapshots: number;
    speciesSnapshots: number;
    populationSnapshots: number;
  };
  regions: SnapshotRegionRow[];
  species: SnapshotSpeciesRow[];
  populations: Array<{
    speciesId: string;
    regionId: string;
    populationCount: number;
    growthRate: number;
    migrationPressure: number;
  }>;
};

/**
 * Criticality diagnostics behind /science.
 *
 * `pairs` rides alongside `curve` on purpose: C(r) is a mean over the region
 * pairs that far apart, and that count collapses toward the map's diagonal (two
 * pairs at the far corner of a 12x9). Without it there is no way to tell the
 * measured span from the tail, where a single product can push C(r) past 1.
 */
export type CorrelationField = {
  xi: number;
  c0: number;
  curve: Array<[number, number]>;
  pairs: Array<[number, number]>;
  /** C(r) is already negative at one step: xi is an upper bound, not a value. */
  xiFloored: boolean;
  /** No variance in the field at all — nothing to correlate; xi is meaningless. */
  degenerate: boolean;
  sampleSize: number;
};

export type ScaleFreePoint = {
  width: number;
  height: number;
  L: number;
  /** Mean ξ over the ensemble; null when every seed came back degenerate. */
  xi: number | null;
  /** Seed-to-seed spread of ξ, and how well the mean is pinned. Null at one seed. */
  xiSd: number | null;
  xiSe: number | null;
  xiOverL: number | null;
  seeds: number;
  flooredSeeds: number;
  degenerateSeeds: number;
  /** Majority verdicts over the ensemble — the seed counts above are the evidence. */
  xiFloored: boolean;
  degenerate: boolean;
};

/** mean ± sd/se of one statistic over the seed ensemble. sd/se are null at n = 1. */
export type EnsembleSpread = {
  mean: number | null;
  sd: number | null;
  se: number | null;
  ci95: [number, number] | null;
  n: number;
};

/** Null until the worker has run a scan — a fresh universe has no verdict yet. */
export type ScaleFreeScan = {
  verdict:
    | "critical"
    | "sub_critical"
    | "intermediate"
    | "inconclusive"
    | "underpowered"
    | "degenerate"
    | "insufficient";
  /** How deep each replayed world was advanced — the experiment's parameter. */
  scanTicks: number;
  /** How old Alpha was when the scan ran. Null on rows written before the split. */
  universeTick: number | null;
  measuredAt: string;
  durationMs: number;
  field: string;
  /** Ensemble size. One seed cannot carry a verdict; see the scan's docstring. */
  seeds: number;
  points: ScaleFreePoint[];
  slope: EnsembleSpread | null;
  dataCollapseError: number | null;
  /** Across-seed spread at fixed size: the floor dataCollapseError has to beat. */
  seedNoise: number | null;
  /** dataCollapseError / seedNoise. ~1 ⇒ the sizes are as close as noise allows. */
  collapseRatio: number | null;
  skipped: Array<{ width: number; height: number; reason: string }>;
};

export type TriggerFamily = {
  instances: number;
  rows: number;
  singletonRows: number;
  topLift: number | null;
  topSupport: number | null;
  /** The singleton artefact's signature: lift can only equal n when support is 1. */
  topLiftEqualsInstances: boolean;
  /** Rows that clear the support gate. Everything else is withheld by the API. */
  reportable: Array<{ pattern: string; condition: string; lift: number; support: number }>;
};

export type DiagnosticsData = {
  model: "diagnostics_v1";
  universe: {
    id: string;
    tick: number;
    ageYears: number;
    regions: number;
    species: number;
    seed: number;
    /** Connected same-hand region clusters; 1 means a single hand won the whole map. */
    domainCount: number;
  };
  correlation: Record<string, CorrelationField>;
  census: {
    morphotypes: {
      distinct: number;
      entropy: number;
      effectiveCount: number;
      convergenceIndex: number;
      top: Array<{ sig: number[]; species: number; lineages: number; population: number }>;
    };
    spatialMotifs: {
      distinct: number;
      entropy: number;
      effectiveCount: number;
      top: Array<{ key: string; count: number }>;
    };
    domainSizePowerLaw: {
      domains: number;
      distinctSizes: number;
      histogram: Array<[number, number]>;
      tau: number | null;
      rSquared: number | null;
    };
  };
  triggers: {
    mode: string;
    minSupport: number;
    families: Record<string, TriggerFamily>;
  };
  scaleFree: ScaleFreeScan | null;
};
