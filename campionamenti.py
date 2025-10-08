# campionamenti_streamlit_sidebar.py
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
# HEADER
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
# UTILITY
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
            sheet.insert_row(HEADER, index=1)
    except Exception as e:
        st.warning(f"Impossibile assicurare header: {e}")

def delete_rows_for_session(session_id):
    try:
        all_vals = safe_get_all_values()
        if not all_vals or len(all_vals) <= 1:
            return
        rows_to_delete = []
        for idx, row in enumerate(all_vals[1:], start=2):
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

# ===============================
# BARRA LATERALE
# ===============================
with st.sidebar:
    st.title("📂 Navigazione")
    st.markdown("Seleziona la sessione o crea nuova sessione:")
    session_ids = sorted(list({r["SessionID"] for r in records if r.get("SessionID")}), reverse=True)
    session_ids_display = ["➕ Nuova sessione"] + session_ids
    selected_session = st.selectbox("SessionID", session_ids_display)

# ===============================
# CREAZIONE O RICHIAMO SESSIONE
# ===============================
if selected_session == "➕ Nuova sessione":
    current_session = None
    SessionID = ""
else:
    current_session = selected_session
    SessionID = current_session

# ===============================
# FORM PRINCIPALE
# ===============================
st.title("📋 Modulo Campionamenti Ambientali — Versione Sidebar")
with st.form("campionamento_form"):
    col1, col2 = st.columns(2)
    with col1:
        ditta = st.text_input("Ditta")
        stabilimento = st.text_input("Stabilimento")
        data_campagna = st.date_input("Data campagna", value=date.today())
        camino = st.text_input("Camino")
        angolo_swirl = st.number_input("Angolo di Swirl", value=0.0)
        diametro_progetto = st.number_input("Diametro Progetto", value=0.0)
        diametro_misurato = st.number_input("Diametro Misurato", value=0.0)
        numero_bocchelli = st.number_input("Numero Bocchelli", value=0)
        diametri_amonte = st.selectbox("Diametri a monte", [">5","<5"])
        diametri_aval = st.selectbox("Diametri a valle", [">5 sbocco camino/>2 curva","<5 sbocco camino/<2 curva"])
        analizzatore = st.selectbox("Analizzatore", ["Horiba","EL3000","MRU","FID","Altro"])
        cert_mix = st.text_input("CertMix")
        cert_o2 = st.text_input("CertO2")
        pc = st.text_input("PC")
        laser = st.text_input("Laser")
        micromanometro = st.text_input("Micromanometro")
        termocoppia = st.text_input("Termocoppia")
        darcy = st.text_input("Darcy")
        kdarcy = st.number_input("KDarcy", value=0.0)
    with col2:
        operatore1 = st.text_input("Operatore 1")
        operatore2 = st.text_input("Operatore 2")
        pressione_statica = st.number_input("Pressione Statica", value=0.0)
        velocita_camino = st.number_input("Velocità Camino", value=0.0)

    num_prelievi = st.number_input("Numero Prelievi", min_value=1, max_value=50, value=1)

    PARAMETRI = ["Polveri", "Polveri SiO2", "Acidi", "SOx", "HCl",
                 "HF", "Metalli", "CrVI", "NH3", "SO3",
                 "Fenolo Formaldeide", "SOV", "Altro"]

    prelievi = []
    for i in range(1, num_prelievi+1):
        st.subheader(f"Prelievo {i}")
        ugello = st.number_input(f"Ugello {i}", value=0)
        durata = st.number_input(f"Durata Prelievo {i} (s)", value=0.0)
        ora_inizio = st.time_input(f"Ora Inizio {i}", value=datetime.now().time())
        filtro_qma = st.text_input(f"Filtro QMA {i}")
        prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"])
        temperatura = st.number_input(f"Temperatura °C {i}", value=0.0)
        pressione = st.number_input(f"Pressione hPa {i}", value=1013.25)
        umidita = st.number_input(f"Umidità % {i}", value=0.0)
        meteo = st.selectbox(f"Meteo {i}", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"])
        peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}", value=0.0)
        peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", value=0.0)
        peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}", value=0.0)
        peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", value=0.0)
        isocinetismo = st.number_input(f"Isocinetismo {i}", value=0.0)
        vel_media = st.number_input(f"Velocità media {i}", value=0.0)
        dp = st.number_input(f"dP {i}", value=0.0)
        temp_fumi = st.number_input(f"Temperatura Fumi {i}", value=0.0)
        note = st.text_area(f"Note {i}")

        num_param = st.number_input(f"Numero Parametri {i}", min_value=1, max_value=20, value=1)
        parametri_prelievo = []
        for j in range(1, num_param+1):
            parametro = st.selectbox(f"Parametro {j}", PARAMETRI)
            altro_parametro = st.text_input(f"Altro Parametro {j}") if parametro=="Altro" else ""
            pompa = st.text_input(f"Pompa {j}")
            portata = st.number_input(f"Portata {j}", value=0.0)
            vol_in = st.number_input(f"Volume Iniziale {j}", value=0.0)
            vol_fin = st.number_input(f"Volume Finale {j}", value=0.0)
            temp_in = st.number_input(f"Temperatura Iniziale {j}", value=0.0)
            temp_fin = st.number_input(f"Temperatura Finale {j}", value=0.0)
            vn = calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, pressione)
            parametri_prelievo.append({
                "Parametro": parametro,
                "AltroParametro": altro_parametro,
                "Pompa": pompa,
                "Portata": portata,
                "VolumeIniziale": vol_in,
                "VolumeFinale": vol_fin,
                "TemperaturaIniziale": temp_in,
                "TemperaturaFinale": temp_fin,
                "VolumeNormalizzato": vn
            })

        # Calcolo umidità
        if st.form_submit_button(f"Calcola Umidità Prelievo {i}"):
            peso_acqua_serp = peso_fin_serp - peso_in_serp
            peso_acqua_gel = peso_fin_gel - peso_in_gel
            peso_tot = peso_acqua_serp + peso_acqua_gel
            vol_acqua = (peso_tot / 18) * 22.414
            # scelgo il primo VN come default
            vol_scelto = parametri_prelievo[0]["VolumeNormalizzato"]
            vol_tot = vol_acqua + vol_scelto
            umidita_fumi = (vol_acqua / vol_tot * 100) if vol_tot!=0 else 0.0
            st.success(f"Umidità fumi Prelievo {i}: {umidita_fumi:.2f}%")

        prelievi.append({
            "ugello": ugello,
            "durata": durata,
            "ora_inizio": ora_inizio,
            "filtro_qma": filtro_qma,
            "prelievo_multiplo": prelievo_multiplo,
            "temperatura": temperatura,
            "pressione": pressione,
            "umidita": umidita,
            "meteo": meteo,
            "peso_in_serp": peso_in_serp,
            "peso_fin_serp": peso_fin_serp,
            "peso_in_gel": peso_in_gel,
            "peso_fin_gel": peso_fin_gel,
            "isocinetismo": isocinetismo,
            "vel_media": vel_media,
            "dp": dp,
            "temp_fumi": temp_fumi,
            "note": note,
            "parametri": parametri_prelievo
        })

    submitted = st.form_submit_button("💾 Salva Campionamenti")

if submitted:
    # genera SessionID leggibile
    if not SessionID:
        SessionID = f"{ditta}_{stabilimento}_{data_campagna.strftime('%Y%m%d')}_{camino}"
    rows_to_append = []
    for idx, p in enumerate(prelievi, start=1):
        for param in p["parametri"]:
            row = {col:"" for col in HEADER}
            row.update({
                "SessionID": SessionID,
                "Ditta": ditta,
                "Stabilimento": stabilimento,
                "Data": data_campagna.strftime("%d/%m/%Y"),
                "Camino": camino,
                "Operatore1": operatore1,
                "Operatore2": operatore2,
                "PressioneStatica": pressione_statica,
                "VelocitàCamino": velocita_camino,
                "AngoloDiSwirl": angolo_swirl,
                "DiametroProgetto": diametro_progetto,
                "DiametroMisurato": diametro_misurato,
                "NumeroBocchelli": numero_bocchelli,
                "DiametriAMonte": diametri_amonte,
                "DiametriAValle": diametri_aval,
                "Analizzatore": analizzatore,
                "CertMix": cert_mix,
                "CertO2": cert_o2,
                "PC": pc,
                "Laser": laser,
                "Micromanometro": micromanometro,
                "Termocoppia": termocoppia,
                "Darcy": darcy,
                "KDarcy": kdarcy,
                "PrelievoN": idx,
                "Ugello": p["ugello"],
                "DurataPrelievo": p["durata"],
                "OraInizio": p["ora_inizio"].strftime("%H:%M:%S"),
                "FiltroQMA": p["filtro_qma"],
                "PrelievoMultiplo": p["prelievo_multiplo"],
                "Temperatura": p["temperatura"],
                "Pressione": p["pressione"],
                "Umidita": p["umidita"],
                "Meteo": p["meteo"],
                "Parametro": param["Parametro"],
                "AltroParametro": param["AltroParametro"],
                "Pompa": param["Pompa"],
                "Portata": param["Portata"],
                "VolumeIniziale": param["VolumeIniziale"],
                "VolumeFinale": param["VolumeFinale"],
                "TemperaturaIniziale": param["TemperaturaIniziale"],
                "TemperaturaFinale": param["TemperaturaFinale"],
                "VolumeNormalizzato": param["VolumeNormalizzato"],
                "PesoIniSerpentina": p["peso_in_serp"],
                "PesoFinSerpentina": p["peso_fin_serp"],
                "PesoIniGel": p["peso_in_gel"],
                "PesoFinGel": p["peso_fin_gel"],
                "Isocinetismo": p["isocinetismo"],
                "VelocitàCampionamento": p["vel_media"],
                "dP": p["dp"],
                "TemperaturaFumi": p["temp_fumi"],
                "Note": p["note"],
                "Ultima_Modifica": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            })
            rows_to_append.append([row.get(c, "") for c in HEADER])

    # elimina eventuali righe esistenti per sessione
    delete_rows_for_session(SessionID)
    append_rows(rows_to_append)
    st.success(f"✅ Campionamento salvato con SessionID: {SessionID}")
