import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import uuid
from datetime import datetime, date, time
import io

# ===============================
# AUTENTICAZIONE GOOGLE SHEETS
# ===============================
creds = Credentials.from_service_account_info(st.secrets["google_service_account"])
client = gspread.authorize(creds)
SHEET_NAME = "1lDwKaEz4_TyEX9qCHwbytmHBWvuUOanbBNtBTMpmytg"
sheet = client.open(SHEET_NAME).sheet1

# ===============================
# FUNZIONI DI SUPPORTO
# ===============================
def get_all_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

def append_row(data: dict):
    sheet.append_row(list(data.values()))

# ===============================
# STREAMLIT APP
# ===============================
st.title("📋 Gestione Campionamenti Ambientali")

# Carico dati esistenti
df = get_all_data()
session_ids = df["SessionID"].unique().tolist() if not df.empty else []

# ---- MENU INIZIALE ----
st.sidebar.header("Selezione campagna")
mode = st.sidebar.radio("Nuova campagna o Riprendi?", ["Nuova campagna", "Riprendi campagna"])

if mode == "Nuova campagna":
    ditta = st.text_input("Ditta")
    stabilimento = st.text_input("Stabilimento")
    data_campagna = st.date_input("Data", value=date.today())

    if st.button("Crea nuova campagna"):
        session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        st.session_state.update({
            "session_id": session_id,
            "ditta": ditta,
            "stabilimento": stabilimento,
            "data": str(data_campagna)
        })
        st.success(f"Nuova campagna creata: {session_id}")

elif mode == "Riprendi campagna":
    if session_ids:
        chosen_id = st.selectbox("Seleziona campagna", session_ids)
        st.session_state["session_id"] = chosen_id
        row = df[df["SessionID"] == chosen_id].iloc[0]
        st.session_state["ditta"] = row["Ditta"]
        st.session_state["stabilimento"] = row["Stabilimento"]
        st.session_state["data"] = row["Data"]
        st.info(f"Campagna caricata: {chosen_id}")
    else:
        st.warning("Non ci sono campagne salvate.")

# ---- INSERIMENTO DATI ----
if "session_id" in st.session_state:
    st.subheader(f"Campagna attiva: {st.session_state['session_id']}")

    # ===============================
    # Dati Camino
    # ===============================
    st.header("Dati Camino")
    pressione_statica = st.number_input("Pressione Statica (Pa)")
    velocita = st.number_input("Velocità (m/s)")
    angolo_swirl = st.number_input("Angolo di Swirl (°)")
    diametro_progetto = st.number_input("Diametro Progetto (mm)")
    diametro_misurato = st.number_input("Diametro Misurato (mm)")
    numero_bocchelli = st.number_input("Numero Bocchelli", min_value=1)
    diametri_a_monte = st.number_input("Diametri Idraulici a Monte")
    diametri_a_valle = st.number_input("Diametri Idraulici a Valle")

    # ===============================
    # Dati Strumenti
    # ===============================
    st.header("Dati Strumenti")
    analizzatore = st.selectbox("Analizzatore", ["Horiba", "EL3000", "MRU", "FID"])
    certificato_mix = st.text_input("Certificato Bombola Mix")
    certificato_o2 = st.text_input("Certificato Bombola O2")
    pc = st.text_input("PC")
    laser = st.text_input("Laser")
    micromanometro = st.text_input("Micromanometro")
    termocoppia = st.text_input("Termocoppia")
    darcy = st.text_input("Darcy")
    k_darcy = st.text_input("K Darcy")

    # ===============================
    # Nuovo Prelievo
    # ===============================
    st.header("Nuovo Prelievo")
    prelievo_n = st.number_input("Numero Prelievo", min_value=1, step=1)

    # DatiGeneraliPrelievo
    ugello = st.text_input("Ugello")
    durata = st.number_input("Durata Prelievo (min)")
    ora_inizio = st.time_input("Ora Inizio", value=time(8,0))
    filtro_qma = st.text_input("Filtro QMA")
    multiplo = st.radio("Prelievo Multiplo?", ["Si", "No"])

    # Dati Meteo
    temperatura = st.number_input("Temperatura aria (°C)")
    pressione = st.number_input("Pressione atmosferica (hPa)")
    umidita = st.number_input("Umidità (%)")

    # ===============================
    # Dati Prelievo - Parametri
    # ===============================
    st.subheader("Parametri")
    param_list = ["Polveri", "Polveri SiO2", "Acidi", "SOx", "HCl", "HF", "Metalli", "CrVI", "NH3", "SO3",
                  "Fenolo Formaldeide", "SOV", "Altro"]
    num_param = st.number_input("Numero parametri", min_value=1, max_value=6, value=1)
    parametri = []
    for i in range(num_param):
        st.markdown(f"**Parametro {i+1}**")
        parametro = st.selectbox(f"Seleziona parametro {i+1}", param_list, key=f"param_{i}")
        if parametro == "Altro":
            parametro = st.text_input(f"Specificare parametro {i+1}", key=f"altro_{i}")
        pompa = st.text_input(f"Pompa {i+1}", key=f"pompa_{i}")
        volume_iniziale = st.number_input(f"Volume Iniziale {i+1}", key=f"vol_in_{i}")
        volume_finale = st.number_input(f"Volume Finale {i+1}", key=f"vol_fin_{i}")
        temp_iniziale = st.number_input(f"Temperatura Iniziale {i+1}", key=f"temp_in_{i}")
        temp_finale = st.number_input(f"Temperatura Finale {i+1}", key=f"temp_fin_{i}")

        calcola_volume = st.checkbox(f"Calcola Volume Normalizzato {i+1}", value=True, key=f"calcola_vol_{i}")
        if calcola_volume:
            volume_normalizzato = (volume_finale - volume_iniziale) * (273.15 / ((temp_iniziale + temp_finale)/2 + 273.15)) * pressione / 1012.25
        else:
            volume_normalizzato = st.number_input(f"Inserisci Volume Normalizzato {i+1}", key=f"vol_norm_{i}")

        parametri.append({
            "Parametro": parametro,
            "Pompa": pompa,
            "VolumeIniziale": volume_iniziale,
            "VolumeFinale": volume_finale,
            "TemperaturaIniziale": temp_iniziale,
            "TemperaturaFinale": temp_finale,
            "VolumeNormalizzato": volume_normalizzato
        })

    # ===============================
    # Umidità prelievo
    # ===============================
    st.subheader("Umidità")
    peso_ini_serp = st.number_input("Peso Iniziale Serpentina")
    peso_fin_serp = st.number_input("Peso Finale Serpentina")
    peso_ini_gel = st.number_input("Peso Iniziale Gel")
    peso_fin_gel = st.number_input("Peso Finale Gel")

    volume_h2o = ((peso_fin_serp - peso_ini_serp) + (peso_fin_gel - peso_ini_gel))/18*22.414
    volume_totale = volume_h2o + max([p["VolumeNormalizzato"] for p in parametri])
    umidita_fumi = volume_h2o / volume_totale

    # ===============================
    # Medie Campionamento
    # ===============================
    st.subheader("Medie Campionamento")
    isocinetismo = st.number_input("Isocinetismo")
    velocita_fumi = st.number_input("Velocità Fumi")
    dp = st.number_input("dP")
    temp_fumi = st.number_input("Temperatura Fumi")

    # ===============================
    # Note
    # ===============================
    st.subheader("Note")
    note = st.text_area("Note aggiuntive")

    # ===============================
    # SALVATAGGIO
    # ===============================
    if st.button("Salva Prelievo"):
        for p in parametri:
            new_row = {
                "SessionID": st.session_state["session_id"],
                "Ditta": st.session_state["ditta"],
                "Stabilimento": st.session_state["stabilimento"],
                "Data": st.session_state["data"],
                "PrelievoN": prelievo_n,
                **p,
                "PesoInizialeSerp": peso_ini_serp,
                "PesoFinaleSerp": peso_fin_serp,
                "PesoInizialeGel": peso_ini_gel,
                "PesoFinaleGel": peso_fin_gel,
                "UmiditaFumi": umidita_fumi,
                "Isocinetismo": isocinetismo,
                "VelocitaFumi": velocita_fumi,
                "dP": dp,
                "TempFumi": temp_fumi,
                "Note": note,
                "PressioneStatica": pressione_statica,
                "VelocitaCamino": velocita,
                "AngoloDiSwirl": angolo_swirl,
                "DiametroProgetto": diametro_progetto,
                "DiametroMisurato": diametro_misurato,
                "NumeroBocchelli": numero_bocchelli,
                "DiametriAMonte": diametri_a_monte,
                "DiametriAValle": diametri_a_valle,
                "Analizzatore": analizzatore,
                "CertMix": certificato_mix,
                "CertO2": certificato_o2,
                "PC": pc,
                "Laser": laser,
                "Micromanometro": micromanometro,
                "Termocoppia": termocoppia,
                "Darcy": darcy,
                "KDarcy": k_darcy,
                "TempAria": temperatura,
                "PressioneAtm": pressione,
                "Umidita": umidita,
                "Ugello": ugello,
                "DurataPrelievo": durata,
                "OraInizio": str(ora_inizio),
                "FiltroQMA": filtro_qma,
                "PrelievoMultiplo": multiplo
            }
            append_row(new_row)
        st.success("Prelievo salvato su Google Sheets ✅")

    # ===============================
    # Visualizzazione dati campagna
    # ===============================
    st.subheader("Dati salvati per questa campagna")
    df = get_all_data()
    df_campagna = df[df["SessionID"] == st.session_state["session_id"]]
    st.dataframe(df_campagna)

    # ===============================
    # MODIFICA PRELIEVI
    # ===============================
    st.subheader("Modifica prelievi esistenti")
    if not df_campagna.empty:
        for idx, row in df_campagna.iterrows():
            with st.expander(f"Prelievo {row['PrelievoN']} - Parametro {row['Parametro']}"):
                pompa = st.text_input("Pompa", value=row["Pompa"], key=f"mod_pompa_{idx}")
                volume_iniziale = st.number_input("Volume Iniziale", value=row["VolumeIniziale"], key=f"mod_volin_{idx}")
                volume_finale = st.number_input("Volume Finale", value=row["VolumeFinale"], key=f"mod_volfin_{idx}")
                temp_iniziale = st.number_input("Temperatura Iniziale", value=row["TemperaturaIniziale"], key=f"mod_tempin_{idx}")
                temp_finale = st.number_input("Temperatura Finale", value=row["TemperaturaFinale"], key=f"mod_tempfin_{idx}")
                calcola_volume = st.checkbox("Calcola Volume Normalizzato", value=True, key=f"mod_calvol_{idx}")
                if calcola_volume:
                    volume_normalizzato = (volume_finale - volume_iniziale) * (273.15 / ((temp_iniziale + temp_finale)/2 + 273.15)) * row["PressioneAtm"] / 1012.25
                else:
                    volume_normalizzato = st.number_input("Volume Normalizzato", value=row["VolumeNormalizzato"], key=f"mod_volnorm_{idx}")
                if st.button("Salva modifiche", key=f"save_mod_{idx}"):
                    sheet.update(f'A{idx+2}:Z{idx+2}', [[
                        row["SessionID"],
                        row["Ditta"],
                        row["Stabilimento"],
                        row["Data"],
                        row["PrelievoN"],
                        row["Parametro"],
                        pompa,
                        volume_iniziale,
                        volume_finale,
                        temp_iniziale,
                        temp_finale,
                        volume_normalizzato,
                        row.get("PesoInizialeSerp", ""),
                        row.get("PesoFinaleSerp", ""),
                        row.get("PesoInizialeGel", ""),
                        row.get("PesoFinaleGel", ""),
                        row.get("UmiditaFumi", ""),
                        row.get("Isocinetismo", ""),
                        row.get("VelocitaFumi", ""),
                        row.get("dP", ""),
                        row.get("TempFumi", ""),
                        row.get("Note", "")
                    ]])
                    st.success(f"Prelievo {row['PrelievoN']} aggiornato ✅")

    # ===============================
    # ESPORTA IN EXCEL
    # ===============================
    st.subheader("Esporta campagna in Excel")
    if not df_campagna.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_campagna.to_excel(writer, index=False, sheet_name="Campagna")
        output.seek(0)
        st.download_button(
            label="⬇️ Scarica report Excel",
            data=output,
            file_name=f"Campagna_{st.session_state['session_id']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Non ci sono dati da esportare per questa campagna.")
