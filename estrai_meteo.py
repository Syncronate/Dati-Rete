import requests
import json
import csv
import os
import time
from datetime import datetime, timedelta
import sys
import urllib3

# Disable SSL warning - keeping this from original script
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def estrai_dati_meteo():
    """
    Extracts weather data from API and appends it to a CSV file.
    This function runs continuously, updating the CSV file every 15 minutes.
    """
    # Fixed CSV filename
    nome_file_csv = "dati_meteo_stazioni.csv"
    
    # API information
    api_url = "https://retemir.regione.marche.it/api/stations/rt-data"
    stazioni_interessate = [
        "Misa",
        "Pianello di Ostra",
        "Nevola",
        "Barbara",
        "Serra dei Conti",
        "Arcevia"
    ]
    sensori_interessati_tipoSens = [0, 1, 5, 6, 9, 10, 100]
    
    # Check if file exists
    file_exists = os.path.isfile(nome_file_csv)
    
    # Variable to store current headers in the CSV file
    intestazione_attuale = []
    
    # If file exists, read the current headers
    if file_exists:
        try:
            with open(nome_file_csv, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                intestazione_attuale = next(reader)  # Get the first row (headers)
                print(f"File esistente trovato con intestazioni: {intestazione_attuale}")
        except Exception as e:
            print(f"Errore nella lettura del file esistente: {e}")
            # If there's an error reading the file, treat it as if it doesn't exist
            file_exists = False
            intestazione_attuale = []
    
    print(f"Iniziando il monitoraggio dei dati meteo. I dati saranno salvati in: {nome_file_csv}")
    print(f"Il programma aggiornerà i dati ogni 15 minuti. Premi Ctrl+C per terminare.")
    
    try:
        while True:
            current_time = datetime.now()
            formatted_time = current_time.strftime('%d/%m/%Y %H:%M')
            print(f"\nEstrazione dati alle {formatted_time}...")
            
            try:
                # Get data from API
                response = requests.get(api_url, verify=False, timeout=30)
                response.raise_for_status()
                dati_meteo = response.json()
                
                # Process data
                tipi_sensori_presenti = set()  # Set for unique sensor types
                dati_per_stazione = {}  # Dictionary to group data by station
                
                # Extract data for each station
                for stazione in dati_meteo:
                    nome_stazione = stazione.get("nome")
                    if nome_stazione in stazioni_interessate:
                        timestamp_stazione = stazione.get("lastUpdateTime")
                        
                        # Convert API timestamp to formatted time
                        try:
                            # Parse timestamp (assuming it's in ISO format)
                            dt_obj = datetime.fromisoformat(timestamp_stazione.replace('Z', '+00:00'))
                            timestamp_formattato = dt_obj.strftime('%d/%m/%Y %H:%M')
                        except (ValueError, AttributeError):
                            # If parsing fails, use current time
                            timestamp_formattato = formatted_time
                            
                        print(f"Dati per la stazione: {nome_stazione}")
                        dati_stazione = {'Timestamp': timestamp_formattato}  # Initialize data for the station
                        
                        for sensore in stazione.get("analog", []):
                            tipoSens = sensore.get("tipoSens")
                            descr_sensore = sensore.get("descr", "").strip()
                            valore_sensore = sensore.get("valore")
                            unita_misura = sensore.get("unmis", "").strip() if sensore.get("unmis") else ""
                            
                            if tipoSens in sensori_interessati_tipoSens:
                                chiave_sensore = f"{descr_sensore} ({unita_misura})"  # Create a unique key for the sensor
                                dati_stazione[chiave_sensore] = valore_sensore
                                tipi_sensori_presenti.add(chiave_sensore)  # Add sensor type to the set
                                print(f"  - {descr_sensore}: {valore_sensore} {unita_misura}")
                                
                        dati_per_stazione[nome_stazione] = dati_stazione
                        print("-" * 30)
                
                # If no stations have data, skip this update
                if not dati_per_stazione:
                    print("Nessun dato disponibile per le stazioni selezionate. Riproverò al prossimo aggiornamento.")
                    time.sleep(15 * 60)  # Wait 15 minutes
                    continue
                
                # Build the final CSV header (sort sensor types)
                nuova_intestazione = ['Data_Ora']
                nuova_intestazione.extend(sorted(list(tipi_sensori_presenti)))
                
                # Check if headers have changed
                headers_changed = False
                if not file_exists or nuova_intestazione != intestazione_attuale:
                    headers_changed = True
                    print("Le intestazioni sono cambiate o il file non esiste. Creando un nuovo file...")
                
                # Create a single row with current time and all station data
                riga_dati = [formatted_time]
                
                # Add data for each sensor from all stations
                for sensore_header in nuova_intestazione[1:]:  # Skip Data_Ora column
                    values = []
                    for nome_stazione in stazioni_interessate:
                        if nome_stazione in dati_per_stazione:
                            value = dati_per_stazione[nome_stazione].get(sensore_header, 'N/A')
                            if value != 'N/A':
                                values.append(str(value))
                    
                    # If we have valid values, use the average; otherwise, use N/A
                    if values:
                        try:
                            # Try to compute average of numerical values
                            numeric_values = [float(v) for v in values]
                            avg_value = sum(numeric_values) / len(numeric_values)
                            riga_dati.append(f"{avg_value:.2f}")
                        except ValueError:
                            # If conversion fails, just use the first value
                            riga_dati.append(values[0])
                    else:
                        riga_dati.append('N/A')
                
                # If headers have changed, create a new file
                if headers_changed:
                    mode = 'w'  # Write mode (creates a new file or overwrites existing file)
                    with open(nome_file_csv, mode, newline='', encoding='utf-8') as csvfile:
                        csv_writer = csv.writer(csvfile)
                        csv_writer.writerow(nuova_intestazione)
                        csv_writer.writerow(riga_dati)
                        print(f"Nuovo file CSV creato con intestazioni aggiornate: {nuova_intestazione}")
                        intestazione_attuale = nuova_intestazione
                        file_exists = True
                else:
                    # Append to existing file
                    with open(nome_file_csv, 'a', newline='', encoding='utf-8') as csvfile:
                        csv_writer = csv.writer(csvfile)
                        csv_writer.writerow(riga_dati)
                
                print(f"Dati meteo aggiornati in: {nome_file_csv}")
                
            except requests.exceptions.RequestException as e:
                print(f"Errore nella richiesta API: {e}")
            except json.JSONDecodeError as e:
                print(f"Errore nel parsing JSON: {e}")
            except Exception as e:
                print(f"Errore generico: {e}")
            
            # Wait for 15 minutes before the next update
            next_update = datetime.now() + timedelta(minutes=15)
            print(f"Prossimo aggiornamento alle {next_update.strftime('%H:%M')}")
            time.sleep(15 * 60)  # 15 minutes in seconds
            
    except KeyboardInterrupt:
        print("\nProgramma terminato dall'utente.")
        sys.exit(0)

if __name__ == "__main__":
    estrai_dati_meteo()
