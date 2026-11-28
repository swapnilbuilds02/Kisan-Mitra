import "server-only";
import { randomBytes, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export type Identity = { id: string; role: string; account_state: string; account_tier: string };
export type TokenPair = { access_token: string; refresh_token: string; token_type: string; expires_in: number };
const ACCESS = "km_access";
const REFRESH = "km_refresh";
const CSRF = "km_csrf";
const REQUEST_TIMEOUT = 12000;

function apiUrl() {
  const value = process.env.AUTH_API_URL?.replace(/\/$/, "");
  if (!value || (!value.startsWith("https://") && !/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(value))) {
    throw new Error("AUTH_API_URL is not configured for HTTPS or local development");
  }
  return value;
}

export async function backend(path: string, body?: unknown, access?: string, extraHeaders: Record<string,string> = {}): Promise<Response> {
  return fetch(`${apiUrl()}${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", ...(access ? {Authorization: `Bearer ${access}`} : {}), ...extraHeaders },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store", signal: AbortSignal.timeout(REQUEST_TIMEOUT),
  });
}

export function jsonError(status: number, code: string) {
  return NextResponse.json({detail: code}, {status, headers: {"Cache-Control": "no-store"}});
}

export function csrfToken() { return randomBytes(32).toString("base64url"); }
export function setCsrf(response: NextResponse, token: string) {
  response.cookies.set(CSRF, token, {httpOnly: false, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/"});
}
export function verifyMutation(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const expectedOrigin = new URL(request.url).origin;
  const cookie = request.cookies.get(CSRF)?.value ?? "";
  const submitted = request.headers.get("x-csrf-token") ?? "";
  if (origin !== expectedOrigin || !cookie || !submitted) return false;
  const a = Buffer.from(cookie), b = Buffer.from(submitted);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function setSession(response: NextResponse, pair: TokenPair) {
  const options = {httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict" as const, path: "/"};
  response.cookies.set(ACCESS, pair.access_token, {...options, maxAge: Math.min(pair.expires_in, 900)});
  response.cookies.set(REFRESH, pair.refresh_token, {...options, maxAge: 30 * 24 * 60 * 60});
  response.headers.set("Cache-Control", "no-store");
}
export function clearSession(response: NextResponse) {
  response.cookies.delete(ACCESS);
  response.cookies.delete(REFRESH);
  response.headers.set("Cache-Control", "no-store");
}

const refreshes = new Map<string, Promise<TokenPair | null>>();
async function rotate(refresh: string): Promise<TokenPair | null> {
  if (!refreshes.has(refresh)) {
    const pending = backend("/api/v1/auth/refresh", {refresh_token: refresh})
      .then(async response => response.ok ? await response.json() as TokenPair : null)
      .catch(() => null);
    refreshes.set(refresh, pending);
    setTimeout(() => refreshes.delete(refresh), 3000);
  }
  return refreshes.get(refresh)!;
}

export async function adminSession(request: NextRequest): Promise<{identity: Identity; access: string; pair?: TokenPair} | null> {
  let access = request.cookies.get(ACCESS)?.value;
  let pair: TokenPair | undefined;
  if (access) {
    const response = await backend("/api/v1/auth/session", undefined, access);
    if (response.ok) {
      const identity = await response.json() as Identity;
      return identity.account_state === "active" && ["admin", "super_admin"].includes(identity.role)
        ? {identity, access} : null;
    }
    if (response.status !== 401) return null;
  }
  const refresh = request.cookies.get(REFRESH)?.value;
  if (!refresh) return null;
  pair = await rotate(refresh) ?? undefined;
  if (!pair) return null;
  access = pair.access_token;
  const response = await backend("/api/v1/auth/session", undefined, access);
  if (!response.ok) return null;
  const identity = await response.json() as Identity;
  if (identity.account_state !== "active" || !["admin", "super_admin"].includes(identity.role)) return null;
  return {identity, access, pair};
}

export function withRotatedSession<T extends NextResponse>(response: T, pair?: TokenPair): T {
  if (pair) setSession(response, pair);
  return response;
}
