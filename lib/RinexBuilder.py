import os.path

from lib import Utils, DecodificaUBX
from lib.GNSSParams import GNSSParams
from lib.MessaggioUBX import MessaggioUBX


class RinexBuilder:

    def __init__(self, fileRoot, path, comPort, rinexMetadata, costellazioni: GNSSParams):
        self.fileRoot = fileRoot
        self.path = path
        self.comPort = comPort
        self.rinexMetadata = rinexMetadata
        self.costellazioni = costellazioni

    def start(self):
        weights = 1
        n_sys = 0
        for gnss in self.costellazioni:
            if gnss["enable"] == 1:
                n_sys += 1

        nSatTot = self.costellazioni.getEnabledSat()
        if nSatTot == 0:
            Utils.printLog("No constellation selected, setting default: GPS-only", self.comPort)
            self.costellazioni = GNSSParams(1)
            nSatTot = self.costellazioni.getEnabledSat()

        # prendo la versione del rinex dai metadati
        rin_ver_id = self.rinexMetadata["version"] # 200, 301 o 304
        # controllo se il sistema utilizza la notazione esponenziale a 3 cifre
        three_digit_exp = (len(("%1.1e" % 1)) == 8)

        # leggo lo stream precedentemente registrato
        data_rover_all = [] # stream completo
        hour = 0 # indice di ore
        hour_str = "%03d" % hour  # indice di ore da impostare come suffisso dei files
        d = self.fileRoot + "_rover_" + self.comPort + "_" + hour_str + ".bin"
        while(os.path.isfile(d)):
            Utils.printLog("Reading: " + d, self.comPort)
            num_bytes = os.stat(d).st_size
            fid_rover = open(d, "r")
            data_rover = fid_rover.read(num_bytes)
            fid_rover.close()
            data_rover_all.append(data_rover)
            hour += 1
            hour_str = "%03d" % hour  # indice di ore da impostare come suffisso dei files
            d = self.fileRoot + "_rover_" + self.comPort + "_" + hour_str + ".bin"

        if len(data_rover_all) > 0:
            Utils.printLog("Decoding rover data", self.comPort)

            patternHEX = [MessaggioUBX.SYNC_CHAR_1, MessaggioUBX.SYNC_CHAR_2]
            patternBIN = ''.join(Utils.msg2bits(patternHEX))
            posUBX = Utils.strfind(patternBIN, ''.join(data_rover_all)) #TODO: arriva direttamente il binario!?

            if len(posUBX) > 0:
                (cell_rover, nmea_sentences) = DecodificaUBX.decode_ublox(data_rover_all, self.costellazioni)

                # inizializzazione delle variabili
                Ncell = len(cell_rover)
                time_R = []
                week_R = []
                ph1_R = []
                pr1_R = []
                dop1_R = []
                snr_R = []
                lock_R = []
                Eph_R = []
                iono = []
                tick_TRACK = []
                tick_PSEUDO = []
                phase_TRACK = []

                i = 0 # TODO: era 1
                for j in range(Ncell):
                    if cell_rover[j][0] == "RXM-RAWX":
                        time_R[i] = cell_rover[j][1]["TOW"]
                        week_R[i] = cell_rover[j][1]["WEEK"]
                        ph1_R[i] = []
                        pr1_R[i] = []
                        snr_R[i] = []
                        lock_R[i] = []
                        for c in range(len(cell_rover[j][1]["NSV"])):
                            # gestisco i valori prossimi allo 0
                            if abs(cell_rover[j][2][c]["CPM"]) < 1e-100:
                                ph1_R[i] = 0
                            else: ph1_R[i] = cell_rover[j][2][c]["CPM"]
                            pr1_R[i] = cell_rover[j][2][c]["PRM"]
                            dop1_R[i] = cell_rover[j][2][c]["DOM"]
                            snr_R[i] = cell_rover[j][2][c]["CNO"]
                            lock_R[i] = cell_rover[j][2][c]["LLI"]

                        i += 1
                    elif cell_rover[j][0] == "RXM-SFRBX":
                        # TODO: da sviluppare
                        # occorre popolare: iono, sat, toe, Eph_R

                    if len(time_R) > 0:
                        (date, DOY) = Utils.gps2date(week_R, time_R)
                        DOYs = [i for n, i in enumerate(DOY) if i not in DOY[:n]].sort()
                        DOY_pos = []

                        for d in DOYs:
                            for i in range(len(DOY)):
                                if DOY[i] == d:
                                    DOY_pos.append(i)

                        n_doy = len(DOYs)
                    else:
                        Utils.printLog("No raw data acquired", self.comPort)
                        return

                    for d in range(n_doy):
                        # prendo l'indice dell'epoca per ogni giorno dell'anno
                        first_epoch = DOY_pos[d]
                        if d < n_doy:
                            last_epoch = DOY_pos[d+1] - 1
                        else:
                            last_epoch = len(time_R)

                        # ------ posizione approssimata ------
                        pos_R = []
                        # ricavo le lunghezze d'onda
                        lambdas = self.costellazioni.getWaveLengths(Eph_R, len(pr1_R))

                        # controllo se le effemeridi sono disponibili
                        if len(Utils.find(Eph_R)) > 0:
