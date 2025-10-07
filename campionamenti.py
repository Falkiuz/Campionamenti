# campionamenti_streamlit_ottim_full.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date
import time

st.set_page_config(layout="wide")

# ===============================
# AUTENTICAZIONE GOOGLE SHEETS
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)
SHEET_ID = "1KCPltH_8EtI5svqRivdwI68DWJ6eE1IK3UDe45PENf8"

# ===============================
# RETRY LOGIC PER SHEET
# ===============================
def get_sheet_with_retry(max_retry=3, delay=2):
    for attempt in range(max_retry):
        try:
            sh = client.open_by_key(SHEET_ID).sheet1
            return sh
        except Exception as e:
            if attempt < max_retry - 1:
                time.sleep(delay)
            else:
                st.error(f"Errore connessione a Google Sheets dopo {max_retry} tentativi: {e}")
                return None

sheet = get_sheet_with_retry()
if sheet is None:
    st.stop()

# ===============================
# HEADER FOGLIO
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
# UTILITY SHEET
# ===============================
def safe_get_all_records():
    try:
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"Errore lettura Google Sheets: {e}")
        return []

def safe_get_all_values():
    try:
        return sheet.get_all_values()
    except Exception as e:
        st.error(f"Errore lettura Google Sheets: {e}")
        return []

def ensure_header():
    try:
        row1 = sheet.row_values(1)
        if not row1 or row1[:len(HEADER)] != HEADER[:len(row1)]:
            sheet.insert_row(HEADER, index=1)
    except Exception as e:
        st.warning(f"Impossibile assicurare header: {e}")

def delete_rows_for_session(session_id):
    try:
        all_vals = safe_get_all_values()
        if not all_vals or len(all_vals)<=1:
            return
        rows_to_delete = []
        for idx, row in enumerate(all_vals[1:], start=2):
            if len(row)>=1 and row[0]==session_id:
                rows_to_delete.append(idx)
        for r in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(r)
    except Exception as e:
        st.error(f"Errore eliminazione righe sessione: {e}")

def append_rows(rows):
    if not rows: return
    try:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"Errore append su Google Sheets: {e}")

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
records = safe_get_all_records()

session_ids = sorted(list({r["SessionID"] for r in records if r.get("SessionID")}), reverse=True)
session_ids_display = ["➕ Nuova sessione"] + session_ids

st.title("📋 Modulo Campionamenti Ambientali — Versione ottimizzata")

# ===============================
# SESSION SELECT / CREATE
# ===============================
selected_session = st.selectbox("Seleziona SessionID o crea nuova sessione", session_ids_display, key="session_select")
if selected_session=="➕ Nuova sessione":
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
session_rows = [r for r in records if r.get("SessionID")==SessionID]
prefill = {}
if session_rows:
    for r in session_rows:
        try: n=int(r.get("PrelievoN",1))
        except: n=1
        pre = prefill.setdefault(n, {"params":[]})
        if "meta" not in pre:
            pre["meta"] = {k:r.get(k,"") for k in [
                "Ugello","DurataPrelievo","OraInizio","FiltroQMA","PrelievoMultiplo",
                "Temperatura","Pressione","Umidita","Meteo",
                "PesoIniSerpentina","PesoFinSerpentina","PesoIniGel","PesoFinGel",
                "Isocinetismo","VelocitàCampionamento","dP","TemperaturaFumi","Note"
            ]}
        param = {k:r.get(k,"") for k in ["Parametro","AltroParametro","Pompa","Portata","VolumeIniziale","VolumeFinale","TemperaturaIniziale","TemperaturaFinale","VolumeNormalizzato"]}
        pre["params"].append(param)

# ===============================
# DATI GENERALI SESSIONE
# ===============================
with st.expander("📂 Dati Generali Sessione", expanded=True):
    col1,col2=st.columns(2)
    with col1:
        ditta=st.text_input("Ditta", value=(session_rows[0].get("Ditta","") if session_rows else ""))
        stabilimento=st.text_input("Stabilimento", value=(session_rows[0].get("Stabilimento","") if session_rows else ""))
        data_campagna=st.date_input("Data campagna", value=date.fromisoformat(session_rows[0].get("Data")) if session_rows and session_rows[0].get("Data") else date.today())
        camino=st.text_input("Camino", value=(session_rows[0].get("Camino","") if session_rows else ""))
    with col2:
        operatore1=st.text_input("Operatore 1", value=(session_rows[0].get("Operatore1","") if session_rows else ""))
        operatore2=st.text_input("Operatore 2", value=(session_rows[0].get("Operatore2","") if session_rows else ""))
        pressione_statica=st.number_input("Pressione Statica", value=float(session_rows[0].get("PressioneStatica",0)) if session_rows else 0.0, step=0.1)
        velocita_camino=st.number_input("Velocità Camino", value=float(session_rows[0].get("VelocitàCamino",0)) if session_rows else 0.0, step=0.1)

# ===============================
# NUMERO PRELIEVI
# ===============================
if prefill:
    max_prel=max(prefill.keys())
    num_prelievi=st.number_input("Numero di prelievi", min_value=1, max_value=50, value=max_prel, key="num_prel_prefill")
else:
    num_prelievi=st.number_input("Numero di prelievi", min_value=1, max_value=50, value=1, key="num_prel_new")

# ===============================
# PARAMETRI DISPONIBILI
# ===============================
PARAMETRI=["Polveri","Polveri SiO2","Acidi","SOx","HCl","HF","Metalli","CrVI","NH3","SO3","Fenolo Formaldeide","SOV","Altro"]

# ===============================
# RACCOLTA DATI PRELIEVI
# ===============================
nuovi_prelievi=[]
for i in range(1,int(num_prelievi)+1):
    with st.expander(f"Prelievo {i}", expanded=False):
        meta=prefill.get(i,{}).get("meta",{})
        col1,col2,col3=st.columns([2,2,2])
        with col1:
            ugello=st.text_input(f"Ugello {i}", value=meta.get("Ugello",""), key=f"ugello_{i}")
            durata=st.number_input(f"Durata Prelievo {i} (s)", value=float(meta.get("DurataPrelievo",0)) if meta.get("DurataPrelievo","")!="" else 0.0, key=f"durata_{i}")
            ora_inizio=st.time_input(f"Ora Inizio {i}", value=(datetime.strptime(meta.get("OraInizio","00:00"), "%H:%M").time() if meta.get("OraInizio","") else datetime.now().time()), key=f"ora_{i}")
            filtro_qma=st.text_input(f"Filtro QMA {i}", value=meta.get("FiltroQMA",""), key=f"filtro_{i}")
            prelievo_multiplo=st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"], index=0 if meta.get("PrelievoMultiplo","")=="" else (0 if meta.get("PrelievoMultiplo")=="NO" else 1), key=f"multi_{i}")
        with col2:
            temperatura=st.number_input(f"Temperatura °C {i}", value=float(meta.get("Temperatura",0)) if meta.get("Temperatura","")!="" else 0.0, key=f"temp_{i}", step=0.1)
            pressione=st.number_input(f"Pressione hPa {i}", value=float(meta.get("Pressione",1013.25)) if meta.get("Pressione","")!="" else 1013.25, key=f"press_{i}", step=0.1)
            umidita=st.number_input(f"Umidità % {i}", value=float(meta.get("Umidita",0)) if meta.get("Umidita","")!="" else 0.0, key=f"umid_{i}", step=0.1)
            meteo=st.selectbox(f"Meteo {i}", ["","Sereno","Nuvoloso","Pioggia","Vento"], index=0 if meta.get("Meteo","")=="" else ["","Sereno","Nuvoloso","Pioggia","Vento"].index(meta.get("Meteo","")), key=f"meteo_{i}")
        with col3:
            peso_in_serp=st.number_input(f"Peso Iniziale Serpentina {i}", value=float(meta.get("PesoIniSerpentina",0)) if meta.get("PesoIniSerpentina","")!="" else 0.0, key=f"pis_{i}")
            peso_fin_serp=st.number_input(f"Peso Finale Serpentina {i}", value=float(meta.get("PesoFinSerpentina",0)) if meta.get("PesoFinSerpentina","")!="" else 0.0, key=f"pfs_{i}")
            peso_in_gel=st.number_input(f"Peso Iniziale Gel {i}", value=float(meta.get("PesoIniGel",0)) if meta.get("PesoIniGel","")!="" else 0.0, key=f"pig_{i}")
            peso_fin_gel=st.number_input(f"Peso Finale Gel {i}", value=float(meta.get("PesoFinGel",0)) if meta.get("PesoFinGel","")!="" else 0.0, key=f"pfg_{i}")
            isocinetismo=st.number_input(f"Isocinetismo {i}", value=float(meta.get("Isocinetismo",0)) if meta.get("Isocinetismo","")!="" else 0.0, key=f"isoc_{i}", step=0.01)
            velocita_camp=st.number_input(f"Velocità Campionamento {i}", value=float(meta.get("VelocitàCampionamento",0)) if meta.get("VelocitàCampionamento","")!="" else 0.0, key=f"vel_{i}", step=0.01)
            dp=st.number_input(f"dP {i}", value=float(meta.get("dP",0)) if meta.get("dP","")!="" else 0.0, key=f"dp_{i}", step=0.01)
            temp_fumi=st.number_input(f"Temperatura Fumi {i}", value=float(meta.get("TemperaturaFumi",0)) if meta.get("TemperaturaFumi","")!="" else 0.0, key=f"tfumi_{i}", step=0.1)
            note=st.text_area(f"Note {i}", value=meta.get("Note",""), key=f"note_{i}")
        # Parametri dinamici
        params_list=[]
        for pidx, p in enumerate(PARAMETRI):
            param_value=st.number_input(f"{p} {i} (mg/m3)", value=0.0, key=f"param_{i}_{pidx}", step=0.01)
            params_list.append({"Parametro":p, "AltroParametro":"","Pompa":"","Portata":"","VolumeIniziale":0.0,"VolumeFinale":0.0,"TemperaturaIniziale":0.0,"TemperaturaFinale":0.0,"VolumeNormalizzato":0.0,"Valore":param_value})
        nuovi_prelievi.append({
            "PrelievoN":i,
            "Ugello":ugello,
            "DurataPrelievo":durata,
            "OraInizio":ora_inizio.strftime("%H:%M"),
            "FiltroQMA":filtro_qma,
            "PrelievoMultiplo":prelievo_multiplo,
            "Temperatura":temperatura,
            "Pressione":pressione,
            "Umidita":umidita,
            "Meteo":meteo,
            "PesoIniSerpentina":peso_in_serp,
            "PesoFinSerpentina":peso_fin_serp,
            "PesoIniGel":peso_in_gel,
            "PesoFinGel":peso_fin_gel,
            "Isocinetismo":isocinetismo,
            "VelocitàCampionamento":velocita_camp,
            "dP":dp,
            "TemperaturaFumi":temp_fumi,
            "Note":note,
            "Parametri":params_list
        })

# ===============================
# ANTEPRIMA DATI
# ===============================
st.markdown("### Anteprima dati prelievi")
df_preview=[]
for p in nuovi_prelievi:
    for param in p["Parametri"]:
        row={**p}
        row.update(param)
        row["SessionID"]=SessionID
        row["Ditta"]=ditta
        row["Stabilimento"]=stabilimento
        row["Data"]=data_campagna.isoformat()
        df_preview.append(row)
st.dataframe(pd.DataFrame(df_preview))

# ===============================
# PULSANTE SALVA
# ===============================
if st.button("💾 Salva sessione su Google Sheets"):
    try:
        delete_rows_for_session(SessionID)
        rows_to_append=[]
        for p in nuovi_prelievi:
            for param in p["Parametri"]:
                row=[SessionID,ditta,stabilimento,data_campagna.isoformat(),"Camino","Operatore1","Operatore2",
                     pressione_statica,velocita_camino,"","","","","","","","","","","","","","","",
                     p["PrelievoN"],p["Ugello"],p["DurataPrelievo"],p["OraInizio"],p["FiltroQMA"],p["PrelievoMultiplo"],
                     p["Temperatura"],p["Pressione"],p["Umidita"],p["Meteo"],
                     param["Parametro"],param["AltroParametro"],param["Pompa"],param["Portata"],
                     param["VolumeIniziale"],param["VolumeFinale"],param["TemperaturaIniziale"],param["TemperaturaFinale"],param["VolumeNormalizzato"],
                     p["PesoIniSerpentina"],p["PesoFinSerpentina"],p["PesoIniGel"],p["PesoFinGel"],0.0,
                     p["Isocinetismo"],p["VelocitàCampionamento"],p["dP"],p["TemperaturaFumi"],p["Note"],"","",datetime.now().isoformat()]
                rows_to_append.append(row)
        append_rows(rows_to_append)
        st.success(f"✅ Sessione {SessionID} salvata ({len(rows_to_append)} righe)")
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
