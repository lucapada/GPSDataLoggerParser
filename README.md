# GPSDataLogger and Parser
"GPSDataLogger and Parser" è il progetto realizzato per il corso "Progetto di Ingegneria Informatica" (5CFU, prof.ssa Maria Grazia Fugini) nell'area di ricerca relativa alle architetture e sistemi di elaborazione.

La traccia sviluppata è quella proposta dal prof. Mirko Reguzzoni: "GPS Data Logger and Parser". 

## Descrizione
The goal is to write a tool to real-time log the binary data stream provided by a GPS receiver, as well as parse this stream by converting it into standard data formats. The tool should manage one or more EVK8 u-blox receivers (available for testing), each of them connected to a COM port. The tool should log the binary stream and decrypt it to produce two ASCII files in RINEX and NMEA formats, containing the positioning information. A synchronization file linking GPS and computer time-stamps has to be written too.  The tool should be developed in Python, c or c++ languages.

## Soluzione Proposta
La richiesta è stata soddisfatta con la realizzazione di un applicativo in Python, cross-platform, versatile e scalabile. L'applicativo soddisfa tutti i requisiti richiesti, analizzati e commentati nella presentazione e nella relazione.

### Installazione ed Esecuzione del Software
Il software necessita l'installazione di Python per poter esseere eseguito. Una volta installato è possibile lanciare il software entrando nella directory del progetto e digitando 
`python main.py` nel Terminale/Windows PowerShell.

### Supporto
Per qualsiasi informazione o segnalazione di possibili malfunzionamenti è possibile scrivere a luca.padalino@mail.polimi.it

## Allegati
- Relazione
- Presentazione
- Documentazione del Codice Sorgente
