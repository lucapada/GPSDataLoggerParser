import datetime
import json
import math
import time

import serial

from modules import GNSS
from modules.UBXCodes import ublox_UBX_codes
from modules.UBXMessage import UBXMessage
from modules.Utils import strfind, msg2bits, splitBytes, find, decode_NAV_TIMEBDS, decode_NAV_TIMEGAL, \
    decode_NAV_TIMEGPS, decode_NAV_TIMEGLO, decode_NAV_TIMEUTC


class LoggingTest():
    def __init__(self, port, baudrate, path, gnss):
        self.port = port
        self.baudrate = baudrate
        self.path = path
        self.gnss = gnss

        self.serial = serial.Serial(port, baudrate)
        if self.serial.isOpen():
            print("Connessione Aperta")

            self.is_active = True

            # TODO: da implementare di là
            self.ubxFile = open(path + self.serial.port + "_rover.ubx", "wb")
            self.timeSyncFile = open(path + self.serial.port + "_times.txt", "wb")
            self.nmeaFile = open(path + self.serial.port + "_NMEA.txt", "wb")
        else:
            print("Errore nella Connessione")
            self.is_active = False

    def deactivate(self):
        self.is_active = False
        self.printLog("deactivate " + self.serial.port)

    def logData(self):
        if self.is_active:
            # 1) chiudo e riapro la connessione
            self.serial.close()
            self.serial.open()
            if self.serial.isOpen():
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
                self.printLog("%7.4f sec (%4d bytes -> %4d bytes)" % (currentTime.seconds, rover_1, rover_2))

                # svuoto la porta raccogliendo i dati inviati finora e depositandoli in data_rover
                data_rover = self.read(rover_1)

                # 3.3) mi metto in ascolto perenne
                while self.is_active:
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
                        self.printLog("%.2f sec (%d bytes)" % (currentTime.seconds, rover_1))

                        # TODO: dopo 60 secondi raccolgo i tempi
                        if currentTime.seconds == 60:
                            # mando le poll per il timesync dopo 60 secondi di osservazione
                            self.ublox_poll_message("NAV", "TIMEUTC", 0, 0)
                            if self.gnss['constellations'][0]['enable'] == 1:
                                self.ublox_poll_message("NAV", "TIMEGPS", 0, 0)
                            if self.gnss['constellations'][2]['enable'] == 1:
                                self.ublox_poll_message("NAV", "TIMEGAL", 0, 0)
                            if self.gnss['constellations'][3]['enable'] == 1:
                                self.ublox_poll_message("NAV", "TIMEBDS", 0, 0)
                            if self.gnss['constellations'][6]['enable'] == 1:
                                self.ublox_poll_message("NAV", "TIMEGLO", 0, 0)

                        # leggo il datarover
                        (ubxData, nmeaData) = self.decode_ublox(data_rover)

                        type = ""
                        if (nmeaData is not None or ubxData is not None) and (len(nmeaData) > 0 or len(ubxData) > 0):
                            if nmeaData is not None and len(nmeaData) > 0:
                                type += " NMEA"
                                for n in nmeaData:
                                    self.nmeaFile.write(bytes(n.encode()))
                            if ubxData is not None and len(ubxData) > 0:
                                type += "UBX"
                                self.timeSyncFile.write(bytes(json.dumps(ubxData).encode()))
                            self.printLog("Decoded %s message(s)" % type)
                        currentTime = datetime.datetime.now() - tic

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
                self.deactivate()
            # X) chiudo gli stream
            self.ubxFile.close()
            self.timeSyncFile.close()
            self.nmeaFile.close()
            self.printLog("Closed logging files. Ready for RINEX conversion.")
        else:
            self.printLog("Impossible to start logging: device is not enabled.")

    # ---------- UBX FUNCTIONS ----------
    def configure_ublox(self, rate=1):
        '''
        Questa funzione configura il ricevitore inviando la richiesta di configurazione (per ciascuna configurazione) un massimo di 3 volte.
        Inizialmente configura il ricevitore inviando un UBX-CFG-CFG.
        Successivamente imposta il rate (1Hz di default)
        Successivamente richiede che il ricevitore invii messaggi di tipo CFG-RAW-RAWX e CFG-RAW-SFRBX.
        Poi disabilita tutti gli NMEA, ad eccezione del GGA.
        '''

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
        '''
        Funzione che invia messaggi di tipo UBX-CFG-CFG allo scopo di configurare il ricevitore.
        '''
        msg = UBXMessage("CFG", "CFG")
        # aggiungo la lunghezza
        lunghezzaPayload = 13
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little'))
        # aggiungo le maschere
        clearMask = [b"\x00", b"\x00", b"\x00", b"\x00"]
        saveMask  = [b"\x00", b"\x00", b"\x00", b"\x00"]
        loadMask  = [b"\x00", b"\x00", b"\x00", b"\x00"]

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
        Controlla che arrivi un ACK dopo una poll.
        :param cls:
        :param id:
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
        '''
        Invia un messaggio UBX-CFG-MSG indicando (mode = 1 o 0) al ricevitore di inviare/bloccare l'invio di un messaggio con quella classe/id.
        '''
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
        '''
        Invia un messaggio UBX-CFG-RATE, impostando measRate, navRate e timeRef.
        '''
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
        '''
        Invia un messaggio UBX-CFG-GNSS attivando la ricezione di messaggi da quel determinato GNSS.
        '''
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
            msg.aggiungiBytes(b"\x01")  # reserved (in teoria, in pratica vedi i valori in GNSSParams sotto la voce "BitField 4..."

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

        #self.ublox_CFG_CFG('save')
        return out

    def ublox_poll_message(self, ClassLab, MsgIDLab, payload_length, parameter=0):
        '''
        Invia la richiesta di messaggio al ricevitore.
        '''
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
        '''
        Funzione che decodifica il messaggio proveniente dall'ublox (bytes).
        Distingue NMEA o UBX e alla fine ritorna entrambi.

        :param msg:
        :param reporter:
        :return:
        '''
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
                    classId = int(msg[pos:(pos+8)], 2).to_bytes(1, byteorder='big')
                    pos += 8
                    # prendo l'id
                    msgId = int(msg[pos:(pos+8)], 2).to_bytes(1, byteorder='big')
                    pos += 8

                    # controllo che il messaggio non sia troncato
                    if(len(find(posUBX, pos, 1)) > 0):
                        f = find(posUBX, pos, 1)[0]
                    else: f = 0
                    posNext = posUBX[f]
                    posRem = posNext - pos

                    # estraggo la lunghezza del payload (2 byte)
                    LEN1 = int(msg[pos:(pos+8)], 2)
                    pos += 8
                    LEN2 = int(msg[pos:(pos+8)], 2)
                    pos += 8

                    LEN = LEN1 + (LEN2 * pow(2,8))

                    if LEN != 0:
                        # subito dopo la lunghezza ho il payload lungo LEN, poi due byte di fine stream (checksum)
                        if (pos + (8*LEN) + 16) <= len(msg):
                            # calcolo il checksum
                            CK_A = 0
                            CK_B = 0

                            slices = []

                            j = pos - 32
                            while j < (pos + 8*LEN):
                                t = msg[j:(j+8)]
                                slices.append(int(msg[j:(j+8)], 2))
                                j += 8

                            for r in range(len(slices)):
                                CK_A = CK_A + slices[r]
                                CK_B = CK_B + CK_A

                            CK_A = CK_A % 256
                            CK_B = CK_B % 256
                            CK_A_rec = int(msg[(pos+8*LEN):(pos+8*LEN+8)], 2)
                            CK_B_rec = int(msg[(pos+8*LEN+8):(pos+8*LEN+16)], 2)

                            # controllo se il checksum corrisponde
                            if CK_A == CK_A_rec and CK_B == CK_B_rec:
                                # posso analizzare il messaggio nel dettaglio, esaminando il payload con l'opportuna funzione in base a id, classe
                                if classId == b"\x01":  # NAV
                                    s = msg[pos:(pos+(8*LEN))]
                                    nB = math.ceil(len(s) / 8)
                                    MSG = int(s, 2).to_bytes(nB, 'little')
                                    MSG = splitBytes(MSG)
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
                            else:
                                self.printLog("Checksum error.")
                                # salto il messaggio troncato
                                if posRem > 0 and (posRem % 8) != 0 and 8*(LEN+4) > posRem:
                                    self.printLog("Truncated UBX message, detected and skipped")
                                    pos = posNext
                                    continue

                            pos += 8*LEN
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
                    while msg[pos:(pos+8)] != "00001101":
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

    # --------------- serial FUNCTION ---------------
    def open_connection(self):
        self.serial.open()

    def serial_close_connect(self):
        '''
        Funzione che chiude e riapre la connessione.
        :return:
        '''
        try:
            self.serial.close()
        except self.serial.SerialException as e:
            self.printLog("Serial error: " + e)
            self.serial.close()

        self.serial.open()

    def in_waiting(self):
        return self.serial.in_waiting

    def read(self, howBytes: int):
        return self.serial.read(howBytes)

    def send_message(self, messaggio, freeQueue=False, jumpException=False):
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

    # FUNZIONI OK
    def printLog(self, msg):
        print(msg)

# OK
def ublox_poll_message(self, ClassLab, MsgIDLab, payload_length, parameter=0):
    '''
    Invia la richiesta di messaggio al ricevitore.
    '''
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

gnss2en = ["GPS", "GLONASS", "Galileo"]
if "GPS" in gnss2en and "QZSS" not in gnss2en:
    gnss2en.append("QZSS")
if "QZSS" in gnss2en and "GPS" not in gnss2en:
    gnss2en.append("GPS")

gnss = GNSS.GNSS
print(gnss)
for g in gnss['constellations']:
    if g['gnss'] in gnss2en:
        g['enable'] = 1
    else:
        g['enable'] = 0
l = LoggingTest("COM3", 9600, "C:/Users/lucap/Desktop/provaGPSDLP/", gnss)
l.logData()
