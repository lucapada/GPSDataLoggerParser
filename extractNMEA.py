import re
from datetime import datetime, timedelta

file_name = input("Percorso (completo) del log .ubx (e.g. C:/../../../file.ubx): ")
acq_date = datetime.strptime(input("Data dell'acquisizione (gg/mm/aaaa): "), "%d/%m/%Y")

file_path = file_name[:-4]

nmea_regex = re.compile(rb'\$GN[A-Z]{3}.*?\r\n')

with open(file_name, 'rb') as file:
    binary_data = file.read()

# crea i due file in cui salvare tempi e stringhe NMEA
nmea_file = open(file_path + "_NMEA.txt", "w")
nmea_times_file = open(file_path + "_NMEA_times.txt", "w")

nmea_strings = nmea_regex.findall(binary_data)
nmea_strings = [nmea.decode('utf-8') for nmea in nmea_strings]

for s in nmea_strings:
    # Estrae il timestamp dalla stringa NMEA
    timestamp = s.split(',')[1]
    # Converte il timestamp in un oggetto datetime e aggiunge 2 ore
    nmea_datetime = datetime.strptime(timestamp, "%H%M%S.%f").replace(year=acq_date.year, month=acq_date.month, day=acq_date.day)
    nmea_datetime = nmea_datetime + timedelta(hours=2)
    # Formatta il datetime nel formato desiderato
    formatted_datetime = nmea_datetime.strftime("%Y-%m-%d %H:%M:%S")
    # scrivo nei files
    nmea_times_file.write(formatted_datetime + "\t" + timestamp + "\n")
    nmea_file.write(s[:-1])

nmea_file.close()
nmea_times_file.close()

print("Estrazione stringhe NMEA completata con successo. Controllare i risultati nella directory del file .ubx.")