# campionamenti_streamlit_sidebar.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date

st.set_page_config(layout="wide", page_title="Modulo Campionamenti", initial_sidebar_state="collapsed")

# ===============================
# AUTENTICAZIONE GOOGLE SHEETS
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID = "1KCPltH_8EtI5svqRivdwI68DWJ6eE1IK3UDe45PENf8"

# ===============================
# UTILITY SHEET
# ===============================
def safe_sheet_open():
    try:
        return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        st.error(f"Errore connessione Google Sheets: {e}")
        return None

sheet = safe_sheet_open()

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

def safe_get_all_records():
    if not sheet:
        return []
    try:
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"Errore lettura Google Sheets: {e}")
        return []

def ensure_header():
    if not sheet:
        return
    try:
        row1 = sheet.row_values(1)
        if not row1 or row1[:len(HEADER)] != HEADER[:len(row1)]:
            sheet.insert_row(HEADER, index=1)
    except Exception as e:
        st.warning(f"Errore assicurazione header: {e}")

def delete_rows_for_session(session_id):
    if not sheet:
        return
    try:
        all_vals = sheet.get_all_values()
        if len(all_vals)<=1: return
        rows_to_delete = [idx for idx, row in enumerate(all_vals[1:], start=2) if row[0]==session_id]
        for r in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(r)
    except Exception as e:
        st.error(f"Errore eliminazione righe sessione: {e}")

def append_rows(rows):
    if not sheet or not rows: return
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
        temp_media = (float(temp_in)+float(temp_fin))/2.0
        return vol_delta*(273.15/(temp_media+273.15))*(float(pressione_hpa)/1013.25)
    except:
        return 0.0

def calcola_umidita(pis, pfs, pig, pfg, vn_scelto):
    peso_acqua_serp = pfs - pis
    peso_acqua_gel = pfg - pig
    peso_acqua_tot = peso_acqua_serp + peso_acqua_gel
    volume_acqua = peso_acqua_tot/18*22.414
    volume_totale = volume_acqua + vn_scelto
    umidita = (volume_acqua/volume_totale*100) if volume_totale!=0 else 0.0
    return volume_acqua, volume_totale, umidita

# ===============================
# INIT
# ===============================
ensure_header()
records = safe_get_all_records()

st.title("📋 Modulo Campionamenti Ambientali — Versione Sidebar")

# ===============================
# SIDEBAR
# ===============================
st.sidebar.title("Navigazione")
section = st.sidebar.radio("Seleziona sezione:", ["Dati Generali","Prelievi"])

# ===============================
# DATI GENERALI SESSIONE
# ===============================
with st.expander("📂 Dati Generali Sessione", expanded=(section=="Dati Generali")):
    col1, col2 = st.columns(2)
    with col1:
        ditta = st.text_input("Ditta")
        stabilimento = st.text_input("Stabilimento")
        data_campagna = st.date_input("Data campagna", value=date.today())
        camino = st.text_input("Camino")
        angolo_swirl = st.number_input("AngoloDiSwirl", value=0.0, step=0.1)
        diametro_progetto = st.number_input("Diametro Progetto", value=0.0, step=0.1)
        diametro_misurato = st.number_input("Diametro Misurato", value=0.0, step=0.1)
        numero_bocchelli = st.number_input("Numero Bocchelli", value=0, step=1)
        diametri_amonte = st.selectbox("Diametri A Monte", [">5","<5"])
        diametri_avalle = st.selectbox("Diametri A Valle", [">5 sbocco camino/>2 curva","<5 sbocco camino/<2 curva"])
    with col2:
        operatore1 = st.text_input("Operatore 1")
        operatore2 = st.text_input("Operatore 2")
        pressione_statica = st.number_input("Pressione Statica", value=0.0, step=0.1)
        velocita_camino = st.number_input("Velocità Camino", value=0.0, step=0.1)
        analizzatore = st.selectbox("Analizzatore", ["Horiba","EL3000","MRU","FID","Altro"])
        cert_mix = st.text_input("CertMix")
        cert_o2 = st.text_input("CertO2")
        pc = st.text_input("PC")
        laser = st.text_input("Laser")
        micromanometro = st.text_input("Micromanometro")
        termocoppia = st.text_input("Termocoppia")
        darcy = st.text_input("Darcy")
        kdarcy = st.number_input("KDarcy", value=0.0, step=0.01)

# ===============================
# SESSION ID
# ===============================
session_id = f"{ditta}_{stabilimento}_{data_campagna.isoformat()}"
st.markdown(f"**SessionID:** `{session_id}`")

# ===============================
# NUMERO PRELIEVI
# ===============================
num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=50, value=1)

# ===============================
# RACCOLTA DATI PRELIEVI
# ===============================
PARAMETRI = ["Polveri", "Polveri SiO2", "Acidi", "SOx", "HCl",
             "HF", "Metalli", "CrVI", "NH3", "SO3",
             "Fenolo Formaldeide", "SOV", "Altro"]

nuovi_prelievi = []

for i in range(1, num_prelievi+1):
    with st.expander(f"Prelievo {i}", expanded=(section=="Prelievi")):
        col1, col2, col3 = st.columns([2,2,2])
        with col1:
            ugello = st.text_input(f"Ugello {i}")
            durata = st.number_input(f"Durata Prelievo {i}", value=0.0, step=0.1)
            ora_inizio = st.time_input(f"Ora Inizio {i}", value=datetime.now().time())
            filtro_qma = st.text_input(f"Filtro QMA {i}")
            prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"])
        with col2:
            temperatura = st.number_input(f"Temperatura °C {i}", value=0.0, step=0.1)
            pressione = st.number_input(f"Pressione hPa {i}", value=1013.25, step=0.1)
            umidita = st.number_input(f"Umidità % {i}", value=0.0, step=0.1)
            meteo = st.selectbox(f"Meteo {i}", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"])
        with col3:
            peso_ini_serp = st.number_input(f"Peso Iniziale Serpentina {i}", value=0.0, step=0.01)
            peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", value=0.0, step=0.01)
            peso_ini_gel = st.number_input(f"Peso Iniziale Gel {i}", value=0.0, step=0.01)
            peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", value=0.0, step=0.01)

        num_param = st.number_input(f"Numero di parametri per prelievo {i}", min_value=1, max_value=20, value=1)
        parametri_prelievo = []
        for j in range(1, num_param+1):
            c1,c2,c3,c4 = st.columns([2,1,1,1])
            with c1:
                parametro = st.selectbox(f"Parametro {j}", PARAMETRI)
                if parametro=="Altro":
                    altro_parametro = st.text_input(f"Specifica parametro {j}")
                    parametro_finale = altro_parametro
                else:
                    parametro_finale = parametro
            with c2:
                vol_in = st.number_input(f"Vol In {j}", value=0.0)
                vol_fin = st.number_input(f"Vol Fin {j}", value=0.0)
            with c3:
                temp_in = st.number_input(f"T In {j}", value=0.0)
                temp_fin = st.number_input(f"T Fin {j}", value=0.0)
            with c4:
                vn = calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, pressione)
                st.markdown(f"**VN:** `{vn:.6f}`")

            parametri_prelievo.append({
                "Parametro": parametro_finale,
                "AltroParametro": (altro_parametro if parametro=="Altro" else ""),
                "VolumeIniziale": vol_in,
                "VolumeFinale": vol_fin,
                "TemperaturaIniziale": temp_in,
                "TemperaturaFinale": temp_fin,
                "VolumeNormalizzato": vn
            })

        vol_choices = [p["VolumeNormalizzato"] for p in parametri_prelievo]
        vol_choice_idx = st.selectbox(f"Volume Normalizzato per Umidità {i}", options=list(range(len(vol_choices))),
                                      format_func=lambda x: f"Parametro {x+1} VN={vol_choices[x]:.6f}")
        vol_scelto = vol_choices[vol_choice_idx]

        # pulsanti calcolo volumi / umidità
        if st.button(f"Calcola umidità Prelievo {i}"):
            volume_acqua, volume_tot, umidita_calc = calcola_umidita(peso_ini_serp, peso_fin_serp, peso_ini_gel, peso_fin_gel, vol_scelto)
            st.success(f"Volume Acqua: {volume_acqua:.4f} — Volume Totale: {volume_tot:.4f} — Umidità: {umidita_calc:.2f}%")

        isocinetismo = st.number_input(f"Isocinetismo {i}", value=0.0, step=0.1)
        velocita_media = st.number_input(f"Velocità media {i}", value=0.0, step=0.1)
        dp = st.number_input(f"dP {i}", value=0.0, step=0.1)
        temp_fumi = st.number_input(f"Temperatura Fumi {i}", value=0.0, step=0.1)
        note = st.text_area(f"Note prelievo {i}")

        # costruzione righe
        for p in parametri_prelievo:
            row = {
                "SessionID": session_id,
                "Ditta": ditta,
                "Stabilimento": stabilimento,
                "Data": data_campagna.isoformat(),
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
                "DiametriAValle": diametri_avalle,
                "TipoValle": "",
                "Analizzatore": analizzatore,
                "CertMix": cert_mix,
                "CertO2": cert_o2,
                "PC": pc,
                "Laser": laser,
                "Micromanometro": micromanometro,
                "Termocoppia": termocoppia,
                "Darcy": darcy,
                "KDarcy": kdarcy,
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
                "Portata": 0.0,
                "VolumeIniziale": p["VolumeIniziale"],
                "VolumeFinale": p["VolumeFinale"],
                "TemperaturaIniziale": p["TemperaturaIniziale"],
                "TemperaturaFinale": p["TemperaturaFinale"],
                "VolumeNormalizzato": p["VolumeNormalizzato"],
                "PesoIniSerpentina": peso_ini_serp,
                "PesoFinSerpentina": peso_fin_serp,
                "PesoIniGel": peso_ini_gel,
                "PesoFinGel": peso_fin_gel,
                "UmiditaFumi": umidita,
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
# SALVA SU GOOGLE SHEETS
# ===============================
if st.button("💾 Salva campionamenti"):
    if not nuovi_prelievi:
        st.warning("Nessun dato da salvare.")
    else:
        delete_rows_for_session(session_id)
        append_rows([[r[h] for h in HEADER] for r in nuovi_prelievi])
        st.success(f"✅ {len(nuovi_prelievi)} righe salvate su Google Sheets!")

st.markdown("---")
st.markdown("Versione con barra laterale compatta e calcolo umidità/volumi tramite pulsanti")
