import { NextRequest, NextResponse } from "next/server";
import { adminSession, backend, jsonError, verifyMutation, withRotatedSession } from "@/lib/server-auth";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
type Decision = { action: "approve" | "reject" | "suspend" | "reactivate"; application_id?: string; partner_id?: string; reason: string };

export async function GET(request: NextRequest) {
  try {
    const session = await adminSession(request);
    if (!session) return jsonError(401, "AUTH_REQUIRED");
    const url = new URL(request.url);
    const role = url.searchParams.get("role");
    const id = url.searchParams.get("application_id");
    const history = url.searchParams.get("history") === "1";
    if (role && !["shop", "consultant"].includes(role)) return jsonError(400, "INVALID_ROLE");
    if (id && !UUID.test(id)) return jsonError(400, "INVALID_APPLICATION_ID");
    const path = id ? `/api/v1/admin/partner-applications/${id}${history ? "/history" : ""}`
      : `/api/v1/admin/partner-applications${role ? `?role=${role}` : ""}`;
    const response = await backend(path, undefined, session.access);
    const payload = await response.json().catch(() => null);
    return withRotatedSession(NextResponse.json(payload ?? {detail: "REQUEST_FAILED"}, {status: response.status}), session.pair);
  } catch { return jsonError(503, "AUTH_BACKEND_UNAVAILABLE"); }
}

export async function POST(request: NextRequest) {
  if (!verifyMutation(request)) return jsonError(403, "CSRF_OR_ORIGIN_DENIED");
  const body = await request.json().catch(() => null) as Decision | null;
  if (!body || !["approve", "reject", "suspend", "reactivate"].includes(body.action) ||
      typeof body.reason !== "string" || body.reason.trim().length < 5 || body.reason.length > 500) return jsonError(400, "INVALID_DECISION");
  const id = body.action === "approve" || body.action === "reject" ? body.application_id : body.partner_id;
  if (!id || !UUID.test(id)) return jsonError(400, "INVALID_TARGET");
  const proof=request.headers.get('x-admin-reauth');
  if (!proof || proof.length > 2048) return jsonError(403,'RECENT_AUTH_REQUIRED');
  try {
    const session = await adminSession(request);
    if (!session) return jsonError(401, "AUTH_REQUIRED");
    const path = body.action === "approve" || body.action === "reject"
      ? `/api/v1/admin/partner-applications/${id}/${body.action}`
      : `/api/v1/admin/partners/${id}/${body.action}`;
    const response = await backend(path, {reason: body.reason.trim()}, session.access, {'X-Admin-Reauth':proof});
    const payload = await response.json().catch(() => null);
    return withRotatedSession(NextResponse.json(payload ?? {detail: "REQUEST_FAILED"}, {status: response.status}), session.pair);
  } catch { return jsonError(503, "AUTH_BACKEND_UNAVAILABLE"); }
}
