from lib import Utils


class GNSSParams:
    vLight = 299792458
    # GPS[MHz]
    FL1 = 1575.420
    FL2 = 1227.600
    FL5 = 1176.450
    # GLONASS[MHz]
    FR1_base = 1602.000
    FR2_base = 1246.000
    FR1_delta = 0.5625
    FR2_delta = 0.4375
    FR_channels = [6,5,4,3,2,1,0,-1,-2,-3,-4,-5,-6,-7]
    # Galileo[MHz]
    FE1 = FL1
    FE5a = FL5
    FE5b = 1207.140
    FE5 = 1191.795
    FE6 = 1278.750
    # BeiDou[MHz]
    FC1 = 1589.740
    FC2 = 1561.098
    FC5b = FE5b
    FC6 = 1268.520
    # QZSS[MHz]
    FJ1 = FL1
    FJ2 = FL2
    FJ5 = FL5
    FJ6 = FE6
    # SBAS[MHz]
    FS1 = FL1
    FS5 = FL5
    FG = [FL1*1e6, FL2*1e6, FL5*1e6]

    FR_base = [FR1_base, FR2_base]
    FR_delta = [FR1_delta, FR2_delta]
    FR1 = [((e * FR_delta[0]) + FR_base[0]) for e in FR_channels]
    FR2 = [((e * FR_delta[1]) + FR_base[1]) for e in FR_channels]

    # GLONASS carriers: frequenze e lunghezze d'onda
    FR = [FR1*1e6, FR2*1e6]
    LAMBDAR = [vLight*e for e in FR]
    # Galileo carriers: frequenze e lunghezze d'onda
    FE = [FE1*1e6,FE5a*1e6,FE5b*1e6,FE5*1e6,FE6*1e6]
    LAMBDAE = [vLight*e for e in FE]
    # BeiDou carriers: frequenze e lunghezze d'onda
    FC = [FC1*1e6,FC2*1e6,FC5b*1e6,FC6*1e6]
    LAMBDAC = [vLight*e for e in FC]
    # QZSS carriers: frequenze e lunghezze d'onda
    FJ = [FJ1*1e6,FJ2*1e6,FJ5*1e6,FJ6*1e6]
    LAMBDAJ = [vLight*e for e in FJ]
    # SBASS carriers: frequenze e lunghezze d'onda
    FS = [FS1*1e6,FS5*1e6]
    LAMBDAS = [vLight*e for e in FS]

    chToUse = 32
    GNSS = [
        {
            "gnssId": 0,
            "gnss": "GPS",
            "configure": 1,
            "enable": 1,
            "minCh": 8,
            "maxCh": 16,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "G",
            "svIdFrom": 1,
            "svIdTo": 32
        },
        {
            "gnssId": 1,
            "gnss": "SBAS",
            "configure": 1,
            "enable": 0,
            "minCh": 1,
            "maxCh": 3,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "S",
            "svIdFrom": 120,
            "svIdTo": 158
        },
        {
            "gnssId": 2,
            "gnss": "Galileo",
            "configure": 1,
            "enable": 1,
            "minCh": 4,
            "maxCh": 8,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "E",
            "svIdFrom": 1,
            "svIdTo": 36
        },
        {
            "gnssId": 3,
            "gnss": "BeiDou",
            "configure": 1,
            "enable": 0,
            "minCh": 8,
            "maxCh": 16,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "B",
            "svIdFrom": 1,
            "svIdTo": 37
        },
        {
            "gnssId": 4,
            "gnss": "IMES",
            "configure": 1,
            "enable": 0,
            "minCh": 0,
            "maxCh": 8,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 3,
            "letter": "I",
            "svIdFrom": 1,
            "svIdTo": 10
        },
        {
            "gnssId": 5,
            "gnss": "QZSS",
            "configure": 1,
            "enable": 1,
            "minCh": 0,
            "maxCh": 3,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 5,
            "letter": "Q",
            "svIdFrom": 1,
            "svIdTo": 10
        },
        {
            "gnssId": 6,
            "gnss": "GLONASS",
            "configure": 1,
            "enable": 1,
            "minCh": 8,
            "maxCh": 14,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "R",
            "svIdFrom": 1,
            "svIdTo": 32
        }
    ]

    def enableGNSS(self, gnssId, enable):
        for gnss in self.GNSS:
            if(gnss["gnssId"] == gnssId):
                gnss["enable"] = enable

    def calculateIndexes(self):
        idxFrom = 0
        nSatTot = 0
        q = 0
        for gnss in self.GNSS:
            if gnss["enable"] == 1:
                numSat = (gnss["svIdTo"] - gnss["svIdFrom"] + 1)
                nSatTot += numSat
                q += 1
                if q == 1:
                    idxTmp_From = 0
                    idxTmp_To = numSat - 1
                    idxFrom = idxTmp_To
                else:
                    idxTmp_From = idxFrom + 1
                    idxTmp_To = idxTmp_From + numSat - 1
                    idxFrom = idxTmp_To

                gnss["idxFrom"] = idxTmp_From
                gnss["idxTo"] = idxTmp_To


    def getEnabledSat(self):
        enabledSat = 0
        for gnss in self.GNSS:
            if(gnss["enable"] == 1):
                enabledSat += (gnss["svIdTo"] - gnss["svIdFrom"] + 1)
        return enabledSat

    def getEnabledGNSS(self):
        enabledGNSS = 0
        for gnss in self.GNSS:
            if(gnss["enable"] == 1):
                enabledGNSS += 1
        return enabledGNSS

    def getIdByGNSS(self, gnss):
        for g in self.GNSS:
            if g["letter"] == gnss:
                return g.gnssId
        return 0

    def getWaveLengths(self, Eph, nSatTot):
        lambdas = []
        for s in range(nSatTot):
            Eph1 = []
            for e in len(Eph):
                Eph1[e] = Eph[e][29]
            pos = Utils.find(Eph1, s, 1, True)
            if len(pos) > 0:
                if chr(Eph[pos][30]) == "G":
                    lambdas[s][1] = self.getWaveLength(self.getIdByGNSS("G"), 1)
                    lambdas[s][2] = self.getWaveLength(self.getIdByGNSS("G"), 2)
                if chr(Eph[pos][30]) == "R":
                    lambdas[s][1] = self.getWaveLength(self.getIdByGNSS("R"), 1, Eph[pos][14])
                    lambdas[s][2] = self.getWaveLength(self.getIdByGNSS("R"), 2, Eph[pos][14])
                if chr(Eph[pos][30]) == "E":
                    lambdas[s][1] = self.getWaveLength(self.getIdByGNSS("E"), 1)
                    lambdas[s][2] = self.getWaveLength(self.getIdByGNSS("E"), 2)
                if chr(Eph[pos][30]) == "B":
                    lambdas[s][1] = self.getWaveLength(self.getIdByGNSS("B"), 1)
                    lambdas[s][2] = self.getWaveLength(self.getIdByGNSS("B"), 2)
                if chr(Eph[pos][30]) == "Q":
                    lambdas[s][1] = self.getWaveLength(self.getIdByGNSS("Q"), 1)
                    lambdas[s][2] = self.getWaveLength(self.getIdByGNSS("Q"), 2)
        return lambdas

    def getLambdaByGnss(self, gnssId, freq, GLOPos):
        if gnssId == self.getIdByGNSS("G"):
            return self.LAMBDAG[freq]
        elif gnssId == self.getIdByGNSS("R"):
            return self.LAMBDAR[freq][GLOPos]
        elif gnssId == self.getIdByGNSS("E"):
            return self.LAMBDAE[freq]
        elif gnssId == self.getIdByGNSS("B"):
            return self.LAMBDAC[freq]
        elif gnssId == self.getIdByGNSS("Q"):
            return self.LAMBDAJ[freq]
        elif gnssId == self.getIdByGNSS("S"):
            return self.LAMBDAS[freq]

    def getWaveLength(self, gnssId, freq, pos):
        if gnssId == self.getIdByGNSS("G"):
            return self.getLambdaByGnss(self.getIdByGNSS("G"), freq)
        elif gnssId == self.getIdByGNSS("R"):
            return self.getLambdaByGnss(self.getIdByGNSS("R"), freq, pos)
        elif gnssId == self.getIdByGNSS("E"):
            return self.getLambdaByGnss(self.getIdByGNSS("E"), freq)
        elif gnssId == self.getIdByGNSS("B"):
            return self.getLambdaByGnss(self.getIdByGNSS("B"), freq)
        elif gnssId == self.getIdByGNSS("Q"):
            return self.getLambdaByGnss(self.getIdByGNSS("Q"), freq)
        elif gnssId == self.getIdByGNSS("S"):
            return self.getLambdaByGnss(self.getIdByGNSS("S"), freq)

    def find_sat_system(self, sat):
        '''
        Data una lista di indici di satelliti, cerca a quale sistema si sta riferendo e assegna il corretto PRN.
        '''
        sys = []
        prn = []

        # ricalcolo gli indici sulla base della configurazione attuale
        self.calculateIndexes()
        for j in range(len(sat)):
            for gnss in self.GNSS:
                if gnss["idxFrom"] <= sat[j] and gnss["idxTo"] >= sat[j]:
                    sys[j] = gnss["letter"]
                    prn[j] = sat[j] - gnss["idxFrom"]

        return (sys, prn)
