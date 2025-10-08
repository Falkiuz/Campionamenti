# campionamenti_streamlit_complete.py
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

# ===============================
# HEADER (ordine colonne su sheet)
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
def get_sheet_with_retry(max_retry=3, delay=1):
    for attempt in range(max_retry):
        try:
            sh = client.open_by_key(SHEET_ID).sheet1
            return sh
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
# FUNZIONI CALCOLO
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
# UI - iniziale: leggi sessioni
# ===============================
st.title("📋 Modulo Campionamenti Ambientali — versione completa")

sheet_read = get_sheet_with_retry()
records = []
session_ids = []
if sheet_read:
    ensure_header(sheet_read)
    records = read_all_records(sheet_read)
    # CORREZIONE: uso r.get("SessionID") per evitare KeyError
    session_ids = sorted(list({r.get("SessionID") for r in records if r.get("SessionID")}), reverse=True)

session_options = ["➕ Nuova sessione"] + session_ids
selected_session = st.selectbox("Seleziona SessionID o crea nuova sessione", session_options, key="select_session")

prefill_enabled = False
if selected_session != "➕ Nuova sessione":
    prefill_enabled = st.checkbox("Richiama dati da questa sessione (prefill)", value=False)

# ===============================
# SESSIONID e dati generali
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
    SessionID = f"{sanitized_d}_{sanitized_s}_{data_campagna.strftime('%Y%m%d')}"
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

col1, col2, col3 = st.columns([3,3,2])
with col1:
    st.text_input("Ditta", value=ditta, key="ditta_prefill")
    st.text_input("Stabilimento", value=stabilimento, key="stabilimento_prefill")
with col2:
    st.date_input("Data campagna", value=data_campagna, key="data_campagna_prefill")
    st.text_input("Camino", value=camino, key="camino_prefill")
with col3:
    st.text_input("Operatore 1", value=operatore1, key="operatore1_prefill")
    st.text_input("Operatore 2", value=operatore2, key="operatore2_prefill")

# ===============================
# DATI GENERALI (una volta per sessione)
# ===============================
with st.expander("📂 Dati generali (compilare una sola volta per sessione)", expanded=True):
    default_row = None
    if prefill_enabled and sheet_read:
        rows = [r for r in records if r.get("SessionID") == SessionID]
        if rows:
            default_row = rows[0]
    pressione_statica = st.number_input("Pressione statica [Pa]", value=float(default_row.get("PressioneStatica",0)) if default_row else 0.0, step=0.1)
    velocita_camino = st.number_input("Velocità camino [m/s]", value=float(default_row.get("VelocitàCamino",0)) if default_row else 0.0, step=0.1)
    angolo_swirl = st.number_input("Angolo di swirl [°]", value=float(default_row.get("AngoloDiSwirl",0)) if default_row else 0.0, step=0.1)
    diametro_progetto = st.number_input("Diametro progetto [mm]", value=float(default_row.get("DiametroProgetto",0)) if default_row else 0.0, step=0.1)
    diametro_misurato = st.number_input("Diametro misurato [mm]", value=float(default_row.get("DiametroMisurato",0)) if default_row else 0.0, step=0.1)
    numero_bocchelli = st.number_input("Numero bocchelli", value=int(default_row.get("NumeroBocchelli",1)) if default_row else 1, step=1, min_value=1)

# ===============================
# PRELIEVI
# ===============================
num_prelievi = st.number_input("Numero prelievi", min_value=1, max_value=18, value=1, step=1)
prelievi_data = []

for i in range(num_prelievi):
    with st.expander(f"📌 Prelievo {i+1}", expanded=True):
        durata = st.number_input(f"Durata prelievo [min] P{i+1}", min_value=1, max_value=120, value=10)
        ora_inizio = st.time_input(f"Orario inizio P{i+1}", value=datetime.now().time())
        vol_in = st.number_input(f"Volume iniziale [L] P{i+1}", value=0.0)
        vol_fin = st.number_input(f"Volume finale [L] P{i+1}", value=0.0)
        temp_in = st.number_input(f"Temperatura iniziale [°C] P{i+1}", value=25.0)
        temp_fin = st.number_input(f"Temperatura finale [°C] P{i+1}", value=25.0)
        peso_ini_serp = st.number_input(f"Peso iniziale serpentina [g] P{i+1}", value=0.0)
        peso_fin_serp = st.number_input(f"Peso finale serpentina [g] P{i+1}", value=0.0)
        peso_ini_gel = st.number_input(f"Peso iniziale gel [g] P{i+1}", value=0.0)
        peso_fin_gel = st.number_input(f"Peso finale gel [g] P{i+1}", value=0.0)
        pressione_hpa = st.number_input(f"Pressione atmosferica [hPa] P{i+1}", value=1013.25)

        vol_norm = calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, pressione_hpa)
        umid_fumi, vol_acqua, vol_totale = calcola_umidita_fumi(peso_ini_serp, peso_fin_serp, peso_ini_gel, peso_fin_gel, vol_norm)

        prelievi_data.append([
            SessionID, ditta, stabilimento, data_campagna.strftime("%Y-%m-%d"), camino, operatore1, operatore2,
            pressione_statica, velocita_camino, angolo_swirl, diametro_progetto, diametro_misurato,
            numero_bocchelli, "", "", "",
            "", "", "", "", "", "", "", "", "",
            i+1, "", durata, ora_inizio.strftime("%H:%M"), "", "",
            "", pressione_hpa, umid_fumi, "",
            "", "", "", "",
            vol_in, vol_fin, temp_in, temp_fin, vol_norm,
            peso_ini_serp, peso_fin_serp, peso_ini_gel, peso_fin_gel, umid_fumi,
            "", "", "", "", "", "", "", datetime.now().isoformat()
        ])

# ===============================
# SALVATAGGIO
# ===============================
if st.button("💾 Salva su Google Sheets"):
    if sheet_read:
        delete_rows_for_session(sheet_read, SessionID)
        append_rows(sheet_read, prelievi_data)
        st.success(f"Dati sessione {SessionID} salvati correttamente su Google Sheets!")

# ===============================
# FINE
# ===============================
