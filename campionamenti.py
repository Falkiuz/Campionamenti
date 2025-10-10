# campionamenti_streamlit_auto.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date
import time

st.set_page_config(layout="wide")

# ===============================
# CONFIG GOOGLE SHEETS
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)
SHEET_ID = "1KCPltH_8EtI5svqRivdwI68DWJ6eE1IK3UDe45PENf8"

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
def get_sheet_with_retry(max_retry=3, delay=1):
    for attempt in range(max_retry):
        try:
            return client.open_by_key(SHEET_ID).sheet1
        except Exception as e:
            if attempt < max_retry - 1:
                time.sleep(delay)
            else:
                st.error(f"Impossibile connettersi a Google Sheets ({max_retry} tentativi): {e}")
                return None

def ensure_header(sheet):
    try:
        row1 = sheet.row_values(1)
        if not row1 or row1[:len(HEADER)] != HEADER[:len(row1)]:
            sheet.insert_row(HEADER, index=1)
    except Exception as e:
        st.warning(f"Impossibile assicurare header: {e}")

def read_all_records(sheet):
    try:
        return sheet.get_all_records()
    except Exception as e:
        st.warning(f"Impossibile leggere records: {e}")
        return []

def delete_rows_for_session(sheet, session_id):
    try:
        all_vals = sheet.get_all_values()
        if not all_vals or len(all_vals) <= 1:
            return
        rows_to_delete = [idx for idx, row in enumerate(all_vals[1:], start=2) if len(row) >= 1 and row[0] == session_id]
        for r in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(r)
    except Exception as e:
        st.error(f"Errore eliminazione righe sessione: {e}")

def append_rows(sheet, rows):
    if not rows:
        return
    try:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"Errore append su Google Sheets: {e}")

# ===============================
# FUNZIONI CALCOLO AUTOMATICO
# ===============================
def calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, pressione_hpa):
    try:
        vol_delta = float(vol_fin) - float(vol_in)
        temp_media = (float(temp_in) + float(temp_fin)) / 2.0
        return vol_delta * (273.15 / (temp_media + 273.15)) * (float(pressione_hpa) / 1013.25)
    except Exception:
        return 0.0

def calcola_umidita_fumi(pis, pfs, pig, pfg, volume_normalizzato):
    try:
        peso_acqua_serp = float(pfs) - float(pis)
        peso_acqua_gel = float(pfg) - float(pig)
        peso_acqua_tot = peso_acqua_serp + peso_acqua_gel
        volume_acqua = (peso_acqua_tot / 18.0) * 22.414
        volume_totale = volume_acqua + float(volume_normalizzato)
        if volume_totale == 0:
            return 0.0, volume_acqua, volume_totale
        umid = (volume_acqua / volume_totale) * 100.0
        return umid, volume_acqua, volume_totale
    except Exception:
        return 0.0, 0.0, 0.0

# ===============================
# SAFE FUNCTIONS
# ===============================
def safe_float(value):
    try:
        return float(value)
    except:
        return 0.0

def safe_int(value):
    try:
        return int(value)
    except:
        return 0

def safe_str(value):
    try:
        return str(value)
    except:
        return ""

# ===============================
# INIZIO APP
# ===============================
st.title("📋 Modulo Campionamenti Ambientali — versione automatica")

sheet_read = get_sheet_with_retry()
records = read_all_records(sheet_read) if sheet_read else []
session_ids = sorted(list({r["SessionID"] for r in records if r.get("SessionID")}), reverse=True)
session_options = ["➕ Nuova sessione"] + session_ids
selected_session = st.selectbox("Seleziona SessionID o crea nuova sessione", session_options, key="select_session")

# Prefill checkbox
prefill_enabled = selected_session != "➕ Nuova sessione" and st.checkbox("Richiama dati da questa sessione (prefill)", value=False)

# ===============================
# GESTIONE SESSIONE
# ===============================
if selected_session == "➕ Nuova sessione":
    colA, colB, colC = st.columns([3,3,2])
    with colA:
        ditta = st.text_input("Ditta", key="ditta")
        stabilimento = st.text_input("Stabilimento", key="stabilimento")
    with colB:
        data_campagna = st.date_input("Data campagna", value=date.today(), key="data_campagna")
        camino = st.text_input("Camino", key="camino")
    with colC:
        operatore1 = st.text_input("Operatore 1", key="operatore1")
        operatore2 = st.text_input("Operatore 2", key="operatore2")

    sanitized_d = (ditta.strip().replace(" ", "_") or "Ditta")
    sanitized_s = (stabilimento.strip().replace(" ", "_") or "Stab")
    sanitized_c = (camino.strip().replace(" ", "_") or "Camino")
    SessionID = f"{sanitized_d}_{sanitized_s}_{sanitized_c}_{data_campagna.strftime('%Y%m%d')}"
else:
    SessionID = selected_session
    ditta = stabilimento = camino = operatore1 = operatore2 = ""
    data_campagna = date.today()
    if prefill_enabled and sheet_read:
        rows = [r for r in records if r.get("SessionID") == SessionID]
        if rows:
            first = rows[0]
            ditta = first.get("Ditta","")
            stabilimento = first.get("Stabilimento","")
            camino = first.get("Camino","")
            operatore1 = first.get("Operatore1","")
            operatore2 = first.get("Operatore2","")
            try:
                data_campagna = date.fromisoformat(first.get("Data")) if first.get("Data") else date.today()
            except:
                data_campagna = date.today()

# ===============================
# DATI GENERALI
# ===============================
with st.expander("📂 Dati generali", expanded=True):
    default_row = rows[0] if prefill_enabled and sheet_read and rows else {}

    pressione_statica = st.number_input("PressioneStatica", value=safe_float(default_row.get("PressioneStatica",0)), step=0.1, key="pressione_statica")
    velocita_camino = st.number_input("VelocitàCamino", value=safe_float(default_row.get("VelocitàCamino",0)), step=0.1, key="velocita_camino")
    angolo_swirl = st.number_input("AngoloDiSwirl", value=safe_float(default_row.get("AngoloDiSwirl",0)), step=0.1, key="angolo_swirl")
    diametro_progetto = st.number_input("DiametroProgetto", value=safe_float(default_row.get("DiametroProgetto",0)), step=0.1, key="diametro_progetto")
    diametro_misurato = st.number_input("DiametroMisurato", value=safe_float(default_row.get("DiametroMisurato",0)), step=0.1, key="diametro_misurato")
    numero_bocchelli = st.number_input("NumeroBocchelli", value=safe_int(default_row.get("NumeroBocchelli",0)), step=1, key="numero_bocchelli")
    diametri_a_monte = st.selectbox("DiametriAMonte", [">5","<5"], index=0 if default_row.get("DiametriAMonte",">5")==">5" else 1, key="diametri_a_monte")
    diametri_a_valle = st.selectbox("DiametriAValle", [">5 sbocco camino/>2 curva","<5 sbocco camino/<2 curva"], index=0 if default_row.get("DiametriAValle","") == ">5 sbocco camino/>2 curva" else 1, key="diametri_a_valle")
    analizzatore = st.selectbox("Analizzatore", ["Horiba","EL3000","MRU","FID","Altro"], index=["Horiba","EL3000","MRU","FID","Altro"].index(default_row.get("Analizzatore","Horiba")), key="analizzatore")
    cert_mix = st.text_input("CertMix", value=safe_str(default_row.get("CertMix","")), key="cert_mix")
    cert_o2 = st.text_input("CertO2", value=safe_str(default_row.get("CertO2","")), key="cert_o2")
    pc = st.text_input("PC", value=safe_str(default_row.get("PC","")), key="pc")
    laser = st.text_input("Laser", value=safe_str(default_row.get("Laser","")), key="laser")
    micromanometro = st.text_input("Micromanometro", value=safe_str(default_row.get("Micromanometro","")), key="micromanometro")
    termocoppia = st.text_input("Termocoppia", value=safe_str(default_row.get("Termocoppia","")), key="termocoppia")
    darcy = st.text_input("Darcy", value=safe_str(default_row.get("Darcy","")), key="darcy")
    kdarcy = st.number_input("KDarcy", value=safe_float(default_row.get("KDarcy",0)), step=0.01, key="kdarcy")

# ===============================
# PRELIEVI AUTOMATICI
# ===============================
num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=50, value=1, key="num_prel_global")
PARAMETRI = ["Polveri","Polveri SiO2","Acidi","SOx","HCl","HF","Metalli","CrVI","NH3","SO3","Fenolo Formaldeide","SOV","Altro"]
nuovi_prelievi = []

for i in range(1, int(num_prelievi)+1):
    with st.expander(f"Prelievo {i}", expanded=False):
        meta_defaults = {}
        if prefill_enabled and sheet_read:
            rows_i = [r for r in records if r.get("SessionID")==SessionID and str(r.get("PrelievoN",""))==str(i)]
            if rows_i: meta_defaults = rows_i[0]

        # Input prelievo
        c1,c2,c3 = st.columns([2,2,2])
        with c1:
            ugello = st.number_input(f"Ugello {i}", value=safe_float(meta_defaults.get("Ugello",0)), key=f"ugello_{i}", step=0.1)
            durata = st.number_input(f"Durata Prelievo {i} (s)", value=safe_float(meta_defaults.get("DurataPrelievo",0)), key=f"durata_{i}", step=0.1)
            ora_inizio = st.time_input(f"Ora Inizio {i}", value=datetime.strptime(meta_defaults.get("OraInizio","00:00"), "%H:%M").time() if meta_defaults.get("OraInizio") else datetime.now().time(), key=f"ora_{i}")
            filtro_qma = st.text_input(f"Filtro QMA {i}", value=safe_str(meta_defaults.get("FiltroQMA","")), key=f"filtro_{i}")
            prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"], index=0 if meta_defaults.get("PrelievoMultiplo","NO")=="NO" else 1, key=f"multi_{i}")
        with c2:
            temperatura = st.number_input(f"Temperatura °C {i}", value=safe_float(meta_defaults.get("Temperatura",0)), key=f"temp_{i}", step=0.1)
            pressione = st.number_input(f"Pressione hPa {i}", value=safe_float(meta_defaults.get("Pressione",1013.25)), key=f"press_{i}", step=0.1)
            umidita = st.number_input(f"Umidità % {i}", value=safe_float(meta_defaults.get("Umidita",0)), key=f"umid_{i}", step=0.1)
            meteo = st.selectbox(f"Meteo {i}", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"], index=["", "Sereno", "Nuvoloso", "Pioggia", "Vento"].index(meta_defaults.get("Meteo","")) if meta_defaults.get("Meteo") else 0, key=f"meteo_{i}")
        with c3:
            peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}", value=safe_float(meta_defaults.get("PesoIniSerpentina",0)), key=f"pis_{i}", step=0.01)
            peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", value=safe_float(meta_defaults.get("PesoFinSerpentina",0)), key=f"pfs_{i}", step=0.01)
            peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}", value=safe_float(meta_defaults.get("PesoIniGel",0)), key=f"pig_{i}", step=0.01)
            peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", value=safe_float(meta_defaults.get("PesoFinGel",0)), key=f"pfg_{i}", step=0.01)

        num_param = st.number_input(f"Numero di parametri per prelievo {i}", min_value=1, max_value=20, value=safe_int(meta_defaults.get("NumParam",1)), key=f"num_param_{i}")
        params_for_prelievo = []

        for j in range(1, int(num_param)+1):
            s1,s2,s3,s4,s5 = st.columns([2,1,1,1,1])
            with s1:
                parametro = st.selectbox(f"Parametro {j} (prel {i})", PARAMETRI, index=0, key=f"param_{i}_{j}")
                altro_parametro = st.text_input(f"Altro parametro {j} (prel {i})", key=f"altro_{i}_{j}") if parametro=="Altro" else ""
            with s2:
                pompa = st.text_input(f"Pompa {j} (prel {i})", key=f"pompa_{i}_{j}")
                portata = st.number_input(f"Portata {j} (prel {i})", value=safe_float(meta_defaults.get("Portata",0)), key=f"portata_{i}_{j}", step=0.01)
            with s3:
                vol_in = st.number_input(f"Volume Iniziale {j} (prel {i})", value=safe_float(meta_defaults.get("VolumeIniziale",0)), key=f"vol_in_{i}_{j}", step=0.1)
                vol_fin = st.number_input(f"Volume Finale {j} (prel {i})", value=safe_float(meta_defaults.get("VolumeFinale",0)), key=f"vol_fin_{i}_{j}", step=0.1)
            with s4:
                temp_in = st.number_input(f"T In {j} (prel {i})", value=safe_float(meta_defaults.get("TemperaturaIniziale",0)), key=f"temp_in_{i}_{j}", step=0.1)
                temp_fin = st.number_input(f"T Fin {j} (prel {i})", value=safe_float(meta_defaults.get("TemperaturaFinale",0)), key=f"temp_fin_{i}_{j}", step=0.1)
            with s5:
                # ✅ NUOVI CAMPI
                isocinetismo = st.number_input(f"Isocinetismo {j} (prel {i})", value=safe_float(meta_defaults.get("Isocinetismo",0)), key=f"isoc_{i}_{j}", step=0.01)
                vel_camp = st.number_input(f"Velocità Campionamento {j} (prel {i})", value=safe_float(meta_defaults.get("VelocitàCampionamento",0)), key=f"velcamp_{i}_{j}", step=0.01)
                dp = st.number_input(f"dP {j} (prel {i})", value=safe_float(meta_defaults.get("dP",0)), key=f"dp_{i}_{j}", step=0.01)
                temp_fumi = st.number_input(f"Temperatura Fumi {j} (prel {i})", value=safe_float(meta_defaults.get("TemperaturaFumi",0)), key=f"tempfumi_{i}_{j}", step=0.1)
                note = st.text_input(f"Note {j} (prel {i})", value=safe_str(meta_defaults.get("Note","")), key=f"note_{i}_{j}")

            # Calcoli automatici
            vol_norm = calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, pressione)
            umid_fumi, _, _ = calcola_umidita_fumi(peso_in_serp, peso_fin_serp, peso_in_gel, peso_fin_gel, vol_norm)

            params_for_prelievo.append([
                SessionID,ditta,stabilimento,str(data_campagna),camino,operatore1,operatore2,
                pressione_statica,velocita_camino,angolo_swirl,diametro_progetto,diametro_misurato,
                numero_bocchelli,diametri_a_monte,diametri_a_valle,"",
                analizzatore,cert_mix,cert_o2,pc,laser,micromanometro,termocoppia,darcy,kdarcy,
                i,ugello,durata,ora_inizio.strftime("%H:%M"),filtro_qma,prelievo_multiplo,
                temperatura,pressione,umidita,meteo,
                parametro,altro_parametro,pompa,portata,
                vol_in,vol_fin,temp_in,temp_fin,vol_norm,
                peso_in_serp,peso_fin_serp,peso_in_gel,peso_fin_gel,umid_fumi,
                isocinetismo,vel_camp,dp,temp_fumi,note,"","",datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

        nuovi_prelievi.extend(params_for_prelievo)

# ===============================
# SALVATAGGIO SU GOOGLE SHEETS
# ===============================
if st.button("💾 Salva su Google Sheets"):
    if sheet_read:
        delete_rows_for_session(sheet_read, SessionID)
        append_rows(sheet_read, nuovi_prelievi)
        st.success(f"Tutti i prelievi per la sessione {SessionID} sono stati salvati!")
