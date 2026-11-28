"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

type Application = {application_id:string;user_id:string;partner_role:"shop"|"consultant";status:string;display_name:string;submitted_at?:string;representative_name?:string;specialization?:string;organization_name?:string;state?:string;district?:string;taluka?:string;locality?:string};
type History = {prior_status:string;new_status:string;reason:string;actor_id:string;decided_at:string};
type Identity = {id:string;role:string;account_state:string};

export default function AdminDashboard() {
  const router = useRouter();
  const [csrf,setCsrf] = useState("");
  const [identity,setIdentity] = useState<Identity|null>(null);
  const [role,setRole] = useState<"shop"|"consultant">("shop");
  const [rows,setRows] = useState<Application[]>([]);
  const [selected,setSelected] = useState<Application|null>(null);
  const [history,setHistory] = useState<History[]>([]);
  const [lookup,setLookup] = useState("");
  const [reason,setReason] = useState("");
  const [reauthPassword,setReauthPassword] = useState("");
  const [currentPassword,setCurrentPassword] = useState("");
  const [newPassword,setNewPassword] = useState("");
  const [confirmPassword,setConfirmPassword] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");

  const load = useCallback(async (currentRole: "shop"|"consultant") => {
    const response = await fetch(`/api/admin?role=${currentRole}`, {cache:"no-store"});
    if (response.status === 401) { router.replace("/login"); return; }
    if (!response.ok) throw new Error("Application list unavailable.");
    setRows(await response.json() as Application[]);
  },[router]);
  useEffect(() => {
    fetch("/api/auth/csrf",{cache:"no-store"}).then(r=>r.json()).then(data=>setCsrf(data.csrf_token)).catch(()=>setError("Security check unavailable."));
    fetch("/api/auth/me",{cache:"no-store"}).then(async response => {
      if (!response.ok) {router.replace("/login");return;}
      const person=await response.json() as Identity;
      if (!["admin","super_admin"].includes(person.role)) {router.replace("/login");return;}
      setIdentity(person); await load("shop");
    }).catch(()=>setError("Cannot reach the authentication service."));
  },[router,load]);
  async function open(id:string) {
    setError("");
    const [detail,decisions] = await Promise.all([
      fetch(`/api/admin?application_id=${encodeURIComponent(id)}`,{cache:"no-store"}),
      fetch(`/api/admin?application_id=${encodeURIComponent(id)}&history=1`,{cache:"no-store"}),
    ]);
    if (!detail.ok || !decisions.ok) throw new Error("Application details unavailable.");
    setSelected(await detail.json() as Application);setHistory(await decisions.json() as History[]);
  }
  async function post(path:string,body:object,proof?:string) {
    const response=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json","x-csrf-token":csrf,...(proof?{'x-admin-reauth':proof}:{})},body:JSON.stringify(body)});
    const payload=await response.json().catch(()=>({detail:"Request failed"}));
    if (response.status===401) {router.replace("/login");throw new Error("Session expired.");}
    if (!response.ok) throw new Error(payload.detail||"Request failed.");
    return payload;
  }
  async function decide(action:"approve"|"reject"|"suspend"|"reactivate") {
    if (!selected || reason.trim().length<5) {setError("Add a reason of at least five characters.");return;}
    if (!reauthPassword) {setError("Enter your current password to confirm this decision.");return;}
    if (!window.confirm(`${action[0].toUpperCase()+action.slice(1)} ${selected.display_name}? This changes account access.`)) return;
    setBusy(true);setError("");setNotice("");
    try {
      const verified=await post("/api/auth/reauth",{current_password:reauthPassword}) as {reauth_token:string};
      await post("/api/admin",{action,application_id:selected.application_id,partner_id:selected.user_id,reason:reason.trim()},verified.reauth_token);
      setNotice("Decision saved.");setReason("");setReauthPassword("");await open(selected.application_id);await load(role);
    } catch (caught) {setError(caught instanceof Error?caught.message:"Decision failed.");}
    finally {setBusy(false);}
  }
  async function changePassword(event:FormEvent) {
    event.preventDefault();if(newPassword!==confirmPassword){setError("Passwords do not match.");return;}
    setBusy(true);setError("");
    try {await post("/api/auth/password-change",{current_password:currentPassword,new_password:newPassword,confirm_password:confirmPassword});router.replace("/login");}
    catch(caught){setError(caught instanceof Error?caught.message:"Password change failed.");}finally{setBusy(false);}
  }
  async function logout() {try{await post("/api/auth/logout",{});}finally{router.replace("/login");}}

  return <main className="adminLayout"><header className="adminHeader"><img src="/kisan-mitra-logo.png" alt="Kisan Mitra" /><div><strong>Owner console</strong><span>{identity?.role === "super_admin" ? "Owner" : "Admin"}</span></div><button onClick={()=>void logout()}>Log out</button></header>
    <div className="adminGrid"><section className="panel"><p className="eyebrow">Partner applications</p><h1>Review queue</h1>
      <div className="tabs"><button className={role==="shop"?"active":""} onClick={()=>{setRole("shop");void load("shop").catch(e=>setError(e.message));}}>Shops</button><button className={role==="consultant"?"active":""} onClick={()=>{setRole("consultant");void load("consultant").catch(e=>setError(e.message));}}>Consultants</button></div>
      {rows.length===0?<p className="hint">No pending applications in this queue.</p>:<ul className="applicationList">{rows.map(row=><li key={row.application_id}><button onClick={()=>void open(row.application_id).catch(e=>setError(e.message))}><strong>{row.display_name}</strong><span>{row.status} · {row.submitted_at ? new Date(row.submitted_at).toLocaleDateString() : ""}</span></button></li>)}</ul>}
      <label>Find an application by ID<input value={lookup} onChange={event=>setLookup(event.target.value)} placeholder="Application UUID" /></label>
      <button className="secondaryButton" onClick={()=>void open(lookup).catch(e=>setError(e.message))}>Open application</button>
    </section>
    <section className="panel"><p className="eyebrow">Application detail</p>{selected?<><h2>{selected.display_name}</h2><dl className="details"><dt>Role</dt><dd>{selected.partner_role}</dd><dt>Status</dt><dd>{selected.status}</dd><dt>Representative</dt><dd>{selected.representative_name||"—"}</dd><dt>Specialization</dt><dd>{selected.specialization||"—"}</dd><dt>Organization</dt><dd>{selected.organization_name||"—"}</dd><dt>Location</dt><dd>{[selected.locality,selected.taluka,selected.district,selected.state].filter(Boolean).join(", ")}</dd></dl>
      <label>Reason for decision<textarea value={reason} onChange={event=>setReason(event.target.value)} rows={3} maxLength={500} /></label>
      <label>Confirm with your current password<input type="password" autoComplete="current-password" value={reauthPassword} onChange={event=>setReauthPassword(event.target.value)} /></label>
      <div className="actions">{selected.status==="pending_approval"&&<><button disabled={busy} onClick={()=>void decide("approve")}>Approve</button><button disabled={busy} className="danger" onClick={()=>void decide("reject")}>Reject</button></>}{selected.status==="approved"&&<button disabled={busy} className="danger" onClick={()=>void decide("suspend")}>Suspend</button>}{selected.status==="suspended"&&<button disabled={busy} onClick={()=>void decide("reactivate")}>Reactivate</button>}</div>
      <h3>Decision history</h3>{history.length? <ul>{history.map((item,index)=><li key={index}>{item.prior_status} → {item.new_status} · {item.reason}</li>)}</ul>:<p className="hint">No decisions recorded.</p>}</>:<p className="hint">Select an application to review its details and history.</p>}</section></div>
    <section className="panel passwordPanel"><h2>Change password</h2><p className="hint">Changing your password signs out existing sessions.</p><form onSubmit={event=>void changePassword(event)}><label>Current password<input type="password" required autoComplete="current-password" value={currentPassword} onChange={event=>setCurrentPassword(event.target.value)} /></label><label>New password<input type="password" required autoComplete="new-password" value={newPassword} onChange={event=>setNewPassword(event.target.value)} /></label><label>Confirm new password<input type="password" required autoComplete="new-password" value={confirmPassword} onChange={event=>setConfirmPassword(event.target.value)} /></label><button disabled={busy||!csrf} type="submit">Update password</button></form></section>
    {notice&&<p role="status" className="notice">{notice}</p>}{error&&<p role="alert" className="error">{error}</p>}
  </main>;
}
