# campionamenti_streamlit_finale.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date

st.set_page_config(layout="wide")

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
st.title("📋 Modulo Campionamenti Ambientali — Versione finale ottimizzata")

# ===============================
# SESSION SELECT / CREATE
# ===============================
# Per le sessioni esistenti leggeremo dal foglio solo al salvataggio per evitare troppe chiamate
session_ids_display = ["➕ Nuova sessione"]
selected_session = st.selectbox("Seleziona SessionID o crea nuova sessione", session_ids_display)

if selected_session == "➕ Nuova sessione":
    if "current_session" not in st.session_state or not st.session_state.get("current_session_is_new", False):
        st.session_state.current_session = datetime.now().strftime("%Y%m%d%H%M%S")
        st.session_state.current_session_is_new = True
else:
    st.session_state.current_session = selected_session
    st.session_state.current_session_is_new = False

SessionID = st.session_state.current_session
st.markdown(f"**SessionID corrente:** `{SessionID}`")

# ===============================
# DATI GENERALI SESSIONE
# ===============================
with st.expander("📂 Dati Generali Sessione", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        ditta = st.text_input("Ditta")
        stabilimento = st.text_input("Stabilimento")
        data_campagna = st.date_input("Data campagna", value=date.today())
        camino = st.text_input("Camino")
    with col2:
        operatore1 = st.text_input("Operatore 1")
        operatore2 = st.text_input("Operatore 2")
        pressione_statica = st.number_input("Pressione Statica", value=0.0, step=0.1)
        velocita_camino = st.number_input("Velocità Camino", value=0.0, step=0.1)

# ===============================
# NUMERO PRELIEVI
# ===============================
num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=50, value=1, key="num_prel")

# ===============================
# PARAMETRI DISPONIBILI
# ===============================
PARAMETRI = ["Polveri","Polveri SiO2","Acidi","SOx","HCl",
             "HF","Metalli","CrVI","NH3","SO3",
             "Fenolo Formaldeide","SOV","Altro"]

# ===============================
# RACCOLTA DATI PRELIEVI
# ===============================
nuovi_prelievi = []

for i in range(1, int(num_prelievi)+1):
    with st.expander(f"Prelievo {i}", expanded=False):
        col1, col2, col3 = st.columns([2,2,2])
        with col1:
            ugello = st.text_input(f"Ugello {i}")
            durata = st.number_input(f"Durata Prelievo {i} (s)", value=0.0, step=0.1)
            ora_inizio = st.time_input(f"Ora Inizio {i}", value=datetime.now().time())
            filtro_qma = st.text_input(f"Filtro QMA {i}")
            prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"], index=0)
        with col2:
            temperatura = st.number_input(f"Temperatura °C {i}", value=0.0, step=0.1)
            pressione = st.number_input(f"Pressione hPa {i}", value=1013.25, step=0.1)
            umidita = st.number_input(f"Umidità % {i}", value=0.0, step=0.1)
            meteo = st.selectbox(f"Meteo {i}", ["","Sereno","Nuvoloso","Pioggia","Vento"], index=0)
        with col3:
            peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}", value=0.0, step=0.01)
            peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", value=0.0, step=0.01)
            peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}", value=0.0, step=0.01)
            peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", value=0.0, step=0.01)

        # numero parametri per prelievo
        num_param = st.number_input(f"Numero di parametri per prelievo {i}", min_value=1, max_value=20, value=1, key=f"num_param_{i}")
        parametri_prelievo = []

        for j in range(1, int(num_param)+1):
            c1, c2, c3, c4 = st.columns([2,1,1,1])
            with c1:
                parametro = st.selectbox(f"Parametro {j}", PARAMETRI)
                if parametro == "Altro":
                    altro_parametro = st.text_input(f"Specificare parametro {j}")
                    parametro_finale = altro_parametro
                else:
                    parametro_finale = parametro
            with c2:
                volume_iniziale = st.number_input(f"Vol in {j}", value=0.0, step=0.1)
                volume_finale = st.number_input(f"Vol fin {j}", value=0.0, step=0.1)
            with c3:
                temp_iniziale = st.number_input(f"T in {j}", value=0.0, step=0.1)
                temp_finale = st.number_input(f"T fin {j}", value=0.0, step=0.1)
            with c4:
                vn = calcola_volume_normalizzato(volume_iniziale, volume_finale, temp_iniziale, temp_finale, pressione)
                st.markdown(f"**VN:** `{vn:.6f}`")

            parametri_prelievo.append({
                "Parametro": parametro_finale,
                "AltroParametro": (altro_parametro if parametro=="Altro" else ""),
                "VolumeIniziale": volume_iniziale,
                "VolumeFinale": volume_finale,
                "TemperaturaIniziale": temp_iniziale,
                "TemperaturaFinale": temp_finale,
                "VolumeNormalizzato": float(f"{vn:.6f}")
            })

        # scelta VN per calcolo umidità fumi
        vol_choices = [p["VolumeNormalizzato"] for p in parametri_prelievo]
        vol_choice_idx = st.selectbox(
            "Scegli quale Volume Normalizzato usare per il calcolo dell'umidità",
            options=list(range(len(vol_choices))),
            format_func=lambda x: f"Parametro {x+1} - VN={vol_choices[x]:.6f}"
        )
        vol_scelto = float(vol_choices[vol_choice_idx])

        volume_h2o = ((peso_fin_serp - peso_in_serp) + (peso_fin_gel - peso_in_gel)) / 18 * 22.414
        volume_totale = volume_h2o + vol_scelto
        umidita_fumi = (volume_h2o / volume_totale) if volume_totale != 0 else 0.0

        st.info(f"Volume H2O: {volume_h2o:.4f} — Volume scelto: {vol_scelto:.6f} — Volume Totale: {volume_totale:.4f}")
        st.info(f"Umidità fumi (calcolata): {umidita_fumi:.6f}")

        # altri parametri
        isocinetismo = st.number_input(f"Isocinetismo {i}", value=0.0, step=0.1)
        velocita_media = st.number_input(f"Velocità media {i}", value=0.0, step=0.1)
        dp = st.number_input(f"dP {i}", value=0.0, step=0.1)
        temp_fumi = st.number_input(f"Temperatura Fumi {i}", value=0.0, step=0.1)
        note = st.text_area(f"Note prelievo {i}")

        # aggiungo righe
        for p in parametri_prelievo:
            row = {
                "SessionID": SessionID,
                "Ditta": ditta,
                "Stabilimento": stabilimento,
                "Data": data_campagna.isoformat(),
                "Camino": camino,
                "Operatore1": operatore1,
                "Operatore2": operatore2,
                "PressioneStatica": pressione_statica,
                "VelocitàCamino": velocita_camino,
                "AngoloDiSwirl": "",
                "DiametroProgetto": "",
                "DiametroMisurato": "",
                "NumeroBocchelli": "",
                "DiametriAMonte": "",
                "DiametriAValle": "",
                "TipoValle": "",
                "Analizzatore": "",
                "CertMix": "",
                "CertO2": "",
                "PC": "",
                "Laser": "",
                "Micromanometro": "",
                "Termocoppia": "",
                "Darcy": "",
                "KDarcy": "",
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
                "Portata": "",
                "VolumeIniziale": p["VolumeIniziale"],
                "VolumeFinale": p["VolumeFinale"],
                "TemperaturaIniziale": p["TemperaturaIniziale"],
                "TemperaturaFinale": p["TemperaturaFinale"],
                "VolumeNormalizzato": p["VolumeNormalizzato"],
                "PesoIniSerpentina": peso_in_serp,
                "PesoFinSerpentina": peso_fin_serp,
                "PesoIniGel": peso_in_gel,
                "PesoFinGel": peso_fin_gel,
                "UmiditaFumi": umidita_fumi,
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
# PULSANTE SALVA
# ===============================
if st.button("💾 Salva campionamenti"):
    if not nuovi_prelievi:
        st.warning("Nessun dato da salvare.")
    else:
        try:
            # --- connessione a Google Sheets SOLO qui ---
            SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
            SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
            creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
            client = gspread.authorize(creds)
            SHEET_ID = "1KCPltH_8EtI5svqRivdwI68DWJ6eE1IK3UDe45PENf8"
            sheet = client.open_by_key(SHEET_ID).sheet1

            # elimina righe vecchie
            all_vals = sheet.get_all_values()
            rows_to_delete = [idx+2 for idx, r in enumerate(all_vals[1:]) if r[0] == SessionID]
            for r in sorted(rows_to_delete, reverse=True):
                sheet.delete_rows(r)

            # append nuove righe
            rows_to_append = [[r.get(col,"") for col in HEADER] for r in nuovi_prelievi]
            sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
            st.success("Dati salvati correttamente su Google Sheets!")
        except Exception as e:
            st.error(f"Errore durante il salvataggio: {e}")
