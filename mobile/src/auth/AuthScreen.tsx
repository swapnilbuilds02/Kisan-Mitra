import { useEffect, useState } from "react";
import { ActivityIndicator, Image, Linking, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { ApiError, authClient, normalizeMobile } from "./client";
import type { Challenge, Identity, RegistrationRole, TokenPair } from "./client";
import PlotManager from "./PlotManager";

type Language = "mr" | "en";
type Screen = "language" | "welcome" | "login" | "loginOtp" | "forgot" | "resetOtp" | "resetPassword" | "roles" | "register" | "registerOtp" | "details" | "pending" | "home" | "expired";
const strings = {
  mr: { title: "किसान मित्र", language: "भाषा निवडा", welcome: "आपल्या शेतीसाठी सोबत", next: "पुढे", login: "प्रवेश करा", mobile: "मोबाइल क्रमांक", password: "पासवर्ड", show: "दाखवा", hide: "लपवा", passwordLogin: "पासवर्डने प्रवेश", otpLogin: "OTP ने प्रवेश", forgot: "पासवर्ड विसरलात?", create: "नवीन खाते", otp: "सहा अंकी OTP", verify: "पडताळा", resend: "OTP पुन्हा पाठवा", farmer: "शेतकरी", shop: "दुकान", consultant: "सल्लागार", register: "नोंदणी", name: "पूर्ण नाव / दुकानाचे नाव", district: "जिल्हा", taluka: "तालुका", village: "गाव / शहर", state: "राज्य", address: "पत्ता (ऐच्छिक)", specialization: "विशेषज्ञता (ऐच्छिक)", organization: "संस्था (ऐच्छिक)", representative: "प्रतिनिधी (ऐच्छिक)", confirm: "पासवर्ड पुन्हा लिहा", consent: "सेवा व गोपनीयता अटी वाचून मान्य आहेत", unavailable: "मंजूर संमती दस्तऐवज उपलब्ध नाही.", complete: "नोंदणी पूर्ण करा", pending: "अर्ज मंजुरीसाठी प्रलंबित आहे", status: "अर्ज स्थिती", logout: "बाहेर पडा", expired: "सत्र संपले आहे. पुन्हा प्रवेश करा.", reset: "नवीन पासवर्ड", request: "OTP पाठवा", back: "मागे", error: "विनंती पूर्ण झाली नाही. पुन्हा प्रयत्न करा.", network: "नेटवर्क उपलब्ध नाही. पुन्हा प्रयत्न करा.", review: "मंजुरीनंतर नवीन प्रवेश करा.", role: "आपली भूमिका निवडा", passwordHint: "किमान 12 अक्षरे, अक्षरे व अंक", policy: "अटी वाचा" },
  en: { title: "Kisan Mitra", language: "Choose your language", welcome: "A companion for your farm", next: "Continue", login: "Sign in", mobile: "Mobile number", password: "Password", show: "Show", hide: "Hide", passwordLogin: "Sign in with password", otpLogin: "Sign in with OTP", forgot: "Forgot password?", create: "Create account", otp: "Six-digit OTP", verify: "Verify", resend: "Resend OTP", farmer: "Farmer", shop: "Shop", consultant: "Consultant", register: "Register", name: "Full name / shop name", district: "District", taluka: "Taluka", village: "Village / city", state: "State", address: "Address (optional)", specialization: "Specialization (optional)", organization: "Organization (optional)", representative: "Representative (optional)", confirm: "Confirm password", consent: "I have read and acknowledge the service and privacy terms", unavailable: "Approved consent document is unavailable.", complete: "Complete registration", pending: "Application awaiting approval", status: "Application status", logout: "Log out", expired: "Your session ended. Please sign in again.", reset: "Set new password", request: "Send OTP", back: "Back", error: "Request failed. Please try again.", network: "Network unavailable. Please try again.", review: "Sign in again after approval.", role: "Choose your role", passwordHint: "At least 12 characters, letters and numbers", policy: "Read terms" },
} as const;
const consent = { id: process.env.EXPO_PUBLIC_CONSENT_DOCUMENT_ID || "", version: process.env.EXPO_PUBLIC_CONSENT_VERSION || "", url: process.env.EXPO_PUBLIC_CONSENT_URL || "" };
const consentAvailable = Boolean(consent.id && consent.version && /^https:\/\//.test(consent.url));

export default function AuthScreen() {
  const [language, setLanguage] = useState<Language>("mr");
  const [screen, setScreen] = useState<Screen>("language");
  const [role, setRole] = useState<RegistrationRole>("farmer");
  const [otpRole, setOtpRole] = useState<RegistrationRole>("farmer");
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [otp, setOtp] = useState("");
  const [challenge, setChallenge] = useState("");
  const [onboardingToken, setOnboardingToken] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [name, setName] = useState("");
  const [representative, setRepresentative] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [organization, setOrganization] = useState("");
  const [state, setState] = useState("Maharashtra");
  const [district, setDistrict] = useState("");
  const [taluka, setTaluka] = useState("");
  const [village, setVillage] = useState("");
  const [address, setAddress] = useState("");
  const [pincode, setPincode] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(0);
  const [partnerStatus, setPartnerStatus] = useState("");
  const copy = strings[language];

  useEffect(() => {
    authClient.restore().then((person) => {
      if (person) { setIdentity(person); setScreen(person.account_state === "pending_approval" ? "pending" : "home"); }
    }).catch((reason: unknown) => {
      if (reason instanceof ApiError && (reason.status === 401 || reason.status === 403)) setScreen("expired");
      else setError(strings.mr.network);
    });
  }, []);
  useEffect(() => { if (!countdown) return; const timer = setTimeout(() => setCountdown(countdown - 1), 1000); return () => clearTimeout(timer); }, [countdown]);

  async function run(action: () => Promise<void>) {
    setBusy(true); setError("");
    try { await action(); }
    catch (reason) {
      if (reason instanceof ApiError && (reason.status === 401 || reason.status === 403) && identity) {
        await authClient.clear(); setIdentity(null); setScreen("expired");
      }
      setError(reason instanceof ApiError && reason.status === 0 ? copy.network : copy.error);
    } finally { setBusy(false); }
  }
  function enter(person: Identity) { setIdentity(person); setScreen(person.account_state === "pending_approval" ? "pending" : "home"); setPassword(""); setOtp(""); }
  async function requestLoginOtp() { await run(async () => {
    const number = normalizeMobile(mobile);
    if (otpRole === "farmer") await authClient.request<{status: string}>("/api/v1/auth/otp/request", { mobile: number });
    else { const result = await authClient.request<Challenge>("/api/v1/auth/partner/otp/request", { mobile_number: number }); setChallenge(result.challenge_id); }
    setCountdown(60); setScreen("loginOtp");
  }); }
  async function verifyLoginOtp() { await run(async () => {
    const number = normalizeMobile(mobile);
    const pair = otpRole === "farmer"
      ? await authClient.request<TokenPair>("/api/v1/auth/otp/verify", { mobile: number, code: otp })
      : await authClient.request<TokenPair>("/api/v1/auth/partner/otp/verify", { challenge_id: challenge, mobile_number: number, otp });
    enter(await authClient.accept(pair));
  }); }
  async function requestRegistration() { await run(async () => {
    const result = await authClient.request<Challenge>(`/api/v1/auth/${role}/register/request`, { mobile_number: normalizeMobile(mobile) });
    setChallenge(result.challenge_id); setCountdown(60); setScreen("registerOtp");
  }); }
  async function verifyRegistration() { await run(async () => {
    const result = await authClient.request<{onboarding_token: string}>(`/api/v1/auth/${role}/register/verify`,
      { challenge_id: challenge, mobile_number: normalizeMobile(mobile), otp });
    setOnboardingToken(result.onboarding_token); setOtp(""); setScreen("details");
  }); }
  async function completeRegistration() { await run(async () => {
    if (!consentAvailable) throw new ApiError(503, "CONSENT_UNAVAILABLE");
    if (password !== confirm || !accepted) throw new ApiError(400, "INVALID_FORM");
    const common = { onboarding_token: onboardingToken, password, confirm_password: confirm, preferred_language: language,
      state, district, taluka, pincode: pincode || null, consent_document_id: consent.id,
      consent_version: consent.version, acknowledge_required_consent: accepted };
    if (role === "farmer") {
      const pair = await authClient.request<TokenPair>("/api/v1/auth/farmer/register/complete", { ...common, full_name: name, village });
      enter(await authClient.accept(pair));
    } else {
      await authClient.request<{status: string}>(`/api/v1/auth/${role}/register/complete`, {
        ...common, display_name: name, representative_name: representative || null, specialization: specialization || null,
        organization_name: organization || null, locality: village, address: address || null,
      });
      enter(await authClient.passwordLogin(mobile, password));
    }
  }); }
  async function requestReset() { await run(async () => {
    const result = await authClient.request<Challenge>("/api/v1/auth/password/forgot", { mobile_number: normalizeMobile(mobile) });
    setChallenge(result.challenge_id); setCountdown(60); setScreen("resetOtp");
  }); }
  async function verifyReset() { await run(async () => {
    const result = await authClient.request<{reset_token: string}>("/api/v1/auth/password/reset/verify",
      { challenge_id: challenge, mobile_number: normalizeMobile(mobile), otp });
    setResetToken(result.reset_token); setScreen("resetPassword");
  }); }
  async function completeReset() { await run(async () => {
    if (password !== confirm) throw new ApiError(400, "PASSWORD_CONFIRMATION_MISMATCH");
    await authClient.request<void>("/api/v1/auth/password/reset", { reset_token: resetToken, new_password: password, confirm_password: confirm });
    setResetToken(""); setPassword(""); setConfirm(""); setScreen("login");
  }); }
  async function loadStatus() { if (!identity || identity.role === "farmer" || identity.role === "admin" || identity.role === "super_admin") return;
    await run(async () => {
      const result = await authClient.authorized<{status: string}>(`/api/v1/${identity.role}/application/status`);
      setPartnerStatus(result.status);
      if (result.status === "approved") { await authClient.logout(); setIdentity(null); setScreen("login"); }
    });
  }
  function field(label: string, value: string, onChange: (value: string) => void, options: {secret?: boolean; keyboard?: "phone-pad" | "number-pad"} = {}) {
    return <View style={styles.field}><Text style={styles.label}>{label}</Text><View style={styles.fieldRow}>
      <TextInput accessibilityLabel={label} autoCapitalize="none" value={value} onChangeText={onChange}
        keyboardType={options.keyboard ?? "default"} secureTextEntry={Boolean(options.secret && !showPassword)}
        style={styles.input} placeholder={label} placeholderTextColor="#738879" />
      {options.secret && <Pressable accessibilityRole="button" onPress={() => setShowPassword(!showPassword)} style={styles.show}><Text>{showPassword ? copy.hide : copy.show}</Text></Pressable>}
    </View></View>;
  }
  function button(label: string, action: () => void, secondary = false, disabled = false) {
    return <Pressable accessibilityRole="button" accessibilityLabel={label} disabled={busy || disabled} onPress={action}
      style={[styles.button, secondary && styles.secondary, (busy || disabled) && styles.disabled]}>
      <Text style={[styles.buttonText, secondary && styles.secondaryText]}>{label}</Text></Pressable>;
  }
  function passwordFields() { return <>{field(copy.password, password, setPassword, {secret: true})}{field(copy.confirm, confirm, setConfirm, {secret: true})}<Text style={styles.hint}>{copy.passwordHint}</Text></>; }

  return <SafeAreaView style={styles.safe}><ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
    <View style={styles.header}><Image source={require("../../assets/icon.png")} style={styles.logo} accessibilityLabel="Kisan Mitra" />
      <View><Text style={styles.brand}>{copy.title}</Text><Text style={styles.subbrand}>{copy.welcome}</Text></View></View>
    {screen === "language" && <><Text style={styles.title}>{copy.language}</Text>
      {button("मराठी", () => setLanguage("mr"), language !== "mr")}{button("English", () => setLanguage("en"), language !== "en")}
      {button(copy.next, () => setScreen("welcome"))}</>}
    {screen === "welcome" && <><Text style={styles.title}>{copy.welcome}</Text>{button(copy.login, () => setScreen("login"))}{button(copy.create, () => setScreen("roles"), true)}</>}
    {screen === "login" && <><Text style={styles.title}>{copy.login}</Text>
      {field(copy.mobile, mobile, setMobile, {keyboard:"phone-pad"})}{field(copy.password, password, setPassword, {secret:true})}
      {button(copy.passwordLogin, () => run(async () => enter(await authClient.passwordLogin(mobile, password))))}
      <Text style={styles.label}>{copy.role}</Text><View style={styles.choices}>{(["farmer","shop","consultant"] as const).map((item) =>
        <Pressable key={item} onPress={() => setOtpRole(item)} style={[styles.choice, otpRole === item && styles.selected]}><Text>{copy[item]}</Text></Pressable>)}</View>
      {button(copy.otpLogin, requestLoginOtp, true)}{button(copy.forgot, () => setScreen("forgot"), true)}{button(copy.create, () => setScreen("roles"), true)}</>}
    {screen === "loginOtp" && <><Text style={styles.title}>{copy.otpLogin}</Text>{field(copy.otp, otp, setOtp, {keyboard:"number-pad"})}
      {button(copy.verify, verifyLoginOtp)}{button(countdown ? `${copy.resend} (${countdown}s)` : copy.resend, requestLoginOtp, true, countdown > 0)}</>}
    {screen === "forgot" && <><Text style={styles.title}>{copy.forgot}</Text>{field(copy.mobile, mobile, setMobile, {keyboard:"phone-pad"})}{button(copy.request, requestReset)}</>}
    {screen === "resetOtp" && <><Text style={styles.title}>{copy.verify}</Text>{field(copy.otp, otp, setOtp, {keyboard:"number-pad"})}
      {button(copy.verify, verifyReset)}{button(countdown ? `${copy.resend} (${countdown}s)` : copy.resend, requestReset, true, countdown > 0)}</>}
    {screen === "resetPassword" && <><Text style={styles.title}>{copy.reset}</Text>{passwordFields()}{button(copy.reset, completeReset)}</>}
    {screen === "roles" && <><Text style={styles.title}>{copy.role}</Text>{(["farmer","shop","consultant"] as const).map((item) =>
      button(copy[item], () => { setRole(item); setScreen("register"); }, role !== item))}</>}
    {screen === "register" && <><Text style={styles.title}>{copy.register} · {copy[role]}</Text>{field(copy.mobile, mobile, setMobile, {keyboard:"phone-pad"})}{button(copy.request, requestRegistration)}</>}
    {screen === "registerOtp" && <><Text style={styles.title}>{copy.verify}</Text><Text style={styles.hint}>{copy.mobile}: {mobile}</Text>
      {field(copy.otp, otp, setOtp, {keyboard:"number-pad"})}{button(copy.verify, verifyRegistration)}
      {button(countdown ? `${copy.resend} (${countdown}s)` : copy.resend, requestRegistration, true, countdown > 0)}</>}
    {screen === "details" && <><Text style={styles.title}>{copy.register} · {copy[role]}</Text>
      {field(copy.name, name, setName)}{role === "shop" && field(copy.representative, representative, setRepresentative)}
      {role === "consultant" && <>{field(copy.specialization, specialization, setSpecialization)}{field(copy.organization, organization, setOrganization)}</>}
      {field(copy.state, state, setState)}{field(copy.district, district, setDistrict)}{field(copy.taluka, taluka, setTaluka)}
      {field(copy.village, village, setVillage)}{role !== "farmer" && field(copy.address, address, setAddress)}
      {field("PIN code (optional)", pincode, setPincode, {keyboard:"number-pad"})}{passwordFields()}
      {consentAvailable ? <><Pressable accessibilityRole="link" onPress={() => Linking.openURL(consent.url)} style={styles.link}><Text style={styles.linkText}>{copy.policy} · {consent.version}</Text></Pressable>
        <Pressable accessibilityRole="checkbox" accessibilityState={{checked:accepted}} onPress={() => setAccepted(!accepted)} style={styles.consent}><Text style={styles.label}>{accepted ? "☑" : "☐"} {copy.consent}</Text></Pressable></>
        : <Text style={styles.error}>{copy.unavailable}</Text>}
      {button(copy.complete, completeRegistration, false, !consentAvailable || !accepted)}</>}
    {screen === "pending" && <><Text style={styles.title}>{copy.pending}</Text><Text style={styles.hint}>{copy.review}</Text>
      <Text style={styles.hint}>{copy.status}: {partnerStatus || "pending_approval"}</Text>{button(copy.status, loadStatus)}
      {button(copy.logout, () => run(async () => { await authClient.logout(); setIdentity(null); setScreen("login"); }), true)}</>}
    {screen === "home" && <><Text style={styles.title}>{identity?.role === "farmer" ? copy.farmer : identity?.role === "shop" ? copy.shop : copy.consultant}</Text>
      <Text style={styles.hint}>{copy.welcome}</Text>
      {identity?.role === "farmer" && <PlotManager language={language} onSessionExpired={() => {void authClient.clear();setIdentity(null);setScreen("expired");}} />}
      {button(copy.logout, () => run(async () => { await authClient.logout(); setIdentity(null); setScreen("login"); }))}</>}
    {screen === "expired" && <><Text style={styles.title}>{copy.expired}</Text>{button(copy.login, () => setScreen("login"))}</>}
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    {busy && <ActivityIndicator color="#1C5635" style={styles.spinner} />}
    {screen !== "language" && screen !== "home" && screen !== "pending" && button(copy.back, () => setScreen("welcome"), true)}
  </ScrollView></SafeAreaView>;
}

const styles = StyleSheet.create({
  safe: {flex:1,backgroundColor:"#F5F8F1"}, container: {padding:24,paddingBottom:56,gap:12},
  header: {flexDirection:"row",alignItems:"center",gap:14,marginBottom:22}, logo: {width:62,height:62,borderRadius:14},
  brand: {fontSize:23,fontWeight:"800",color:"#193B2B"}, subbrand: {fontSize:13,color:"#506858"},
  title: {fontSize:27,fontWeight:"800",color:"#193B2B",marginBottom:8}, label: {fontSize:15,fontWeight:"600",color:"#244731"},
  field: {gap:6}, fieldRow: {flexDirection:"row",alignItems:"center",borderWidth:1,borderColor:"#C5D4C8",borderRadius:12,backgroundColor:"#FFFFFF"},
  input: {flex:1,minHeight:52,paddingHorizontal:14,fontSize:16,color:"#193B2B"}, show: {paddingHorizontal:12,minHeight:44,justifyContent:"center"},
  button: {minHeight:52,backgroundColor:"#193B2B",borderRadius:12,alignItems:"center",justifyContent:"center",paddingHorizontal:14},
  secondary: {backgroundColor:"#E4EDE4",borderWidth:1,borderColor:"#C5D4C8"}, disabled: {opacity:0.5},
  buttonText: {color:"white",fontWeight:"700",fontSize:16,textAlign:"center"}, secondaryText: {color:"#193B2B"},
  choices: {flexDirection:"row",gap:8,flexWrap:"wrap"}, choice: {padding:11,borderRadius:10,backgroundColor:"#E4EDE4"}, selected: {backgroundColor:"#B8D3BB"},
  hint: {color:"#526E5A",fontSize:14,lineHeight:21}, error: {color:"#9B2E29",fontSize:15,marginTop:8},
  link: {paddingVertical:8}, linkText: {color:"#185A36",textDecorationLine:"underline"}, consent: {paddingVertical:12,minHeight:48}, spinner: {marginTop:10},
});
