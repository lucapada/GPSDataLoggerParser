import time
from math import ceil, floor
import numpy as np
import serial

from lib import GNSSParams, UBX, Utils, DecodificaUBX


class RealtimeUBX:
    def __init__(self, COMPort, fileRootOut, costellazioni: GNSSParams):
        self.comPort = COMPort
        self.fileRootOut = fileRootOut
        self.costellazioni = costellazioni
        self.flag = True

    def setFlag(self, value):
        self.flag = value

    def getFlag(self):
        return self.flag

    def start(self):
        # creo i files binari
        # rover binary stream
        fid_rover = open(self.fileRootOut + "_rover_" + self.comPort + "_000.bin", "a")
        # nmea sentences
        fid_nmea = open(self.fileRootOut + "_nmea_" + self.comPort + ".txt", "a")
        # hour
        hour = 0

        nN = self.costellazioni.getEnabledSat  # numero delle ambiguità di fase
        iono = []  # parametri ionosfera

        # -----------------------------------------------------------------------
        #                    connessione al ricevitore
        # -----------------------------------------------------------------------
        roverObj = serial.Serial(self.comPort, UBX.BAUD_RATE)
        if(roverObj.is_open):
            roverObj.close()
            roverObj.open()

        # configurazione del ricevitore
        ubxObj = UBX.UBX(roverObj)
        ubxObj.configure_ublox(1) #TODO: occhio al flag della configurazione!

        # ------- inizio dell'acquisizione -------
        tic = time.time()
        # stabilisco il ritardo del ricevitore
        receiver_delay = 0.05

        # ------- acquisizione dell'intestazione -------
        Utils.printLog("ROVER LOCK PHASE (HEADER PACKAGE)")

        rover_1 = 0
        rover_2 = 0
        while((rover_1 != rover_2) or (rover_1 == 0) or (rover_1 < 0)):
            # starting time
            current_time = time.time() - tic
            rover_1 = ubxObj.in_waiting()
            time.sleep(receiver_delay)
            rover_2 = ubxObj.in_waiting()

            Utils.printLog(current_time + "s (" + rover_1 + "bytes --> " + rover_2 + "bytes)", self.comPort)

        # svuoto la porta (dati non decodificati)
        data_rover = ubxObj.read(rover_1)

        # ------- posizione iniziale -------
        Utils.printLog("ROVER POSITIONING (STAND-ALONE)...", self.comPort)
        Utils.printLog("it might take some time to acquire signal from a sufficient number of satellites")

        # pseudoranges
        pr_R = []
        # ephemerides
        Eph = []
        # satellite with observations available
        satObs = []
        nSatObs_old = []

        # satellite with epemeris available
        satEph = []
        min_nsat_LS = 3 + self.costellazioni.getEnabledGNSS()

        while((len(satObs) < min_nsat_LS) or not any(Utils.ismember(satObs, satEph))):
            # TODO: cambiare qui nell'ottica del multicostellazione
            # poll available ephemeris
            ubxObj.ublox_poll_message("AID", "EPH", 0)
            time.sleep(0.1)
            # poll available ionosphere, Health and UTC
            ubxObj.ublox_poll_message("AID", "HUI", 0)
            time.sleep(0.1)

            # inizializzazione
            rover_1 = 0
            rover_2 = 0

            # inizio la determinazione delle epoche
            while(rover_1 != rover_2 or rover_1 == 0):
                # starting time
                current_time = time.time() - tic
                # controllo la porta
                rover_1 = ubxObj.in_waiting()
                time.sleep(receiver_delay)
                rover_2 = ubxObj.in_waiting()

            data_rover = ubxObj.read(rover_1)
            fid_rover.write(data_rover)
            (cell_rover, nmea_sentences) = DecodificaUBX.decode_ublox(data_rover,self.costellazioni)

            for i in range(len(cell_rover)):
                if(cell_rover[0] == "RXM-RAWX"):
                    time_GPS = round(cell_rover[i][1]["TOW"])
                    pr_R[0] = []
                    for c in cell_rover[i][2]:
                        pr_R[0].append(c["PRM"])
                elif(cell_rover[0] == "AID-EPH"):
                    idx = cell_rover[i][1].multiConstellation
                    if(idx > 0):
                        Eph[idx] = cell_rover[i][1]
                        weekno = Eph[idx][23]
                        Eph[idx][31] = Utils.weektime2tow(weekno, Eph[idx][31])
                        Eph[idx][32] = Utils.weektime2tow(weekno, Eph[idx][32])
                elif(cell_rover[0] == "AID-HUI"):
                    iono[0] = {
                        "alpha0": cell_rover[i][2]["alpha0"],
                        "alpha1": cell_rover[i][2]["alpha1"],
                        "alpha2": cell_rover[i][2]["alpha2"],
                        "alpha3": cell_rover[i][2]["alpha3"],
                        "beta0": cell_rover[i][2]["beta0"],
                        "beta1": cell_rover[i][2]["beta1"],
                        "beta2": cell_rover[i][2]["beta2"],
                        "beta3": cell_rover[i][2]["beta3"],
                    }
                elif(cell_rover[0] == "RXM-SFRBX"):
                    # decodificare qui i subframe
                    #TODO: una volta decodificati i subframes, fare qui il discorso dei subframes

            # prendo i satelliti con effemeridi disponibili
            satEph = []
            for i in range(len(Eph)):
                s = 0
                for j in Eph[i]:
                    s += abs(j)
                if s > 0: satEph.append(i)

            # elimino i dati se le effemeridi non sono disponibili
            for s in range(nN):
                if s not in satEph:
                    pr_R[s] = 0

            # satelliti con osservazioni disponibili
            satObs = []
            for p in range(len(pr_R)):
                if pr_R[p] != 0:
                    satObs.append(p)

            if len(nSatObs_old) or len(satObs) != nSatObs_old:
                Utils.printLog(len(satObs) + " satellites with ephemerides", self.comPort)
                nSatObs_old = len(satObs)


        # ricavo le lunghezze d'onda delle costellazioni
        # lambdas = self.costellazioni.getWaveLengths(Eph, nN)

        nS = 0
        for i in pr_R:
            nS += sum(i)
        Utils.printLog("ROVER approximate position computed using " + nS + " satellites", self.comPort)

        # ---------- acquisizione del prossimo messaggio (per la sincronizzazione) ----------
        Utils.printLog("ROVER SYNCHRONIZATION...", self.comPort)

        rover_1 = 0
        rover_2 = 0
        syncRover = False
        while not syncRover:
            # determino l'epoca
            while rover_1 != rover_2 or rover_1 == 0 or (rover_1 < 0):
                # starting time
                current_time = tic - time.time()
                # controllo la porta seriale
                rover_1 = ubxObj.in_waiting()
                time.sleep(receiver_delay)
                rover_2 = ubxObj.in_waiting()
                # stampo
                Utils.printLog(current_time + " sec. (" + rover_1 + "bytes --> " + rover_2 + "bytes)", self.comPort)

            data_rover = ubxObj.read(rover_1)
            (cell_rover, nmea_sentences) = DecodificaUBX.decode_ublox(data_rover, self.costellazioni)

            for i in range(len(cell_rover)):
                if (cell_rover[0] == "RXM-RAWX"):
                    # TODO: sempre nell'ottica del multiGNSS, di per sè questo non è il tempo di GPS, ma del GNSS di quel momento
                    time_GPS = round(cell_rover[i][1]["TOW"])
                    week_GPS = cell_rover[i][1]["WEEK"]
                    syncRover = True

        # starting time is set
        safety_lag = 0.1
        start_time = current_time - safety_lag

        # preparo l'epoca
        dtime = ceil(current_time-start_time)
        while (current_time-start_time) < dtime:
            current_time = tic - time.time()

        # aumento l'epoca GPS (in realtà no?!)
        time_GPS += dtime

        # reinizializzo il tempo di inizio
        start_time = start_time + dtime - 1

        # ---------- acquisizione dei dati dal ricevitore ----------
        b = 1 # posizione corrente nel buffer
        B = 20 # dimensione buffer
        # creo il buffer
        tick_R = []
        time_R = []
        week_R = []
        pr_R = []
        ph_R = []
        dop_R = []
        snr_R = []

        # inizializzo il contatore
        t = 1
        # inizializzo l'incremento temporale (default 1s)
        dtime = 1
        # avvio un loop infinito (fino a che non interrompo l'acquisizione)
        while self.getFlag():
            Utils.printLog("--- TIMING: epoch " + t + ": GPS Time=" + week_GPS + ":" + time_GPS, self.comPort)

            # gestisco il file
            if floor(t/3600) > hour:
                hour = floor(t/3600)
                hour_str = "%03d" %hour

                # chiudo il file precedente
                fid_rover.close()

                # apro un nuovo file con l'ora aggiornata
                fid_rover = open(self.fileRootOut + "_rover_" + self.comPort + "_" + hour_str + ".bin", "a")

                # TODO: a quanto pare l'NMEA non viene chiuso

            # prendo i dati dal ricevitore
            Utils.printLog("--- ROVER DATA ---", self.comPort)

            # acquisisco il tempo
            current_time = tic - time.time()
            step_time = round(current_time-start_time)

            # inizializzo i dati
            rover_init = ubxObj.in_waiting()
            rover_1 = rover_init
            rover_2 = rover_init

            # tempo di attesa massimo dal ricevitore
            dtMax_rover = 0.2
            while ((rover_1 != rover_2) or (rover_1 == rover_init)) and ((current_time-start_time-step_time) < dtMax_rover):
                # acquisisco il tempo
                current_time = tic - time.time()

                # check della porta seriale
                rover_1 = ubxObj.in_waiting()
                time.sleep(receiver_delay)
                rover_2 = ubxObj.in_waiting()

            # notifico
            Utils.printLog((current_time-start_time) + " sec (" + rover_1 + "bytes --> " + rover_2 + "bytes)", self.comPort)

            # gestisco i depositi temporanei (shift e reset)
            if dtime < B:
                tick_R[dtime:] = tick_R[0:(len(tick_R)-dtime-1)]
                time_R[dtime:] = time_R[0:(len(time_R)-dtime-1)]
                week_R[dtime:] = week_R[0:(len(week_R)-dtime-1)]
                pr_R[dtime:] = pr_R[0:(len(pr_R)-dtime-1)]
                ph_R[dtime:] = ph_R[0:(len(ph_R)-dtime-1)]
                dop_R[dtime:] = dop_R[0:(len(dop_R)-dtime-1)]
                snr_R[dtime:] = snr_R[0:(len(snr_R)-dtime-1)]

                tick_R[0:(dtime-1)] = []
                time_R[0:(dtime-1)] = []
                week_R[0:(dtime-1)] = []
                pr_R[0:(dtime-1)] = []
                ph_R[0:(dtime-1)] = []
                dop_R[0:(dtime-1)] = []
                snr_R[0:(dtime-1)] = []
            else:
                tick_R = []
                time_R = []
                week_R = []
                pr_R = []
                ph_R = []
                dop_R = []
                snr_R = []

            # leggo il tipo
            type = ""
            # controllo se la scrittura dei pacchetti è terminata
            if rover_1 == rover_2 and rover_1 != 0:
                # leggo dalla porta seriale
                data_rover = ubxObj.read(rover_1)
                # scrivo subito nel fid del rover
                fid_rover.write(data_rover)

                # decodifico il messaggio, stavolta mi interesso anche delle NMEA
                (cell_rover, nmea_sentences) = DecodificaUBX.decode_ublox(data_rover, self.costellazioni)

                # creo dei contatori per i tipi di dato acquisiti
                nEPH = 0
                nHUI = 0

                for i in range(len(cell_rover)):
                    if(cell_rover[i][0] == "RXM-RAWX"):
                        # calcolo l'indice del buffer
                        index = time_GPS - round(cell_rover[i][1]["TOW"]) + 1
                        if index <= B:
                            while index < 1:
                                time_GPS += 1
                                index = time_GPS - round(cell_rover[i][1]["TOW"]) + 1

                            # scrivo nel buffer
                            tick_R[index] = 1
                            time_R[index] = round(cell_rover[i][1]["TOW"])
                            week_R[index] = cell_rover[i][1]["WEEK"]
                            pr_R[index] = []
                            for k in range(len(cell_rover[i][2])):
                                pr_R.append(cell_rover[i][2][k]["PRM"])
                            ph_R[index] = []
                            for k in range(len(cell_rover[i][2])):
                                ph_R.append(cell_rover[i][2][k]["CPM"])
                            dop_R[index] = []
                            for k in range(len(cell_rover[i][2])):
                                dop_R.append(cell_rover[i][2][k]["DOM"])
                            snr_R[index] = []
                            for k in range(len(cell_rover[i][2])):
                                dop_R.append(cell_rover[i][2][k]["CNO"])

                            # manage nealry null data
                            for pos in range(len(ph_R)):
                                if abs(ph_R[index][pos]) < 1e-100:
                                    ph_R[index][pos] = 0
                            type.append("RXM-RAWX ")
                    elif cell_rover[i][0] == "AID-EPH":
                        # prendo il numero del satellite
                        idx = cell_rover[i][1][0]
                        if len(idx) != 0 and idx > 0:
                            Eph[idx] = cell_rover[i][1]
                            weekno = Eph[idx][23]
                            Eph[idx][31] = Utils.weektime2tow(weekno, Eph[idx][31])
                            Eph[idx][32] = Utils.weektime2tow(weekno, Eph[idx][32])
                        if nEPH == 0:
                            type.append("AID-EPH ")
                        nEPH += 1
                    elif cell_rover[i][0] == "AID-HUI":
                        # parametri di ionosfera
                        iono[0] = cell_rover[i][2][8:15]
                        if nHUI == 0:
                            type.append("AID-HUI ")
                        nHUI += 1

                #TODO: non sono sicuro che funzioni
                if len(nmea_sentences) > 0:
                    n = len(nmea_sentences)
                    for i in range(n):
                        fid_nmea.write([chr(nmea) for nmea in nmea_sentences[n]])
                    type.append("NMEA ")
            # acquisizione del tempo
            current_time = tic - time.time()

            i = min(b, B)
            sat_pr = []
            for tPR in pr_R[i]:
                if tPR != 0:
                    sat_pr.append(tPR)
            sat_ph = []
            for tPH in ph_R[i]:
                if tPH != 0:
                    sat_ph.append(tPH)
            sat = sat_pr + sat_ph

            Utils.printLog("decoding: " + (current_time-start_time) + " sec (" + "".join(type) + " messages)", self.comPort)
            Utils.printLog("GPS time= " + time_R[i] + "(" + len(sat) + " satellites)", self.comPort)

            (sys_pr, prn_pr) = self.costellazioni.find_sat_system(sat_pr)
            (sys_ph, prn_ph) = self.costellazioni.find_sat_system(sat_ph)

            Utils.printLog("C1 SAT: " + [sys_pr[j] + " " + prn_pr[j] for j in range(len(sat_pr))], self.comPort)
            Utils.printLog("L1 SAT: " + [sys_ph[j] + " " + prn_ph[j] for j in range(len(sat_ph))], self.comPort)

            # richiedo le effemeridi
            if len(sat) > 0 and index > 0:
                # satelliti con osservazioni disponibili per la richiesta di effemeridi
                conf_sat_eph = []
                conf_sat_eph[sat_pr-1] = 1
                # ciclo di aggiornamento degli effemeridi
                conf_eph = []
                for e in Eph:
                    if abs(e[0]) == 0:
                        conf_eph.append(1)
                    else: conf_eph.append(0)
                sat_index = np.argsort(snr_R[index])[::-1]

                # TODO: non sono sicuro delle successive due righe
                conf_sat_eph = conf_sat_eph[sat_index]
                conf_eph = conf_eph[sat_index]

                check = 0
                i = 1

                while check == 0 and i <= nN:
                    s = sat_index[i]
                    # se il satellite i è disponibile
                    if abs(conf_sat_eph[i]) == 1:
                        if conf_eph[i] == 0:
                            time_eph = Eph[s][31]
                            tk = Utils.check_t(time_GPS-time_eph)
                        if conf_eph[i] == 1 or tk > 3600:
                            ubxObj.ublox_poll_message("AID", "EPH", 1, s.to_bytes(2, 'big'))
                            Utils.printLog("Satellite " + s + " ephemeris polled", self.comPort)
                        check = 1
                    i += 1

            # TODO: qui dovrebbe valorizzare la variabile locale "flag". In teoria uso get e set esterni.

            # computo eventuale delay dato dal processing dei dati
            dtime1 = ceil(current_time-start_time-step_time)
            # computo il delay dato da cause esterne dopo il processing dei dati
            current_time = tic - time.sleep()
            dtime2 = ceil(current_time-start_time-step_time)
            if dtime2 > dtime1:
                Utils.printLog("WARNING: System slowdown: " + (current_time-start_time) + " (delay " + (dtime2-dtime1) + " sec)", self.comPort)
            dtime = dtime2

            # vado alla prossima epoca
            while (current_time-start_time-step_time) < dtime:
                current_time = tic - time.time()

            # incremento l'epoca GPS
            time_GPS += dtime
            b += dtime

            if t == 1:
                start_time += dtime

        # ripristino della configurazione ublox
        # TODO: attivare dopo aver modificato CFG_CFG
        # Utils.printLog("Restoring saved u-blox receiver configuration...", self.comPort)
        # reply_load = ubxObj.ublox_CFG_CFG("load")
        # tries = 0
        # while not reply_load:
        #     tries += 1
        #     if tries > 3:
        #         Utils.printLog("It was not possible to reload the receiver previous configuration.", self.comPort)
        #         break
        #     reply_load = ubxObj.ublox_CFG_CFG("load")

        # chiudo connessioni e files
        roverObj.close()
        fid_rover.close()
        fid_nmea.close()
