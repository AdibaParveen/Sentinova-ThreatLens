export const ALERT_STATUSES = ["new", "acknowledged", "in_progress", "resolved", "closed"];
export const INCIDENT_STATUSES = ["open", "investigating", "contained", "resolved", "closed"];
export const IOC_STATUSES = ["active", "expired", "whitelisted", "under_review"];
export const IOC_TYPES = ["ip", "domain", "url", "email", "hash_md5", "hash_sha1", "hash_sha256", "cve"];
export const SEVERITIES = ["critical", "high", "medium", "low"];
export const TLP = ["clear", "green", "amber", "red"];
export const ROLES = ["administrator", "security_engineer", "incident_responder", "threat_hunter", "soc_analyst", "executive"];
export const USER_STATUSES = ["pending", "active", "locked", "disabled"];

export async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
