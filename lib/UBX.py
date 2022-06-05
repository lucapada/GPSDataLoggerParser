import datetime
import time
from time import sleep
import serial

from lib import Codici, Utils, MessaggioUBX

BAUD_RATE = 57600


# BUFFER_SIZE = pow(2,12)
# MIN_BYTES = 0

class UBX:

    # --------------- SERIAL METHODS ---------------
    def __init__(self, serialObj):
        '''Costruttore della classe. Imposta il serialObj passato come parametro'''
        self.serialObj = serialObj

    def open_connection(self):
        self.serialObj.open()

    def serial_close_connect(self):
        '''
        Funzione che chiude e riapre la connessione.
        '''
        COMPort = self.serialObj.name
        try:
            self.serialObj.close()
        except serial.SerialException as e:
            Utils.printLog("Serial error: " + e, COMPort)
            self.serialObj.close()

        self.serialObj = serial.Serial(COMPort, baudrate=BAUD_RATE)
        self.serialObj.open()

    def in_waiting(self):
        return self.serialObj.in_waiting

    def read(self, howBytes: int):
        return self.serialObj.read(howBytes)

    def send_message(self, messaggio, freeQueue=False, jumpException=False):
        if (freeQueue):
            bytes2read = self.serialObj.in_waiting
            if (bytes2read > 0):
                self.serialObj.read(bytes2read)
                sleep(0.01)

        try:
            self.serialObj.write(messaggio)
            #sleep(0.01)
        except serial.SerialException as e:
            if (jumpException == False):
                # TODO: manca la stop async
                self.serialObj.write(messaggio)
                sleep(0.01)
            else:
                Utils.printLog("Serial write error: " + e)

    # --------------- UBLOX CONFIGURATION ---------------

    # OK
    def configure_ublox(self, rate=1):
        '''
        Questa funzione configura il ricevitore inviando la richiesta di configurazione (per ciascuna configurazione) un massimo di 3 volte.
        Inizialmente configura il ricevitore inviando un UBX-CFG-CFG.
        Successivamente imposta il rate (1Hz di default)
        Successivamente richiede che il ricevitore invii messaggi di tipo CFG-RAW-RAWX e CFG-RAW-SFRBX.
        Poi disabilita tutti gli NMEA, ad eccezione del GGA.
        '''
        # save receiver configuration
        # Utils.printLog(self.serialObj.name, "Saving receiver configuration...")
        # reply_SAVE = self.ublox_CFG_CFG('save')
        # tries = 0
        # while (reply_SAVE == False):
        #     tries += 1
        #     if (tries > 3):
        #         break
        #
        #     self.serial_close_connect()
        #     reply_SAVE = self.ublox_CFG_CFG('save')
        #
        # if (reply_SAVE):
        #     Utils.printLog("done", self.serialObj.name)
        # else:
        #     Utils.printLog("failed", self.serialObj.name)

        # set measurement rate
        # if (rate == -1):
        #    rate = 1
        Utils.printLog("Setting measurement rate to " + rate + "Hz...", self.serialObj.name)
        reply_RATE = self.ublox_CFG_RATE(1000 / rate, 1, 1)
        tries = 0
        while (reply_RATE == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_RATE = self.ublox_CFG_RATE(1000 / rate, 1, 1)

        if (reply_RATE):
            Utils.printLog("done", self.serialObj.name)
        else:
            Utils.printLog("failed", self.serialObj.name)

        # enable raw measurement
        Utils.printLog("Enabling raw data output (necessary for .obs RINEX file)...", self.serialObj.name)
        reply_RAW = self.ublox_CFG_MSG("RXM", "RAWX", 1)
        tries = 0
        while (reply_RAW == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_RAW = self.ublox_CFG_MSG("RXM", "RAWX", 1)

        if (reply_RAW):
            Utils.printLog("done", self.serialObj.name)
        else:
            Utils.printLog("failed", self.serialObj.name)

        # enable SFRB buffer output!
        Utils.printLog("Enabling u-blox receiver subframe buffer (SFRBX) messages...")
        reply_SFRBX = self.ublox_CFG_MSG("RXM", "SFRBX", 1)
        tries = 0
        while (reply_SFRBX == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_SFRBX = self.ublox_CFG_MSG("RXM", "SFRBX", 1)
        if (reply_SFRBX):
            Utils.printLog("done", self.serialObj.name)
        else:
            Utils.printLog("failed", self.serialObj.name)

        # enable GGA messages, disable all others NMEA messages.
        # check page 143 of the UBX manual.
        Utils.printLog("Configuring u-blox receiver NMEA Standard/Proprietary messages:", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GGA", 1)
        Utils.printLog("enabling GGA", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GLL", 0)
        Utils.printLog("disabling GLL", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GSA", 0)
        Utils.printLog("disabling GSA", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GSV", 0)
        Utils.printLog("disabling GSV", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "RMC", 0)
        Utils.printLog("disabling RMC", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "VTG", 0)
        Utils.printLog("disabling VTG", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GRS", 0)
        Utils.printLog("disabling GRS", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GST", 0)
        Utils.printLog("disabling GST", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "ZDA", 0)
        Utils.printLog("disabling ZDA", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GBS", 0)
        Utils.printLog("disabling GBS", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "DTM", 0)
        Utils.printLog("disabling DTM", self.serialObj.name)
        # nella versione 0.4.2 di goGPS mancano GBQ, GLQ, GNQ, GNS, GPQ, THS, TXT, VLW
        self.ublox_CFG_MSG("NMEA", "GBQ", 0)
        Utils.printLog("disabling GBQ", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GLQ", 0)
        Utils.printLog("disabling GLQ", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GNQ", 0)
        Utils.printLog("disabling GNQ", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GNS", 0)
        Utils.printLog("disabling GNS", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "GPQ", 0)
        Utils.printLog("disabling GPQ", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "THS", 0)
        Utils.printLog("disabling THS", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "TXT", 0)
        Utils.printLog("disabling TXT", self.serialObj.name)
        self.ublox_CFG_MSG("NMEA", "VLW", 0)
        Utils.printLog("disabling VLW", self.serialObj.name)

        # imposto NMEA proprietario
        self.ublox_CFG_MSG("PUBX", "POSITION", 0)
        Utils.printLog("disabling POSITION", self.serialObj.name)
        self.ublox_CFG_MSG("PUBX", "RATE", 0)
        Utils.printLog("disabling RATE", self.serialObj.name)
        self.ublox_CFG_MSG("PUBX", "SVSTATUS", 0)
        Utils.printLog("disabling SVSTATUS", self.serialObj.name)
        self.ublox_CFG_MSG("PUBX", "TIME", 0)
        Utils.printLog("disabling TIME", self.serialObj.name)
        self.ublox_CFG_MSG("PUBX", "CONFIG", 0)
        Utils.printLog("disabling CONFIG", self.serialObj.name)

    # OK
    def ublox_check_ACK(self, cls, id):
        '''
        Controlla che arrivi un ACK dopo una poll.
        '''
        out = False

        msg = MessaggioUBX.MessaggioUBX("ACK", "ACK")
        lunghezzaPayload = 2
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little'))
        msg.aggiungiBytes(Codici.ublox_UBX_codes(cls, id))

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())

        # acquisisco il time di ora
        start_time = datetime.datetime.now()
        # aspetto massimo mezzo secondo
        dtMax = 0.5
        reply_1 = 0
        reply_2 = 0
        while ((reply_1 != reply_2) or (reply_1 == 0)):
            # acquisisto l'ora corrente
            current_time = datetime.datetime.now()
            time_diff = current_time - start_time
            if ((time_diff.microseconds / 1000) > dtMax):
                return out

            reply_1 = self.in_waiting()
            sleep(0.1)
            reply_2 = self.in_waiting()

        reply = self.read(reply_1)

        idx = Utils.strfind(reply, msg.getMessaggio(True)[0:3])
        if (len(idx) > 0 and len(reply[idx[0]:]) >= 10):
            reply = reply[idx[0]:(idx[0] + 9)]
            if (msg.getMessaggio(True) == reply):
                out = True
        # if (~isempty(index) & length(reply(index:end)) >= 10)
        #     % extract acknowledge message from reply
        #     reply = reply(index:index+9);

        #     if (reply == ACK) %#ok<BDSCI>
        #         out = 1;
        #     end
        # end
        return out

    # OK (check delle maschere)
    def ublox_CFG_CFG(self, action):
        '''
        Funzione che invia messaggi di tipo UBX-CFG-CFG allo scopo di configurare il ricevitore.
        '''
        msg = MessaggioUBX.MessaggioUBX("CFG", "CFG")
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
        out = self.ublox_check_ACK("CFG", "CFG")
        sleep(0.01)
        return out

    # OK
    def ublox_CFG_MSG(self, cls, id, mode):
        '''
        Invia un messaggio UBX-CFG-MSG indicando (mode = 1 o 0) al ricevitore di inviare/bloccare l'invio di un messaggio con quella classe/id.
        '''
        msg = MessaggioUBX.MessaggioUBX("CFG", "MSG")
        # aggiungo la lunghezza
        lunghezzaPayload = 3
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little'))
        # se rate = 1, lo voglio, altrimenti no
        if mode == 1:
            rate = b"\x01"
        else:
            rate = b"\x00"

        msg.aggiungiBytes(Codici.ublox_UBX_codes(cls, id))
        msg.aggiungiByte(rate)

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())

        # invio la richiesta e raccolgo la risposta
        self.send_message(msg.getMessaggio(True), True, True)
        return self.ublox_check_ACK("CFG", "MSG")

    # OK
    def ublox_CFG_GNSS(self, gnssParams):
        '''
        Invia un messaggio UBX-CFG-GNSS attivando la ricezione di messaggi da quel determinato GNSS.
        '''

        msg = MessaggioUBX.MessaggioUBX("CFG", "GNSS")
        # aggiungo la lunghezza
        lunghezzaPayload = 4 + 8*len(gnssParams)
        msg.aggiungiBytes(lunghezzaPayload.to_bytes(2, 'little', signed=False))

        # ora compongo il payload
        msg.aggiungiBytes(b"\x00") # msgVer
        msg.aggiungiBytes(gnssParams.chToUse.to_bytes(1, 'little')) # numTrkChHw (read only)
        msg.aggiungiBytes(gnssParams.chToUse.to_bytes(1, 'little')) # numTrkChUse
        msg.aggiungiBytes(len(gnssParams).to_bytes(1, 'little')) # numConfigBlocks

        for b in gnssParams:
            msg.aggiungiBytes(b['gnssId'].to_bytes(1,'little')) # gnssId
            msg.aggiungiBytes(b['chMin'].to_bytes(1,'little')) # resTrkCh (chMin)
            msg.aggiungiBytes(b['chMax'].to_bytes(1,'little')) # maxTrkCh (chMax)
            msg.aggiungiBytes(b"\x00") # reserved1
            # devo comporre la mask. Parto dalla destra, come per le configurazioni, quindi:
            msg.aggiungiBytes(b['enable'].to_bytes(1,'little')) # enable
            msg.aggiungiBytes(b"\x00") # reserved
            msg.aggiungiBytes(b['signals']) # sigConfMask
            msg.aggiungiBytes(b"\x00") # reserved (in teoria, in pratica vedi i valori in GNSSParams sotto la voce "BitField 4...

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())
        # invio la richiesta e raccolgo la risposta
        self.send_message(msg.getMessaggio(True), True, True)
        out = self.ublox_check_ACK("CFG", "GNSS")
        time.sleep(0.5)
        return out

    # OK
    def ublox_CFG_RATE(self, measRate, navRate, timeRef):
        '''
        Invia un messaggio UBX-CFG-RATE, impostando measRate, navRate e timeRef.
        '''
        msg = MessaggioUBX.MessaggioUBX("CFG", "RATE")
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

    # OK
    def ublox_poll_message(self, ClassLab, MsgIDLab, payload_length, parameter=0):
        '''
        Invia la richiesta di messaggio al ricevitore.
        '''
        msg = MessaggioUBX.MessaggioUBX(ClassLab, MsgIDLab)
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
            # TODO: 1 byte HEX
            msg.aggiungiBytes(parameter.to_bytes(1, 'little'));

        # calcolo il checksum
        cs = msg.calcola_checksum()
        msg.aggiungiBytes(cs)

        # invio la richiesta e raccolgo la risposta, senza liberare quello che c'è nel buffer!
        self.send_message(msg.getMessaggio(True), True, True)
