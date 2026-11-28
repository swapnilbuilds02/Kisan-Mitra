import * as SecureStore from "expo-secure-store";

export type Role = "farmer" | "shop" | "consultant" | "admin" | "super_admin";
export type Identity = { id: string; role: Role; account_state: string; account_tier: string };
export type TokenPair = { access_token: string; refresh_token: string; token_type: "bearer"; expires_in: number };
export type Challenge = { status: "accepted"; challenge_id: string };
export type RegistrationRole = "farmer" | "shop" | "consultant";

const REFRESH_KEY = "km.auth.refresh.v1";
const REQUEST_TIMEOUT_MS = 12000;
const configuredUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  constructor(public status: number, public code: string) {
    super(code);
  }
}

export function normalizeMobile(input: string): string {
  const digits = input.trim().replace(/[\s-]/g, "");
  const result = /^(?:\+91|91)?([6-9][0-9]{9})$/.exec(digits);
  if (!result) throw new ApiError(400, "INVALID_MOBILE");
  return result[1];
}

export class AuthClient {
  private accessToken: string | null = null;
  private refreshPromise: Promise<TokenPair> | null = null;

  private baseUrl(): string {
    const localDev = __DEV__ && /^http:\/\/(localhost|127\.0\.0\.1|10\.0\.2\.2)(:\d+)?$/.test(configuredUrl);
    if (!configuredUrl || (!configuredUrl.startsWith("https://") && !localDev)) {
      throw new ApiError(503, "API_NOT_CONFIGURED");
    }
    return configuredUrl;
  }

  async request<T>(path: string, body?: unknown, token?: string, method?: "GET" | "POST" | "PATCH"): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(`${this.baseUrl()}${path}`, {
        method: method ?? (body === undefined ? "GET" : "POST"),
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new ApiError(response.status, typeof payload.detail === "string" ? payload.detail : "REQUEST_FAILED");
      }
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(0, controller.signal.aborted ? "REQUEST_TIMEOUT" : "NETWORK_UNAVAILABLE");
    } finally {
      clearTimeout(timer);
    }
  }

  private async save(pair: TokenPair): Promise<void> {
    await SecureStore.setItemAsync(REFRESH_KEY, pair.refresh_token, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
    this.accessToken = pair.access_token;
  }

  async accept(pair: TokenPair): Promise<Identity> {
    await this.save(pair);
    try {
      const identity = await this.me();
      if (identity.role === "admin" || identity.role === "super_admin") {
        await this.clear();
        throw new ApiError(403, "ADMIN_WEB_ONLY");
      }
      return identity;
    } catch (error) {
      await this.clear();
      throw error;
    }
  }

  async passwordLogin(mobile: string, password: string): Promise<Identity> {
    const pair = await this.request<TokenPair>("/api/v1/auth/password/login", { mobile_number: normalizeMobile(mobile), password });
    return this.accept(pair);
  }

  async refresh(): Promise<TokenPair> {
    if (this.refreshPromise) return this.refreshPromise;
    this.refreshPromise = (async () => {
      const saved = await SecureStore.getItemAsync(REFRESH_KEY);
      if (!saved) throw new ApiError(401, "SESSION_EXPIRED");
      try {
        const pair = await this.request<TokenPair>("/api/v1/auth/refresh", { refresh_token: saved });
        await this.save(pair);
        return pair;
      } catch (error) {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) await this.clear();
        throw error;
      }
    })();
    try { return await this.refreshPromise; }
    finally { this.refreshPromise = null; }
  }

  async restore(): Promise<Identity | null> {
    if (!(await SecureStore.getItemAsync(REFRESH_KEY))) return null;
    await this.refresh();
    const identity = await this.me();
    if (identity.role === "admin" || identity.role === "super_admin") {
      await this.clear();
      throw new ApiError(403, "ADMIN_WEB_ONLY");
    }
    return identity;
  }

  async authorized<T>(path: string, body?: unknown, method?: "GET" | "POST" | "PATCH"): Promise<T> {
    if (!this.accessToken) await this.refresh();
    try { return await this.request<T>(path, body, this.accessToken ?? undefined, method); }
    catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      await this.refresh();
      return this.request<T>(path, body, this.accessToken ?? undefined, method);
    }
  }

  async me(): Promise<Identity> {
    return this.authorized<Identity>("/api/v1/auth/session");
  }

  async logout(): Promise<void> {
    try {
      if (!this.accessToken && await SecureStore.getItemAsync(REFRESH_KEY)) await this.refresh();
      if (this.accessToken) await this.request<void>("/api/v1/auth/logout", {}, this.accessToken);
    } finally { await this.clear(); }
  }

  async clear(): Promise<void> {
    this.accessToken = null;
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  }
}

export const authClient = new AuthClient();
