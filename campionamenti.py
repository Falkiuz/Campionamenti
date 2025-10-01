import streamlit as st
import pandas as pd
from datetime import date
import os

st.title("📋 Modulo Campionamenti Ambientali")

# --- File bozza ---
BOZZA_FILE = "bozza.csv"

# --- Funzione per caricare bozza ---
def carica_bozza():
    if os.path.exists(BOZZA_FILE):
        return pd.read_csv(BOZZA_FILE)
    return pd.DataFrame()

# --- Funzione per salvare bozza ---
def salva_bozza(dati_generali, dati_meteo, nuovi_prelievi):
    df_generali = pd.DataFrame([dati_generali])
    df_meteo = pd.DataFrame([dati_meteo])
    df_prelievi = pd.DataFrame(nuovi_prelievi)

    # Carico eventuale bozza esistente
    bozza = carica_bozza()

    if not bozza.empty and "Prelievo" in bozza.columns:
        # Mantieni i prelievi vecchi
        prelievi_vecchi = bozza[bozza["Prelievo"].notna()]
        df_prelievi = pd.concat([prelievi_vecchi, df_prelievi], ignore_index=True)

    # Combino tutto in un unico CSV
    df_bozza = pd.concat([df_generali, df_meteo, df_prelievi], axis=1, sort=False)
    df_bozza.to_csv(BOZZA_FILE, index=False)
    st.success("💾 Bozza salvata con successo!")

# --- Carico bozza ---
bozza = carica_bozza()

# =========================
# 📌 Sezione 1 - Dati Generali
# =========================
st.header("Dati Generali")
def campo_valore(nome, default=""):
    if not bozza.empty and nome in bozza.columns:
        return st.text_input(nome, value=str(bozza[nome].iloc[0]))
    return st.text_input(nome, value=default)

ditta = campo_valore("Ditta")
stabilimento = campo_valore("Stabilimento")
data_campagna = st.date_input("Data", value=date.today())
camino = campo_valore("Camino")
operatore1 = campo_valore("Operatore 1")
operatore2 = campo_valore("Operatore 2")

# =========================
# 📌 Sezione 2 - Dati Meteo e Ambientali
# =========================
st.header("Dati Meteo e Ambientali")
def campo_numero(nome, default=0.0):
    if not bozza.empty and nome in bozza.columns:
        return float(bozza[nome].iloc[0])
    return st.number_input(nome, value=default, step=0.1)

temperatura = campo_numero("Temperatura °C")
pressione = campo_numero("Pressione hPa")
umidita = campo_numero("Umidità %")
if not bozza.empty and "Meteo" in bozza.columns:
    meteo = st.selectbox("Meteo", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"], index=["", "Sereno", "Nuvoloso", "Pioggia", "Vento"].index(bozza["Meteo"].iloc[0]))
else:
    meteo = st.selectbox("Meteo", ["", "Sereno", "Nuvoloso", "Pioggia", "Vento"])

# =========================
# 📌 Sezione 3 - Prelievi
# =========================
st.header("Prelievi")
num_prelievi = st.number_input("Numero di prelievi", min_value=3, max_value=20, value=3)
nuovi_prelievi = []

for i in range(1, num_prelievi + 1):
    st.subheader(f"Prelievo {i}")
    for j in range(1, 7):  # max 6 parametri
        with st.expander(f"Parametro {j}"):
            key_base = f"{i}_{j}"
            nome_param = st.text_input(f"Nome parametro {j}", key=f"nome_{key_base}")
            valore = st.text_input(f"Valore", key=f"valore_{key_base}")
            unita = st.text_input(f"Unità di misura", key=f"unita_{key_base}")
            metodo = st.text_input(f"Metodo", key=f"metodo_{key_base}")
            strumento = st.text_input(f"Strumento", key=f"strumento_{key_base}")

            if nome_param:
                nuovi_prelievi.append({
                    "Prelievo": i,
                    "Parametro": nome_param,
                    "Valore": valore,
                    "Unità": unita,
                    "Metodo": metodo,
                    "Strumento": strumento
                })

# --- Pulsante Salva Bozza ---
if st.button("💾 Salva Bozza"):
    dati_generali = {
        "Ditta": ditta,
        "Stabilimento": stabilimento,
        "Data": data_campagna,
        "Camino": camino,
        "Operatore 1": operatore1,
        "Operatore 2": operatore2
    }
    dati_meteo = {
        "Temperatura °C": temperatura,
        "Pressione hPa": pressione,
        "Umidità %": umidita,
        "Meteo": meteo
    }
    salva_bozza(dati_generali, dati_meteo, nuovi_prelievi)

# --- Pulsante Esporta Finale ---
if st.button("💾 Esporta in Excel"):
    if nuovi_prelievi:
        df_generali = pd.DataFrame([{
            "Ditta": ditta,
            "Stabilimento": stabilimento,
            "Data": data_campagna,
            "Camino": camino,
            "Operatore 1": operatore1,
            "Operatore 2": operatore2
        }])
        df_meteo = pd.DataFrame([{
            "Temperatura °C": temperatura,
            "Pressione hPa": pressione,
            "Umidità %": umidita,
            "Meteo": meteo
        }])
        df_prelievi = pd.DataFrame(nuovi_prelievi)
        filename = f"report_campagna_{stabilimento}_{camino}.xlsx"
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            df_generali.to_excel(writer, sheet_name="Dati Generali", index=False)
            df_meteo.to_excel(writer, sheet_name="Dati Meteo", index=False)
            df_prelievi.to_excel(writer, sheet_name="Prelievi", index=False)
        st.success(f"✅ Report generato: {filename}")
        with open(filename, "rb") as f:
            st.download_button(
                label="⬇️ Scarica Report",
                data=f,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("⚠️ Nessun dato inserito!")
