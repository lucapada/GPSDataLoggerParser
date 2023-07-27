import datetime
import math
import os
import threading
import time
import re

from . import SerialParser
from .GNSS import GNSS
from .UBXMessage import UBXMessage
from .UBXCodes import ublox_UBX_codes
from .Utils import strfind, msg2bits, splitBytes, find, decode_NAV_TIMEBDS, decode_NAV_TIMEGAL, decode_NAV_TIMEGPS, \
    decode_NAV_TIMEGLO, decode_NAV_TIMEUTC, decode_RXM_RAWX

from datetime import datetime, timedelta

ATTEMPTS_DEFAULT = 5
SEC_TO_WAIT_DEFAULT = 10

# utilizzo la soglia di buffer (impostata a 512) per gli snapshot in fase di acquisizione
# SNAPSHOT_UBX_DEFAULT = 20
# SNAPSHOT_NMEA_DEFAULT = 100

class Logger():
    """
    Classe che gestisce la raccolta dati dal dispositivo.
    """

    def __init__(self, mainWindow, active_serial: SerialParser, filePath: str, gnss: dict, weekField: bool, leapSField: bool):
        """
        Costruttore dell'oggetto.

        :param mainWindow: collegamento alla GUI
        :param active_serial: oggetto SerialParser relativo alla connessione aperta
        :param filePath: percorso in cui salvare le elaborazioni
        :param gnss: dizionario contenente i GNSS configurati, da cui ricevere dati
        :param weekField: parametro booleano relativo all'inclusione del numero della settimana nel file inerente la sincronizzazione dei tempi tra GNSS e pc locale
        :param leapSField: parametro booleano relativo all'inclusione del numero dei leap seconds nel file inerente la sincronizzazione dei tempi tra GNSS e pc locale
        """
        self.serial = active_serial
        self.is_active = True
        gnssObj = GNSS
        for g in gnssObj['constellations']:
            if gnss[g['gnss']] == 1:
                g['enable'] = 1
            else:
                g['enable'] = 0
        self.gnss = gnssObj
        self.filePath = filePath
        self.mainWindow = mainWindow
        self.weekField = weekField
        self.leapSField = leapSField

        self.ubxFile = open(self.filePath + "/" + self.serial.port.replace("/","_") + "_rover.ubx","wb", 512)
        self.timeSyncFile = open(self.filePath + "/" + self.serial.port.replace("/","_") + "_times.txt", "wb", 512)
        self.timeSyncNMEAFile = open(self.filePath + "/" + self.serial.port.replace("/","_") + "_NMEA_times.txt", "wb", 512)
        self.nmeaFile = open(self.filePath + "/" + self.serial.port.replace("/","_") + "_NMEA.txt", "wb", 512)

        self.attempts = ATTEMPTS_DEFAULT

    def deactivateLogger(self):
        """
        Procedura che disattiva la periferica e riporta l'esito nella console.
        :return:
        """
        self.is_active = False
        self.printLog("[LOGGER] Deactivate Receiver")

    # Data Logging Main Function
    def logData(self):
        """
        Funzione principale per l'acquisizioni dei dati. E' la funzione che viene eseguita al lancio del thread. Nel dettaglio, configura la periferica salvandone lo stato e indicando i messaggi da ricevere (NMEA-GGA, UBX-RXM-RAWX, UBX-RXM-SFRBX, UBX-CFG-MSG, UBX-CFG-CFG).
        Successivamente si pone in ascolto ed elabora lo stream che riceve avvalendosi della funzione decode_ublox. Salva all'interno di files che vengono creati i risultati delle elaborazioni.
        :return:
        """
        while self.attempts > 0:
            try:
                t = threading.currentThread()

                if self.is_active:
                    # 1) chiudo e riapro la connessione
                    self.serial.close()
                    self.serial.open()
                    if self.serial.isOpen():
                        # 1.1) azzero i tentativi, visto che se sono qui sicuramente sono riuscito a ripristinare la connessione, azzero i contatori per gli snapshot
                        self.attempts = ATTEMPTS_DEFAULT
                        # SNAPSHOT_UBX = 0
                        # SNAPSHOT_NMEA = 0
                        # 2) configurazione UBLOX
                        replySave = self.configure_ublox(1)

                        # 3) COLLEZIONE DATI
                        tic = datetime.datetime.now()
                        receiverDelay = 0.05

                        # 3.1) inizio raccolta dati
                        rover_1 = 0
                        rover_2 = 0
                        while (rover_1 != rover_2) or (rover_1 == 0) or (rover_1 < 0):
                            currentTime = datetime.datetime.now() - tic
                            rover_1 = self.in_waiting()
                            time.sleep(receiverDelay)
                            rover_2 = self.in_waiting()
                        self.printLog("%.2f sec (%4d bytes -> %4d bytes)" % (currentTime.seconds, rover_1, rover_2))

                        # svuoto la porta raccogliendo i dati inviati finora e depositandoli in data_rover
                        data_rover = self.read(rover_1)

                        # 3.3) mi metto in ascolto perenne
                        while self.is_active and getattr(t, "running", True):
                            type = ""
                            currentTime = datetime.datetime.now() - tic
                            rover_init = self.in_waiting()
                            rover_1 = rover_init
                            rover_2 = rover_init
                            dtMax_rover = 2

                            while (rover_1 != rover_2 or rover_1 == rover_init) and currentTime.seconds < dtMax_rover:
                                currentTime = datetime.datetime.now() - tic
                                rover_1 = self.in_waiting()
                                time.sleep(receiverDelay)
                                rover_2 = self.in_waiting()

                            if(rover_1 == rover_2) and rover_1 != 0:
                                data_rover = self.read(rover_1)
                                self.ubxFile.write(data_rover)
                                # self.ubxFile.flush()
                                self.printLog("%.2f sec (%d bytes)" % (currentTime.seconds, rover_1))

                                # dopo 60 secondi raccolgo i tempi
                                # if currentTime.seconds == 60:
                                #     # mando le poll per il timesync dopo 60 secondi di osservazione
                                #     self.ublox_poll_message("NAV", "TIMEUTC", 0, 0)
                                #     if self.gnss['constellations'][0]['enable'] == 1:
                                #         self.ublox_poll_message("NAV", "TIMEGPS", 0, 0)
                                #     if self.gnss['constellations'][2]['enable'] == 1:
                                #         self.ublox_poll_message("NAV", "TIMEGAL", 0, 0)
                                #     if self.gnss['constellations'][3]['enable'] == 1:
                                #         self.ublox_poll_message("NAV", "TIMEBDS", 0, 0)
                                #     if self.gnss['constellations'][6]['enable'] == 1:
                                #         self.ublox_poll_message("NAV", "TIMEGLO", 0, 0)

                                # leggo il datarover
                                (ubxData, nmeaData) = self.decode_ublox_new(data_rover)

                                if (nmeaData is not None or ubxData is not None) and (len(nmeaData) > 0 or len(ubxData) > 0):
                                    if nmeaData is not None and len(nmeaData) > 0:
                                        type += " NMEA"
                                        for n in nmeaData:
                                            self.nmeaFile.write(bytes(n.encode()))
                                            riga = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\t" + n.split(",")[1] + "\n"
                                            self.timeSyncNMEAFile.write(bytes(riga.encode()))
                                        # SNAPSHOT_NMEA += len(nmeaData)
                                    if ubxData is not None and len(ubxData) > 0:
                                        for u in ubxData:
                                            if u[0] == "RXM-RAWX":
                                                type += " UBX"
                                                # aggiungo la week?
                                                weekInfo = ""
                                                if self.weekField is True:
                                                    weekInfo = "\t" + str(u[1]['week'])
                                                # aggiungo leapS?
                                                leapSInfo = ""
                                                if self.leapSField is True:
                                                    leapSInfo = "\t" + str(u[1]['leapS'])
                                                riga = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\t" + str(u[1]['rcvTow']) + weekInfo + leapSInfo + "\n"
                                                self.timeSyncFile.write(bytes(riga.encode()))
                                                # SNAPSHOT_UBX += 1

                                    self.printLog("Decoded %s message(s)" % (type[1:len(type)]))

                                    # temporaneamente disattivato: utilizzo la soglia a 512 nel buffer di output per gli snapshot...
                                    #
                                    # ogni X messaggi intercettati (quindi scritti) salvo uno snapshot
                                    # non uso il metodo closeStream perché differenzio UBX ed NMEA...
                                    # TODO: in caso di cambio di nomenclatura dei files, cambiare qui...
                                    # if SNAPSHOT_UBX >= SNAPSHOT_UBX_DEFAULT:
                                    #     self.printLog("%d datagram UBX reached. Save Snapshot..." % SNAPSHOT_UBX)
                                    #     self.ubxFile.close()
                                    #     self.timeSyncFile.close()
                                    #     # time.sleep(0.01)
                                    #     self.ubxFile = open(self.filePath + "/" + self.serial.port.replace("/", "_") + "_rover.ubx", "ab", 512)
                                    #     self.timeSyncFile = open(self.filePath + "/" + self.serial.port.replace("/", "_") + "_times.txt", "ab", 512)
                                    #     SNAPSHOT_UBX = 0
                                    #     self.printLog("UBX snapshot saved. Continue logging...")
                                    #
                                    # if SNAPSHOT_NMEA >= SNAPSHOT_NMEA_DEFAULT:
                                    #     self.printLog("%d NMEA sentences reached. Save Snapshot..." % SNAPSHOT_NMEA)
                                    #     self.ubxFile.close()
                                    #     self.nmeaFile.close()
                                    #     self.timeSyncNMEAFile.close()
                                    #     # time.sleep(0.01)
                                    #     self.ubxFile = open(self.filePath + "/" + self.serial.port.replace("/", "_") + "_rover.ubx", "ab", 512)
                                    #     self.nmeaFile = open(self.filePath + "/" + self.serial.port.replace("/", "_") + "_NMEA.txt", "ab", 512)
                                    #     self.timeSyncNMEAFile = open(self.filePath + "/" + self.serial.port.replace("/", "_") + "_NMEA_times.txt", "ab", 512)
                                    #     SNAPSHOT_NMEA = 0
                                    #     self.printLog("NMEA snapshot saved. Continue logging...")

                                currentTime = datetime.datetime.now() - tic
                                # del data_rover

                        # X-1) ripristino configurazione originale
                        if replySave:
                            self.printLog("Restoring saved u-blox receiver configuration...")
                            replyLoad = self.ublox_CFG_CFG("load")
                            tries = 0
                            while replySave and not replyLoad:
                                tries += 1
                                if tries > 3:
                                    self.printLog("It was not possible to reload the receiver previous configuration.")
                                    break
                                replyLoad = self.ublox_CFG_CFG("load")
                        self.deactivateLogger()
                        self.attempts = 0
                    # self.printLog("Closing logging files.")
                    # fileNames = self.closeStream(t, True)
                else:
                    self.printLog("Impossible to start logging: device is not enabled.")
            except OSError as errore:
                # il software prova autonomamente a ristabilire la connessione
                secToWait = SEC_TO_WAIT_DEFAULT

                # stampo errore
                self.printLog("LOGGER ERROR")
                errorText = "Oops. It seems that the receiver is no longer connected. It will make %d attempts to reconnect, every %d seconds." % (self.attempts, secToWait)
                self.printLog(errorText)

                # chiudo subito i files
                fileNames = self.closeStream(t, False)
                # riapro i files: OCCHIO ALL'INDICE di fileNames! GUARDARE I FILES ALL'INTERNO di closeStream!
                self.ubxFile = open(fileNames[0], "ab", 512)
                self.timeSyncFile = open(fileNames[1], "ab", 512)
                self.timeSyncNMEAFile = open(fileNames[2], "ab", 512)
                self.nmeaFile = open(fileNames[3], "ab", 512)

                # diminuisco i tentativi
                errorText = "Attempt no. %d" % (ATTEMPTS_DEFAULT - self.attempts)
                self.printLog(errorText)
                time.sleep(secToWait)
                self.attempts -= 1
            except Exception as exceptionError:
                self.printLog("LOGGER ERROR")
                self.printLog(exceptionError)
                self.printLog("Logging operation interrupted. No more data will be acquired")
                # in caso di eccezione non dovuta a dispositivo sconnesso, interrompo l'acquisizione
                # TODO: se si desidera consumare un tentativo, diminuire di uno al posto di impostare a 0
                self.attempts = 0

        self.printLog("Closing logging files.")

        file_name = self.ubxFile.name
        nmea_txt = self.nmeaFile.name[:-4] + "_def.txt"
        nmea_times_txt = self.timeSyncNMEAFile.name[:-4] + "_def.txt"

        fileNames = self.closeStream(t, True)

        # TODO: check da qui in poi
        # self.printLog("Updating NMEA files...")
        # # estrazione stringhe NMEA
        # acq_date = datetime.datetime.now
        # nmea_regex = re.compile(rb'\$GN[A-Z]{3}.*?\r\n')

        # with open(file_name, 'rb') as file:
        #     binary_data = file.read()

        # # crea i due file in cui salvare tempi e stringhe NMEA
        # nmea_file = open(nmea_txt, "w")
        # nmea_times_file = open(nmea_times_txt, "w")

        # nmea_strings = nmea_regex.findall(binary_data)
        # nmea_strings = [nmea.decode('utf-8') for nmea in nmea_strings]

        # for s in nmea_strings:
        #     # Estrae il timestamp dalla stringa NMEA
        #     timestamp = s.split(',')[1]
        #     # Converte il timestamp in un oggetto datetime e aggiunge 2 ore
        #     nmea_datetime = datetime.strptime(timestamp, "%H%M%S.%f").replace(year=acq_date.year, month=acq_date.month, day=acq_date.day)
        #     nmea_datetime = nmea_datetime + timedelta(hours=2)
        #     # Formatta il datetime nel formato desiderato
        #     formatted_datetime = nmea_datetime.strftime("%Y-%m-%d %H:%M:%S")
        #     # scrivo nei files
        #     nmea_times_file.write(formatted_datetime + "\t" + timestamp + "\n")
        #     nmea_file.write(s)

        # nmea_file.close()
        # nmea_times_file.close()

    def closeStream(self, threadObj, renameFiles = False):
        """
        Procedura che chiude i files in cui vengono salvati i dati e li rinomina aggiungendo il timestamp al termine del nome.
        :param threadObj: oggetto Thread relativo al log
        :param renameFiles: flag che rinomina il file con la data di inizio acquisizione se impostato a True
        :return: array contenente i nuovi nomi dei files
        """

        # X) chiudo gli stream
        self.ubxFile.close()
        self.timeSyncFile.close()
        self.timeSyncNMEAFile.close()
        self.nmeaFile.close()

        # X+1) rinomino i files acquisiti (solo se il booleano è a true)
        ts = getattr(threadObj, "nameTS", "")

        newFileNames = [
            self.filePath + "/" + self.serial.port.replace("/", "_") + "_" + ts + "_rover.ubx",
            self.filePath + "/" + self.serial.port.replace("/", "_") + "_" + ts + "_times.txt",
            self.filePath + "/" + self.serial.port.replace("/", "_") + "_" + ts + "_NMEA_times.txt",
            self.filePath + "/" + self.serial.port.replace("/", "_") + "_" + ts + "_NMEA.txt",
        ]

        # oldFileNames = [
        #     self.filePath + "/" + self.serial.port.replace("/", "_") + "_rover.ubx",
        #     self.filePath + "/" + self.serial.port.replace("/", "_") + "_times.txt",
        #     self.filePath + "/" + self.serial.port.replace("/", "_") + "_NMEA_times.txt",
        #     self.filePath + "/" + self.serial.port.replace("/", "_") + "_NMEA.txt"
        # ]

        oldFileNames = [
            self.ubxFile.name,
            self.timeSyncFile.name,
            self.timeSyncNMEAFile.name,
            self.nmeaFile.name
        ]

        if ts is not None and ts != "":
            if renameFiles is True:
                os.rename(oldFileNames[0], newFileNames[0])
                os.rename(oldFileNames[1], newFileNames[1])
                os.rename(oldFileNames[2], newFileNames[2])
                os.rename(oldFileNames[3], newFileNames[3])
                self.printLog("Renamed logging files adding timestamp to filename. Ready for RINEX conversion.")
                return newFileNames
            else:
                return oldFileNames
        else:
            return oldFileNames

    def printLog(self, msg):
        """
        Funzione che stampa a video nella console presente nella GUI il messaggio passato via parametro.
        :param msg: messaggio da stampare nella console.
        :return:
        """
        # print(msg, flush=True)
        self.mainWindow.printLog("[LOGGER \"" + self.serial.port + "\"]: " + msg)
        #print("[LOGGER \"" + self.serial.port + "\"]: " + msg, flush=True)

    # ---------- UBX FUNCTIONS ----------
    def configure_ublox(self, rate=1):
        """
        Questa funzione configura il ricevitore inviando la richiesta di configurazione (per ciascuna configurazione) un massimo di 3 volte.
        Inizialmente configura il ricevitore inviando un UBX-CFG-CFG.
        Successivamente imposta il rate (1Hz di default)
        Successivamente richiede che il ricevitore invii messaggi di tipo CFG-RAW-RAWX e CFG-RAW-SFRBX.
        Poi disabilita tutti gli NMEA, ad eccezione del GGA.
        :param rate: velocità (1Hz di default)
        :return:
        """
        # save receiver configuration
        self.printLog("Saving receiver configuration...")
        reply_SAVE = self.ublox_CFG_CFG('save')
        tries = 0
        while (reply_SAVE == False):
            tries += 1
            if (tries > 3):
                break

            self.serial_close_connect()
            reply_SAVE = self.ublox_CFG_CFG('save')

        if (reply_SAVE):
            self.printLog("done")
        else:
            self.printLog("failed")

        ## set measurement rate
        if (rate == -1):
            rate = 1
        self.printLog("Setting measurement rate to " + str(rate) + "Hz...")
        reply_RATE = self.ublox_CFG_RATE(int(1000 / rate), 1, 1)
        tries = 0
        while (reply_RATE == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_RATE = self.ublox_CFG_RATE(int(1000 / rate), 1, 1)

        if (reply_RATE):
            self.printLog("done")
        else:
            self.printLog("failed")

        ## enable raw measurement
        self.printLog("Enabling raw data output (necessary for .obs RINEX file)...")
        reply_RAW = self.ublox_CFG_MSG("RXM", "RAWX", 1)
        tries = 0
        while (reply_RAW == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_RAW = self.ublox_CFG_MSG("RXM", "RAWX", 1)

        if (reply_RAW):
            self.printLog("done")
        else:
            self.printLog("failed")

        ## enable SFRB buffer output!
        self.printLog(
            "Enabling u-blox receiver subframe buffer (SFRBX) messages (necessary for .nav RINEX files)...")
        reply_SFRBX = self.ublox_CFG_MSG("RXM", "SFRBX", 1)
        tries = 0
        while (reply_SFRBX == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_SFRBX = self.ublox_CFG_MSG("RXM", "SFRBX", 1)
        if (reply_SFRBX):
            self.printLog("done")
        else:
            self.printLog("failed")

        ## set GNSS
        self.printLog("Enabling u-blox receiver GNSS...")
        reply_GNSS = self.ublox_CFG_GNSS(self.gnss)
        tries = 0
        while (reply_GNSS == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_GNSS = self.ublox_CFG_GNSS(self.gnss)
        if (reply_GNSS):
            self.printLog("done")
        else:
            self.printLog("failed")

        ## enable GGA messages, disable all others NMEA messages.
        ## check page 143 of the UBX manual.
        self.printLog("Configuring u-blox receiver NMEA Standard/Proprietary messages:")
        self.ublox_CFG_MSG("NMEA", "GGA", 1)
        self.printLog("enabling GGA")
        self.ublox_CFG_MSG("NMEA", "GLL", 0)
        self.printLog("disabling GLL")
        self.ublox_CFG_MSG("NMEA", "GSA", 0)
        self.printLog("disabling GSA")
        self.ublox_CFG_MSG("NMEA", "GSV", 0)
        self.printLog("disabling GSV")
        self.ublox_CFG_MSG("NMEA", "RMC", 0)
        self.printLog("disabling RMC")
        self.ublox_CFG_MSG("NMEA", "VTG", 0)
        self.printLog("disabling VTG")
        self.ublox_CFG_MSG("NMEA", "GRS", 0)
        self.printLog("disabling GRS")
        self.ublox_CFG_MSG("NMEA", "GST", 0)
        self.printLog("disabling GST")
        self.ublox_CFG_MSG("NMEA", "ZDA", 0)
        self.printLog("disabling ZDA")
        self.ublox_CFG_MSG("NMEA", "GBS", 0)
        self.printLog("disabling GBS")
        self.ublox_CFG_MSG("NMEA", "DTM", 0)
        self.printLog("disabling DTM")
        ## nella versione 0.4.2 di goGPS mancano GBQ, GLQ, GNQ, GNS, GPQ, THS, TXT, VLW
        self.ublox_CFG_MSG("NMEA", "GBQ", 0)
        self.printLog("disabling GBQ")
        self.ublox_CFG_MSG("NMEA", "GLQ", 0)
        self.printLog("disabling GLQ")
        self.ublox_CFG_MSG("NMEA", "GNQ", 0)
        self.printLog("disabling GNQ")
        self.ublox_CFG_MSG("NMEA", "GNS", 0)
        self.printLog("disabling GNS")
        self.ublox_CFG_MSG("NMEA", "GPQ", 0)
        self.printLog("disabling GPQ")
        self.ublox_CFG_MSG("NMEA", "THS", 0)
        self.printLog("disabling THS")
        self.ublox_CFG_MSG("NMEA", "TXT", 0)
        self.printLog("disabling TXT")
        self.ublox_CFG_MSG("NMEA", "VLW", 0)
        self.printLog("disabling VLW")

        ## imposto NMEA proprietario
        self.ublox_CFG_MSG("PUBX", "POSITION", 0)
        self.printLog("disabling POSITION")
        self.ublox_CFG_MSG("PUBX", "RATE", 0)
        self.printLog("disabling RATE")
        self.ublox_CFG_MSG("PUBX", "SVSTATUS", 0)
        self.printLog("disabling SVSTATUS")
        self.ublox_CFG_MSG("PUBX", "TIME", 0)
        self.printLog("disabling TIME")
        self.ublox_CFG_MSG("PUBX", "CONFIG", 0)
        self.printLog("disabling CONFIG")

        return reply_SAVE

    def ublox_CFG_CFG(self, action):
        """
        Funzione che invia messaggi di tipo UBX-CFG-CFG allo scopo di configurare il ricevitore.
        :param action: indica il tipo di azione abbinata al messaggio (salvataggio della configurazione, caricamento della configurazione salvata, reset del dispositivo)
        :return:
        """
        msg = UBXMessage("CFG", "CFG")
        # aggiungo la lunghezza
        lunghezzaPayload = 13
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little'))
        # aggiungo le maschere
        clearMask = [b"\x00", b"\x00", b"\x00", b"\x00"]
        saveMask = [b"\x00", b"\x00", b"\x00", b"\x00"]
        loadMask = [b"\x00", b"\x00", b"\x00", b"\x00"]

        # a seconda dell'action il valore della maschera cambia...
        if (action == "save"):
            # saveMask = [b"\xff", b"\xff", b"\x00", b"\x00"]
            saveMask = [b"\x1f", b"\x1f", b"\x00", b"\x00"]
        elif (action == "clear"):
            clearMask = [b"\x1f", b"\x1f", b"\x00", b"\x00"]
            loadMask = [b"\x1f", b"\x1f", b"\x00", b"\x00"]
            # clearMask = [b"\xff", b"\xff", b"\x00", b"\x00"]
            # loadMask = [b"\xff", b"\xff", b"\x00", b"\x00"]
        elif (action == "load"):
            loadMask = [b"\x1f", b"\x1f", b"\x00", b"\x00"]
            # loadMask = [b"\xff", b"\xff", b"\x00", b"\x00"]

        msg.aggiungiBytes(clearMask)
        msg.aggiungiBytes(saveMask)
        msg.aggiungiBytes(loadMask)

        # 7 sarebbe 00000111, pag. 196 del manuale sarebbe devEEPROM, devFlash e devBBR, non devSpiFlash.
        deviceMask = 7
        msg.aggiungiBytes(deviceMask.to_bytes(1, 'little'))

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())

        # invio la richiesta e raccolgo la risposta
        self.send_message(msg.getMessaggio(True), True, False)
        time.sleep(0.01)
        out = self.ublox_check_ACK("CFG", "CFG")
        return out

    def ublox_check_ACK(self, cls, id):
        '''
        Controlla che arrivi un ACK dopo una poll per un dato messaggio.
        :param cls: classe del messaggio
        :param id: id del messaggio
        :return:
        '''
        out = False

        msg = UBXMessage("ACK", "ACK")
        lunghezzaPayload = 2
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little'))
        bcls, bid = ublox_UBX_codes(cls, id)
        msg.aggiungiBytes([bcls, bid])

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())

        # acquisisco il time di ora
        start_time = datetime.datetime.now()
        # aspetto massimo mezzo secondo
        dtMax = 5
        reply_1 = 0
        reply_2 = 0
        while (reply_1 != reply_2) or reply_1 == 0:
            # acquisisto l'ora corrente
            current_time = datetime.datetime.now()
            time_diff = current_time - start_time
            if time_diff.seconds > dtMax:
                return out

            reply_1 = self.in_waiting()
            time.sleep(0.5)
            reply_2 = self.in_waiting()
            # print(str(reply_1) + " - " + str(reply_2) + " (" + str(time_diff.seconds) + "s)")

        reply = ''.join(msg2bits(splitBytes(self.read(reply_1))))
        msgBin = ''.join(msg2bits(msg.getMessaggio()[0:3]))

        idx = strfind(msgBin, reply)
        if (len(idx) > 0 and len(reply[idx[0]:]) >= 10):
            compACK = ''.join(msg2bits(msg.getMessaggio()))
            reply = reply[idx[0]:(idx[0] + len(compACK))]
            if (reply == compACK):
                out = True
        return out

    def ublox_CFG_MSG(self, cls, id, mode):
        """
        Invia un messaggio UBX-CFG-MSG indicando (mode = 1 o 0) al ricevitore di inviare/bloccare l'invio di un messaggio con quella classe/id.
        :param cls: classe del messaggio
        :param id: identificativo del messaggio
        :param mode: modalità (1 per voler ricevere il messaggio, 0 per non riceverlo)
        :return:
        """
        msg = UBXMessage("CFG", "MSG")
        # aggiungo la lunghezza
        lunghezzaPayload = 3
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little'))
        # se rate = 1, lo voglio, altrimenti no
        if mode == 1:
            rate = b"\x01"
        else:
            rate = b"\x00"

        (bCls, bId) = ublox_UBX_codes(cls, id)
        msg.aggiungiBytes([bCls, bId])
        msg.aggiungiByte(rate)

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())

        # invio la richiesta e raccolgo la risposta
        self.send_message(msg.getMessaggio(True), True, True)
        return self.ublox_check_ACK("CFG", "MSG")

    def ublox_CFG_RATE(self, measRate, navRate, timeRef):
        """
        Invia un messaggio UBX-CFG-RATE, impostando measRate, navRate e timeRef.
        :param measRate: velocità misurazioni (in ms)
        :param navRate: velocità navigazione (in ms)
        :param timeRef: riferimento temporale
        :return:
        """
        msg = UBXMessage("CFG", "RATE")
        # aggiungo la lunghezza
        lunghezzaPayload = 6
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little'))

        # imposto measRate (in ms!)
        msg.aggiungiBytes(measRate.to_bytes(2, 'little', signed=False))
        # imposto navRate (in cicli!)
        msg.aggiungiBytes(navRate.to_bytes(2, 'little', signed=False))
        # imposto timeRef: è questo quello che è cambiato dalla versione 18:
        #   0: UTC Time
        #   1: GPS
        #   2: GLONASS Time
        #   3: BeiDou Time
        #   4: Galileo Time
        #   5: Navlc Time
        msg.aggiungiBytes(timeRef.to_bytes(2, 'little', signed=False))

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())

        # invio la richiesta e raccolgo la risposta
        self.send_message(msg.getMessaggio(True), True, True)
        return self.ublox_check_ACK("CFG", "RATE")

    def ublox_CFG_GNSS(self, gnssParams):
        """
        Invia un messaggio UBX-CFG-GNSS attivando la ricezione di messaggi da quel determinato GNSS.
        :param gnssParams: informazioni GNSS
        :return:
        """
        msg = UBXMessage("CFG", "GNSS")
        # aggiungo la lunghezza
        lunghezzaPayload = 4 + 8 * len(gnssParams['constellations'])
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little', signed=False))

        # ora compongo il payload
        msg.aggiungiBytes(b"\x00")  # msgVer
        msg.aggiungiBytes(b"\x00")  # numTrkChHw (read only)
        msg.aggiungiBytes(gnssParams['chToUse'].to_bytes(1, 'little'))  # numTrkChUse, 20 = 32.
        msg.aggiungiBytes(len(gnssParams['constellations']).to_bytes(1, 'little'))  # numConfigBlocks

        for b in gnssParams['constellations']:
            msg.aggiungiBytes(b['gnssId'].to_bytes(1, 'little'))  # gnssId
            msg.aggiungiBytes(b['minCh'].to_bytes(1, 'little'))  # resTrkCh (chMin)
            msg.aggiungiBytes(b['maxCh'].to_bytes(1, 'little'))  # maxTrkCh (chMax)
            msg.aggiungiBytes(b"\x00")  # reserved1
            # devo comporre la mask. Parto dalla destra, come per le configurazioni, quindi:
            msg.aggiungiBytes(b['enable'].to_bytes(1, 'little'))  # enable
            msg.aggiungiBytes(b"\x00")  # reserved
            msg.aggiungiBytes(b['signals'])  # sigConfMask
            msg.aggiungiBytes(
                b"\x01")  # reserved (in teoria, in pratica vedi i valori in GNSSParams sotto la voce "BitField 4..."

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())
        # invio la richiesta e raccolgo la risposta
        self.send_message(msg.getMessaggio(True), True, True)
        time.sleep(0.6)
        out = self.ublox_check_ACK("CFG", "GNSS")

        '''
        TODO: If Galileo is enabled, UBX-CFG-GNSS must be followed by UBX-CFG-CFG to save the current configuration to BBR
        and then by UBX-CFG-RST with resetMode set to Hardware reset.
        '''

        # self.ublox_CFG_CFG('save')
        return out

    def ublox_poll_message(self, ClassLab, MsgIDLab, payload_length, parameter=0):
        """
        Invia la richiesta di messaggio al ricevitore.
        :param ClassLab: classe del messaggio richiesto
        :param MsgIDLab: id del messaggio richiesto
        :param payload_length: lunghezza del payload
        :param parameter: eventuali parametri (0 per default)
        :return:
        """
        msg = UBXMessage(ClassLab, MsgIDLab)
        # aggiungo la lunghezza
        if (payload_length == 0):
            lunghezzaPayload = 0
            lunghezzaPayload_byte = lunghezzaPayload.to_bytes(2, 'little')
            msg.aggiungiBytes(lunghezzaPayload_byte)
        else:
            lunghezzaPayload = 1
            lunghezzaPayload_byte = lunghezzaPayload.to_bytes(2, 'little')
            msg.aggiungiBytes(lunghezzaPayload_byte)

            # aggiungo il payload
            # 1 byte HEX
            msg.aggiungiBytes(parameter.to_bytes(1, 'little'));

        # calcolo il checksum
        cs = msg.calcola_checksum()
        msg.aggiungiBytes(cs)

        # invio la richiesta e raccolgo la risposta, senza liberare quello che c'è nel buffer!
        self.send_message(msg.getMessaggio(True), True, True)

    def decode_ublox(self, msg):
        """
        Funzione che decodifica il messaggio proveniente dall'ublox (bytes). Distingue NMEA o UBX e alla fine ritorna entrambi.
        :param msg: messaggio in bytes
        :return:
        """
        msg = "".join(msg2bits(splitBytes(msg)))

        messaggioUBX = "".join(msg2bits([UBXMessage.SYNC_CHAR_1, UBXMessage.SYNC_CHAR_2]))  # b5 62
        posUBX = strfind(messaggioUBX, msg)

        messaggioNMEA = "".join(msg2bits([b"\x24", b"\x47", b"\x4e"]))  # $ G N
        posNMEA = strfind(messaggioNMEA, msg)

        # variabili che conterranno quello che andrò ad esportare
        data = []
        NMEA_sentences = []
        NMEA_string = ""

        # il messaggio che ho è misto: occorre capire l'indice da cui partire a decodificare
        if len(posUBX) > 0 and len(posNMEA) > 0:
            if posUBX[0] < posNMEA[0]:
                pos = posUBX[0]
            else:
                pos = posNMEA[0]
        elif len(posUBX) > 0:
            pos = posUBX[0]
        elif len(posNMEA) > 0:
            pos = posNMEA[0]
        else:
            return (None, None)

        # inizio la fase di decodifica del messaggio
        i = 0

        # controllo che io abbia UBX o NMEA nei primi 2/3 frammenti
        while (pos + 16) <= len(msg):
            # controllo se ho l'header UBX
            if msg[pos:(pos + 16)] == messaggioUBX:
                # aumento il contatore
                i += 1
                # salto i primi due bytes di intestazione del messaggio
                pos += 16
                # ora dovrei avere classe, id e lunghezza del payload
                if (pos + 32) <= len(msg):
                    # prendo la classe
                    classId = int(msg[pos:(pos + 8)], 2).to_bytes(1, byteorder='big')
                    pos += 8
                    # prendo l'id
                    msgId = int(msg[pos:(pos + 8)], 2).to_bytes(1, byteorder='big')
                    pos += 8

                    # controllo che il messaggio non sia troncato
                    if (len(find(posUBX, pos, 1)) > 0):
                        f = find(posUBX, pos, 1)[0]
                    else:
                        f = 0
                    posNext = posUBX[f]
                    posRem = posNext - pos

                    # estraggo la lunghezza del payload (2 byte)
                    LEN1 = int(msg[pos:(pos + 8)], 2)
                    pos += 8
                    LEN2 = int(msg[pos:(pos + 8)], 2)
                    pos += 8

                    LEN = LEN1 + (LEN2 * pow(2, 8))

                    if LEN != 0:
                        # subito dopo la lunghezza ho il payload lungo LEN, poi due byte di fine stream (checksum)
                        if (pos + (8 * LEN) + 16) <= len(msg):
                            # calcolo il checksum
                            CK_A = 0
                            CK_B = 0

                            slices = []

                            j = pos - 32
                            while j < (pos + 8 * LEN):
                                t = msg[j:(j + 8)]
                                slices.append(int(msg[j:(j + 8)], 2))
                                j += 8

                            for r in range(len(slices)):
                                CK_A = CK_A + slices[r]
                                CK_B = CK_B + CK_A

                            CK_A = CK_A % 256
                            CK_B = CK_B % 256
                            CK_A_rec = int(msg[(pos + 8 * LEN):(pos + 8 * LEN + 8)], 2)
                            CK_B_rec = int(msg[(pos + 8 * LEN + 8):(pos + 8 * LEN + 16)], 2)

                            # controllo se il checksum corrisponde
                            if CK_A == CK_A_rec and CK_B == CK_B_rec:
                                s = msg[pos:(pos + (8 * LEN))]
                                nB = math.ceil(len(s) / 8)
                                MSG = int(s, 2).to_bytes(nB, 'little')
                                MSG = splitBytes(MSG)
                                # posso analizzare il messaggio nel dettaglio, esaminando il payload con l'opportuna funzione in base a id, classe
                                if classId == b"\x01":  # NAV
                                    if msgId == b"\x24":  # NAV-TIMEBDS
                                        data.append(decode_NAV_TIMEBDS(MSG))
                                    elif msgId == b"\x25":  # NAV-TIMEGAL
                                        data.append(decode_NAV_TIMEGAL(MSG))
                                    elif msgId == b"\x20":  # NAV-TIMEGPS
                                        data.append(decode_NAV_TIMEGPS(MSG))
                                    elif msgId == b"\x23":  # NAV-TIMEGLO
                                        data.append(decode_NAV_TIMEGLO(MSG))
                                    elif msgId == b"\x21":  # NAV-TIMEUTC
                                        data.append(decode_NAV_TIMEUTC(MSG))
                                elif classId == b"\x02": # RXM
                                    if msgId == b"\x15": # RXM-RAWX
                                        data.append(decode_RXM_RAWX(MSG))
                            else:
                                self.printLog("Checksum error.")
                                # salto il messaggio troncato
                                if posRem > 0 and (posRem % 8) != 0 and 8 * (LEN + 4) > posRem:
                                    self.printLog("Truncated UBX message, detected and skipped")
                                    pos = posNext
                                    continue

                            pos += 8 * LEN
                            pos += 16
                        else:
                            break
                else:
                    break
            # controllo se ho l'header NMEA
            elif (pos + 24) <= len(msg) and msg[pos:(pos + 24)] == messaggioNMEA:
                # cerco la fine del messaggio (CRLF)
                # NMEA0183 solitamente è lungo 82, ma al fine di evitare lunghezze non valide sono usati un massimo di 100 caratteri.
                if (len(msg) - pos) < 800:
                    posFineNMEA = strfind("".join(msg2bits(splitBytes(b"\x0d\x0a"))), msg[pos:])
                else:
                    posFineNMEA = strfind("".join(msg2bits(splitBytes(b"\x0d\x0a"))), msg[pos:(pos + 800)])
                if len(posFineNMEA) > 0:
                    # salvo la stringa
                    while msg[pos:(pos + 8)] != "00001101":
                        NMEA_string += chr(int(msg[pos:(pos + 8)], 2))
                        pos += 8

                    # salvo soltanto l'\n
                    pos += 8
                    NMEA_string += chr(int(msg[pos:(pos + 8)], 2))
                    pos += 8

                    NMEA_sentences.append(NMEA_string)
                    NMEA_string = ""
                else:
                    # la sentence NMEA è iniziata, ma non è disponibile.
                    # scorro l'header e continuo
                    pos += 24
            else:
                # controllo se ci sono altri pacchetti
                # pos = pos_UBX(find(pos_UBX > pos, 1));
                # if (isempty(pos)), break, end;
                if len(find(posUBX, pos, 1)) > 0:
                    p = find(posUBX, pos, 1)[0]
                    if len(posUBX) >= p:
                        pos = posUBX[p]
                else:
                    break
        return (data, NMEA_sentences)

    def decode_ublox_new(self, msg):
            try:
                # trovo tutte le stringhe NMEA
                NMEA_regex = re.compile(rb'\$GN[A-Z]{3}.*?\r\n')
                NMEA_sentences = NMEA_regex.findall(msg)
                NMEA_sentences = [nmea.decode('utf-8') for nmea in NMEA_sentences]
                if len(NMEA_sentences) <= 0:
                    NMEA_sentences = None

                # processo gli UBX
                msg = "".join(msg2bits(splitBytes(msg)))
                
                messaggioUBX = "".join(msg2bits([UBXMessage.SYNC_CHAR_1, UBXMessage.SYNC_CHAR_2]))  # b5 62
                posUBX = strfind(messaggioUBX, msg)

                # variabili che conterranno quello che andrò ad esportare
                data = []
                
                if len(posUBX) > 0:
                    pos = posUBX[0]
                else:
                    return (None, NMEA_sentences)

                # inizio la fase di decodifica del messaggio
                i = 0

                # controllo che io abbia UBX o NMEA nei primi 2/3 frammenti
                while (pos + 16) <= len(msg):
                    # controllo se ho l'header UBX
                    if msg[pos:(pos + 16)] == messaggioUBX:
                        # aumento il contatore
                        i += 1
                        # salto i primi due bytes di intestazione del messaggio
                        pos += 16
                        # ora dovrei avere classe, id e lunghezza del payload
                        if (pos + 32) <= len(msg):
                            # prendo la classe
                            classId = int(msg[pos:(pos + 8)], 2).to_bytes(1, byteorder='big')
                            pos += 8
                            # prendo l'id
                            msgId = int(msg[pos:(pos + 8)], 2).to_bytes(1, byteorder='big')
                            pos += 8

                            # controllo che il messaggio non sia troncato
                            if (len(find(posUBX, pos, 1)) > 0):
                                f = find(posUBX, pos, 1)[0]
                            else:
                                f = 0
                            posNext = posUBX[f]
                            posRem = posNext - pos

                            # estraggo la lunghezza del payload (2 byte)
                            LEN1 = int(msg[pos:(pos + 8)], 2)
                            pos += 8
                            LEN2 = int(msg[pos:(pos + 8)], 2)
                            pos += 8

                            LEN = LEN1 + (LEN2 * pow(2, 8))

                            if LEN != 0:
                                # subito dopo la lunghezza ho il payload lungo LEN, poi due byte di fine stream (checksum)
                                if (pos + (8 * LEN) + 16) <= len(msg):
                                    # calcolo il checksum
                                    CK_A = 0
                                    CK_B = 0

                                    slices = []

                                    j = pos - 32
                                    while j < (pos + 8 * LEN):
                                        t = msg[j:(j + 8)]
                                        slices.append(int(msg[j:(j + 8)], 2))
                                        j += 8

                                    for r in range(len(slices)):
                                        CK_A = CK_A + slices[r]
                                        CK_B = CK_B + CK_A

                                    CK_A = CK_A % 256
                                    CK_B = CK_B % 256
                                    CK_A_rec = int(msg[(pos + 8 * LEN):(pos + 8 * LEN + 8)], 2)
                                    CK_B_rec = int(msg[(pos + 8 * LEN + 8):(pos + 8 * LEN + 16)], 2)

                                    # controllo se il checksum corrisponde
                                    if CK_A == CK_A_rec and CK_B == CK_B_rec:
                                        s = msg[pos:(pos + (8 * LEN))]
                                        nB = math.ceil(len(s) / 8)
                                        MSG = int(s, 2).to_bytes(nB, 'little')
                                        MSG = splitBytes(MSG)
                                        # posso analizzare il messaggio nel dettaglio, esaminando il payload con l'opportuna funzione in base a id, classe
                                        if classId == b"\x01":  # NAV
                                            if msgId == b"\x24":  # NAV-TIMEBDS
                                                data.append(decode_NAV_TIMEBDS(MSG))
                                            elif msgId == b"\x25":  # NAV-TIMEGAL
                                                data.append(decode_NAV_TIMEGAL(MSG))
                                            elif msgId == b"\x20":  # NAV-TIMEGPS
                                                data.append(decode_NAV_TIMEGPS(MSG))
                                            elif msgId == b"\x23":  # NAV-TIMEGLO
                                                data.append(decode_NAV_TIMEGLO(MSG))
                                            elif msgId == b"\x21":  # NAV-TIMEUTC
                                                data.append(decode_NAV_TIMEUTC(MSG))
                                        elif classId == b"\x02": # RXM
                                            if msgId == b"\x15": # RXM-RAWX
                                                data.append(decode_RXM_RAWX(MSG))
                                    else:
                                        self.printLog("Checksum error.")
                                        # salto il messaggio troncato
                                        if posRem > 0 and (posRem % 8) != 0 and 8 * (LEN + 4) > posRem:
                                            self.printLog("Truncated UBX message, detected and skipped")
                                            pos = posNext
                                            continue

                                    pos += 8 * LEN
                                    pos += 16
                                else:
                                    break
                        else:
                            break
                    else:
                        # TODO: provare questo...
                        # controllo se ci sono altri pacchetti
                        # pos = pos_UBX(find(pos_UBX > pos, 1));
                        # if (isempty(pos)), break, end;
                        if len(find(posUBX, pos, 1)) > 0:
                            p = find(posUBX, pos, 1)[0]
                            if len(posUBX) >= p:
                                pos = posUBX[p]
                        else:
                            break
                return (data, NMEA_sentences)
            except Exception as error:
                print(error)
                self.printLog("Print Error. Check console.")

    # --------------- serial FUNCTION ---------------
    def open_connection(self):
        self.serial.open()

    def serial_close_connect(self):
        """
        Funzione che chiude e riapre la connessione.
        :return:
        """
        try:
            self.serial.close()
        except self.serial.SerialException as e:
            self.printLog("Serial error: " + e)
            self.serial.close()

        self.serial.open()

    def in_waiting(self):
        """
        Funzione che restituisce il numero di bytes nel buffer della periferica.
        :return:
        """
        return self.serial.in_waiting

    def read(self, howBytes: int):
        """
        Funzione che legge i bytes indicati come parametro.
        :param howBytes: quanti bytes leggere dal buffer.
        :return:
        """
        return self.serial.read(howBytes)

    def send_message(self, messaggio, freeQueue=False, jumpException=False):
        """
        Funzione che invia un messaggio alla periferica liberando o meno la coda e ignorando o meno le possibili eccezioni.
        :param messaggio: messaggio in bytes da inviare
        :param freeQueue: booleano che indica se liberare o meno i bytes nel buffer di entrata
        :param jumpException: booleano che indica se restituire o meno eccezione in caso di errore
        :return:
        """
        if (freeQueue):
            bytes2read = self.serial.in_waiting
            if (bytes2read > 0):
                self.serial.read(bytes2read)
                time.sleep(0.01)
        try:
            self.serial.write(messaggio)
            time.sleep(0.01)
        except self.serial.SerialException as e:
            if not jumpException:
                # TODO: manca la stop async
                self.serial.write(messaggio)
                time.sleep(0.01)
            else:
                self.printLog("Serial write error: " + e)
