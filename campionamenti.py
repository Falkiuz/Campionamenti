import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date

# ===============================
# AUTENTICAZIONE GOOGLE SHEETS
# ===============================
creds = Credentials.from_service_account_info(st.secrets["google_service_account"])
client = gspread.authorize(creds)
SHEET_ID = "1lDwKaEz4_TyEX9qCHwbytmHBWvuUOanbBNtBTMpmytg"  # sostituisci con l'ID del foglio
sheet = client.open_by_key(SHEET_ID).sheet1

# ===============================
# FUNZIONI DI SUPPORTO
# ===============================
def carica_dati():
    try:
        records = sheet.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame()
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
        return pd.DataFrame()

def salva_dati(nuovi_dati):
    if isinstance(nuovi_dati, pd.DataFrame) and not nuovi_dati.empty:
        try:
            sheet.append_rows(nuovi_dati.values.tolist(), value_input_option="USER_ENTERED")
        except Exception as e:
            st.error(f"Errore salvataggio dati: {e}")

def calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, press):
    try:
        return (vol_fin - vol_in) * (273.15 / ((temp_in + temp_fin)/2 + 273.15)) * press / 1012.25
    except ZeroDivisionError:
        return 0

# ===============================
# CARICAMENTO DATI ESISTENTI
# ===============================
df = carica_dati()
volume_normalizzati_esistenti = df["VolumeNormalizzato"].dropna().tolist() if "VolumeNormalizzato" in df.columns else []

# ===============================
# TITOLI E SEZIONI PRINCIPALI
# ===============================
st.title("📋 Modulo Campionamenti Ambientali")

# ===============================
# Funzione per input dati generali
# ===============================
def input_dati_generali(df):
    def campo_valore(nome, default=""):
        return st.text_input(nome, value=str(df[nome].iloc[-1]) if nome in df.columns and not df.empty else default)
    
    with st.expander("📂 Dati Generali", expanded=True):
        ditta = campo_valore("Ditta")
        stabilimento = campo_valore("Stabilimento")
        data_campagna = st.date_input("Data", value=date.today())
        camino = campo_valore("Camino")
        operatore1 = campo_valore("Operatore 1")
        operatore2 = campo_valore("Operatore 2")

        # Dati Camino
        st.subheader("Dati Camino")
        pressione_statica = st.number_input("Pressione Statica", step=0.1)
        velocita = st.number_input("Velocità", step=0.1)
        angolo_swirl = st.number_input("Angolo di Swirl", step=0.1)
        diametro_progetto = st.number_input("Diametro Progetto", step=0.1)
        diametro_misurato = st.number_input("Diametro Misurato", step=0.1)
        numero_bocchelli = st.number_input("Numero Bocchelli", step=1)
        diametri_monte = st.number_input("Diametri Monte", step=0.1)
        diametri_valle = st.number_input("Diametri Valle", step=0.1)

        # Dati Strumenti
        st.subheader("Dati Strumenti")
        analizzatore = st.selectbox("Analizzatore", ["Horiba", "EL3000", "MRU", "FID"])
        cert_bombola_mix = st.text_input("Certificato Bombola Mix")
        cert_bombola_o2 = st.text_input("Certificato Bombola O2")
        pc = st.text_input("PC")
        laser = st.text_input("Laser")
        micromanometro = st.text_input("Micromanometro")
        termocoppia = st.text_input("Termocoppia")
        darcy = st.text_input("Darcy")
        kdarcy = st.text_input("KDarcy")

    return {
        "Ditta": ditta,
        "Stabilimento": stabilimento,
        "Data": str(data_campagna),
        "Camino": camino,
        "Operatore 1": operatore1,
        "Operatore 2": operatore2,
        "Pressione Statica": pressione_statica,
        "Velocità": velocita,
        "Angolo Swirl": angolo_swirl,
        "Diametro Progetto": diametro_progetto,
        "Diametro Misurato": diametro_misurato,
        "Numero Bocchelli": numero_bocchelli,
        "Diametri Monte": diametri_monte,
        "Diametri Valle": diametri_valle,
        "Analizzatore": analizzatore,
        "Cert Bombola Mix": cert_bombola_mix,
        "Cert Bombola O2": cert_bombola_o2,
        "PC": pc,
        "Laser": laser,
        "Micromanometro": micromanometro,
        "Termocoppia": termocoppia,
        "Darcy": darcy,
        "KDarcy": kdarcy
    }

dati_generali = input_dati_generali(df)

# ===============================
# Funzione per input singolo prelievo
# ===============================
PARAMETRI = ["Polveri", "Polveri SiO2", "Acidi", "SOx", "HCl",
             "HF", "Metalli", "CrVI", "NH3", "SO3",
             "Fenolo Formaldeide", "SOV", "Altro"]

def input_prelievo(i, volume_normalizzati_esistenti):
    with st.expander(f"Prelievo {i}", expanded=True):
        # Dati Generali Prelievo
        st.markdown("**Dati Generali Prelievo**")
        ugello = st.text_input(f"Ugello {i}", key=f"ugello_{i}")
        durata = st.number_input(f"Durata Prelievo {i} (s)", key=f"durata_{i}")
        ora_inizio = st.time_input(f"Ora Inizio {i}", key=f"ora_{i}")
        filtro_qma = st.text_input(f"Filtro QMA {i}", key=f"filtro_{i}")
        prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"], key=f"multi_{i}")

        # Dati Meteo
        st.markdown("**Dati Meteo**")
        temperatura = st.number_input(f"Temperatura °C {i}", key=f"temp_{i}", step=0.1)
        pressione = st.number_input(f"Pressione hPa {i}", key=f"press_{i}", step=0.1)
        umidita = st.number_input(f"Umidità % {i}", key=f"umid_{i}", step=0.1)
        meteo = st.selectbox(f"Meteo {i}", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"], key=f"meteo_{i}")

        # Parametri multipli
        st.markdown("**Parametri**")
        parametri_scelti = st.multiselect(f"Seleziona Parametri {i}", PARAMETRI, key=f"param_{i}")
        parametri_finali = []
        for p in parametri_scelti:
            if p == "Altro":
                altro_parametro = st.text_input(f"Specificare parametro {i}", key=f"altro_{i}")
                parametri_finali.append(altro_parametro)
            else:
                parametri_finali.append(p)

        # Volumi
        volume_iniziale = st.number_input(f"Volume Iniziale {i}", key=f"vol_in_{i}", step=0.1)
        volume_finale = st.number_input(f"Volume Finale {i}", key=f"vol_fin_{i}", step=0.1)
        temp_iniziale = st.number_input(f"Temperatura Iniziale {i}", key=f"temp_in_{i}", step=0.1)
        temp_finale = st.number_input(f"Temperatura Finale {i}", key=f"temp_fin_{i}", step=0.1)

        calcola_volume = st.checkbox(f"Calcola Volume Normalizzato {i}", value=True, key=f"calc_vol_{i}")
        if calcola_volume:
            volume_normalizzato = calcola_volume_normalizzato(volume_iniziale, volume_finale, temp_iniziale, temp_finale, pressione)
        else:
            if volume_normalizzati_esistenti:
                volume_normalizzato = st.selectbox(f"Scegli Volume Normalizzato dai prelievi precedenti", volume_normalizzati_esistenti, key=f"vol_norm_sel_{i}")
            else:
                volume_normalizzato = st.number_input(f"Volume Normalizzato manuale {i}", key=f"vol_norm_{i}")

        # Umidità Fumi
        st.markdown("**Umidità Fumi**")
        peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}", key=f"pis_{i}", step=0.01)
        peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", key=f"pfs_{i}", step=0.01)
        peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}", key=f"pig_{i}", step=0.01)
        peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", key=f"pfg_{i}", step=0.01)

        volume_h2o = ((peso_fin_serp - peso_in_serp) + (peso_fin_gel - peso_in_gel)) / 18 * 22.414
        volume_totale = volume_h2o + volume_normalizzato
        umidita_fumi = volume_h2o / volume_totale if volume_totale != 0 else 0

        # Medie Campionamento
        st.markdown("**Medie Campionamento**")
        isocinetismo = st.number_input(f"Isocinetismo {i}", key=f"isoc_{i}", step=0.1)
        velocita_media = st.number_input(f"Velocità media {i}", key=f"vel_{i}", step=0.1)
        dp = st.number_input(f"dP {i}", key=f"dp_{i}", step=0.1)
        temp_fumi = st.number_input(f"Temperatura Fumi {i}", key=f"temp_fumi_{i}", step=0.1)

        # Note
        note = st.text_area(f"Note prelievo {i}", key=f"note_{i}")

    return {
        "Parametro": ", ".join(parametri_finali),
        "Ugello": ugello,
        "Durata": durata,
        "OraInizio": str(ora_inizio),
        "FiltroQMA": filtro_qma,
        "PrelievoMultiplo": prelievo_multiplo,
        "Temperatura": temperatura,
        "Pressione": pressione,
        "Umidita": umidita,
        "Meteo": meteo,
        "VolumeIniziale": volume_iniziale,
        "VolumeFinale": volume_finale,
        "TemperaturaIniziale": temp_iniziale,
        "TemperaturaFinale": temp_finale,
        "VolumeNormalizzato": volume_normalizzato,
        "UmiditaFumi": umidita_fumi,
        "Isocinetismo": isocinetismo,
        "VelocitaMedia": velocita_media,
        "dP": dp,
        "TemperaturaFumi": temp_fumi,
        "Note": note
    }

# ===============================
# PRELIEVI
# ===============================
st.header("Prelievi")
num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=20, value=1)

# Inizializza session_state se non esiste
if "prelievi" not in st.session_state:
    st.session_state.prelievi = [{} for _ in range(num_prelievi)]

nuovi_prelievi = []
for i in range(1, num_prelievi + 1):
    prelievo = input_prelievo(i, volume_normalizzati_esistenti)
    st.session_state.prelievi[i-1] = prelievo
    # Unisci dati generali + prelievo
    dati_completi = {**dati_generali, **prelievo}
    nuovi_prelievi.append(dati_completi)

# --- Pulsante Salva ---
if st.button("💾 Salva Prelievi"):
    df_nuovo = pd.DataFrame(nuovi_prelievi)
    salva_dati(df_nuovo)
    st.success("✅ Prelievi salvati correttamente su Google Sheets!")
