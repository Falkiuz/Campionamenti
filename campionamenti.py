import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
import time
import uuid

# ===============================
# AUTENTICAZIONE GOOGLE SHEETS
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)
SHEET_ID = "1KCPltH_8EtI5svqRivdwI68DWJ6eE1IK3UDe45PENf8"

def open_sheet_with_retry(sheet_id, retries=5, delay=2):
    for attempt in range(retries):
        try:
            return client.open_by_key(sheet_id).sheet1
        except APIError as e:
            st.warning(f"Errore API (tentativo {attempt+1}/{retries}): {e}")
            time.sleep(delay)
    st.error("Impossibile aprire il foglio. Riprova più tardi.")
    return None

sheet = open_sheet_with_retry(SHEET_ID)
if sheet is None:
    st.stop()

# ===============================
# FUNZIONI UTILI
# ===============================
def read_existing_data(sheet):
    """Legge i dati esistenti dal foglio in un DataFrame"""
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_smart(df, session_id):
    """
    Salvataggio intelligente: cancella righe esistenti della SessionID
    e scrive le nuove righe.
    """
    all_data = read_existing_data(sheet)
    all_data = all_data[all_data['SessionID'] != session_id]  # elimina vecchie righe
    df_to_save = pd.concat([all_data, df], ignore_index=True)

    # Pulisce foglio
    sheet.clear()
    sheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())

def calculate_normalized_volume(volume, temperature_ini, temperature_fin, pressure, selected_volume):
    """Calcolo volume normalizzato considerando pressione ambiente"""
    V_norm = selected_volume * (pressure / 1013.25)
    return V_norm

# ===============================
# INTERFACCIA STREAMLIT
# ===============================
st.title("Modulo Campionamenti")

# Richiama SessionID
existing_data = read_existing_data(sheet)
session_options = ["Nuova"] + existing_data['SessionID'].unique().tolist()
session_choice = st.selectbox("Seleziona SessionID o nuova", session_options)

if session_choice == "Nuova":
    session_id = str(uuid.uuid4())
    prefill_data = {}
else:
    session_id = session_choice
    prefill_data = existing_data[existing_data['SessionID'] == session_id].iloc[0].to_dict()

# ===============================
# Dati generali
# ===============================
st.header("Dati generali")
ditta = st.text_input("Ditta", value=prefill_data.get("Ditta",""))
stabilimento = st.text_input("Stabilimento", value=prefill_data.get("Stabilimento",""))
data_campionamento = st.date_input("Data", value=prefill_data.get("Data", pd.Timestamp.today()))
pressione_ambiente = st.number_input("Pressione ambiente [hPa]", value=prefill_data.get("Pressione", 1013.25))

# ===============================
# Inserimento prelievi e parametri
# ===============================
num_prelievi = st.number_input("Numero prelievi", min_value=1, max_value=18, value=1, step=1)
parametri = []

for i in range(int(num_prelievi)):
    st.subheader(f"Prelievo {i+1}")
    param_nome = st.text_input(f"Parametro {i+1}", value=prefill_data.get("Parametro",""))
    volume_ini = st.number_input(f"Volume iniziale {param_nome}", value=prefill_data.get("VolumeIniziale",0.0))
    volume_fin = st.number_input(f"Volume finale {param_nome}", value=prefill_data.get("VolumeFinale",0.0))
    temp_ini = st.number_input(f"Temperatura iniziale {param_nome}", value=prefill_data.get("TemperaturaIniziale",0.0))
    temp_fin = st.number_input(f"Temperatura finale {param_nome}", value=prefill_data.get("TemperaturaFinale",0.0))
    selected_volume = st.number_input(f"Volume normalizzato selezionato {param_nome}", value=prefill_data.get("VolumeNormalizzato",0.0))

    vol_norm = calculate_normalized_volume(volume_fin, temp_ini, temp_fin, pressione_ambiente, selected_volume)
    st.write(f"Volume normalizzato calcolato: {vol_norm:.2f}")

    parametri.append({
        "SessionID": session_id,
        "Ditta": ditta,
        "Stabilimento": stabilimento,
        "Data": data_campionamento,
        "Parametro": param_nome,
        "VolumeIniziale": volume_ini,
        "VolumeFinale": volume_fin,
        "TemperaturaIniziale": temp_ini,
        "TemperaturaFinale": temp_fin,
        "VolumeNormalizzato": vol_norm,
        "Pressione": pressione_ambiente
    })

# ===============================
# Tabella riepilogo prima del salvataggio
# ===============================
st.subheader("Riepilogo parametri")
df_params = pd.DataFrame(parametri)
st.dataframe(df_params)

# ===============================
# Salvataggio su Google Sheets
# ===============================
if st.button("Salva su Google Sheets"):
    save_smart(df_params, session_id)
    st.success("Dati salvati correttamente!")
