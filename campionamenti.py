import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from time import sleep

# ===============================
# AUTENTICAZIONE GOOGLE SHEETS
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID = "1KCPltH_8EtI5svqRivdwI68DWJ6eE1IK3UDe45PENf8"

# ===============================
# FUNZIONE RETRY PER GSPREAD
# ===============================
def open_sheet_with_retry(sheet_id, max_retries=3, wait_sec=2):
    for attempt in range(max_retries):
        try:
            return client.open_by_key(sheet_id).sheet1
        except gspread.exceptions.APIError as e:
            if attempt < max_retries - 1:
                sleep(wait_sec)
            else:
                raise e

sheet = open_sheet_with_retry(SHEET_ID)

# ===============================
# CARICAMENTO DATI ESISTENTI
# ===============================
records = sheet.get_all_records()
expected_columns = ["SessionID","Ditta","Stabilimento","Data","Camino","Operatore1","Operatore2",
                    "PressioneStatica","VelocitàCamino","AngoloDiSwirl","DiametroProgetto",
                    "DiametroMisurato","NumeroBocchelli","DiametriAMonte","DiametriAValle","TipoValle",
                    "Analizzatore","CertMix","CertO2","PC","Laser","Micromanometro","Termocoppia",
                    "Darcy","KDarcy","PrelievoN","Ugello","DurataPrelievo","OraInizio","FiltroQMA",
                    "PrelievoMultiplo","Temperatura","Pressione","Umidita","Meteo","Parametro",
                    "AltroParametro","Pompa","Portata","VolumeIniziale","VolumeFinale",
                    "TemperaturaIniziale","TemperaturaFinale","VolumeNormalizzato",
                    "PesoIniSerpentina","PesoFinSerpentina","PesoIniGel","PesoFinGel","UmiditaFumi",
                    "Isocinetismo","VelocitàCampionamento","dP","TemperaturaFumi","Note",
                    "Asse1_JSON","Asse2_JSON"]

if len(records) == 0:
    existing_data = pd.DataFrame(columns=expected_columns)
else:
    existing_data = pd.DataFrame(records)
    for col in expected_columns:
        if col not in existing_data.columns:
            existing_data[col] = ""

# ===============================
# MENU SESSIONID
# ===============================
session_options = ["Nuova"] + existing_data['SessionID'].unique().tolist() if 'SessionID' in existing_data.columns else ["Nuova"]
selected_session = st.selectbox("Seleziona SessionID", session_options)

# ===============================
# MODULO CAMPIONAMENTO
# ===============================
st.header("Modulo Campionamenti")

# Seleziona dati principali se SessionID esiste
if selected_session != "Nuova":
    prelievo_data = existing_data[existing_data['SessionID'] == selected_session].copy()
else:
    prelievo_data = pd.DataFrame(columns=expected_columns)

# Mostra campi principali
ditta = st.text_input("Ditta", prelievo_data['Ditta'].iloc[0] if not prelievo_data.empty else "")
stabilimento = st.text_input("Stabilimento", prelievo_data['Stabilimento'].iloc[0] if not prelievo_data.empty else "")
data = st.date_input("Data")
camino = st.text_input("Camino")

# Parametri multipli
num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=18, value=1, step=1)
parametri_list = []

for i in range(int(num_prelievi)):
    st.subheader(f"Prelievo {i+1}")
    param_nome = st.text_input(f"Parametro Prelievo {i+1}")
    altro_param = st.text_input(f"Altro Parametro {i+1}")
    temp_ini = st.number_input(f"Temperatura Iniziale {i+1}", value=0.0)
    temp_fin = st.number_input(f"Temperatura Finale {i+1}", value=0.0)
    vol_ini = st.number_input(f"Volume Iniziale {i+1}", value=0.0)
    vol_fin = st.number_input(f"Volume Finale {i+1}", value=0.0)
    press_atm = st.number_input(f"Pressione Atmosferica hPa {i+1}", value=1013.25)
    
    vol_norm = (vol_fin - vol_ini) * (press_atm / 1013.25)  # Normalizzazione pressione
    parametri_list.append({
        "Parametro": param_nome,
        "AltroParametro": altro_param,
        "TemperaturaIniziale": temp_ini,
        "TemperaturaFinale": temp_fin,
        "VolumeIniziale": vol_ini,
        "VolumeFinale": vol_fin,
        "VolumeNormalizzato": vol_norm,
        "Pressione": press_atm
    })

# ===============================
# VISTA RIEPILOGO
# ===============================
st.subheader("Riepilogo Parametri Prelievo")
df_prelievi = pd.DataFrame(parametri_list)
st.dataframe(df_prelievi)

# ===============================
# SALVATAGGIO INTELLIGENTE
# ===============================
if st.button("Salva su Google Sheets"):
    # Rimuove righe esistenti per la SessionID selezionata
    if selected_session != "Nuova":
        to_keep = existing_data[existing_data['SessionID'] != selected_session]
    else:
        to_keep = existing_data

    # Assegna nuova SessionID se è Nuova
    import uuid
    session_id = selected_session if selected_session != "Nuova" else str(uuid.uuid4())

    # Crea righe da salvare
    rows_to_save = []
    for idx, r in df_prelievi.iterrows():
        row = {col: "" for col in expected_columns}
        row.update({
            "SessionID": session_id,
            "Ditta": ditta,
            "Stabilimento": stabilimento,
            "Data": str(data),
            "Camino": camino,
            "Parametro": r["Parametro"],
            "AltroParametro": r["AltroParametro"],
            "TemperaturaIniziale": r["TemperaturaIniziale"],
            "TemperaturaFinale": r["TemperaturaFinale"],
            "VolumeIniziale": r["VolumeIniziale"],
            "VolumeFinale": r["VolumeFinale"],
            "VolumeNormalizzato": r["VolumeNormalizzato"],
            "Pressione": r["Pressione"]
        })
        rows_to_save.append([row[c] for c in expected_columns])

    # Appendi sul foglio
    sheet.append_rows(rows_to_save)
    st.success(f"Dati salvati correttamente con SessionID: {session_id}")
