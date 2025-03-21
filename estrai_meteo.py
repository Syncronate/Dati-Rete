import requests
import schedule
import time
import json
import csv
from datetime import datetime

def estrai_dati_meteo():
    api_url = "https://retemir.regione.marche.it/api/stations/rt-data"
    stazioni_interessate = [
        "Misa",
        "Pianello di Ostra",
        "Nevola",
        "Barbara",
        "Serra dei Conti",
        "Arcevia"
    ]  # <--- Lista delle stazioni che ti interessano, AGGIORNATA CON LA TUA LISTA
    sensori_interessati_tipoSens = [0, 1, 5, 6, 9, 10, 100] # Esempio: Pioggia, Temperatura, Umidità, Vento, Livello fiumi
    nome_file_csv = f"dati_meteo_stazioni_selezionate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    try:
        response = requests.get(api_url, verify=False) # <--- Aggiungi verify=False
        response.raise_for_status()
        dati_meteo = response.json()

        with open(nome_file_csv, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Stazione', 'Sensore Tipo', 'Descrizione Sensore', 'Valore', 'Unità di Misura', 'Timestamp'])

            for stazione in dati_meteo:
                nome_stazione = stazione.get("nome")
                if nome_stazione in stazioni_interessate: # <--- Filtra per NOME della stazione
                    timestamp_stazione = stazione.get("lastUpdateTime")
                    print(f"Dati per la stazione: {nome_stazione}")
                    for sensore in stazione.get("analog", []):
                        tipoSens = sensore.get("tipoSens")
                        descr_sensore = sensore.get("descr").strip()
                        valore_sensore = sensore.get("valore")
                        unita_misura = sensore.get("unmis").strip() if sensore.get("unmis") else ""

                        if tipoSens in sensori_interessati_tipoSens: # <--- Filtra per TIPO di sensore (opzionale, puoi rimuovere se vuoi tutti i sensori per queste stazioni)
                            csv_writer.writerow([nome_stazione, tipoSens, descr_sensore, valore_sensore, unita_misura, timestamp_stazione])
                            print(f"  - Sensore tipo {tipoSens} ({descr_sensore}): {valore_sensore} {unita_misura}")
                    print("-" * 30)
        print(f"Dati meteo per le stazioni selezionate salvati in: {nome_file_csv}")


    except requests.exceptions.RequestException as e:
        print(f"Errore nella richiesta API: {e}")
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing JSON: {e}")
    except Exception as e:
        print(f"Errore generico: {e}")


# Esegui la funzione una volta subito per testare
estrai_dati_meteo()

# Pianifica l'esecuzione periodica (es. ogni 5 minuti)
schedule.every(5).minutes.do(estrai_dati_meteo)

print("Script di estrazione dati meteo avviato per le stazioni selezionate. In esecuzione ogni 5 minuti...")
while True:
    schedule.run_pending()
    time.sleep(1)
