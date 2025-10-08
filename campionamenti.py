# campionamenti_streamlit_completo.py
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
        if not all_vals or len(all_vals)<=1:
            return
        rows_to_delete = [idx for idx, row in enumerate(all_vals[1:], start=2) if len(row)>=1 and row[0]==session_id]
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
        temp_media = (float(temp_in)+float(temp_fin))/2.0
        return vol_delta*(273.15/(temp_media+273.15))*(float(pressione_hpa)/1013.25)
    except Exception:
        return 0.0

def calcola_umidita(peso_ini_serp, peso_fin_serp, peso_ini_gel, peso_fin_gel, vol_scelto):
    peso_acqua_serp = peso_fin_serp - peso_ini_serp
    peso_acqua_gel = peso_fin_gel - peso_ini_gel
    peso_acqua_tot = peso_acqua_serp + peso_acqua_gel
    volume_acqua = (peso_acqua_tot/18)*22.414
    volume_totale = vol_scelto + volume_acqua
    umidita = (volume_acqua/volume_totale*100) if volume_totale!=0 else 0.0
    return umidita, volume_acqua, volume_totale

# ===============================
# INIT
# ===============================
ensure_header()
records = safe_get_all_records()
all_values = safe_get_all_values()

# ===============================
# BARRA LATERALE
# ===============================
with st.sidebar:
    st.title("📂 Navigazione")
    scelta_sezione = st.radio("Seleziona sezione", ["Dati Generali","Prelievi","Anteprima e Salvataggio"])

# ===============================
# SESSIONE
# ===============================
st.title("📋 Modulo Campionamenti Ambientali — Versione completa")

# Genera sessionID automatico se nuova
def crea_session_id(ditta, stabilimento, camino):
    oggi = date.today().strftime("%Y%m%d")
    return f"{ditta}_{stabilimento}_{camino}[{oggi}]"

# Chiedi Ditta/Stabilimento/Camino all’inizio per ID
ditta = st.text_input("Ditta", value="")
stabilimento = st.text_input("Stabilimento", value="")
camino = st.text_input("Camino", value="")

SessionID = crea_session_id(ditta, stabilimento, camino)
st.markdown(f"**SessionID corrente:** `{SessionID}`")

# ===============================
# DATI GENERALI SESSIONE
# ===============================
if scelta_sezione=="Dati Generali":
    col1, col2 = st.columns(2)
    with col1:
        operatore1 = st.text_input("Operatore 1", value="")
        operatore2 = st.text_input("Operatore 2", value="")
        pressione_statica = st.number_input("Pressione Statica", value=0.0, step=0.1)
        velocita_camino = st.number_input("Velocità Camino", value=0.0, step=0.1)
        angolo_swirl = st.number_input("Angolo Di Swirl", value=0.0, step=0.1)
        diametro_progetto = st.number_input("Diametro Progetto", value=0.0, step=0.1)
    with col2:
        diametro_misurato = st.number_input("Diametro Misurato", value=0.0, step=0.1)
        numero_bocchelli = st.number_input("Numero Bocchelli", value=0, step=1)
        diametri_a_monte = st.selectbox("Diametri A Monte", [">5","<5"])
        diametri_a_valle = st.selectbox("Diametri A Valle", [">5 sbocco camino/>2 curva","<5 sbocco camino/<2 curva"])
        tipo_valle = st.text_input("Tipo Valle","")
        analizzatore = st.selectbox("Analizzatore", ["Horiba","EL3000","MRU","FID","Altro"])
        cert_mix = st.text_input("CertMix","")
        cert_o2 = st.text_input("CertO2","")
        pc = st.text_input("PC","")
        laser = st.text_input("Laser","")
        micromanometro = st.text_input("Micromanometro","")
        termocoppia = st.text_input("Termocoppia","")
        darcy = st.text_input("Darcy","")
        kdarcy = st.number_input("KDarcy", value=0.0, step=0.1)

# ===============================
# PRELIEVI E PARAMETRI
# ===============================
PARAMETRI = ["Polveri", "Polveri SiO2", "Acidi", "SOx", "HCl",
             "HF", "Metalli", "CrVI", "NH3", "SO3",
             "Fenolo Formaldeide", "SOV", "Altro"]

nuovi_prelievi = []

if scelta_sezione=="Prelievi":
    num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=50, value=1, key="num_prel_new")

    for i in range(1,int(num_prelievi)+1):
        with st.expander(f"Prelievo {i}", expanded=False):
            col1,col2,col3 = st.columns([2,2,2])
            with col1:
                ugello = st.number_input(f"Ugello {i}", value=0, step=1, key=f"ugello_{i}")
                durata = st.number_input(f"Durata Prelievo {i} (s)", value=0.0, step=0.1, key=f"durata_{i}")
                ora_inizio = st.time_input(f"Ora Inizio {i}", value=datetime.now().time(), key=f"ora_{i}")
                filtro_qma = st.text_input(f"Filtro QMA {i}", value="", key=f"filtro_{i}")
                prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"], index=0, key=f"multi_{i}")
            with col2:
                temperatura = st.number_input(f"Temperatura °C {i}", value=0.0, step=0.1, key=f"temp_{i}")
                pressione = st.number_input(f"Pressione hPa {i}", value=1013.25, step=0.1, key=f"press_{i}")
                umidita = st.number_input(f"Umidità % {i}", value=0.0, step=0.1, key=f"umid_{i}")
                meteo = st.selectbox(f"Meteo {i}", ["","Sereno","Nuvoloso","Pioggia","Vento"], index=0, key=f"meteo_{i}")
            with col3:
                peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}", value=0.0, step=0.01, key=f"pis_{i}")
                peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", value=0.0, step=0.01, key=f"pfs_{i}")
                peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}", value=0.0, step=0.01, key=f"pig_{i}")
                peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", value=0.0, step=0.01, key=f"pfg_{i}")

            # Parametri per prelievo
            num_param = st.number_input(f"Numero di parametri per prelievo {i}", min_value=1, max_value=20, value=1, key=f"num_param_{i}")
            parametri_prelievo = []
            for j in range(1,int(num_param)+1):
                c1,c2,c3,c4 = st.columns([2,1,1,1])
                with c1:
                    parametro = st.selectbox(f"Parametro {j}", PARAMETRI, index=0, key=f"param_{i}_{j}")
                    if parametro=="Altro":
                        altro_parametro = st.text_input(f"Specificare parametro {j}", value="", key=f"altro_{i}_{j}")
                        parametro_finale = altro_parametro
                    else:
                        parametro_finale = parametro
                with c2:
                    volume_iniziale = st.number_input(f"Vol in {j}", value=0.0, step=0.1, key=f"vol_in_{i}_{j}")
                    volume_finale = st.number_input(f"Vol fin {j}", value=0.0, step=0.1, key=f"vol_fin_{i}_{j}")
                with c3:
                    temp_iniziale = st.number_input(f"T in {j}", value=0.0, step=0.1, key=f"temp_in_{i}_{j}")
                    temp_finale = st.number_input(f"T fin {j}", value=0.0, step=0.1, key=f"temp_fin_{i}_{j}")
                with c4:
                    if st.button(f"Calcola VN Prelievo {i} Parametro {j}"):
                        vn = calcola_volume_normalizzato(volume_iniziale, volume_finale, temp_iniziale, temp_finale, pressione)
                        st.success(f"Volume Normalizzato: {vn:.6f}")
                    else:
                        vn = 0.0

                parametri_prelievo.append({
                    "Parametro": parametro_finale,
                    "AltroParametro": (altro_parametro if parametro=="Altro" else ""),
                    "VolumeIniziale": volume_iniziale,
                    "VolumeFinale": volume_finale,
                    "TemperaturaIniziale": temp_iniziale,
                    "TemperaturaFinale": temp_finale,
                    "VolumeNormalizzato": vn,
                    "Pompa": "",
                    "Portata": 0.0,
                    "PesoIniSerpentina": peso_in_serp,
                    "PesoFinSerpentina": peso_fin_serp,
                    "PesoIniGel": peso_in_gel,
                    "PesoFinGel": peso_fin_gel,
                    "UmiditaFumi": 0.0
                })

            # Calcolo umidità per prelievo
            if st.button(f"Calcola Umidità Prelievo {i}"):
                for p in parametri_prelievo:
                    um, vol_acq, vol_tot = calcola_umidita(
                        p["PesoIniSerpentina"], p["PesoFinSerpentina"],
                        p["PesoIniGel"], p["PesoFinGel"], p["VolumeNormalizzato"]
                    )
                    p["UmiditaFumi"] = um
                    st.success(f"Umidità Prelievo {i} Parametro {p['Parametro']}: {um:.2f}%")

            # Raccoglie dati per append
            for idx,param in enumerate(parametri_prelievo):
                row = [
                    SessionID,ditta,stabilimento,date.today().strftime("%d/%m/%Y"),camino,
                    operatore1,operatore2,pressione_statica,velocita_camino,angolo_swirl,
                    diametro_progetto,diametro_misurato,numero_bocchelli,diametri_a_monte,diametri_a_valle,tipo_valle,
                    analizzatore,cert_mix,cert_o2,pc,laser,micromanometro,termocoppia,darcy,kdarcy,
                    i,param.get("Ugello",0),durata,ora_inizio.strftime("%H:%M"),filtro_qma,prelievo_multiplo,
                    temperatura,pressione,umidita,meteo,
                    param["Parametro"],param["AltroParametro"],param["Pompa"],param["Portata"],
                    param["VolumeIniziale"],param["VolumeFinale"],param["TemperaturaIniziale"],param["TemperaturaFinale"],param["VolumeNormalizzato"],
                    param["PesoIniSerpentina"],param["PesoFinSerpentina"],param["PesoIniGel"],param["PesoFinGel"],param["UmiditaFumi"],
                    0,0,0,0,"",0,0,"",datetime.now().strftime("%d/%m/%Y %H:%M")
                ]
                nuovi_prelievi.append(row)

# ===============================
# SALVATAGGIO
# ===============================
if scelta_sezione=="Anteprima e Salvataggio":
    st.subheader("Anteprima dati da salvare")
    df_preview = pd.DataFrame(nuovi_prelievi, columns=HEADER)
    st.dataframe(df_preview)

    if st.button("Salva su Google Sheet"):
        delete_rows_for_session(SessionID)
        append_rows(nuovi_prelievi)
        st.success("Dati salvati correttamente!")
