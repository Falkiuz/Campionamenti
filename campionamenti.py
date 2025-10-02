import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date

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
# FUNZIONI DI SUPPORTO
# ===============================
def carica_dati():
    records = sheet.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame()

def salva_dati(nuovi_dati):
    if isinstance(nuovi_dati, pd.DataFrame) and not nuovi_dati.empty:
        sheet.append_rows(nuovi_dati.values.tolist(), value_input_option="USER_ENTERED")

df = carica_dati()

# ===============================
# TITOLI E SEZIONI PRINCIPALI
# ===============================
st.title("📋 Modulo Campionamenti Ambientali")

# --- Dati Generali ---
with st.expander("📂 Dati Generali", expanded=True):
    def campo_valore(nome, default=""):
        return st.text_input(nome, value=str(df[nome].iloc[-1]) if nome in df.columns and not df.empty else default)

    ditta = campo_valore("Ditta")
    stabilimento = campo_valore("Stabilimento")
    data_campagna = st.date_input("Data", value=date.today())
    camino = campo_valore("Camino")
    operatore1 = campo_valore("Operatore 1")
    operatore2 = campo_valore("Operatore 2")

# ===============================
# PRELIEVI
# ===============================
st.header("Prelievi")
num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=20, value=1)

PARAMETRI = ["Polveri", "Polveri SiO2", "Acidi", "SOx", "HCl",
             "HF", "Metalli", "CrVI", "NH3", "SO3",
             "Fenolo Formaldeide", "SOV", "Altro"]

nuovi_prelievi = []

for i in range(1, num_prelievi + 1):
    with st.expander(f"Prelievo {i}", expanded=True):
        # --- Dati Generali Prelievo ---
        ugello = st.text_input(f"Ugello {i}", key=f"ugello_{i}")
        durata = st.number_input(f"Durata Prelievo {i} (s)", key=f"durata_{i}")
        ora_inizio = st.time_input(f"Ora Inizio {i}", key=f"ora_{i}")
        filtro_qma = st.text_input(f"Filtro QMA {i}", key=f"filtro_{i}")
        prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO", "SI"], key=f"multi_{i}")

        # --- Dati Meteo ---
        temperatura = st.number_input(f"Temperatura °C {i}", key=f"temp_{i}", step=0.1)
        pressione = st.number_input(f"Pressione hPa {i}", key=f"press_{i}", step=0.1)
        umidita = st.number_input(f"Umidità % {i}", key=f"umid_{i}", step=0.1)
        meteo = st.selectbox(f"Meteo {i}", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"], key=f"meteo_{i}")

        # --- Parametri multipli ---
        st.markdown("**Parametri Prelievo**")
        parametri_prelievo = []
        num_param = st.number_input(f"Numero di parametri per prelievo {i}", min_value=1, max_value=20, value=1, key=f"num_param_{i}")
        for j in range(1, num_param + 1):
            with st.expander(f"Parametro {j} del Prelievo {i}", expanded=True):
                parametro = st.selectbox(f"Parametro {j}", PARAMETRI, key=f"param_{i}_{j}")
                if parametro == "Altro":
                    parametro = st.text_input(f"Specificare parametro {j}", key=f"altro_{i}_{j}")
                volume_iniziale = st.number_input(f"Volume Iniziale {j}", key=f"vol_in_{i}_{j}", step=0.1)
                volume_finale = st.number_input(f"Volume Finale {j}", key=f"vol_fin_{i}_{j}", step=0.1)
                temp_iniziale = st.number_input(f"Temperatura Iniziale {j}", key=f"temp_in_{i}_{j}", step=0.1)
                temp_finale = st.number_input(f"Temperatura Finale {j}", key=f"temp_fin_{i}_{j}", step=0.1)

                calcola_volume = st.checkbox(f"Calcola Volume Normalizzato {j}", value=True, key=f"calc_vol_{i}_{j}")
                if calcola_volume:
                    volume_normalizzato = (volume_finale - volume_iniziale) * (273.15 / ((temp_iniziale + temp_finale)/2 + 273.15)) * pressione/1013.25
                else:
                    volume_normalizzato = st.number_input(f"Volume Normalizzato manuale {j}", key=f"vol_norm_{i}_{j}")

                parametri_prelievo.append({
                    "Parametro": parametro,
                    "VolumeIniziale": volume_iniziale,
                    "VolumeFinale": volume_finale,
                    "TemperaturaIniziale": temp_iniziale,
                    "TemperaturaFinale": temp_finale,
                    "VolumeNormalizzato": volume_normalizzato
                })

        # --- Umidità fumi ---
        st.markdown("**Umidità Fumi**")
        peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}", key=f"pis_{i}", step=0.01)
        peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", key=f"pfs_{i}", step=0.01)
        peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}", key=f"pig_{i}", step=0.01)
        peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", key=f"pfg_{i}", step=0.01)

        volume_h2o = ((peso_fin_serp - peso_in_serp) + (peso_fin_gel - peso_in_gel)) / 18 * 22.414
        volume_totale = volume_h2o + max([p["VolumeNormalizzato"] for p in parametri_prelievo])
        umidita_fumi = volume_h2o / volume_totale if volume_totale != 0 else 0

        # --- Medie Campionamento ---
        st.markdown("**Medie Campionamento**")
        isocinetismo = st.number_input(f"Isocinetismo {i}", key=f"isoc_{i}", step=0.1)
        velocita_media = st.number_input(f"Velocità media {i}", key=f"vel_{i}", step=0.1)
        dp = st.number_input(f"dP {i}", key=f"dp_{i}", step=0.1)
        temp_fumi = st.number_input(f"Temperatura Fumi {i}", key=f"temp_fumi_{i}", step=0.1)

        # --- Note ---
        note = st.text_area(f"Note prelievo {i}", key=f"note_{i}")

        # --- Salva dati prelievo in lista ---
        nuovi_prelievi.append({
            "Ditta": ditta,
            "Stabilimento": stabilimento,
            "DataCampagna": data_campagna.isoformat(),
            "Camino": camino,
            "Operatore1": operatore1,
            "Operatore2": operatore2,
            "Ugello": ugello,
            "Durata": durata,
            "OraInizio": ora_inizio.strftime("%H:%M"),
            "FiltroQMA": filtro_qma,
            "PrelievoMultiplo": prelievo_multiplo,
            "Temperatura": temperatura,
            "Pressione": pressione,
            "Umidità": umidita,
            "Meteo": meteo,
            "Parametri": parametri_prelievo,
            "PesoInSerp": peso_in_serp,
            "PesoFinSerp": peso_fin_serp,
            "PesoInGel": peso_in_gel,
            "PesoFinGel": peso_fin_gel,
            "VolumeH2O": volume_h2o,
            "UmiditaFumi": umidita_fumi,
            "Isocinetismo": isocinetismo,
            "VelocitàMedia": velocita_media,
            "dP": dp,
            "TempFumi": temp_fumi,
            "Note": note
        })

# ===============================
# PULSANTE SALVATAGGIO
# ===============================
if st.button("💾 Salva Campionamenti"):
    df_nuovi = pd.DataFrame(nuovi_prelievi)
    salva_dati(df_nuovi)
    st.success("Dati salvati correttamente su Google Sheets!")
