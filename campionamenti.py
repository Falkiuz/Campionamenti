# campionamenti_streamlit_finale.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date, time

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
    except:
        return []

def safe_get_all_values():
    try:
        return sheet.get_all_values()
    except:
        return []

def ensure_header():
    try:
        row1 = sheet.row_values(1)
        if not row1 or row1[:len(HEADER)] != HEADER[:len(row1)]:
            sheet.insert_row(HEADER, index=1)
    except:
        pass

def delete_rows_for_session(session_id):
    try:
        all_vals = safe_get_all_values()
        if not all_vals or len(all_vals)<=1:
            return
        rows_to_delete=[]
        for idx,row in enumerate(all_vals[1:],start=2):
            if len(row)>=1 and row[0]==session_id:
                rows_to_delete.append(idx)
        for r in sorted(rows_to_delete,reverse=True):
            sheet.delete_rows(r)
    except:
        pass

def append_rows(rows):
    if not rows:
        return
    try:
        sheet.append_rows(rows,value_input_option="USER_ENTERED")
    except:
        pass

def calcola_volume_normalizzato(vol_in,vol_fin,temp_in,temp_fin,pressione_hpa):
    try:
        vol_delta = float(vol_fin)-float(vol_in)
        temp_media = (float(temp_in)+float(temp_fin))/2.0
        return vol_delta*(273.15/(temp_media+273.15))*(float(pressione_hpa)/1013.25)
    except:
        return 0.0

# ===============================
# INIT
# ===============================
ensure_header()
records = safe_get_all_records()

# Dati generali inizializzati
ditta = ""
stabilimento = ""
data_campionamento = date.today()
camino = ""
operatore1=""
operatore2=""
pressione_statica=0.0
velocita_camino=0.0
angolo_swirl=0.0
diametro_progetto=0.0
diametro_misurato=0.0
numero_bocchelli=0
diametri_a_monte=""
diametri_a_valle=""
tipo_valle=""
analizzatore=""
cert_mix=""
cert_o2=""
pc=""
laser=""
micromanometro=""
termocoppia=""
darcy=""
kdarcy=0.0

# ===============================
# SESSIONI
# ===============================
session_ids = sorted(list({r["SessionID"] for r in records if r.get("SessionID")}), reverse=True)
session_ids_display = ["➕ Nuova sessione"]+session_ids
selected_session = st.sidebar.selectbox("Seleziona SessionID o crea nuova sessione", session_ids_display)

if selected_session=="➕ Nuova sessione":
    SessionID = None
else:
    SessionID = selected_session

# ===============================
# BARRA LATERALE: navigazione
# ===============================
sezione = st.sidebar.radio("Sezione",["Dati Generali","Prelievi","Riepilogo"])

# ===============================
# DATI GENERALI
# ===============================
if sezione=="Dati Generali":
    ditta = st.text_input("Ditta",value=ditta)
    stabilimento = st.text_input("Stabilimento",value=stabilimento)
    data_campionamento = st.date_input("Data campagna",value=data_campionamento)
    camino = st.text_input("Camino",value=camino)
    operatore1 = st.text_input("Operatore1",value=operatore1)
    operatore2 = st.text_input("Operatore2",value=operatore2)
    pressione_statica = st.number_input("Pressione Statica",value=pressione_statica,step=0.1)
    velocita_camino = st.number_input("Velocità Camino",value=velocita_camino,step=0.1)
    angolo_swirl = st.number_input("Angolo Di Swirl",value=angolo_swirl,step=0.1)
    diametro_progetto = st.number_input("Diametro Progetto",value=diametro_progetto,step=0.1)
    diametro_misurato = st.number_input("Diametro Misurato",value=diametro_misurato,step=0.1)
    numero_bocchelli = st.number_input("Numero Bocchelli",value=numero_bocchelli,step=1)
    diametri_a_monte = st.selectbox("Diametri A Monte",[">5","<5"])
    diametri_a_valle = st.selectbox("Diametri A Valle",[">5 sbocco camino/>2 curva","<5 sbocco camino/<2 curva"])
    analizzatore = st.selectbox("Analizzatore",["Horiba","EL3000","MRU","FID","Altro"])
    cert_mix = st.text_input("CertMix",value=cert_mix)
    cert_o2 = st.text_input("CertO2",value=cert_o2)
    pc = st.text_input("PC",value=pc)
    laser = st.text_input("Laser",value=laser)
    micromanometro = st.text_input("Micromanometro",value=micromanometro)
    termocoppia = st.text_input("Termocoppia",value=termocoppia)
    darcy = st.text_input("Darcy",value=darcy)
    kdarcy = st.number_input("K Darcy",value=kdarcy,step=0.1)

# ===============================
# PRELIEVI
# ===============================
if sezione=="Prelievi":
    num_prelievi = st.number_input("Numero Prelievi",min_value=1,max_value=50,value=1)
    prelievi=[]
    PARAMETRI=["Polveri","Polveri SiO2","Acidi","SOx","HCl","HF","Metalli","CrVI","NH3","SO3","Fenolo Formaldeide","SOV","Altro"]

    for i in range(1,int(num_prelievi)+1):
        with st.expander(f"Prelievo {i}",expanded=False):
            ugello = st.number_input(f"Ugello {i}",value=0,step=1)
            durata = st.number_input(f"Durata {i} (s)",value=0,step=0.1)
            ora_inizio = st.time_input(f"Ora Inizio {i}",value=datetime.now().time())
            filtro_qma = st.text_input(f"Filtro QMA {i}")
            prelievo_multiplo = st.selectbox(f"Prelievo Multiplo {i}",["NO","SI"])
            temperatura = st.number_input(f"Temperatura °C {i}",value=0,step=0.1)
            pressione = st.number_input(f"Pressione hPa {i}",value=1013.25,step=0.1)
            umidita = st.number_input(f"Umidità % {i}",value=0.0,step=0.1)
            meteo = st.selectbox(f"Meteo {i}",["","Sereno","Nuvoloso","Pioggia","Vento"])
            peso_in_serp = st.number_input(f"Peso Iniziale Serpentina {i}",value=0.0,step=0.01)
            peso_fin_serp = st.number_input(f"Peso Finale Serpentina {i}",value=0.0,step=0.01)
            peso_in_gel = st.number_input(f"Peso Iniziale Gel {i}",value=0.0,step=0.01)
            peso_fin_gel = st.number_input(f"Peso Finale Gel {i}",value=0.0,step=0.01)

            num_param = st.number_input(f"Numero parametri {i}",min_value=1,max_value=20,value=1)
            parametri=[]
            for j in range(1,int(num_param)+1):
                parametro = st.selectbox(f"Parametro {j}",PARAMETRI)
                altro_parametro = ""
                if parametro=="Altro":
                    altro_parametro=st.text_input(f"Specificare {j}")
                volume_iniziale = st.number_input(f"Vol In {j}",value=0.0,step=0.1)
                volume_finale = st.number_input(f"Vol Fin {j}",value=0.0,step=0.1)
                temp_iniziale = st.number_input(f"T In {j}",value=0.0,step=0.1)
                temp_finale = st.number_input(f"T Fin {j}",value=0.0,step=0.1)
                vn=calcola_volume_normalizzato(volume_iniziale,volume_finale,temp_iniziale,temp_finale,pressione)
                st.write(f"Volume Normalizzato {j}: {vn:.6f}")
                pompa = st.text_input(f"Pompa {j}")
                portata = st.number_input(f"Portata {j}",value=0.0,step=0.01)

                parametri.append({
                    "Parametro": parametro,
                    "AltroParametro": altro_parametro,
                    "VolumeIniziale": volume_iniziale,
                    "VolumeFinale": volume_finale,
                    "TemperaturaIniziale": temp_iniziale,
                    "TemperaturaFinale": temp_finale,
                    "VolumeNormalizzato": vn,
                    "Pompa": pompa,
                    "Portata": portata
                })

            prelievi.append({
                "Ugello":ugello,"DurataPrelievo":durata,"OraInizio":ora_inizio,"FiltroQMA":filtro_qma,
                "PrelievoMultiplo":prelievo_multiplo,"Temperatura":temperatura,"Pressione":pressione,"Umidita":umidita,
                "Meteo":meteo,"PesoIniSerpentina":peso_in_serp,"PesoFinSerpentina":peso_fin_serp,
                "PesoIniGel":peso_in_gel,"PesoFinGel":peso_fin_gel,"Parametri":parametri
            })

    if st.button("Salva prelievi su Google Sheet"):
        SessionID = f"{ditta}{stabilimento}[{data_campionamento.strftime('%d%m%Y')}_{camino}]"
        delete_rows_for_session(SessionID)
        rows_to_save=[]
        for idx,prel in enumerate(prelievi,1):
            for p in prel["Parametri"]:
                row = [
                    SessionID,ditta,stabilimento,data_campionamento.strftime("%d/%m/%Y"),camino,
                    operatore1,operatore2,pressione_statica,velocita_camino,angolo_swirl,
                    diametro_progetto,diametro_misurato,numero_bocchelli,diametri_a_monte,diametri_a_valle,tipo_valle,
                    analizzatore,cert_mix,cert_o2,pc,laser,micromanometro,termocoppia,darcy,kdarcy,
                    idx,prel["Ugello"],prel["DurataPrelievo"],prel["OraInizio"].strftime("%H:%M"),prel["FiltroQMA"],prel["PrelievoMultiplo"],
                    prel["Temperatura"],prel["Pressione"],prel["Umidita"],prel["Meteo"],
                    p["Parametro"],p["AltroParametro"],p["Pompa"],p["Portata"],
                    p["VolumeIniziale"],p["VolumeFinale"],p["TemperaturaIniziale"],p["TemperaturaFinale"],p["VolumeNormalizzato"],
                    prel["PesoIniSerpentina"],prel["PesoFinSerpentina"],prel["PesoIniGel"],prel["PesoFinGel"],0.0,
                    0.0,0.0,0.0,0.0,""
                ]
                rows_to_save.append(row)
        append_rows(rows_to_save)
        st.success("Dati salvati correttamente!")
