# campionamenti_streamlit_ottim_retry.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date
import time

st.set_page_config(layout="wide")

# ===============================
# AUTENTICAZIONE GOOGLE SHEETS (BLOCCO DA NON MODIFICARE)
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID = "1KCPltH_8EtI5svqRivdwI68DWJ6eE1IK3UDe45PENf8"
sheet = client.open_by_key(SHEET_ID).sheet1

# ===============================
# HEADER (deve corrispondere al foglio)
# ===============================
HEADER = [
    "SessionID","Ditta","Stabilimento","Data","Camino","Operatore1","Operatore2",
    "PressioneStatica","VelocitàCamino","AngoloDiSwirl","DiametroProgetto","DiametroMisurato",
    "NumeroBocchelli","DiametriAMonte","DiametriAValle","TipoValle",
    "Analizzatore","CertMix","CertO2","PC","Laser","Micromanometro","Termocoppia","Darcy","KDarcy",
    "PrelievoN","Ugello","DurataPrelievo","OraInizio","FiltroQMA","PrelievoMultiplo",
    "Temperatura","Pressione","Umidita","Meteo",
    "Parametro","AltroParametro","Pompa","Portata",
    "VolumeIniziale","VolumeFinale","TemperaturaIniziale","TemperaturaFinale","VolumeNormalizzato",
    "PesoIniSerpentina","PesoFinSerpentina","PesoIniGel","PesoFinGel","UmiditaFumi",
    "Isocinetismo","VelocitàCampionamento","dP","TemperaturaFumi","Note","Asse1_JSON","Asse2_JSON","Ultima_Modifica"
]

# ===============================
# UTILITY: retry e operazioni su sheet
# ===============================
MAX_RETRIES = 3
RETRY_DELAY = 2  # secondi

def retry(func):
    def wrapper(*args, **kwargs):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < MAX_RETRIES:
                    st.warning(f"[Tentativo {attempt}] Errore connessione a Google Sheets: {e}. Riprovo tra {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    st.error(f"Errore persistente dopo {MAX_RETRIES} tentativi: {e}")
                    return None
    return wrapper

@retry
def safe_get_all_records():
    return sheet.get_all_records()

@retry
def safe_get_all_values():
    return sheet.get_all_values()

@retry
def delete_rows_for_session(session_id):
    all_vals = safe_get_all_values()
    if not all_vals or len(all_vals) <= 1:
        return
    rows_to_delete = []
    for idx, row in enumerate(all_vals[1:], start=2):
        if len(row) >= 1 and row[0] == session_id:
            rows_to_delete.append(idx)
    for r in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(r)

@retry
def append_rows(rows):
    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")

def ensure_header():
    try:
        row1 = sheet.row_values(1)
        if not row1 or row1[:len(HEADER)] != HEADER[:len(row1)]:
            sheet.insert_row(HEADER, index=1)
    except Exception as e:
        st.warning(f"Impossibile assicurare header: {e}")

# ===============================
# CALCOLI
# ===============================
def calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, pressione_hpa):
    try:
        vol_delta = float(vol_fin) - float(vol_in)
        temp_media = (float(temp_in) + float(temp_fin)) / 2.0
        return vol_delta * (273.15 / (temp_media + 273.15)) * (float(pressione_hpa) / 1013.25)
    except Exception:
        return 0.0

# ===============================
# INIT
# ===============================
ensure_header()
records = safe_get_all_records() or []
all_values = safe_get_all_values() or []

# list of sessionIDs presenti
session_ids = sorted(list({r["SessionID"] for r in records if r.get("SessionID")}), reverse=True)
session_ids_display = ["➕ Nuova sessione"] + session_ids

st.title("📋 Modulo Campionamenti Ambientali — Versione ottimizzata con retry")

# ===============================
# SESSION SELECT / CREATE
# ===============================
selected_session = st.selectbox("Seleziona SessionID o crea nuova sessione", session_ids_display)
if selected_session == "➕ Nuova sessione":
    if "current_session" not in st.session_state or not st.session_state.get("current_session_is_new", False):
        st.session_state.current_session = datetime.now().strftime("%Y%m%d%H%M%S")
        st.session_state.current_session_is_new = True
else:
    st.session_state.current_session = selected_session
    st.session_state.current_session_is_new = False

SessionID = st.session_state.current_session
st.markdown(f"**SessionID corrente:** `{SessionID}`")

# ===============================
# PREFILL
# ===============================
session_rows = [r for r in records if r.get("SessionID") == SessionID]
prefill = {}
if session_rows:
    for r in session_rows:
        try:
            n = int(r.get("PrelievoN", 1))
        except Exception:
            n = 1
        pre = prefill.setdefault(n, {"params": []})
        if "meta" not in pre:
            pre["meta"] = {
                "Ugello": r.get("Ugello",""),
                "Durata": r.get("DurataPrelievo",""),
                "OraInizio": r.get("OraInizio",""),
                "FiltroQMA": r.get("FiltroQMA",""),
                "PrelievoMultiplo": r.get("PrelievoMultiplo",""),
                "Temperatura": r.get("Temperatura",""),
                "Pressione": r.get("Pressione",""),
                "Umidita": r.get("Umidita",""),
                "Meteo": r.get("Meteo",""),
                "PesoIniSerpentina": r.get("PesoIniSerpentina",""),
                "PesoFinSerpentina": r.get("PesoFinSerpentina",""),
                "PesoIniGel": r.get("PesoIniGel",""),
                "PesoFinGel": r.get("PesoFinGel",""),
                "Isocinetismo": r.get("Isocinetismo",""),
                "VelocitàCampionamento": r.get("VelocitàCampionamento",""),
                "dP": r.get("dP",""),
                "TemperaturaFumi": r.get("TemperaturaFumi",""),
                "Note": r.get("Note","")
            }
        param = {
            "Parametro": r.get("Parametro",""),
            "AltroParametro": r.get("AltroParametro",""),
            "Pompa": r.get("Pompa",""),
            "Portata": r.get("Portata",""),
            "VolumeIniziale": r.get("VolumeIniziale",""),
            "VolumeFinale": r.get("VolumeFinale",""),
            "TemperaturaIniziale": r.get("TemperaturaIniziale",""),
            "TemperaturaFinale": r.get("TemperaturaFinale",""),
            "VolumeNormalizzato": r.get("VolumeNormalizzato","")
        }
        pre["params"].append(param)

# ===============================
# DATI GENERALI SESSIONE
# ===============================
with st.expander("📂 Dati Generali Sessione", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        ditta = st.text_input("Ditta", value=(session_rows[0].get("Ditta","") if session_rows else ""))
        stabilimento = st.text_input("Stabilimento", value=(session_rows[0].get("Stabilimento","") if session_rows else ""))
        data_campagna = st.date_input("Data campagna", value=date.fromisoformat(session_rows[0].get("Data")) if session_rows and session_rows[0].get("Data") else date.today())
        camino = st.text_input("Camino", value=(session_rows[0].get("Camino","") if session_rows else ""))
    with col2:
        operatore1 = st.text_input("Operatore 1", value=(session_rows[0].get("Operatore1","") if session_rows else ""))
        operatore2 = st.text_input("Operatore 2", value=(session_rows[0].get("Operatore2","") if session_rows else ""))
        pressione_statica = st.number_input("Pressione Statica", value=float(session_rows[0].get("PressioneStatica",0)) if session_rows else 0.0, step=0.1)
        velocita_camino = st.number_input("Velocità Camino", value=float(session_rows[0].get("VelocitàCamino",0)) if session_rows else 0.0, step=0.1)

# ===============================
# NUMERO PRELIEVI
# ===============================
if prefill:
    max_prel = max(prefill.keys())
    num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=50, value=max_prel, key="num_prel_prefill")
else:
    num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=50, value=1, key="num_prel_new")

# ===============================
# PARAMETRI
# ===============================
PARAMETRI = ["Polveri", "Polveri SiO2", "Acidi", "SOx", "HCl",
             "HF", "Metalli", "CrVI", "NH3", "SO3",
             "Fenolo Formaldeide", "SOV", "Altro"]

# ===============================
# RACCOLTA DATI PRELIEVI
# ===============================
nuovi_prelievi = []

for i in range(1, int(num_prelievi)+1):
    with st.expander(f"Prelievo {i}", expanded=False):
        meta = prefill.get(i, {}).get("meta", {})
        col1, col2, col3 = st.columns([2,2,2])
        with col1:
            ugello = st.text_input(f"Ugello {i}", value=meta.get("Ugello",""), key=f"ugello_{i}")
            durata = st.number_input(f"Durata Prelievo {i} (s)", value=float(meta.get("Durata",0)) if meta.get("Durata","")!="" else 0.0, key=f"durata_{i}")
            ora_inizio = st.time_input(f"Ora Inizio {i}", value=(datetime.strptime(meta.get("OraInizio","00:00"), "%H:%M").time() if meta.get("OraInizio","") else datetime.now().time()), key=f"ora_{i}")
            filtro_qma = st.text_input(f"Filtro QMA {i}", value=meta.get("FiltroQMA",""), key=f"filtro_{i}")
            prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"], index=0 if meta.get("PrelievoMultiplo","")=="" else (0 if meta.get("PrelievoMultiplo")=="NO" else 1), key=f"multi_{i}")
        with col2:
            temperatura = st.number_input(f"Temperatura °C {i}", value=float(meta.get("Temperatura",0)) if meta.get("Temperatura","")!="" else 0.0, key=f"temp_{i}", step=0.1)
            pressione = st.number_input(f"Pressione hPa {i}", value=float(meta.get("Pressione",1013.25)) if meta.get("Pressione","")!="" else 1013.25, key=f"press_{i}", step=0.1)
            umidita = st.number_input(f"Umidità % {i}", value=float(meta.get("Umidita",0)) if meta.get("Umidita","")!="" else 0.0, key=f"umid_{i}", step=0.1)
            meteo = st.selectbox(f"Meteo {i}", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"], index=0 if meta.get("Meteo","")=="" else ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"].index(meta.get("Meteo","")), key=f"meteo_{i}")
        with col3:
            peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}", value=float(meta.get("PesoIniSerpentina",0)) if meta.get("PesoIniSerpentina","")!="" else 0.0, key=f"pis_{i}", step=0.01)
            peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", value=float(meta.get("PesoFinSerpentina",0)) if meta.get("PesoFinSerpentina","")!="" else 0.0, key=f"pfs_{i}", step=0.01)
            peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}", value=float(meta.get("PesoIniGel",0)) if meta.get("PesoIniGel","")!="" else 0.0, key=f"pig_{i}", step=0.01)
            peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", value=float(meta.get("PesoFinGel",0)) if meta.get("PesoFinGel","")!="" else 0.0, key=f"pfg_{i}", step=0.01)

        # parametri per prelievo
        params_existing = prefill.get(i, {}).get("params", [])
        num_params_default = len(params_existing) if params_existing else 1
        num_param = st.number_input(f"Numero di parametri per prelievo {i}", min_value=1, max_value=20, value=num_params_default, key=f"num_param_{i}")

        parametri_prelievo = []
        for j in range(1, int(num_param)+1):
            p_pref = params_existing[j-1] if j-1 < len(params_existing) else {}
            c1, c2, c3, c4 = st.columns([2,1,1,1])
            with c1:
                parametro = st.selectbox(f"Parametro {j}", PARAMETRI, index=0 if p_pref.get("Parametro","")=="" else (PARAMETRI.index(p_pref.get("Parametro")) if p_pref.get("Parametro") in PARAMETRI else len(PARAMETRI)-1), key=f"param_{i}_{j}")
                if parametro == "Altro":
                    altro_parametro = st.text_input(f"Specificare parametro {j}", value=p_pref.get("AltroParametro",""), key=f"altro_{i}_{j}")
                    parametro_finale = altro_parametro
                else:
                    parametro_finale = parametro
            with c2:
                volume_iniziale = st.number_input(f"Vol in {j}", value=float(p_pref.get("VolumeIniziale",0)) if p_pref.get("VolumeIniziale","")!="" else 0.0, key=f"vol_in_{i}_{j}", step=0.1)
                volume_finale = st.number_input(f"Vol fin {j}", value=float(p_pref.get("VolumeFinale",0)) if p_pref.get("VolumeFinale","")!="" else 0.0, key=f"vol_fin_{i}_{j}", step=0.1)
            with c3:
                temp_iniziale = st.number_input(f"T in {j}", value=float(p_pref.get("TemperaturaIniziale",0)) if p_pref.get("TemperaturaIniziale","")!="" else 0.0, key=f"temp_in_{i}_{j}", step=0.1)
                temp_finale = st.number_input(f"T fin {j}", value=float(p_pref.get("TemperaturaFinale",0)) if p_pref.get("TemperaturaFinale","")!="" else 0.0, key=f"temp_fin_{i}_{j}", step=0.1)
            with c4:
                vn = calcola_volume_normalizzato(volume_iniziale, volume_finale, temp_iniziale, temp_finale, pressione)
                st.markdown(f"**VN:** `{vn:.6f}`")
            parametri_prelievo.append({
                "Parametro": parametro_finale,
                "AltroParametro": (altro_parametro if parametro=="Altro" else ""),
                "VolumeIniziale": volume_iniziale,
                "VolumeFinale": volume_finale,
                "TemperaturaIniziale": temp_iniziale,
                "TemperaturaFinale": temp_finale,
                "VolumeNormalizzato": float(f"{vn:.6f}")
            })

        # scelta volume per umidità
        vol_choices = [p["VolumeNormalizzato"] for p in parametri_prelievo]
        vol_choice_idx = st.selectbox(
            "Scegli quale Volume Normalizzato usare per il calcolo dell'umidità",
            options=list(range(len(vol_choices))),
            format_func=lambda x: f"Parametro {x+1} - VN={vol_choices[x]:.6f}",
            key=f"vol_choice_{i}"
        )
        vol_scelto = float(vol_choices[vol_choice_idx])

        # calcolo umidità fumi
        volume_h2o = ((peso_fin_serp - peso_in_serp) + (peso_fin_gel - peso_in_gel)) / 18 * 22.414
        volume_totale = volume_h2o + vol_scelto
        umidita_fumi = (volume_h2o / volume_totale) if volume_totale != 0 else 0.0

        st.info(f"Volume H2O: {volume_h2o:.4f}  — Volume scelto: {vol_scelto:.6f}  — Volume Totale: {volume_totale:.4f}")
        st.info(f"Umidità fumi (calcolata): {umidita_fumi:.6f}")

        # medie e note
        isocinetismo = st.number_input(f"Isocinetismo {i}", value=float(meta.get("Isocinetismo",0)) if meta.get("Isocinetismo","")!="" else 0.0, key=f"isoc_{i}", step=0.1)
        velocita_media = st.number_input(f"Velocità media {i}", value=float(meta.get("VelocitàCampionamento",0)) if meta.get("VelocitàCampionamento","")!="" else 0.0, key=f"vel_{i}", step=0.1)
        dp = st.number_input(f"dP {i}", value=float(meta.get("dP",0)) if meta.get("dP","")!="" else 0.0, key=f"dp_{i}", step=0.1)
        temp_fumi = st.number_input(f"Temperatura Fumi {i}", value=float(meta.get("TemperaturaFumi",0)) if meta.get("TemperaturaFumi","")!="" else 0.0, key=f"temp_fumi_{i}", step=0.1)
        note = st.text_area(f"Note prelievo {i}", value=meta.get("Note",""), key=f"note_{i}")

        # aggiungo righe
        for p in parametri_prelievo:
            row = {
                "SessionID": SessionID,
                "Ditta": ditta,
                "Stabilimento": stabilimento,
                "Data": data_campagna.isoformat(),
                "Camino": camino,
                "Operatore1": operatore1,
                "Operatore2": operatore2,
                "PressioneStatica": pressione_statica,
                "VelocitàCamino": velocita_camino,
                "AngoloDiSwirl": "",
                "DiametroProgetto": "",
                "DiametroMisurato": "",
                "NumeroBocchelli": "",
                "DiametriAMonte": "",
                "DiametriAValle": "",
                "TipoValle": "",
                "Analizzatore": "",
                "CertMix": "",
                "CertO2": "",
                "PC": "",
                "Laser": "",
                "Micromanometro": "",
                "Termocoppia": "",
                "Darcy": "",
                "KDarcy": "",
                "PrelievoN": i,
                "Ugello": ugello,
                "DurataPrelievo": durata,
                "OraInizio": ora_inizio.strftime("%H:%M"),
                "FiltroQMA": filtro_qma,
                "PrelievoMultiplo": prelievo_multiplo,
                "Temperatura": temperatura,
                "Pressione": pressione,
                "Umidita": umidita,
                "Meteo": meteo,
                "Parametro": p["Parametro"],
                "AltroParametro": p.get("AltroParametro",""),
                "Pompa": "",
                "Portata": "",
                "VolumeIniziale": p["VolumeIniziale"],
                "VolumeFinale": p["VolumeFinale"],
                "TemperaturaIniziale": p["TemperaturaIniziale"],
                "TemperaturaFinale": p["TemperaturaFinale"],
                "VolumeNormalizzato": p["VolumeNormalizzato"],
                "PesoIniSerpentina": peso_in_serp,
                "PesoFinSerpentina": peso_fin_serp,
                "PesoIniGel": peso_in_gel,
                "PesoFinGel": peso_fin_gel,
                "UmiditaFumi": umidita_fumi,
                "Isocinetismo": isocinetismo,
                "VelocitàCampionamento": velocita_media,
                "dP": dp,
                "TemperaturaFumi": temp_fumi,
                "Note": note,
                "Asse1_JSON": "",
                "Asse2_JSON": "",
                "Ultima_Modifica": datetime.utcnow().isoformat()
            }
            nuovi_prelievi.append(row)

# ===============================
# RIEPILOGO E SALVATAGGIO
# ===============================
st.markdown(f"**Totale righe da salvare:** {len(nuovi_prelievi)}")
if st.button("💾 Salva su Google Sheets"):
    delete_rows_for_session(SessionID)
    append_rows([ [row.get(h,"") for h in HEADER] for row in nuovi_prelievi ])
    st.success(f"✅ Sessione {SessionID} salvata con {len(nuovi_prelievi)} righe")
