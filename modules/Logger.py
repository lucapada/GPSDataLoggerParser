import datetime
import time

from serial.serialutil import SerialException
from . import SerialParser as ser
from . import Reporter
from . import UBXMessage
from UBXCodes import ublox_UBX_codes
from .Utils import strfind


class Logger:

    def __init__(self, active_serial: ser.SerialParser, gnss: dict, filePath: str):
        # --------------------------------------------
        self._reporter = Reporter()
        # --------------------------------------------
        self.serial = active_serial
        self.is_active = True

    # Continuously log data
    def logData(self) -> str:
        # TODO: implementare qui la logica ora in realtime.py
        # data = ""
        # while self.is_active:
        #     try:
        #         with open(self._logfile, "a") as logfile:
        #             data = self.serial.getNewData()
        #             logfile.write(data)
        #
        #     # Handle if device disconnected
        #     except (SerialException, KeyboardInterrupt):
        #         self.is_active = False
        #         self.printLoggingMessage(
        #             f"(THREAD ERROR) Device disconnected, ending thread associated with the logger after closing files...")
        #
        # return data

    def printLoggingMessage(self, message:str):
        self._reporter.printLog(f"[{self.serial.port}]: {message}")

    # --------------- serial FUNCTION ---------------
    # OK
    def open_connection(self):
        self.serial.open()
    # OK
    def serial_close_connect(self):
        '''
        Funzione che chiude e riapre la connessione.
        :return:
        '''
        try:
            self.serial.close()
        except self.serial.SerialException as e:
            self.printLoggingMessage("Serial error: " + e)
            self.serial.close()

        self.serial.open()
    # OK
    def in_waiting(self):
        return self.serial.in_waiting
    # OK
    def read(self, howBytes: int):
        return self.serial.read(howBytes)
    # OK
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
                self.printLoggingMessage("Serial write error: " + e)

    # --------------- ublox FUNCTION ---------------
    def configure_ublox(self, rate=1):
        '''
        Questa funzione configura il ricevitore inviando la richiesta di configurazione (per ciascuna configurazione) un massimo di 3 volte.
        Inizialmente configura il ricevitore inviando un UBX-CFG-CFG.
        Successivamente imposta il rate (1Hz di default)
        Successivamente richiede che il ricevitore invii messaggi di tipo CFG-RAW-RAWX e CFG-RAW-SFRBX.
        Poi disabilita tutti gli NMEA, ad eccezione del GGA.
        '''
        # TODO: occhio qui sotto
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
        self.printLoggingMessage("Setting measurement rate to " + rate + "Hz...")
        reply_RATE = self.ublox_CFG_RATE(1000 / rate, 1, 1)
        tries = 0
        while (reply_RATE == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_RATE = self.ublox_CFG_RATE(1000 / rate, 1, 1)

        if (reply_RATE):
            self.printLoggingMessage("done")
        else:
            self.printLoggingMessage("failed")

        # enable raw measurement
        self.printLoggingMessage("Enabling raw data output (necessary for .obs RINEX file)...")
        reply_RAW = self.ublox_CFG_MSG("RXM", "RAWX", 1)
        tries = 0
        while (reply_RAW == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_RAW = self.ublox_CFG_MSG("RXM", "RAWX", 1)

        if (reply_RAW):
            self.printLoggingMessage("done")
        else:
            self.printLoggingMessage("failed")

        # enable SFRB buffer output!
        self.printLoggingMessage("Enabling u-blox receiver subframe buffer (SFRBX) messages (necessary for .nav RINEX files)...")
        reply_SFRBX = self.ublox_CFG_MSG("RXM", "SFRBX", 1)
        tries = 0
        while (reply_SFRBX == False):
            tries += 1
            if (tries > 3):
                break
            self.serial_close_connect()
            reply_SFRBX = self.ublox_CFG_MSG("RXM", "SFRBX", 1)
        if (reply_SFRBX):
            self.printLoggingMessage("done")
        else:
            self.printLoggingMessage("failed")

        # enable GGA messages, disable all others NMEA messages.
        # check page 143 of the UBX manual.
        self.printLoggingMessage("Configuring u-blox receiver NMEA Standard/Proprietary messages:")
        self.ublox_CFG_MSG("NMEA", "GGA", 1)
        self.printLoggingMessage("enabling GGA")
        self.ublox_CFG_MSG("NMEA", "GLL", 0)
        self.printLoggingMessage("disabling GLL")
        self.ublox_CFG_MSG("NMEA", "GSA", 0)
        self.printLoggingMessage("disabling GSA")
        self.ublox_CFG_MSG("NMEA", "GSV", 0)
        self.printLoggingMessage("disabling GSV")
        self.ublox_CFG_MSG("NMEA", "RMC", 0)
        self.printLoggingMessage("disabling RMC")
        self.ublox_CFG_MSG("NMEA", "VTG", 0)
        self.printLoggingMessage("disabling VTG")
        self.ublox_CFG_MSG("NMEA", "GRS", 0)
        self.printLoggingMessage("disabling GRS")
        self.ublox_CFG_MSG("NMEA", "GST", 0)
        self.printLoggingMessage("disabling GST")
        self.ublox_CFG_MSG("NMEA", "ZDA", 0)
        self.printLoggingMessage("disabling ZDA")
        self.ublox_CFG_MSG("NMEA", "GBS", 0)
        self.printLoggingMessage("disabling GBS")
        self.ublox_CFG_MSG("NMEA", "DTM", 0)
        self.printLoggingMessage("disabling DTM")
        # nella versione 0.4.2 di goGPS mancano GBQ, GLQ, GNQ, GNS, GPQ, THS, TXT, VLW
        self.ublox_CFG_MSG("NMEA", "GBQ", 0)
        self.printLoggingMessage("disabling GBQ")
        self.ublox_CFG_MSG("NMEA", "GLQ", 0)
        self.printLoggingMessage("disabling GLQ")
        self.ublox_CFG_MSG("NMEA", "GNQ", 0)
        self.printLoggingMessage("disabling GNQ")
        self.ublox_CFG_MSG("NMEA", "GNS", 0)
        self.printLoggingMessage("disabling GNS")
        self.ublox_CFG_MSG("NMEA", "GPQ", 0)
        self.printLoggingMessage("disabling GPQ")
        self.ublox_CFG_MSG("NMEA", "THS", 0)
        self.printLoggingMessage("disabling THS")
        self.ublox_CFG_MSG("NMEA", "TXT", 0)
        self.printLoggingMessage("disabling TXT")
        self.ublox_CFG_MSG("NMEA", "VLW", 0)
        self.printLoggingMessage("disabling VLW")

        # imposto NMEA proprietario
        self.ublox_CFG_MSG("PUBX", "POSITION", 0)
        self.printLoggingMessage("disabling POSITION")
        self.ublox_CFG_MSG("PUBX", "RATE", 0)
        self.printLoggingMessage("disabling RATE")
        self.ublox_CFG_MSG("PUBX", "SVSTATUS", 0)
        self.printLoggingMessage("disabling SVSTATUS")
        self.ublox_CFG_MSG("PUBX", "TIME", 0)
        self.printLoggingMessage("disabling TIME")
        self.ublox_CFG_MSG("PUBX", "CONFIG", 0)
        self.printLoggingMessage("disabling CONFIG")

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
        msg.aggiungiBytes(ublox_UBX_codes(cls, id))

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())

        # acquisisco il time di ora
        start_time = datetime.datetime.now()
        # aspetto massimo mezzo secondo
        dtMax = 0.5
        reply_1 = 0
        reply_2 = 0
        while reply_1 != reply_2 or reply_1 == 0:
            # acquisisto l'ora corrente
            current_time = datetime.datetime.now()
            time_diff = current_time - start_time
            if (time_diff.microseconds / 1000) > dtMax:
                return out

            reply_1 = self.in_waiting()
            time.sleep(0.1)
            reply_2 = self.in_waiting()

        reply = self.read(reply_1)

        idx = strfind(reply, msg.getMessaggio(True)[0:3])
        if (len(idx) > 0 and len(reply[idx[0]:]) >= 10):
            reply = reply[idx[0]:(idx[0] + 9)]
            if (msg.getMessaggio(True) == reply):
                out = True
        return out

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
        out = self.ublox_check_ACK("CFG", "CFG")
        time.sleep(0.01)
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

        msg.aggiungiBytes(ublox_UBX_codes(cls, id))
        msg.aggiungiByte(rate)

        # calcolo il checksum
        msg.aggiungiBytes(msg.calcola_checksum())

        # invio la richiesta e raccolgo la risposta
        self.send_message(msg.getMessaggio(True), True, True)
        return self.ublox_check_ACK("CFG", "MSG")

    def ublox_CFG_GNSS(self, gnssParams):
        '''
        Invia un messaggio UBX-CFG-GNSS attivando la ricezione di messaggi da quel determinato GNSS.
        '''

        msg = UBXMessage("CFG", "GNSS")
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
