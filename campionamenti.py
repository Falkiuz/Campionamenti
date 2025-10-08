# campionamenti_streamlit_final.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date

st.set_page_config(layout="wide")

# ===============================
# AUTENTICAZIONE GOOGLE SHEETS
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
# UTILITY: safe sheet operations
# ===============================
def safe_get_all_records():
    try:
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"Errore connessione a Google Sheets: {e}")
        return []

def safe_get_all_values():
    try:
        return sheet.get_all_values()
    except Exception as e:
        st.error(f"Errore connessione a Google Sheets: {e}")
        return []

def ensure_header():
    try:
        row1 = sheet.row_values(1)
        if not row1 or row1[:len(HEADER)] != HEADER[:len(row1)]:
            all_values = sheet.get_all_values()
            if len(all_values) == 0 or all(all(cell=="" for cell in all_values[0])):
                sheet.insert_row(HEADER, index=1)
    except Exception as e:
        st.warning(f"Impossibile assicurare header: {e}")

def delete_rows_for_session(session_id):
    try:
        all_vals = safe_get_all_values()
        if not all_vals or len(all_vals) <= 1:
            return
        rows_to_delete = []
        for idx, row in enumerate(all_vals[1:], start=2):  # skip header
            if len(row) >= 1 and row[0] == session_id:
                rows_to_delete.append(idx)
        for r in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(r)
    except Exception as e:
        st.error(f"Errore eliminazione righe sessione: {e}")

def append_rows(rows):
    if not rows:
        return
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

def calcola_umidita(peso_in_serp, peso_fin_serp, peso_in_gel, peso_fin_gel, vol_scelto):
    peso_acqua_serp = peso_fin_serp - peso_in_serp
    peso_acqua_gel = peso_fin_gel - peso_in_gel
    peso_acqua_tot = peso_acqua_serp + peso_acqua_gel
    volume_acqua = peso_acqua_tot / 18 * 22.414
    volume_totale = volume_acqua + vol_scelto
    umidita = (volume_acqua / volume_totale * 100) if volume_totale != 0 else 0.0
    return peso_acqua_serp, peso_acqua_gel, peso_acqua_tot, volume_acqua, volume_totale, umidita

# ===============================
# INIT
# ===============================
ensure_header()
records = safe_get_all_records()
all_values = safe_get_all_values()

# ===============================
# SIDEBAR
# ===============================
st.sidebar.title("📋 Navigazione Campionamenti")
page = st.sidebar.radio("Seleziona sezione", ["Dati Generali", "Prelievi", "Anteprima e Salvataggio"])

# ===============================
# SESSION SELECT / CREATE
# ===============================
session_ids = sorted(list({r["SessionID"] for r in records if r.get("SessionID")}), reverse=True)
session_ids_display = ["➕ Nuova sessione"] + session_ids
selected_session = st.sidebar.selectbox("Seleziona SessionID o crea nuova sessione", session_ids_display)

# CAMPAGNA BASE (senza prefill automatico)
if selected_session == "➕ Nuova sessione":
    st.session_state.current_session = None
else:
    st.session_state.current_session = selected_session

# ===============================
# DATI GENERALI
# ===============================
if page == "Dati Generali":
    st.title("📂 Dati Generali Sessione")
    col1, col2 = st.columns(2)
    with col1:
        ditta = st.text_input("Ditta")
        stabilimento = st.text_input("Stabilimento")
        data_campagna = st.date_input("Data campagna", value=date.today())
        camino = st.text_input("Camino")
    with col2:
        operatore1 = st.text_input("Operatore 1")
        operatore2 = st.text_input("Operatore 2")
        pressione_statica = st.number_input("Pressione Statica", step=0.1)
        velocita_camino = st.number_input("Velocità Camino", step=0.1)
        angolo_swirl = st.number_input("Angolo di Swirl", step=0.1)
        diametro_progetto = st.number_input("Diametro Progetto", step=0.1)
        diametro_misurato = st.number_input("Diametro Misurato", step=0.1)
        numero_bocchelli = st.number_input("Numero Bocchelli", step=1)
        diametri_a_monte = st.selectbox("Diametri a monte", [">5","<5"])
        diametri_a_valle = st.selectbox("Diametri a valle", [">5 sbocco camino/>2 curva","<5 sbocco camino/<2 curva"])
        tipo_valle = st.text_input("Tipo Valle")
        analizzatore = st.selectbox("Analizzatore", ["Horiba","EL3000","MRU","FID","Altro"])
        cert_mix = st.text_input("CertMix")
        cert_o2 = st.text_input("CertO2")
        pc = st.text_input("PC")
        laser = st.text_input("Laser")
        micromanometro = st.text_input("Micromanometro")
        termocoppia = st.text_input("Termocoppia")
        darcy = st.text_input("Darcy")
        kdarcy = st.number_input("KDarcy", step=0.01)
    
    # Generazione SessionID leggibile
    if ditta and stabilimento and data_campagna and camino:
        SessionID = f"{ditta}_{stabilimento}_{data_campagna.strftime('%Y%m%d')}_{camino}"
        st.sidebar.markdown(f"**SessionID corrente:** `{SessionID}`")
    else:
        SessionID = None

# ===============================
# PRELIEVI
# ===============================
if page == "Prelievi":
    st.title("📂 Inserimento Prelievi")
    num_prelievi = st.number_input("Numero prelievi", min_value=1, max_value=50, value=1, step=1)
    prelievi = []
    PARAMETRI = ["Polveri","Polveri SiO2","Acidi","SOx","HCl","HF","Metalli","CrVI","NH3","SO3","Fenolo Formaldeide","SOV","Altro"]
    
    for i in range(1, num_prelievi+1):
        with st.expander(f"Prelievo {i}", expanded=False):
            col1, col2, col3 = st.columns([2,2,2])
            with col1:
                ugello = st.number_input(f"Ugello {i}")
                durata = st.number_input(f"Durata Prelievo {i} (s)")
                ora_inizio = st.time_input(f"Ora Inizio {i}", value=datetime.now().time())
                filtro_qma = st.text_input(f"Filtro QMA {i}")
                prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"])
            with col2:
                temperatura = st.number_input(f"Temperatura °C {i}")
                pressione = st.number_input(f"Pressione hPa {i}", value=1013.25)
                umidita = st.number_input(f"Umidità % {i}")
                meteo = st.selectbox(f"Meteo {i}", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"])
            with col3:
                peso_ini_serp = st.number_input(f"Peso Iniziale Serpentina {i}")
                peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}")
                peso_ini_gel = st.number_input(f"Peso Iniziale Gel {i}")
                peso_fin_gel = st.number_input(f"Peso Finale Gel {i}")
                isocinetismo = st.number_input(f"Isocinetismo {i}")
                velocita_media = st.number_input(f"Velocità Campionamento {i}")
                dp = st.number_input(f"dP {i}")
                temp_fumi = st.number_input(f"Temperatura Fumi {i}")
                note = st.text_area(f"Note prelievo {i}")

            # Parametri
            num_param = st.number_input(f"Numero parametri per prelievo {i}", min_value=1, max_value=20, value=1)
            parametri = []
            for j in range(1,int(num_param)+1):
                c1, c2, c3, c4 = st.columns([2,1,1,1])
                with c1:
                    parametro = st.selectbox(f"Parametro {j}", PARAMETRI)
                    if parametro=="Altro":
                        altro_parametro = st.text_input(f"Specificare parametro {j}")
                    else:
                        altro_parametro = ""
                with c2:
                    vol_in = st.number_input(f"Vol In {j}")
                    vol_fin = st.number_input(f"Vol Fin {j}")
                with c3:
                    temp_in = st.number_input(f"T In {j}")
                    temp_fin = st.number_input(f"T Fin {j}")
                with c4:
                    vn = calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, pressione)
                    st.markdown(f"**VN:** `{vn:.6f}`")
                
                parametri.append({
                    "Parametro": parametro,
                    "AltroParametro": altro_parametro,
                    "VolumeIniziale": vol_in,
                    "VolumeFinale": vol_fin,
                    "TemperaturaIniziale": temp_in,
                    "TemperaturaFinale": temp_fin,
                    "VolumeNormalizzato": vn
                })
            
            # Bottone calcolo umidità
            if st.button(f"Calcola Umidità Prelievo {i}"):
                vol_scelto = st.selectbox(f"Scegli Volume Normalizzato per Umidità {i}", [p["VolumeNormalizzato"] for p in parametri])
                peso_serp, peso_gel, peso_tot, vol_acqua, vol_tot, umid = calcola_umidita(
                    peso_ini_serp, peso_fin_serp, peso_ini_gel, peso_fin_gel, vol_scelto
                )
                st.info(f"Umidità fumi: {umid:.2f}% (Vol Acqua={vol_acqua:.2f}, Vol Totale={vol_tot:.2f})")

# ===============================
# ANTEPRIMA E SALVA
# ===============================
if page=="Anteprima e Salvataggio":
    st.title("📄 Anteprima e Salvataggio")
    st.info("Qui mostriamo l'anteprima e si può salvare su Google Sheets (da implementare mapping e append).")
