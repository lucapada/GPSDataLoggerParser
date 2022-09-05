# GPSDataLogger and Parser
"GPSDataLogger and Parser" è il progetto realizzato per il corso "Progetto di Ingegneria Informatica" (5CFU, prof.ssa Maria Grazia Fugini) nell'area di ricerca relativa alle architetture e sistemi di elaborazione.

La traccia sviluppata è quella proposta dal prof. Mirko Reguzzoni: "GPS Data Logger and Parser". 

## Descrizione
L'obiettivo del progetto è scrivere uno strumento che registra in tempo reale il flusso di dati in formato binario, fornito da un ricevitore GPS, nonché analizzarlo convertendolo in formati di dati standard. Lo strumento deve gestire uno o più ricevitori u-blox EVK8 (disponibili per il test), ciascuno dei quali collegato a una porta COM. Lo strumento deve registrare il flusso binario e decriptarlo per produrre due file ASCII nei formati RINEX e NMEA, contenenti le informazioni di posizionamento. Deve essere scritto anche un file di sincronizzazione che colleghi i time-stamp del GPS e del computer.  Lo strumento deve essere sviluppato in linguaggio Python, c o c++.

## Soluzione Proposta
La richiesta è stata soddisfatta con la realizzazione di un applicativo in Python, cross-platform, versatile e scalabile. L'applicativo soddisfa tutti i requisiti richiesti, analizzati e commentati nella presentazione e nella relazione.

### Installazione ed Esecuzione del Software
Il software necessita l'installazione di Python per poter esseere eseguito. 
Successivamente è necessario installare i pacchetti relativi alla libreria utilizzata per la GUI digitando `pip install pyqt5`.
Ora è possibile lanciare il software entrando nella directory del progetto e digitando 
`python main.py` nel Terminale/Windows PowerShell.

### Supporto
Per qualsiasi informazione o segnalazione di possibili malfunzionamenti è possibile scrivere a luca.padalino@mail.polimi.it

## Allegati (contenuto della cartella "docs")
1. Relazione ai Tutor (proff. Mirko Reguzzoni e Lorenzo Rossi, D.I.C.A.)
2. Presentazione alla prof.ssa Titolare del Corso (prof.ssa Maria Grazia Fugini)
3. Slides di Presentazione del Progetto
4. Manuale Operativo
5. [Documentazione del Codice Sorgente](https://lucapada.github.io/GPSDataLoggerParser)
