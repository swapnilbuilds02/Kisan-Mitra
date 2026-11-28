import { NextRequest, NextResponse } from "next/server";
import { adminSession, backend, clearSession, csrfToken, jsonError, setCsrf, setSession, TokenPair, verifyMutation, withRotatedSession } from "@/lib/server-auth";

type Context = {params: Promise<{action: string}>};
const allowed = new Set(["login", "otp-request", "otp-verify", "forgot", "reset-verify", "reset", "password-change", "logout", "reauth"]);

async function relay(path: string, body: unknown, access?: string) {
  const response = await backend(path, body, access);
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  return {response, payload};
}

export async function GET(request: NextRequest, context: Context) {
  const {action} = await context.params;
  if (action === "csrf") {
    const token = csrfToken();
    const result = NextResponse.json({csrf_token: token});
    setCsrf(result, token);
    result.headers.set("Cache-Control", "no-store");
    return result;
  }
  if (action !== "me") return jsonError(404, "NOT_FOUND");
  try {
    const session = await adminSession(request);
    if (!session) { const denied=jsonError(401,"AUTH_REQUIRED");clearSession(denied);return denied; }
    return withRotatedSession(NextResponse.json(session.identity, {headers: {"Cache-Control": "no-store"}}), session.pair);
  } catch { return jsonError(503, "AUTH_BACKEND_UNAVAILABLE"); }
}

export async function POST(request: NextRequest, context: Context) {
  const {action} = await context.params;
  if (!allowed.has(action)) return jsonError(404, "NOT_FOUND");
  if (!verifyMutation(request)) return jsonError(403, "CSRF_OR_ORIGIN_DENIED");
  const body = await request.json().catch(() => null);
  if (body === null || typeof body !== "object" || Array.isArray(body)) return jsonError(400, "INVALID_REQUEST");
  try {
    if (action === "login" || action === "otp-verify") {
      const path = action === "login" ? "/api/v1/auth/password/login" : "/api/v1/auth/admin/otp/verify";
      const {response, payload} = await relay(path, body);
      if (!response.ok || !payload) return jsonError(response.status, "INVALID_CREDENTIALS");
      const pair = payload as TokenPair;
      const identityResponse = await backend("/api/v1/auth/session", undefined, pair.access_token);
      const identity = identityResponse.ok ? await identityResponse.json() as {role: string; account_state: string} : null;
      if (!identity || identity.account_state !== "active" || !["admin", "super_admin"].includes(identity.role)) {
        await backend("/api/v1/auth/logout", {}, pair.access_token).catch(() => null);
        return jsonError(403, "ADMIN_ONLY");
      }
      const result = NextResponse.json({status: "authenticated"});
      setSession(result, pair);
      return result;
    }
    if (action === "otp-request" || action === "forgot" || action === "reset-verify" || action === "reset") {
      const path = ({"otp-request": "/api/v1/auth/admin/otp/request", forgot: "/api/v1/auth/password/forgot",
        "reset-verify": "/api/v1/auth/password/reset/verify", reset: "/api/v1/auth/password/reset"} as const)[action as "otp-request" | "forgot" | "reset-verify" | "reset"];
      const {response, payload} = await relay(path, body);
      if (!response.ok) return jsonError(response.status, typeof payload?.detail === "string" ? payload.detail : "REQUEST_FAILED");
      const result = NextResponse.json(payload ?? {status: "updated"}, {status: response.status === 204 ? 200 : response.status});
      result.headers.set("Cache-Control", "no-store");
      return result;
    }
    const session = await adminSession(request);
    if (!session) {
      const denied=jsonError(401,"AUTH_REQUIRED");clearSession(denied);return denied;
    }
    if (action === "logout") {
      await backend("/api/v1/auth/logout", {}, session.access).catch(() => null);
      const result = NextResponse.json({status: "logged_out"});
      clearSession(result);
      return result;
    }
    if (action === "reauth") {
      const {response,payload}=await relay("/api/v1/admin/reauth",body,session.access);
      if (!response.ok) return jsonError(response.status,"INVALID_CREDENTIALS");
      return withRotatedSession(NextResponse.json(payload,{headers:{"Cache-Control":"no-store"}}),session.pair);
    }
    const {response, payload} = await relay("/api/v1/auth/password/change", body, session.access);
    if (!response.ok) return jsonError(response.status, typeof payload?.detail === "string" ? payload.detail : "REQUEST_FAILED");
    const result = NextResponse.json({status: "changed"});
    clearSession(result);
    return result;
  } catch { return jsonError(503, "AUTH_BACKEND_UNAVAILABLE"); }
}
