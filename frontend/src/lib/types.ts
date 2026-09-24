export type Role =
  | "administrator"
  | "security_engineer"
  | "incident_responder"
  | "threat_hunter"
  | "soc_analyst"
  | "executive";

export type NavItem = { id: string; label: string; href: string; perm: string };

export type User = {
  id: string;
  email: string;
  full_name: string;
  organization: string;
  job_title: string;
  role: Role;
  status: string;
  email_verified: boolean;
  mfa_enabled: boolean;
  profile_picture: string | null;
  created_at: string | null;
  last_login_at: string | null;
  is_demo: boolean;
};

export type Preferences = {
  theme: string;
  density: string;
  default_dashboard: string;
  refresh_interval: number;
  visible_widgets: Record<string, boolean>;
  saved_layouts: Record<string, unknown>;
  default_filters: Record<string, unknown>;
  notifications: Record<string, boolean>;
};

export type Indicator = {
  id: string;
  value: string;
  type: string;
  severity_score: number;
  severity: string;
  confidence: number;
  tlp: string;
  status: string;
  first_seen: string | null;
  last_seen: string | null;
  country?: string | null;
  city?: string | null;
  lat?: number | null;
  lon?: number | null;
  category: string;
  malware_family?: string | null;
  notes?: string | null;
  tags: string[];
  is_demo?: boolean;
  sources?: { name: string; confidence: number; verdict: string; reported_at: string }[];
  attack?: { id: string; name: string; tactic: string }[];
  relationships?: { id: string; source_id: string; target_id: string; type: string }[];
  internal_events?: { id: string; type: string; source_host: string; user: string | null; occurred_at: string }[];
  enrichment?: Record<string, unknown>;
  score_breakdown?: {
    score: number;
    label: string;
    components: Record<string, unknown>;
    weights: Record<string, number>;
  };
};

export type Alert = {
  id: string;
  title: string;
  severity: string;
  severity_score: number;
  status: string;
  source: string;
  category: string;
  created_at: string;
  updated_at: string | null;
  assignee: { id: string; name: string } | null;
  indicator: Indicator | null;
  notes: string | null;
};

export type Incident = {
  id: string;
  title: string;
  severity: string;
  status: string;
  assignee: string | null;
  created_at: string;
  updated_at: string | null;
  timeline?: { id: string; type: string; message: string; created_at: string }[];
  checklist?: { id: string; label: string; done: boolean }[];
  indicators?: Indicator[];
  alerts?: string[];
  events?: { id: string; type: string; source_host: string; value: string; occurred_at: string }[];
};

export type Paged<T> = { total?: number; page?: number; items: T[] };

export type SocCounters = {
  new_alerts: number;
  unassigned: number;
  my_queue: number;
  critical_alerts: number;
  active_incidents: number;
};

export type ExecDash = {
  risk_score: number;
  critical_indicators: number;
  high_indicators: number;
  active_incidents: number;
  open_alerts: number;
  categories: Record<string, number>;
  geographies: Record<string, number>;
  sources: Record<string, number>;
  alerts_received: number;
  alerts_resolved: number;
  severity_distribution: Record<string, number>;
  map_points: { value: string; lat: number; lon: number; country: string | null; severity: number; type: string }[];
};

export type Hunt = { id: string; name: string; description: string; query: Record<string, string>; tags: string[] };

export type Feed = {
  id: string;
  name: string;
  provider: string;
  type: string;
  status: string;
  enabled: boolean;
  last_poll_at: string | null;
  next_poll_at: string | null;
  poll_interval_minutes: number;
  indicators_received: number;
  error_count: number;
  last_error?: string | null;
};

export type ReportRow = {
  id: string;
  title: string;
  type: string;
  format: string;
  created_at: string;
  status: string;
};

export type SessionRow = {
  id: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_seen_at: string | null;
  revoked: boolean;
};

export type ApiKeyRow = {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  revoked: boolean;
};

export type WebhookRow = {
  id: string;
  name: string;
  url: string;
  events: string[];
  enabled: boolean;
  secret_prefix: string;
};

export type AuditRow = {
  id: string;
  timestamp: string;
  user: string;
  role: string;
  action: string;
  resource: string;
  resource_id: string | null;
  ip_address: string | null;
  correlation_id: string | null;
  result: string;
  metadata: Record<string, unknown> | null;
};

export type AttackTech = { id: string; name: string; tactic: string; covered: boolean };

export type GraphData = {
  nodes: { id: string; label: string; type: string; severity: number }[];
  edges: { source: string; target: string; type: string }[];
};

export type DirectoryUser = { id: string; name: string; role: string; email: string };
