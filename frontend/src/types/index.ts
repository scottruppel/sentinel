export interface Bom {
  id: string;
  name: string;
  description: string | null;
  program: string | null;
  version: string | null;
  source_filename: string | null;
  uploaded_at: string;
  component_count: number;
  risk_score_overall: number | null;
  metadata: Record<string, unknown>;
}

export interface Component {
  id: string;
  bom_id: string;
  reference_designator: string | null;
  mpn: string;
  mpn_normalized: string;
  manufacturer: string | null;
  description: string | null;
  quantity: number;
  category: string | null;
  package: string | null;
  value: string | null;
  is_critical: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface EnrichmentStatus {
  bom_id: string;
  total_components: number;
  enriched_components: number;
  pending_components: number;
}

export interface EnrichmentRecord {
  id: string | null;
  component_id: string | null;
  source: string;
  fetched_at: string | null;
  lifecycle_status: string | null;
  yteol: number | null;
  total_inventory: number | null;
  avg_lead_time_days: number | null;
  distributor_count: number | null;
  num_alternates: number | null;
  country_of_origin: string | null;
  single_source: boolean | null;
  rohs_compliant: boolean | null;
  reach_compliant: boolean | null;
  data: Record<string, unknown>;
}

export interface RiskFactor {
  factor: string;
  detail: string;
  contribution: number;
}

export interface RiskScore {
  id: string;
  component_id: string;
  scored_at: string;
  profile: string;
  lifecycle_risk: number;
  supply_risk: number;
  geographic_risk: number;
  supplier_risk: number;
  regulatory_risk: number;
  composite_score: number;
  risk_factors: RiskFactor[];
  recommendation: string | null;
}

export interface RiskSummary {
  overall_score: number;
  max_component_risk: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  top_risks: { component_id: string; composite_score: number; profile: string }[];
  risk_by_category: Record<string, { count: number; avg_composite: number }>;
}

export interface ComponentWithRisk extends Component {
  risk_score: RiskScore | null;
  enrichment: EnrichmentRecord | null;
}

export interface Scenario {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  scenario_type: string;
  parameters: Record<string, unknown>;
  affected_bom_ids: string[] | null;
  status: string;
  summary?: {
    total_components_affected?: number;
    boms_affected?: number;
    avg_risk_delta?: number;
  } | null;
}

export interface ScenarioResult {
  scenario_id: string;
  name: string;
  summary: {
    total_components_affected: number;
    boms_affected: number;
    avg_risk_delta: number;
    components_at_critical: number;
    components_with_no_alternate_source: number;
  };
  baseline_bom_risk: Record<string, number>;
  scenario_bom_risk: Record<string, number>;
  bom_names?: Record<string, string>;
  affected_components: AffectedComponent[];
}

export interface CrossExposureRow {
  mpn_normalized: string;
  manufacturer: string | null;
  bom_count: number;
  bom_ids: string[];
  total_quantity: number;
}

export interface AffectedComponent {
  mpn: string;
  manufacturer: string | null;
  boms: string[];
  baseline_risk: number;
  scenario_risk: number;
  delta: number;
  risk_factors: string[];
  recommendation: string | null;
}

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low';

export function getRiskLevel(score: number): RiskLevel {
  if (score >= 70) return 'critical';
  if (score >= 50) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface NarrativeCitation {
  title: string;
  source_url: string;
  published_at: string | null;
  relevance: string;
}

export interface NarrativeAnalysis {
  facts_used: string[];
  interpretation: string;
  portfolio_impact: string;
  actions: string[];
  citations: NarrativeCitation[];
}

export interface MarketEventPublic {
  id: string;
  title: string;
  summary: string | null;
  source_url: string;
  published_at: string | null;
  event_type: string | null;
  region_tags: string[];
  keywords: string[];
}

export interface NarrativeResponse {
  analysis: NarrativeAnalysis;
  source: 'llm' | 'rules';
  policy_version: string;
  remote_llm_used: boolean;
  matched_events: MarketEventPublic[];
  raw_model_error: string | null;
}

export interface IntelligenceSettings {
  llm_enabled: boolean;
  llm_provider?: string;
  llm_base_url: string;
  llm_model: string;
  policy_version: string;
}

export interface IngestResult {
  inserted: number;
  skipped: number;
  errors: string[];
}
