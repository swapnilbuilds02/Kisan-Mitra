"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Mode = "password" | "otp" | "forgot" | "resetOtp" | "resetPassword";
type ApiResult = {detail?: string; status?: string; challenge_id?: string; reset_token?: string};

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("password");
  const [csrf, setCsrf] = useState("");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [otp, setOtp] = useState("");
  const [challenge, setChallenge] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/auth/csrf", {cache:"no-store"}).then(r => r.json()).then(data => setCsrf(data.csrf_token)).catch(() => setError("Connection unavailable."));
    fetch("/api/auth/me", {cache:"no-store"}).then(r => { if (r.ok) router.replace("/admin"); }).catch(() => {});
  }, [router]);
  useEffect(() => { if (!countdown) return; const timer = setTimeout(() => setCountdown(countdown - 1), 1000); return () => clearTimeout(timer); }, [countdown]);

  async function post(action: string, body: Record<string,string>): Promise<ApiResult> {
    if (!csrf) throw new Error("Security check unavailable. Refresh this page.");
    const response = await fetch(`/api/auth/${action}`, {method:"POST",headers:{"Content-Type":"application/json","x-csrf-token":csrf},body:JSON.stringify(body)});
    const result = await response.json() as ApiResult;
    if (!response.ok) throw new Error(response.status === 401 ? "Details could not be verified." : result.detail || "Request unavailable.");
    return result;
  }
  async function run(action: () => Promise<void>) { setBusy(true); setError(""); try { await action(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Request unavailable."); } finally { setBusy(false); } }
  function mobileNumber() { const value = mobile.trim().replace(/[\s-]/g, ""); if (!/^(?:\+91|91)?[6-9][0-9]{9}$/.test(value)) throw new Error("Enter a valid registered mobile number."); return value; }
  function requestOtp() { void run(async () => { const result = await post("otp-request", {mobile_number:mobileNumber()}); setChallenge(result.challenge_id || ""); setCountdown(60); setMode("otp"); }); }
  function requestReset() { void run(async () => { const result = await post("forgot", {mobile_number:mobileNumber()}); setChallenge(result.challenge_id || ""); setCountdown(60); setMode("resetOtp"); }); }
  return <main className="authLayout"><section className="authCard">
    <img className="authLogo" src="/kisan-mitra-logo.png" alt="Kisan Mitra" />
    <p className="eyebrow">Private owner console</p><h1>{mode === "forgot" ? "Recover password" : mode.startsWith("reset") ? "Reset password" : "Welcome back"}</h1>
    <p className="description">Use your registered mobile number. Administrative access is checked by the server.</p>
    <form onSubmit={(event) => { event.preventDefault(); if (mode === "password") void run(async () => { await post("login",{mobile_number:mobileNumber(),password}); router.replace("/admin"); });
      else if (mode === "otp") void run(async () => { await post("otp-verify",{challenge_id:challenge,mobile_number:mobileNumber(),otp}); router.replace("/admin"); });
      else if (mode === "forgot") requestReset();
      else if (mode === "resetOtp") void run(async () => { const result = await post("reset-verify",{challenge_id:challenge,mobile_number:mobileNumber(),otp}); setResetToken(result.reset_token || ""); setMode("resetPassword"); });
      else void run(async () => { if (password !== confirm) throw new Error("Passwords do not match."); await post("reset",{reset_token:resetToken,new_password:password,confirm_password:confirm}); setPassword(""); setConfirm(""); setMode("password"); }); }}>
      {mode !== "resetPassword" && <label>Mobile number<input required inputMode="tel" autoComplete="tel" value={mobile} onChange={event => setMobile(event.target.value)} placeholder="Registered mobile number" /></label>}
      {(mode === "password" || mode === "resetPassword") && <><label>{mode === "password" ? "Password" : "New password"}<span className="inputRow"><input required type={showPassword ? "text" : "password"} autoComplete={mode === "password" ? "current-password" : "new-password"} value={password} onChange={event => setPassword(event.target.value)} /><button type="button" className="inlineButton" onClick={() => setShowPassword(!showPassword)}>{showPassword ? "Hide" : "Show"}</button></span></label>
        {mode === "resetPassword" && <label>Confirm password<input required type={showPassword ? "text" : "password"} autoComplete="new-password" value={confirm} onChange={event => setConfirm(event.target.value)} /></label>}</>}
      {(mode === "otp" || mode === "resetOtp") && <label>Six-digit OTP<input required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={otp} onChange={event => setOtp(event.target.value)} /></label>}
      <button className="primaryButton" disabled={busy || !csrf} type="submit">{busy ? "Please wait…" : mode === "password" ? "Sign in" : mode === "forgot" ? "Send reset OTP" : mode === "resetPassword" ? "Save new password" : "Verify OTP"}</button>
    </form>
    {(mode === "otp" || mode === "resetOtp") && <button className="textButton" disabled={busy || countdown > 0} onClick={mode === "otp" ? requestOtp : requestReset}>Resend OTP {countdown > 0 ? `(${countdown}s)` : ""}</button>}
    <div className="authLinks"><button onClick={() => {setError("");setMode("password");}}>Password login</button><button onClick={requestOtp}>OTP login</button><button onClick={() => {setError("");setMode("forgot");}}>Forgot password</button></div>
    {error && <p className="error" role="alert">{error}</p>}
    <p className="hint">Owner accounts are provisioned privately. There is no public registration.</p>
  </section></main>;
}
