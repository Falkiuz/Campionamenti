# campionamenti_streamlit_complete.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date
import time

st.set_page_config(layout="wide")

# ===============================
# CONFIG GOOGLE SHEETS
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)
SHEET_ID = "1KCPltH_8EtI5svqRivdwI68DWJ6eE1IK3UDe45PENf8"

# ===============================
# HEADER (ordine colonne su sheet)
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
# UTILITY SHEET (retry leggere)
# ===============================
def get_sheet_with_retry(max_retry=3, delay=1):
    for attempt in range(max_retry):
        try:
            sh = client.open_by_key(SHEET_ID).sheet1
            return sh
        except Exception as e:
            if attempt < max_retry - 1:
                time.sleep(delay)
            else:
                st.error(f"Impossibile connettersi a Google Sheets ({max_retry} tentativi): {e}")
                return None

def ensure_header(sheet):
    try:
        row1 = sheet.row_values(1)
        if not row1 or row1[:len(HEADER)] != HEADER[:len(row1)]:
            sheet.insert_row(HEADER, index=1)
    except Exception as e:
        st.warning(f"Impossibile assicurare header: {e}")

def read_all_records(sheet):
    try:
        return sheet.get_all_records()
    except Exception as e:
        st.warning(f"Impossibile leggere records: {e}")
        return []

def delete_rows_for_session(sheet, session_id):
    try:
        all_vals = sheet.get_all_values()
        if not all_vals or len(all_vals) <= 1:
            return
        rows_to_delete = [idx for idx, row in enumerate(all_vals[1:], start=2) if len(row) >= 1 and row[0] == session_id]
        for r in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(r)
    except Exception as e:
        st.error(f"Errore eliminazione righe sessione: {e}")

def append_rows(sheet, rows):
    if not rows:
        return
    try:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"Errore append su Google Sheets: {e}")

# ===============================
# FUNZIONI CALCOLO
# ===============================
def calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, pressione_hpa):
    try:
        vol_delta = float(vol_fin) - float(vol_in)
        temp_media = (float(temp_in) + float(temp_fin)) / 2.0
        return vol_delta * (273.15 / (temp_media + 273.15)) * (float(pressione_hpa) / 1013.25)
    except Exception:
        return 0.0

def calcola_umidita_fumi(pis, pfs, pig, pfg, volume_normalizzato):
    # pesi in g (o unità coerente). formula: PesoAcquaSerp + PesoAcquaGel -> VolumeAcqua = PesoTot/18*22.414
    try:
        peso_acqua_serp = float(pfs) - float(pis)
        peso_acqua_gel = float(pfg) - float(pig)
        peso_acqua_tot = peso_acqua_serp + peso_acqua_gel
        volume_acqua = (peso_acqua_tot / 18.0) * 22.414
        volume_totale = volume_acqua + float(volume_normalizzato)
        if volume_totale == 0:
            return 0.0, volume_acqua, volume_totale
        umid = (volume_acqua / volume_totale) * 100.0
        return umid, volume_acqua, volume_totale
    except Exception:
        return 0.0, 0.0, 0.0

# ===============================
# UI - iniziale: leggi sessioni (solo per elenco)
# ===============================
st.title("📋 Modulo Campionamenti Ambientali — versione completa")

sheet_read = get_sheet_with_retry()
records = []
session_ids = []
if sheet_read:
    ensure_header(sheet_read)
    records = read_all_records(sheet_read)
    session_ids = sorted(list({r["SessionID"] for r in records if r.get("SessionID")}), reverse=True)

session_options = ["➕ Nuova sessione"] + session_ids
selected_session = st.selectbox("Seleziona SessionID o crea nuova sessione", session_options, key="select_session")

# Prefill condizionato: checkbox mostrato solo quando si sceglie sessione esistente
prefill_enabled = False
if selected_session != "➕ Nuova sessione":
    prefill_enabled = st.checkbox("Richiama dati da questa sessione (prefill)", value=False)

# ===============================
# SESSIONID leggibile
# ===============================
if selected_session == "➕ Nuova sessione":
    colA, colB, colC = st.columns([3,3,2])
    with colA:
        ditta = st.text_input("Ditta", key="ditta")
        stabilimento = st.text_input("Stabilimento", key="stabilimento")
    with colB:
        data_campagna = st.date_input("Data campagna", value=date.today(), key="data_campagna")
        camino = st.text_input("Camino", key="camino")
    with colC:
        operatore1 = st.text_input("Operatore 1", key="operatore1")
        operatore2 = st.text_input("Operatore 2", key="operatore2")

    # genera SessionID leggibile
    sanitized_d = (ditta.strip().replace(" ", "_") or "Ditta")
    sanitized_s = (stabilimento.strip().replace(" ", "_") or "Stab")
    SessionID = f"{sanitized_d}_{sanitized_s}_{data_campagna.strftime('%Y%m%d')}"
else:
    # quando richiami una sessione esistente, tenta di estrarre Ditta/Stabilimento/Data dalla prima riga (se prefill)
    SessionID = selected_session
    # default vuoti (se non prefill)
    ditta = ""
    stabilimento = ""
    data_campagna = date.today()
    camino = ""
    operatore1 = ""
    operatore2 = ""
    if prefill_enabled and sheet_read:
        # prendi le righe della sessione
        rows = [r for r in records if r.get("SessionID") == SessionID]
        if rows:
            first = rows[0]
            ditta = first.get("Ditta","") or ""
            stabilimento = first.get("Stabilimento","") or ""
            # Data può essere in formato stringa - proviamo a parse
            try:
                data_campagna = date.fromisoformat(first.get("Data")) if first.get("Data") else date.today()
            except Exception:
                data_campagna = date.today()
            camino = first.get("Camino","") or ""
            operatore1 = first.get("Operatore1","") or ""
            operatore2 = first.get("Operatore2","") or ""

    col1, col2, col3 = st.columns([3,3,2])
    with col1:
        st.text_input("Ditta", value=ditta, key="ditta_prefill")
        st.text_input("Stabilimento", value=stabilimento, key="stabilimento_prefill")
    with col2:
        st.date_input("Data campagna", value=data_campagna, key="data_campagna_prefill")
        st.text_input("Camino", value=camino, key="camino_prefill")
    with col3:
        st.text_input("Operatore 1", value=operatore1, key="operatore1_prefill")
        st.text_input("Operatore 2", value=operatore2, key="operatore2_prefill")

# Seleziona/mostra i campi generali aggiuntivi (solo una volta per sessione)
with st.expander("📂 Dati generali (compilare una sola volta per sessione)", expanded=True):
    # se prefill_enabled e selected_session esistente, popola valori di default da first row se disponibile
    default_row = None
    if prefill_enabled and sheet_read:
        rows = [r for r in records if r.get("SessionID") == SessionID]
        if rows:
            default_row = rows[0]

    angolo_swirl = st.number_input("AngoloDiSwirl", value=float(default_row.get("AngoloDiSwirl",0)) if default_row else 0.0, step=0.1, key="angolo_swirl")
    diametro_progetto = st.number_input("DiametroProgetto", value=float(default_row.get("DiametroProgetto",0)) if default_row else 0.0, step=0.1, key="diametro_progetto")
    diametro_misurato = st.number_input("DiametroMisurato", value=float(default_row.get("DiametroMisurato",0)) if default_row else 0.0, step=0.1, key="diametro_misurato")
    numero_bocchelli = st.number_input("NumeroBocchelli", value=int(default_row.get("NumeroBocchelli",0)) if default_row else 0, step=1, key="numero_bocchelli")
    diametri_a_monte = st.selectbox("DiametriAMonte", options=[">5","<5"], index=0 if not default_row else (0 if default_row.get("DiametriAMonte",">5")==">5" else 1), key="diametri_a_monte")
    diametri_a_valle = st.selectbox("DiametriAValle", options=[">5 sbocco camino/>2 curva","<5 sbocco camino/<2 curva"], index=0 if not default_row else (0 if default_row.get("DiametriAValle","") == ">5 sbocco camino/>2 curva" else 1), key="diametri_a_valle")
    analizzatore = st.selectbox("Analizzatore", options=["Horiba","EL3000","MRU","FID","Altro"], index=0 if not default_row else (["Horiba","EL3000","MRU","FID","Altro"].index(default_row.get("Analizzatore","Horiba")) if default_row and default_row.get("Analizzatore") in ["Horiba","EL3000","MRU","FID","Altro"] else 0), key="analizzatore")
    cert_mix = st.text_input("CertMix", value=default_row.get("CertMix","") if default_row else "", key="cert_mix")
    cert_o2 = st.text_input("CertO2", value=default_row.get("CertO2","") if default_row else "", key="cert_o2")
    pc = st.text_input("PC", value=default_row.get("PC","") if default_row else "", key="pc")
    laser = st.text_input("Laser", value=default_row.get("Laser","") if default_row else "", key="laser")
    micromanometro = st.text_input("Micromanometro", value=default_row.get("Micromanometro","") if default_row else "", key="micromanometro")
    termocoppia = st.text_input("Termocoppia", value=default_row.get("Termocoppia","") if default_row else "", key="termocoppia")
    darcy = st.text_input("Darcy", value=default_row.get("Darcy","") if default_row else "", key="darcy")
    kdarcy = st.number_input("KDarcy", value=float(default_row.get("KDarcy",0)) if default_row else 0.0, step=0.01, key="kdarcy")

# ===============================
# NUMERO PRELIEVI
# ===============================
num_prelievi = st.number_input("Numero di prelievi", min_value=1, max_value=50, value=1, key="num_prel_global")

# ===============================
# PARAMETRI DISPONIBILI
# ===============================
PARAMETRI = ["Polveri","Polveri SiO2","Acidi","SOx","HCl",
             "HF","Metalli","CrVI","NH3","SO3",
             "Fenolo Formaldeide","SOV","Altro"]

# container per tutti i dati
nuovi_prelievi = []

# loop prelievi
for i in range(1, int(num_prelievi) + 1):
    with st.expander(f"Prelievo {i}", expanded=False):
        # se prefill_enabled, cerco i valori nella sessione selezionata (possibile che ci siano più righe per prelievo)
        meta_defaults = {}
        if prefill_enabled and sheet_read:
            rows_i = [r for r in records if r.get("SessionID") == SessionID and str(r.get("PrelievoN","")) == str(i)]
            if rows_i:
                # prendo il primo come default
                meta_defaults = rows_i[0]

        # colonne
        c1, c2, c3 = st.columns([2,2,2])
        with c1:
            ugello = st.number_input(f"Ugello {i}", value=float(meta_defaults.get("Ugello",0)) if meta_defaults else 0.0, key=f"ugello_{i}", step=0.1)
            durata = st.number_input(f"Durata Prelievo {i} (s)", value=float(meta_defaults.get("DurataPrelievo",0)) if meta_defaults else 0.0, key=f"durata_{i}", step=0.1)
            ora_inizio = st.time_input(f"Ora Inizio {i}", value=(datetime.strptime(meta_defaults.get("OraInizio","00:00"), "%H:%M").time() if meta_defaults and meta_defaults.get("OraInizio") else datetime.now().time()), key=f"ora_{i}")
            filtro_qma = st.text_input(f"Filtro QMA {i}", value=meta_defaults.get("FiltroQMA","") if meta_defaults else "", key=f"filtro_{i}")
            prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}", ["NO","SI"], index=0 if not meta_defaults or meta_defaults.get("PrelievoMultiplo","")=="NO" else 1, key=f"multi_{i}")
        with c2:
            temperatura = st.number_input(f"Temperatura °C {i}", value=float(meta_defaults.get("Temperatura",0)) if meta_defaults else 0.0, key=f"temp_{i}", step=0.1)
            pressione = st.number_input(f"Pressione hPa {i}", value=float(meta_defaults.get("Pressione",1013.25)) if meta_defaults else 1013.25, key=f"press_{i}", step=0.1)
            umidita = st.number_input(f"Umidità % {i}", value=float(meta_defaults.get("Umidita",0)) if meta_defaults else 0.0, key=f"umid_{i}", step=0.1)
            meteo = st.selectbox(f"Meteo {i}", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"], index=0 if not meta_defaults or not meta_defaults.get("Meteo") else ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"].index(meta_defaults.get("Meteo")), key=f"meteo_{i}")
        with c3:
            peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}", value=float(meta_defaults.get("PesoIniSerpentina",0)) if meta_defaults else 0.0, key=f"pis_{i}", step=0.01)
            peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}", value=float(meta_defaults.get("PesoFinSerpentina",0)) if meta_defaults else 0.0, key=f"pfs_{i}", step=0.01)
            peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}", value=float(meta_defaults.get("PesoIniGel",0)) if meta_defaults else 0.0, key=f"pig_{i}", step=0.01)
            peso_fin_gel = st.number_input(f"Peso Finale Gel {i}", value=float(meta_defaults.get("PesoFinGel",0)) if meta_defaults else 0.0, key=f"pfg_{i}", step=0.01)

        # numero parametri per prelievo
        num_param = st.number_input(f"Numero di parametri per prelievo {i}", min_value=1, max_value=20, value=int(meta_defaults.get("NumParam",1)) if meta_defaults and meta_defaults.get("NumParam") else 1, key=f"num_param_{i}")

        # spazio per memorizzare VN temporanei (session_state)
        vn_list = []
        params_for_prelievo = []
        for j in range(1, int(num_param) + 1):
            s1, s2, s3, s4 = st.columns([2,1,1,1])
            with s1:
                parametro = st.selectbox(f"Parametro {j} (prel {i})", PARAMETRI, index=0, key=f"param_{i}_{j}")
                altro_parametro = ""
                if parametro == "Altro":
                    altro_parametro = st.text_input(f"Specificare parametro {j} (prel {i})", key=f"altro_{i}_{j}")

            with s2:
                pompa = st.text_input(f"Pompa {j} (prel {i})", value="", key=f"pompa_{i}_{j}")
                portata = st.number_input(f"Portata {j} (prel {i})", value=0.0, step=0.01, key=f"portata_{i}_{j}")
            with s3:
                vol_in = st.number_input(f"Volume Iniziale {j} (prel {i})", value=float(meta_defaults.get("VolumeIniziale",0)) if meta_defaults else 0.0, key=f"vol_in_{i}_{j}", step=0.1)
                vol_fin = st.number_input(f"Volume Finale {j} (prel {i})", value=float(meta_defaults.get("VolumeFinale",0)) if meta_defaults else 0.0, key=f"vol_fin_{i}_{j}", step=0.1)
            with s4:
                temp_in = st.number_input(f"T In {j} (prel {i})", value=float(meta_defaults.get("TemperaturaIniziale",0)) if meta_defaults else 0.0, key=f"temp_in_{i}_{j}", step=0.1)
                temp_fin = st.number_input(f"T Fin {j} (prel {i})", value=float(meta_defaults.get("TemperaturaFinale",0)) if meta_defaults else 0.0, key=f"temp_fin_{i}_{j}", step=0.1)

            # display VN se già calcolata in session_state
            vn_key = f"vn_{i}_{j}"
            vn_val = st.session_state.get(vn_key, None)
            if vn_val is not None:
                st.markdown(f"**VN (param {j} prel {i}):** `{vn_val:.6f}`")
            else:
                st.markdown(f"**VN (param {j} prel {i}):** (non calcolato)")

            params_for_prelievo.append({
                "Parametro": (altro_parametro if parametro == "Altro" else parametro),
                "AltroParametro": (altro_parametro if parametro == "Altro" else ""),
                "Pompa": pompa,
                "Portata": portata,
                "VolumeIniziale": vol_in,
                "VolumeFinale": vol_fin,
                "TemperaturaIniziale": temp_in,
                "TemperaturaFinale": temp_fin,
                "vn_key": vn_key  # riferimento al key vn
            })
            # colleziono vn in lista per il select delle scelte
            vn_list.append(vn_val)

        # Bottoni: calcola volumi (tutti i parametri del prelievo) e calcola umidità
        col_calc1, col_calc2 = st.columns([1,1])
        with col_calc1:
            if st.button(f"🔹 Calcola volumi (Prelievo {i})", key=f"calc_vol_{i}"):
                # calcola e salva in session_state per ogni parametro
                for j_idx, p in enumerate(params_for_prelievo, start=1):
                    vol_in = st.session_state.get(f"vol_in_{i}_{j_idx}", 0.0)
                    vol_fin = st.session_state.get(f"vol_fin_{i}_{j_idx}", 0.0)
                    temp_in = st.session_state.get(f"temp_in_{i}_{j_idx}", 0.0)
                    temp_fin = st.session_state.get(f"temp_fin_{i}_{j_idx}", 0.0)
                    press = st.session_state.get(f"press_{i}", 1013.25)
                    vn = calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, press)
                    st.session_state[f"vn_{i}_{j_idx}"] = float(f"{vn:.6f}")
                st.experimental_rerun()  # per aggiornare i valori mostrati

        with col_calc2:
            # scelta quale VN usare per umidità -> se vn_list ha None, proviamo comunque a calcolare al volo per mostrare opzioni
            # costruiamo lista opzioni dinamicamente
            vol_opts = []
            for j_idx, p in enumerate(params_for_prelievo, start=1):
                vn_val = st.session_state.get(f"vn_{i}_{j_idx}", None)
                if vn_val is None:
                    # calcola temporaneamente dal form
                    vol_in = st.session_state.get(f"vol_in_{i}_{j_idx}", 0.0)
                    vol_fin = st.session_state.get(f"vol_fin_{i}_{j_idx}", 0.0)
                    temp_in = st.session_state.get(f"temp_in_{i}_{j_idx}", 0.0)
                    temp_fin = st.session_state.get(f"temp_fin_{i}_{j_idx}", 0.0)
                    press = st.session_state.get(f"press_{i}", 1013.25)
                    vn_temp = calcola_volume_normalizzato(vol_in, vol_fin, temp_in, temp_fin, press)
                    vol_opts.append((j_idx, float(f"{vn_temp:.6f}")))
                else:
                    vol_opts.append((j_idx, float(vn_val)))

            # if no params (shouldn't happen), default
            if not vol_opts:
                vol_opts = [(1, 0.0)]

            # format_func
            def fmt(opt):
                return f"Parametro {opt[0]} - VN={opt[1]:.6f}"

            # selected index (store j index)
            sel_index = st.selectbox(f"Scegli VN per umidità (Prelievo {i})", options=vol_opts, format_func=fmt, key=f"vol_choice_{i}")
            # show calc button
            if st.button(f"🔹 Calcola umidità fumi (Prelievo {i})", key=f"calc_um_{i}"):
                # prendi pesi
                pis = st.session_state.get(f"pis_{i}", 0.0)
                pfs = st.session_state.get(f"pfs_{i}", 0.0)
                pig = st.session_state.get(f"pig_{i}", 0.0)
                pfg = st.session_state.get(f"pfg_{i}", 0.0)
                chosen_vn = sel_index[1]  # vol_opts entry (j_idx, vn)
                um, vol_acq, vol_tot = calcola_umidita_fumi(pis, pfs, pig, pfg, chosen_vn)
                st.session_state[f"umidita_fumi_{i}"] = float(f"{um:.6f}")
                st.session_state[f"volume_acqua_{i}"] = float(f"{vol_acq:.6f}")
                st.session_state[f"volume_totale_{i}"] = float(f"{vol_tot:.6f}")
                st.experimental_rerun()

        # mostra risultati calcolati se presenti
        if st.session_state.get(f"volume_acqua_{i}") is not None:
            st.info(f"Volume H2O (Prelievo {i}): {st.session_state.get(f'volume_acqua_{i}'):.6f} Nm³")
            st.info(f"Volume Totale (Prelievo {i}): {st.session_state.get(f'volume_totale_{i}'):.6f} Nm³")
            st.info(f"Umidità fumi (Prelievo {i}): {st.session_state.get(f'umidita_fumi_{i}'):.6f} %")

        # medie e note (già gestite)
        isocinetismo = st.number_input(f"Isocinetismo {i}", value=float(meta_defaults.get("Isocinetismo",0)) if meta_defaults else 0.0, key=f"isoc_{i}", step=0.1)
        velocita_media = st.number_input(f"VelocitàCampionamento {i}", value=float(meta_defaults.get("VelocitàCampionamento",0)) if meta_defaults else 0.0, key=f"vel_{i}", step=0.1)
        dp = st.number_input(f"dP {i}", value=float(meta_defaults.get("dP",0)) if meta_defaults else 0.0, key=f"dp_{i}", step=0.1)
        temp_fumi = st.number_input(f"TemperaturaFumi {i}", value=float(meta_defaults.get("TemperaturaFumi",0)) if meta_defaults else 0.0, key=f"tf_{i}", step=0.1)
        note = st.text_area(f"Note prelievo {i}", value=meta_defaults.get("Note","") if meta_defaults else "", key=f"note_{i}")

        # ora compiliamo le righe per il salvataggio: una riga per parametro
        for j_idx, p in enumerate(params_for_prelievo, start=1):
            vn_val = st.session_state.get(f"vn_{i}_{j_idx}", calcola_volume_normalizzato(p["VolumeIniziale"], p["VolumeFinale"], p["TemperaturaIniziale"], p["TemperaturaFinale"], pressione))
            umid_fumi_val = st.session_state.get(f"umidita_fumi_{i}", "")
            # session-level fields (se creazione nuova sessione, prendo i valori attuali; se prefill, i campi di sessione sono quelli mostrati)
            sess_ditta = st.session_state.get("ditta") or st.session_state.get("ditta_prefill") or ""
            sess_stab = st.session_state.get("stabilimento") or st.session_state.get("stabilimento_prefill") or ""
            sess_data = (st.session_state.get("data_campagna").isoformat() if st.session_state.get("data_campagna") else (st.session_state.get("data_campagna_prefill").isoformat() if st.session_state.get("data_campagna_prefill") else date.today().isoformat()))
            sess_camino = st.session_state.get("camino") or st.session_state.get("camino_prefill") or ""
            sess_op1 = st.session_state.get("operatore1") or st.session_state.get("operatore1_prefill") or ""
            sess_op2 = st.session_state.get("operatore2") or st.session_state.get("operatore2_prefill") or ""

            row = {
                "SessionID": SessionID,
                "Ditta": sess_ditta,
                "Stabilimento": sess_stab,
                "Data": sess_data,
                "Camino": sess_camino,
                "Operatore1": sess_op1,
                "Operatore2": sess_op2,
                "PressioneStatica": st.session_state.get("pressione_statica") if st.session_state.get("pressione_statica") is not None else "",
                "VelocitàCamino": st.session_state.get("velocita_camino") if st.session_state.get("velocita_camino") is not None else "",
                "AngoloDiSwirl": st.session_state.get("angolo_swirl",""),
                "DiametroProgetto": st.session_state.get("diametro_progetto",""),
                "DiametroMisurato": st.session_state.get("diametro_misurato",""),
                "NumeroBocchelli": st.session_state.get("numero_bocchelli",""),
                "DiametriAMonte": st.session_state.get("diametri_a_monte",""),
                "DiametriAValle": st.session_state.get("diametri_a_valle",""),
                "TipoValle": "",
                "Analizzatore": st.session_state.get("analizzatore",""),
                "CertMix": st.session_state.get("cert_mix",""),
                "CertO2": st.session_state.get("cert_o2",""),
                "PC": st.session_state.get("pc",""),
                "Laser": st.session_state.get("laser",""),
                "Micromanometro": st.session_state.get("micromanometro",""),
                "Termocoppia": st.session_state.get("termocoppia",""),
                "Darcy": st.session_state.get("darcy",""),
                "KDarcy": st.session_state.get("kdarcy",""),
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
                "AltroParametro": p["AltroParametro"],
                "Pompa": p["Pompa"],
                "Portata": p["Portata"],
                "VolumeIniziale": p["VolumeIniziale"],
                "VolumeFinale": p["VolumeFinale"],
                "TemperaturaIniziale": p["TemperaturaIniziale"],
                "TemperaturaFinale": p["TemperaturaFinale"],
                "VolumeNormalizzato": float(f"{vn_val:.6f}") if vn_val is not None else "",
                "PesoIniSerpentina": peso_in_serp,
                "PesoFinSerpentina": peso_fin_serp,
                "PesoIniGel": peso_in_gel,
                "PesoFinGel": peso_fin_gel,
                "UmiditaFumi": umid_fumi_val,
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
# ANTEPRIMA (opzionale)
# ===============================
if nuovi_prelievi:
    st.subheader("Anteprima dati (prima del salvataggio)")
    st.dataframe(pd.DataFrame(nuovi_prelievi))

# ===============================
# SALVATAGGIO (solo quando premi)
# ===============================
if st.button("💾 Salva campionamenti su Google Sheets"):
    if not nuovi_prelievi:
        st.warning("Nessun dato da salvare.")
    else:
        sheet_write = get_sheet_with_retry()
        if not sheet_write:
            st.error("Impossibile connettersi a Google Sheets per il salvataggio.")
        else:
            try:
                ensure_header(sheet_write)
                # elimina righe vecchie della stessa sessione
                delete_rows_for_session(sheet_write, SessionID)
                # prepara righe secondo HEADER
                rows_to_append = []
                for r in nuovi_prelievi:
                    row_values = [r.get(col, "") for col in HEADER]
                    rows_to_append.append(row_values)
                # append (in blocco)
                append_rows(sheet_write, rows_to_append)
                st.success(f"✅ Sessione {SessionID} salvata ({len(rows_to_append)} righe).")
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")
