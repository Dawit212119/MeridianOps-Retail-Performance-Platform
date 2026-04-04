import api from "./api";

export interface AuditEvent {
  id: number;
  action: string;
  resource_type: string;
  resource_id: string;
  store_id: number | null;
  actor_user_id: number | null;
  detail_json: string;
  created_at: string;
}

export async function listAuditEvents(params?: {
  resource_type?: string;
  action?: string;
  limit?: number;
}): Promise<AuditEvent[]> {
  const query = new URLSearchParams();
  if (params?.resource_type) query.set("resource_type", params.resource_type);
  if (params?.action) query.set("action", params.action);
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  const { data } = await api.get(`/audit/events${qs ? `?${qs}` : ""}`);
  return data;
}

export async function listMemberAuditEvents(memberCode?: string): Promise<AuditEvent[]> {
  const query = memberCode ? `?member_code=${encodeURIComponent(memberCode)}` : "";
  const { data } = await api.get(`/audit/events/member${query}`);
  return data;
}

export async function listCampaignAuditEvents(): Promise<AuditEvent[]> {
  const { data } = await api.get("/audit/events/campaign");
  return data;
}

export async function listOrderAuditEvents(): Promise<AuditEvent[]> {
  const { data } = await api.get("/audit/events/order");
  return data;
}
