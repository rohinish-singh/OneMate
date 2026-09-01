/**
 * OneMate API TypeScript Definitions
 * Strictly mirrors backend schemas and API contracts.
 */

// ==========================================
// Generic API & Error Types
// ==========================================

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

export interface ApiError {
  detail: string | ApiErrorDetail[];
  status?: number;
}

export interface HealthResponse {
  status: string;
}

// ==========================================
// CPSE
// ==========================================

export interface CPSE {
  id: string;
  code: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface CPSECreateRequest {
  code: string;
  name: string;
}

export interface CPSEDeleteResponse {
  status: string;
  deleted_id: string;
  deleted_type: string;
}

// ==========================================
// Materials
// ==========================================

export interface MaterialDeleteResponse {
  status: string;
  deleted_id: string;
  deleted_type: string;
}

export interface MaterialListItem {
  id: string;
  cpse_id: string;
  source_material_code: string;
  source_description: string;
  category: string | null;
  normalized_description: string | null;
}

export interface MaterialDetailResponse {
  id: string;
  cpse_id: string;
  source_material_code: string;
  source_description: string;
  source_uom: string;
  source_specifications: string | null;
  raw_source_data: Record<string, unknown> | null;
  category: string | null;
  valve_type: string | null;
  size: string | null;
  body_material: string | null;
  pressure_class: string | null;
  connection_type: string | null;
  trim: string | null;
  normalized_uom: string | null;
  normalized_description: string | null;
  normalized_attributes: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ImportRowError {
  row: number;
  error: string;
}

export interface MaterialImportResponse {
  total_rows: number;
  imported_rows: number;
  rejected_rows: number;
  duplicate_rows: number;
  errors: ImportRowError[];
}

export interface NormalizeResponse {
  status: string;
  material_id: string;
  normalized: boolean;
}

// ==========================================
// Matching & Recommendations
// ==========================================

export type MatchClassification = 'SAME' | 'POTENTIALLY_EQUIVALENT' | 'DIFFERENT';

export interface MatchRecommendationItem {
  candidate_id: string;
  classification: string;
  confidence: number;
  explanation: string | null;
}

export interface MatchResponse {
  status: string;
  material_id: string;
  candidate_count: number;
  recommendations_created: number;
  recommendations: MatchRecommendationItem[];
}

export interface HarmonizeResponse {
  status: string;
  reason?: string;
  national_material_id?: string;
  national_material_action?: string;
  mapping_id?: string;
  national_code?: string;
}

// ==========================================
// National Materials
// ==========================================

export interface NationalMaterialListItem {
  id: string;
  national_code: string;
  canonical_description: string;
  status: string | null;
}

export interface NationalMaterialDetailResponse {
  id: string;
  national_code: string;
  category: string;
  canonical_description: string;
  valve_type: string;
  size: string;
  body_material: string;
  pressure_class: string;
  connection_type: string;
  trim: string;
  normalized_uom: string;
  identity_key: string;
  status: string | null;
}

// ==========================================
// Mapping History
// ==========================================

export interface MaterialMappingHistoryItem {
  id: string;
  material_id: string;
  national_material_id: string;
  basis: string;
  status: string;
  recommendation_id: string | null;
  created_at: string;
  updated_at: string;
}

// ==========================================
// Reviews
// ==========================================

export interface ReviewQueueItem {
  recommendation_id: string;
  source_material_id: string;
  candidate_material_id: string;
  classification: string;
  confidence: number | null;
  evidence: Record<string, unknown> | null;
  explanation: string | null;
  source_valve_type: string | null;
  source_size: string | null;
  source_body_material: string | null;
  source_pressure_class: string | null;
  source_connection_type: string | null;
  source_trim: string | null;
}

export interface ReviewQueueResponse {
  queue: ReviewQueueItem[];
}

export type ReviewActionType = 'ACCEPT' | 'REJECT' | 'MARK_DIFFERENT' | 'OVERRIDE';

export interface ReviewActionRequest {
  action: ReviewActionType | string;
  reason?: string | null;
  national_material_id?: string | null;
}

export interface ReviewActionResponse {
  status: string;
  action: string;
  mapping_id: string | null;
  national_material_id: string | null;
}

// ==========================================
// Audit Logs
// ==========================================

export interface AuditLogItem {
  id: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  reason: string | null;
  created_at: string;
}

export interface AuditLogFilterParams {
  entity_type?: string;
  entity_id?: string;
  skip?: number;
  limit?: number;
}

// ==========================================
// Dashboard
// ==========================================

export interface InventoryMetrics {
  total_materials: number;
  total_cpses: number;
}

export interface HarmonizationMetrics {
  total_national_materials: number;
  total_mapped_materials: number;
  automation_rate_percentage: number;
}

export interface ReviewMetrics {
  pending_reviews: number;
  completed_reviews: number;
}

export interface CPSEBreakdown {
  cpse_id: string;
  cpse_name: string;
  total_materials: number;
  mapped_materials: number;
}

export interface DashboardResponse {
  inventory: InventoryMetrics;
  harmonization: HarmonizationMetrics;
  review: ReviewMetrics;
  cpse_breakdown: CPSEBreakdown[];
}
