import { useEffect, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { ApiError, authClient } from "./client";

type Language = "mr" | "en";
type Plot = { id: string; plot_name: string; crop_type: string; grape_variety: string | null;
  area: string | number; area_unit: string; village: string; taluka: string; district: string; state: string;
  latitude: string | number | null; longitude: string | number | null; location_permission_at: string | null;
  pruning_date: string | null; current_crop_stage: string; preferred_language: Language;
  status: "active" | "archived"; is_selected: boolean };
type Weather = {status:"current"|"stale"|"unavailable";source:string|null;observed_at:string|null;
  location_precision:string;temperature_c:number|null;rainfall_mm:number|null;summary:string|null};

const words = {
  mr: { title:"माझे प्लॉट", add:"नवीन प्लॉट", edit:"बदला", save:"जतन करा", cancel:"रद्द करा",
    name:"प्लॉटचे नाव", crop:"पीक (grape)", variety:"द्राक्ष वाण (ऐच्छिक)", area:"क्षेत्रफळ",
    unit:"एकक: acre / hectare / sq_m", village:"गाव", taluka:"तालुका", district:"जिल्हा",
    state:"राज्य", pruning:"छाटणी तारीख YYYY-MM-DD (ऐच्छिक)", stage:"पीक अवस्था (उदा. pruned)",
    latitude:"अक्षांश (ऐच्छिक)", longitude:"रेखांश (ऐच्छिक)", permission:"अचूक स्थान वापरण्यास संमती",
    selected:"निवडलेला प्लॉट", select:"हा प्लॉट निवडा", archive:"संग्रहित करा", weather:"हवामान संदर्भ",
    unavailable:"हवामान उपलब्ध नाही", stale:"जुने हवामान", confirm:"हा प्लॉट संग्रहित करायचा?",
    error:"विनंती पूर्ण झाली नाही. पुन्हा प्रयत्न करा.", noPlots:"अजून प्लॉट नाहीत.",
    active:"सक्रिय", archived:"संग्रहित", coordinates:"स्थानासाठी संमती आवश्यक आहे."},
  en: { title:"My plots", add:"Add plot", edit:"Edit", save:"Save plot", cancel:"Cancel",
    name:"Plot name", crop:"Crop (grape)", variety:"Grape variety (optional)", area:"Area",
    unit:"Unit: acre / hectare / sq_m", village:"Village", taluka:"Taluka", district:"District",
    state:"State", pruning:"Pruning date YYYY-MM-DD (optional)", stage:"Crop stage (for example pruned)",
    latitude:"Latitude (optional)", longitude:"Longitude (optional)", permission:"I permit precise location use",
    selected:"Selected plot", select:"Select this plot", archive:"Archive", weather:"Weather context",
    unavailable:"Weather unavailable", stale:"Stale weather", confirm:"Archive this plot?",
    error:"Request failed. Please try again.", noPlots:"No plots yet.", active:"Active", archived:"Archived",
    coordinates:"Precise location requires permission."},
} as const;

const empty = {plot_name:"", crop_type:"grape", grape_variety:"", area:"", area_unit:"acre",
  village:"", taluka:"", district:"", state:"Maharashtra", latitude:"", longitude:"",
  pruning_date:"", current_crop_stage:"not_set"};

const cropNames:Record<string,{mr:string;en:string}> = {
  grape:{mr:"द्राक्ष",en:"Grapes"},
};
const stageNames:Record<string,{mr:string;en:string}> = {
  not_set:{mr:"अवस्था दिलेली नाही",en:"Stage not set"}, dormant:{mr:"विश्रांती",en:"Dormant"},
  pruned:{mr:"छाटणीनंतर",en:"Pruned"}, budbreak:{mr:"कळी फुटणे",en:"Budbreak"},
  flowering:{mr:"फुलोरा",en:"Flowering"}, fruit_set:{mr:"फळधारणा",en:"Fruit set"},
  veraison:{mr:"रंग बदल",en:"Veraison"}, harvest:{mr:"काढणी",en:"Harvest"},
};
const areaNames:Record<string,{mr:string;en:string}> = {
  acre:{mr:"एकर",en:"acres"}, hectare:{mr:"हेक्टर",en:"hectares"},
  sq_m:{mr:"चौ. मी.",en:"square metres"},
};

export default function PlotManager({language,onSessionExpired}:{language:Language;onSessionExpired:()=>void}) {
  const copy = words[language];
  const display = (map:Record<string,{mr:string;en:string}>,code:string) => map[code]?.[language]??code;
  const [plots,setPlots] = useState<Plot[]>([]);
  const [editing,setEditing] = useState<string|null>(null);
  const [form,setForm] = useState({...empty});
  const [locationPermission,setLocationPermission] = useState(false);
  const [showForm,setShowForm] = useState(false);
  const [weather,setWeather] = useState<Record<string,Weather>>({});
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");

  async function load() { setPlots(await authClient.authorized<Plot[]>("/api/v1/farmer/plots")); }
  useEffect(() => { void load().catch(handleError); }, []);
  function handleError(reason:unknown) {
    if (reason instanceof ApiError && (reason.status===401 || reason.status===403)) onSessionExpired();
    else setError(copy.error);
  }
  async function run(action:()=>Promise<void>) {
    setBusy(true);setError("");
    try {await action();} catch(reason) {handleError(reason);} finally {setBusy(false);}
  }
  function field(key:keyof typeof empty,label:string,keyboard?:"decimal-pad") {
    return <View style={styles.field}><Text style={styles.label}>{label}</Text><TextInput value={form[key]}
      onChangeText={value=>setForm(previous=>({...previous,[key]:value}))} style={styles.input}
      keyboardType={keyboard??"default"} accessibilityLabel={label} placeholder={label} /></View>;
  }
  function edit(plot:Plot) {
    setEditing(plot.id);setShowForm(true);setError("");
    setForm({plot_name:plot.plot_name,crop_type:plot.crop_type,grape_variety:plot.grape_variety??"",
      area:String(plot.area),area_unit:plot.area_unit,village:plot.village,taluka:plot.taluka,
      district:plot.district,state:plot.state,latitude:plot.latitude?.toString()??"",
      longitude:plot.longitude?.toString()??"",pruning_date:plot.pruning_date??"",
      current_crop_stage:plot.current_crop_stage});
    setLocationPermission(Boolean(plot.location_permission_at));
  }
  async function save() { await run(async()=>{
    if ((form.latitude||form.longitude) && !locationPermission) throw new Error(copy.coordinates);
    if ((form.latitude && !Number.isFinite(Number(form.latitude))) ||
        (form.longitude && !Number.isFinite(Number(form.longitude)))) throw new Error(copy.error);
    const payload = {plot_name:form.plot_name.trim(),crop_type:form.crop_type.trim().toLowerCase(),
      grape_variety:form.grape_variety.trim()||null,area:form.area,area_unit:form.area_unit,
      village:form.village.trim(),taluka:form.taluka.trim(),district:form.district.trim(),
      state:form.state.trim(),latitude:form.latitude?Number(form.latitude):null,
      longitude:form.longitude?Number(form.longitude):null,location_permission:locationPermission,
      pruning_date:form.pruning_date||null,current_crop_stage:form.current_crop_stage.trim().toLowerCase(),
      preferred_language:language};
    if (editing) await authClient.authorized(`/api/v1/farmer/plots/${editing}`,payload,"PATCH");
    else await authClient.authorized("/api/v1/farmer/plots",payload);
    setShowForm(false);setEditing(null);setForm({...empty});setLocationPermission(false);await load();
  }); }
  async function select(id:string) {await run(async()=>{await authClient.authorized(`/api/v1/farmer/plots/${id}/select`,{});await load();});}
  function archive(id:string) {Alert.alert(copy.archive,copy.confirm,[{text:copy.cancel,style:"cancel"},
    {text:copy.archive,style:"destructive",onPress:()=>void run(async()=>{
      await authClient.authorized(`/api/v1/farmer/plots/${id}/archive`,{});await load();})}]);}
  async function readWeather(id:string) {await run(async()=>{
    const result=await authClient.authorized<Weather>(`/api/v1/farmer/plots/${id}/weather/context`);
    setWeather(previous=>({...previous,[id]:result}));
  });}
  function button(label:string,onPress:()=>void,disabled=false) {
    return <Pressable accessibilityRole="button" disabled={busy||disabled} onPress={onPress}
      style={[styles.button,(busy||disabled)&&styles.disabled]}><Text style={styles.buttonText}>{label}</Text></Pressable>;
  }

  return <View style={styles.wrap}><Text style={styles.title}>{copy.title}</Text>
    {!showForm && button(copy.add,()=>{setEditing(null);setForm({...empty});setLocationPermission(false);setShowForm(true);})}
    {showForm && <View style={styles.card}>
      {field("plot_name",copy.name)}{field("crop_type",copy.crop)}{field("grape_variety",copy.variety)}
      {field("area",copy.area,"decimal-pad")}{field("area_unit",copy.unit)}
      {field("village",copy.village)}{field("taluka",copy.taluka)}{field("district",copy.district)}
      {field("state",copy.state)}{field("pruning_date",copy.pruning)}{field("current_crop_stage",copy.stage)}
      {field("latitude",copy.latitude,"decimal-pad")}{field("longitude",copy.longitude,"decimal-pad")}
      <Pressable accessibilityRole="checkbox" accessibilityState={{checked:locationPermission}}
        onPress={()=>{if(locationPermission) setForm(previous=>({...previous,latitude:"",longitude:""}));
          setLocationPermission(!locationPermission);}} style={styles.permission}>
        <Text>{locationPermission?"☑":"☐"} {copy.permission}</Text></Pressable>
      {button(copy.save,()=>void save())}{button(copy.cancel,()=>{setShowForm(false);setEditing(null);})}
    </View>}
    {plots.length===0 && !showForm && <Text style={styles.muted}>{copy.noPlots}</Text>}
    {plots.map(plot=><View key={plot.id} style={styles.card}>
      <Text style={styles.name}>{plot.plot_name} {plot.is_selected?"✓":""}</Text>
      <Text style={styles.muted}>{display(cropNames,plot.crop_type)} · {plot.area} {display(areaNames,plot.area_unit)} · {plot.village}, {plot.district}</Text>
      <Text style={styles.muted}>{plot.status==="active"?copy.active:copy.archived} · {display(stageNames,plot.current_crop_stage)}</Text>
      {plot.status==="active" && <View style={styles.actions}>
        {button(copy.edit,()=>edit(plot))}{!plot.is_selected && button(copy.select,()=>void select(plot.id))}
        {button(copy.weather,()=>void readWeather(plot.id))}{button(copy.archive,()=>archive(plot.id))}
      </View>}
      {weather[plot.id] && <Text style={styles.muted}>{weather[plot.id].status==="unavailable"?copy.unavailable:
        `${weather[plot.id].status==="stale"?copy.stale:copy.weather}: ${weather[plot.id].summary??""} · ${weather[plot.id].temperature_c??"—"}°C · ${weather[plot.id].source??""}`}</Text>}
    </View>)}
    {error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
  </View>;
}

const styles=StyleSheet.create({wrap:{gap:12,marginTop:24},title:{fontSize:23,fontWeight:"700",color:"#193B2B"},
  card:{padding:14,backgroundColor:"#fff",borderRadius:12,gap:10,borderWidth:1,borderColor:"#D4E1D5"},
  name:{fontSize:18,fontWeight:"700",color:"#193B2B"},muted:{fontSize:14,color:"#506858"},
  field:{gap:4},label:{fontSize:14,color:"#244731"},input:{minHeight:48,borderWidth:1,borderColor:"#C5D4C8",borderRadius:8,paddingHorizontal:12,fontSize:16},
  permission:{minHeight:48,justifyContent:"center"},actions:{gap:8},button:{minHeight:48,backgroundColor:"#193B2B",borderRadius:9,justifyContent:"center",alignItems:"center",paddingHorizontal:12},
  buttonText:{color:"#fff",fontSize:15,fontWeight:"700"},disabled:{opacity:0.5},error:{color:"#9B2E29",fontSize:14}});
