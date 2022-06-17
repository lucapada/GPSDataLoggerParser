import datetime
import math

import serial

from modules import Reporter, UBXMessage


# OK - TEST
def splitBytes(stream: bytes):
    '''
    Riceve uno stream di bytes e crea un array contenente ciascun byte in ciascuna posizione.
    :param stream:
    :return:
    '''
    splittedBytes = []
    for k in stream:
        splittedBytes.append(k.to_bytes(1, 'big'))
    return splittedBytes


# OK - TEST
def msg2bits(msgBytes: list):
    '''
    Funzione che codifica ciascun byte presente nell'array "msgBytes" nel corrispettivo bit, ritornando una lista di bit.
    :param msgBytes:
    :return:
    '''
    bits = []
    for n in msgBytes:
        i = int.from_bytes(n, 'little', signed=False)
        bits.append(format(i, '#010b')[2:])
    return bits


# Funzioni Custom
def ieee754double(bits):
    s = int(bits[0])
    e = int(bits[1:12], 2)
    m = bits[12:64]
    mant = 1
    for b in range(len(m)):
        mant += int(m[b]) * pow(2, -(b + 1))
    return pow(-1, s) * mant * pow(2, e - 1023)


def ieee754single(bits):
    s = int(bits[0])
    e = int(bits[1:9], 2)
    m = bits[9:32]
    mant = 1
    for b in range(len(m)):
        mant += int(m[b]) * pow(2, -(b + 1))
    return pow(-1, s) * mant * pow(2, e - 127)

def reshape(stringa: str, n: int) -> list:
    out = []
    k = 0
    s = ""
    for c in stringa:
        s += c
        k += 1
        if k == n:
            out.append(s)
            s = ""
            k = 0
    return out

def twos_complement(input: str) -> int:
    '''
    Restituisce il corrispondente decimale di un complemento a due.
    :param input:
    :return:
    '''
    out = []
    if input[0] == "1":
        for i in range(len(input)):
            if input[i] == "1":
                out[i] = "0"
            else: out[i] = "1"
        out = -1 * int(out, 2) - 1
    else:
        out = int(input, 2)
    return out

# Porting di funzioni MATLAB
# TODO: da testare
def ismember(A: list, B: list):
    '''
    Returns an array of size A. If elements of A is contained in B returns True for that element, otherwise False.
    You can control all the elements are False by using not any(ismember(A,B))
    :param A:
    :param B:
    :return:
    '''
    out = []
    for a in A:
        if (a in B):
            out.append(True)
        else:
            out.append(False)
    return out


# OK - TEST
def strfind(what: bytes, where: bytes):
    '''
    Funzione che trova la stringa "what" nella stringa "where" e restituisce un array di corrispondenze.
    :param what:
    :param where:
    :return:
    '''
    corr = []
    l = len(what)
    c = 0
    while (c < len(where)):
        if (where[c:c + l] == what[0:l]):
            corr.append(c)
        c += 1
    return corr


# OK - TEST
def find(elements, greaterThan, topK, equals=False):
    '''
    Funzione restituisce gli indici dei primi "topK" elementi trovati in "elements" più grandi di "greaterThan".
    Se "equals" = True, cerca solo gli elementi uguali a "greatherThan", altrimenti quelli più grandi di "greaterThan".
    :param elements:
    :param greaterThan:
    :param topK:
    :param equals:
    :return:
    '''

    # TODO: sistemare nel caso di array multidimensionali! (non penso che servano)
    # a = numpy.array()
    # numpy.array(a.flatten())
    lA = elements

    i = []
    c = 0
    k = 0
    for v in lA:
        if c < topK:
            if equals is False and greaterThan <= v:
                i.append(k)
                c += 1
            elif greaterThan == v:
                i.append(k)
                c += 1
        k += 1
    return i


# Porting di funzioni sviluppate in goGPS 0.4.2
# TODO: controllare
def weektime2tow(week, time):
    '''
    Conversion from GPS time in continuous format (similar to datenum) to GPS time in week, seconds-of-week.
    :param week:
    :param time:
    :return:
    '''
    return time - week * 7 * 86400

# TODO: controllare
def weektow2time(week, sow, sys):
    time = week * 7 * 86400 + sow
    BDS_mask = []
    for s in sys:
        BDS_mask.append(s == "C")
    if any(BDS_mask):
        GPS_BDS_week = 1356
        time[BDS_mask] = (GPS_BDS_week + week[BDS_mask]) * 7 * 86400 + sow[BDS_mask]
    return time

# TODO: controllare
def check_t(time):
    '''
    :param time:
    :return:
    '''
    half_week = 302400
    corrTime = time
    if time > half_week:
        corrTime = time - 2 * half_week
    elif time < -half_week:
        corrTime = time + 2 * half_week
    return corrTime


# TODO: controllare
def gps2date(gps_week, gps_sow):
    gps_start_datenum = 722820  # TODO: 723186 (1981-1-6), ora è 1980
    gps_dow = []
    date = []
    gps_sod = []
    doy = []
    for i in range(len(gps_week)):
        gps_dow[i] = math.floor(gps_sow[i] / 86400)
        date[i] = datetime.fromordinal(gps_start_datenum + 7 * gps_week[i] + gps_dow[i])
        gps_sod[i] = gps_sow[i] - gps_dow[i] * 86400
        date[i] = [
            date[i].year,
            date[i].month,
            date[i].day,
            math.floor(gps_sod[i] / 3600),
            math.floor((gps_sod[i] / 60) - (math.floor(gps_sod[i] / 3600) * 60)),
            gps_sod[i] - (3600 * math.floor(gps_sod[i] / 3600)) - (
                        60 * math.floor((gps_sod[i] / 60) - (math.floor(gps_sod[i] / 3600) * 60)))
        ]

        doy[i] = math.floor(
            datetime.datetime(date[0], date[1], date[2], date[3], date[4], date[5]).timetuple().tm_yday) - 1

    return date, doy


# --------------- DECODING FUNCTIONS ---------------
# TODO: controllare
def decode_ublox(msg, reporter: Reporter):
    '''
    Funzione che decodifica il messaggio proveniente dall'ublox (bytes).
    Distingue NMEA o UBX e alla fine ritorna entrambi.

    :param msg:
    :param reporter:
    :return:
    '''
    msg = splitBytes(msg)

    messaggioUBX = [UBXMessage.SYNC_CHAR_1, UBXMessage.SYNC_CHAR_2]  # b5 62
    posUBX = strfind(messaggioUBX, msg)

    messaggioNMEA = [b"\x24", b"\x47", b"\x4e"]  # $ G N
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
        return

    # inizio la fase di decodifica del messaggio
    i = 0

    # controllo che io abbia UBX o NMEA nei primi 2/3 frammenti
    while (pos + 2) <= len(msg):
        # controllo se ho l'header UBX
        if msg[pos:(pos + 1)] == messaggioUBX[0:1]:
            # aumento il contatore
            i += 1
            # salto i primi due bytes di intestazione del messaggio
            pos += 2
            # ora dovrei avere classe, id e lunghezza del payload
            if (pos + 4) <= len(msg):
                # prendo la classe
                classId = msg[pos]
                pos += 1
                # prendo l'id
                msgId = msg[pos]
                pos += 1

                # controllo che il messaggio non sia troncato
                posNext = posUBX[find(posUBX, pos, 1)]
                posRem = posNext - pos

                # estraggo la lunghezza del payload (2 byte)
                LEN = int.from_bytes(b''.join([msg[pos], msg[pos + 1]]), 'little', signed=False)
                pos += 2

                if LEN != 0:
                    # subito dopo la lunghezza ho il payload lungo LEN, poi due byte di fine stream (checksum)
                    if (pos + LEN + 2) <= len(msg):
                        # calcolo il checksum
                        CK_A = 0
                        CK_B = 0

                        k = 0
                        slices = []
                        chkStart = pos - 4
                        chkEnd = pos + LEN
                        for j in range(chkStart, chkEnd):
                            slices[k] = msg[j]
                            k += 1

                        slicesInt = []
                        for s in range(len(slices)):
                            slicesInt[s] = int.from_bytes(slices[s], 'little')

                        for r in range(k - 1):
                            CK_A = CK_A + slicesInt[r]
                            CK_B = CK_B + CK_A

                        CK_A = CK_A % 256
                        CK_B = CK_B % 256
                        CK_A_rec = int.from_bytes(msg[pos + LEN + 1], 'little', signed=False)
                        CK_B_rec = int.from_bytes(msg[pos + LEN + 2], 'little', signed=False)

                        # controllo se il checksum corrisponde
                        if CK_A == CK_A_rec and CK_B == CK_B_rec:
                            # posso analizzare il messaggio nel dettaglio, esaminando il payload con l'opportuna funzione in base a id, classe
                            # if (classId == b"\x0b"):  # AID
                            #     if (msgId == b"\x31"):  # AID-EPH
                            #         data[i] = decode_AID_EPH(msg[pos:(pos + LEN)], costellazioni)
                            #     elif (msgId == b"\x02"):  # AID-HUI
                            #         data = decode_AID_HUI(msg[pos:(pos + LEN)], costellazioni)
                            if classId == b"\x02":  # RXM
                                if msgId == b"\x15":  # RXM-RAWX
                                    data = decode_RXM_RAWX(msg[pos:(pos + LEN)])
                                elif msgId == b"\x15":  # RXM-SFRBX
                                    data = decode_RXM_SFRBX(msg[pos:(pos + LEN)])
                            elif classId == b"\x01":  # NAV
                                if msgId == b"\x24":  # NAV-TIMEBDS
                                    data = decode_NAV_TIMEBDS(msg[pos:(pos + LEN)])
                                elif msgId == b"\x25":  # NAV-TIMEGAL
                                    data = decode_NAV_TIMEGAL(msg[pos:(pos + LEN)])
                                elif msgId == b"\x20":  # NAV-TIMEGPS
                                    data = decode_NAV_TIMEGPS(msg[pos:(pos + LEN)])
                                elif msgId == b"\x23":  # NAV-TIMEGLO
                                    data = decode_NAV_TIMEGLO(msg[pos:(pos + LEN)])
                                elif msgId == b"\x21":  # NAV-TIMEUTC
                                    data = decode_NAV_TIMEUTC(msg[pos:(pos + LEN)])
                        else:
                            reporter.printLog("Checksum error.")
                            # salto il messaggio troncato
                            if posRem > 0 and (posRem % 8) != 0 and (LEN + 4) > posRem:
                                reporter.printLog("Truncated UBX message, detected and skipped")
                                pos = posNext
                                continue

                        pos += LEN
                        pos += 2
                    else:
                        break
            else:
                break
        # controllo se ho l'header NMEA
        elif (pos + 4) <= len(msg) and msg[pos:(pos + 3)] == messaggioNMEA[0:2]:
            # cerco la fine del messaggio (CRLF)
            # NMEA0183 solitamente è lungo 82, ma al fine di evitare lunghezze non valide sono usati un massimo di 100 caratteri.
            if (len(msg) - pos) < 99:
                posFineNMEA = strfind(msg[pos:], [b"\x0d", b"\x0a"])
            else:
                posFineNMEA = strfind(msg[pos:(pos + 99)], [b"\x0d", b"\x0a"])
            if len(posFineNMEA) != 0:
                # salvo la stringa
                while msg[pos] != b"\x0d":
                    bits = "".join(msg2bits(splitBytes(msg[pos])))
                    binary_int = int(bits, 2)
                    byte_number = binary_int.bit_length() + 7 // 8
                    binary_array = binary_int.to_bytes(byte_number, "big")
                    ascii_text = binary_array.decode()

                    NMEA_string += ascii_text
                    pos += 1

                pos += 1
                # salvo soltanto l'LF
                bits = "".join(msg2bits(splitBytes(msg[pos])))
                binary_int = int(bits, 2)
                byte_number = binary_int.bit_length() + 7 // 8
                binary_array = binary_int.to_bytes(byte_number, "big")
                ascii_text = binary_array.decode()
                NMEA_string += ascii_text

                pos += 1
                NMEA_sentences.append(NMEA_string)
                NMEA_string = ""
            else:
                # la sentence NMEA è iniziata, ma non è disponibile.
                # scorro l'header e continuo
                pos += 3
        else:
            # controllo se ci sono altri pacchetti
            pos = posUBX[find(posUBX, pos, 1)]
            if len(pos) == 0:
                break

    return data, NMEA_sentences


# TODO: da sviluppare da capo
def decode_RXM_SFRBX(msg):
    '''
    Funzione che decodifica un messaggio binario di tipo RXM-SFRBX.
    :param msg:
    :return:
    '''

    # msg = splitBytes(msg)
    data = []
    data[0] = "RXM-SFRBX"

    gnssId = int.from_bytes(msg[0], 'little', signed=False)
    svId = int.from_bytes(msg[1], 'little', signed=False)
    sigId = int.from_bytes(msg[2], 'little', signed=False)
    freqId = int.from_bytes(msg[3], 'little', signed=False)
    numWords = int.from_bytes(msg[4], 'little', signed=False)
    chn = int.from_bytes(msg[5], 'little', signed=False)
    version = int.from_bytes(msg[6], 'little', signed=False) # 0x02
    # 7, 1byte reserved

    data[1] = {
        "gnssId": gnssId,
        "svId": svId,
        "sigId": sigId,
        "freqId": freqId,
        "numWords": numWords,
        "chn": chn
    }

    data[2] = []
    '''
    Nota per l'interpretazione dei subframe:
    a quanto pare, l'ordine delle parole rispetta quello del pacchetto
    il fatto che è little endian, si vede nella composizione delle parole: 
    vengono suddivise a blocchi di 8 e vengono poi ribaltate, parola dopo parola.
    goGPS lavora con i bit e lo fa perché si lavora col little endian...
    https://youtu.be/bWG4A0I21i4?list=PLX2gX-ftPVXXGdn_8m2HCIJS7CfKMCwol
    '''

    # data word is different GNSS by GNSS.
    if (gnssId == 0 or gnssId == 5) and numWords == 10:
        # GPS or QZSS L1C/A
        # nel GPS ho 10 dataword, dalla 3° la struttura cambia a seconda del subframe di riferimento.
        dwrds = []
        for w in range(numWords):
            wS = 8 + 4 * w
            dwrd_bit = "".join(msg2bits([msg[wS + 3], msg[wS + 2], msg[wS + 1], msg[wS]])) # implemento qui il Little Endian
            dwrds.append(dwrd_bit[2:])

        # la prima parola è TLM e posso ignorarla
        # la seconda parola è HOW e da lì estraggo il subframe-id.
        sfId = int(dwrds[1][21:23], 2)
        if sfId == 1:
            # sfId 1) Satellite Clock Correction Terms + GPS Week Number
            SF1D0 = dwrds[2]
            SF1D1 = dwrds[3]
            SF1D2 = dwrds[4]
            SF1D3 = dwrds[5]
            SF1D4 = dwrds[6]
            SF1D5 = dwrds[7]
            SF1D6 = dwrds[8]
            SF1D7 = dwrds[9]

            weekno = int(SF1D0[0:9], 2)
            code_on_L2 = int(SF1D0[10:11], 2)
            svaccur = int(SF1D0[12:15], 2)
            svhealth = int(SF1D0[16:21], 2)
            IODC_MSBs = SF1D0[22:23], 2
            IODC_LSBs = SF1D5[0:7], 2
            IODC = int((IODC_LSBs + IODC_MSBs), 2)
            L2flag = int(SF1D1[0], 2)
            tgd = twos_complement(SF1D4[16:23]) * pow(2, -31)
            toc = int(SF1D5[8:23], 2) * pow(2, 4)
            af2 = twos_complement(SF1D6[0:7]) * pow(2, -55)
            af1 = twos_complement(SF1D6[8:23]) * pow(2, -43)
            af0 = twos_complement(SF1D7[0:21]) * pow(2, -31)
        elif sfId == 2:
            # subframe 2) Precise Ephemeris Data (part 1)
            SF2D0 = dwrds[2]
            SF2D1 = dwrds[3]
            SF2D2 = dwrds[4]
            SF2D3 = dwrds[5]
            SF2D4 = dwrds[6]
            SF2D5 = dwrds[7]
            SF2D6 = dwrds[8]
            SF2D7 = dwrds[9]

            IODE2 = int(SF2D0[0:7], 2)
            Crs = twos_complement(SF2D0[8:23]) * pow(2, -5)
            delta_n = twos_complement(SF2D1[0:15]) * math.pi * pow(2, -43)
            M0 = twos_complement((SF2D1[16:23] + SF2D2[0:23])) * math.pi * pow(2, -31)
            Cuc = twos_complement(SF2D3[0:15]) * pow(2, -29)
            e = int((SF2D3[16:23] + SF2D4[0:23]), 2) * pow(2, -33)
            Cus = twos_complement(SF2D5[0:15]) * pow(2, -29)
            root_A = int((SF2D5[16:23] + SF2D6[0:23]), 2) * pow(2, -19)
            toe = int(SF2D7[0:15]) * pow(2, 4)
            fit_int = int(SF2D7[16])
        elif sfId == 3:
            # subframe 3) Precise Ephemeris Data (part 2)
            SF3D0 = dwrds[2]
            SF3D1 = dwrds[3]
            SF3D2 = dwrds[4]
            SF3D3 = dwrds[5]
            SF3D4 = dwrds[6]
            SF3D5 = dwrds[7]
            SF3D6 = dwrds[8]
            SF3D7 = dwrds[9]

            Cic = twos_complement(SF3D0[0:15]) * pow(2, -29)
            omega0 = twos_complement((SF3D0[16:23] + SF3D1[0:23])) * math.pi * pow(2, -31)
            Cis = twos_complement(SF3D2[0:15]) * pow(2, -29)
            i0 = twos_complement((SF3D2[16:23] + SF3D3[0:23])) * math.pi * pow(2, -31)
            Crc = twos_complement(SF3D4[0:15]) * pow(2, -5)
            omega = twos_complement((SF3D4[16:23] + SF3D5[0:23])) * math.pi * pow(2, -31)
            omegadot = twos_complement(SF3D6[0:23]) * math.pi * pow(2, -43)
            IODE3 = int(SF3D7[0:7])
            IDOT = twos_complement(SF3D7[8:21]) * math.pi * pow(2, -43)
        elif sfId == 4:
            if int(dwrds[2][11:16], 2) == 56:
                # sf 4 and 5 of EVERY frame are needed to complete the entire nav message
                # subframe 4) Ionospheric + UTC Data + Almanac for SVs (25 to 32)
                # subframe 5) Almanac for SVs (1 to 24) + Almanac Reference Time
                SF4D0 = dwrds[2]
                SF4D1 = dwrds[3]
                SF4D2 = dwrds[4]
                SF4D3 = dwrds[5]
                SF4D4 = dwrds[6]
                SF4D5 = dwrds[7]
                SF4D6 = dwrds[8]
                SF4D7 = dwrds[9]

                data[1]['a0'] = twos_complement(SF4D0[8:15]) * pow(2, -30)
                data[1]['a1'] = twos_complement(SF4D0[16:23]) * pow(2, -27)
                data[1]['a2'] = twos_complement(SF4D1[0:7]) * pow(2, -24)
                data[1]['a3'] = twos_complement(SF4D1[8:15]) * pow(2, -24)
                data[1]['b0'] = twos_complement(SF4D1[16:23]) * pow(2, 11)
                data[1]['b1'] = twos_complement(SF4D2[0:7]) * pow(2, 14)
                data[1]['b2'] = twos_complement(SF4D2[8:13]) * pow(2, 16)
                data[1]['b3'] = twos_complement(SF4D2[16:23]) * pow(2, 16)
                data[1]['leap_seconds'] = twos_complement(SF4D6[0:7])

        if IODC == IODE2 and IODC == IODE3 and constellations.GPS.enabled:
            data[2][0] = svId # PRN
            data[2][1] = af2
            data[2][2] = M0
            data[2][3] = root_A
            data[2][4] = delta_n
            data[2][5] = e
            data[2][6] = omega
            data[2][7] = Cuc
            data[2][8] = Cus
            data[2][9] = Crc
            data[2][10] = Crs
            data[2][11] = i0
            data[2][12] = IDOT
            data[2][13] = Cic
            data[2][14] = Cis
            data[2][15] = omega0
            data[2][16] = omegadot
            data[2][17] = toe
            data[2][18] = af0
            data[2][19] = af1
            data[2][20] = toc
            data[2][21] = IODE3
            data[2][22] = code_on_L2
            data[2][23] = weekno
            data[2][24] = L2flag
            data[2][25] = svaccur
            data[2][26] = svhealth
            data[2][27] = tgd
            data[2][28] = fit_int
            data[2][29] = constellations.GPS.indexes(PRN) #TODO: vedere questo una volta sistemate le GNSS.
            data[3][30] = 71 # G (char)
            data[3][31] = weektow2time(weekno, toe, 'G')
            data[3][32] = weektow2time(weekno, toc, 'G')
    elif gnssId == 1:
        # SBAS
    elif gnssId == 2:
        # Galileo E1OS I/NAV


    elif gnssId == 3:
        # BeiDou B1I

    elif gnssId == 4:
        # IMES
    elif gnssId == 6:
        # GLONASS L1


    return data


# TODO: dovremmo esserci. Aggiungere gnssId e svId?
def decode_RXM_RAWX(msg):
    '''
    Funzione che decodifica un messaggio binario di tipo RXM-RAWX.
    :param msg:
    :return:
    '''

    # msg = splitBytes(msg)
    data = []
    data[0] = "RXM-RAWX"

    # week time - 8bytes in IEE754 double precision format #TODO non sono sicuro del little endian
    tow = ieee754double(''.join(msg2bits([msg[7], msg[6], msg[5], msg[4], msg[3], msg[2], msg[1], msg[0]])))

    # GPS week number - 2bytes (unsigned int)
    week = int.from_bytes(b''.join([msg[8], msg[9]]), 'little', signed=False)

    # GPS leap seconds
    leapS = int.from_bytes(msg[10], 'little', signed=True)

    # number of measurements
    numMeas = int.from_bytes(msg[11], 'little', signed=False)

    # receiver tracking status bitfields
    recStat = msg2bits(msg[12])
    clkReset = recStat[6]
    leapSec = recStat[7]

    # version
    version = int.from_bytes(msg[13], 'little', signed=False)

    # reserved 14-15

    '''
    2.1) TOW  = week time (in seconds)
    2.2) WEEK = GPS week
    2.3) NSV  = number of visible satellites
    2.4) RES  = reserved field (not used)
    '''
    data[1] = {
        "TOW": tow,
        "WEEK": week,
        "NSV": numMeas,
        "RES": ""  # non sono usati
    }

    data[2] = []
    # repeated block for each meas
    for m in range(numMeas):
        cS = 16 + 32 * m

        # pseudorange measurament: #TODO non sono sicuro del little endian
        prMes = ieee754double(''.join(msg2bits(
            [msg[cS + 7], msg[cS + 6], msg[cS + 5], msg[cS + 4], msg[cS + 3], msg[cS + 2], msg[cS + 1], msg[cS]])))

        cS += 8
        # carrier phase measurament cycles: #TODO non sono sicuro del little endian
        cpMes = ieee754double(''.join(msg2bits(
            [msg[cS + 7], msg[cS + 6], msg[cS + 5], msg[cS + 4], msg[cS + 3], msg[cS + 2], msg[cS + 1], msg[cS]])))

        cS += 8
        # doppler measurament: #TODO non sono sicuro del little endian
        doMes = ieee754single(''.join(msg2bits([msg[cS + 3], msg[cS + 2], msg[cS + 1], msg[cS]])))

        cS += 4
        # gnssId
        gnssId = int.from_bytes(msg[cS], 'little', signed=False)
        cS += 1

        # svId
        svId = int.from_bytes(msg[cS], 'little', signed=False)
        cS += 1

        # sigId
        sigId = int.from_bytes(msg[cS], 'little', signed=False)
        cS += 1

        # freqId
        freqId = int.from_bytes(msg[cS], 'little', signed=False)
        cS += 1

        # locktime
        locktime = int.from_bytes(b''.join([msg[cS], msg[cS + 1]]), 'little', signed=False)
        cS += 2

        # cno
        cno = int.from_bytes(msg[cS], 'little', signed=False)
        cS += 1

        # prStdev (il manuale dice: 0.01*2^n)
        prStdev = 0
        prStdev_bit = msg2bits(splitBytes(msg[cS]))
        prStdev += int(prStdev_bit[7]) * pow(2, 0)
        prStdev += int(prStdev_bit[6]) * pow(2, 1)
        prStdev += int(prStdev_bit[5]) * pow(2, 2)
        prStdev += int(prStdev_bit[4]) * pow(2, 3)
        prStdev = 0.01 * pow(2, prStdev)  # ho applicato la scala
        cS += 1

        # cpStdev (il manuale dice: 0.004)
        cpStdev = 0
        cpStdev_bit = msg2bits(splitBytes(msg[cS]))
        cpStdev += int(cpStdev_bit[7]) * pow(2, 0)
        cpStdev += int(cpStdev_bit[6]) * pow(2, 1)
        cpStdev += int(cpStdev_bit[5]) * pow(2, 2)
        cpStdev += int(cpStdev_bit[4]) * pow(2, 3)
        cpStdev = cpStdev * 0.004
        cS += 1

        # doStdev (il manuale dice: 0.002*2^n)
        doStdev = 0
        doStdev_bit = msg2bits(splitBytes(msg[cS]))
        doStdev += int(doStdev_bit[7]) * pow(2, 0)
        doStdev += int(doStdev_bit[6]) * pow(2, 1)
        doStdev += int(doStdev_bit[5]) * pow(2, 2)
        doStdev += int(doStdev_bit[4]) * pow(2, 3)
        doStdev = 0.002 * pow(2, doStdev)
        cS += 1

        # trkStat
        trkStat_bit = msg2bits(msg[cS])
        prValid = int(trkStat_bit[7])
        cpValid = int(trkStat_bit[6])
        halfCyc = int(trkStat_bit[5])
        subHalfCyc = int(doStdev_bit[4])
        # cS += 1

        '''
        3.1) CPM  = phase measurements (in cycles)
        3.2) PRM  = pseudorange measurements (C/A code in meters)
        3.3) DOM  = doppler measurements (in Hertz)
        3.4) SV   = space vehicle number
        3.5) MQI  = measurement quality index
        3.6) CNO  = signal-to-noise ratio (in dbHz)
        3.7) LLI  = loss of lock indicator
        '''
        data[2].append({
            "CPM": cpMes,
            "PRM": prMes,
            "DOM": doMes,
            "SV": svId,
            # TODO: che valore assegnare a MQI e LLI?
            # "MQI": ,
            "CNO": cno,
            # "LLI":
        })

    return data


def decode_NAV_TIMEBDS(msg):
    # msg = splitBytes(msg)
    data = []
    data[0] = "NAV-TIMEBDS"
    data[1] = {
        "iTOW": int.from_bytes([msg[0], msg[1], msg[2], msg[3]], 'little', False),
        "SOW": int.from_bytes([msg[4], msg[5], msg[6], msg[7]], 'little', False),
        "fSOW": int.from_bytes([msg[8], msg[9], msg[10], msg[11]], 'little', True),
        "week": int.from_bytes([msg[12], msg[13]], 'little', True),
        "leapS": int.from_bytes([msg[14]], 'little', True),
        "valid": {
            "leapSValid": msg2bits(splitBytes(msg[15]))[5],
            "weekValid": msg2bits(splitBytes(msg[15]))[6],
            "sowValid": msg2bits(splitBytes(msg[15]))[7]
        },
        "tAcc": int.from_bytes([msg[16], msg[17], msg[18], msg[19]], 'little', False)
    }
    return data


def decode_NAV_TIMEGAL(msg):
    # msg = splitBytes(msg)
    data = []
    data[0] = "NAV-TIMEGAL"
    data[1] = {
        "iTOW": int.from_bytes([msg[0], msg[1], msg[2], msg[3]], 'little', False),
        "galTow": int.from_bytes([msg[4], msg[5], msg[6], msg[7]], 'little', False),
        "fGalTow": int.from_bytes([msg[8], msg[9], msg[10], msg[11]], 'little', True),
        "galWno": int.from_bytes([msg[12], msg[13]], 'little', True),
        "leapS": int.from_bytes([msg[14]], 'little', True),
        "valid": {
            "leapSValid": msg2bits(splitBytes(msg[15]))[5],
            "galWnoValid": msg2bits(splitBytes(msg[15]))[6],
            "galTowValid": msg2bits(splitBytes(msg[15]))[7]
        },
        "tAcc": int.from_bytes([msg[16], msg[17], msg[18], msg[19]], 'little', False)
    }
    return data


def decode_NAV_TIMEGPS(msg):
    # msg = splitBytes(msg)
    data = []
    data[0] = "NAV-TIMEGPS"
    data[1] = {
        "iTOW": int.from_bytes([msg[0], msg[1], msg[2], msg[3]], 'little', False),
        "fTOW": int.from_bytes([msg[4], msg[5], msg[6], msg[7]], 'little', True),
        "week": int.from_bytes([msg[8], msg[9]], 'little', True),
        "leapS": int.from_bytes([msg[10]], 'little', True),
        "valid": {
            "leapValid": msg2bits(splitBytes(msg[11]))[5],
            "weekValid": msg2bits(splitBytes(msg[11]))[6],
            "towValid": msg2bits(splitBytes(msg[11]))[7],
        },
        "tAcc": int.from_bytes([msg[12], msg[13], msg[14], msg[15]], 'little', False)
    }
    return data


def decode_NAV_TIMEGLO(msg):
    # msg = splitBytes(msg)
    data = []
    data[0] = "NAV-TIMEGLO"
    data[1] = {
        "iTOW": int.from_bytes([msg[0], msg[1], msg[2], msg[3]], 'little', False),
        "TOD": int.from_bytes([msg[4], msg[5], msg[6], msg[7]], 'little', False),
        "fTOD": int.from_bytes([msg[8], msg[9], msg[10], msg[11]], 'little', True),
        "Nt": int.from_bytes([msg[12], msg[13]], 'little', True),
        "N4": int.from_bytes([msg[14]], 'little', True),
        "valid": {
            "dateValid": msg2bits(splitBytes(msg[15]))[6],
            "todValid": msg2bits(splitBytes(msg[15]))[7]
        },
        "tAcc": int.from_bytes([msg[16], msg[17], msg[18], msg[19]], 'little', False)
    }
    return data


def decode_NAV_TIMEUTC(msg):
    # msg = splitBytes(msg)
    data = []
    data[0] = "NAV-TIMEUTC"
    data[1] = {
        "iTOW": int.from_bytes([msg[0], msg[1], msg[2], msg[3]], 'little', False),
        "tAcc": int.from_bytes([msg[4], msg[5], msg[6], msg[7]], 'little', False),
        "nano": int.from_bytes([msg[8], msg[9], msg[10], msg[11]], 'little', True),
        "year": int.from_bytes([msg[12], msg[13]], 'little', False),
        "month": int.from_bytes([msg[14]], 'little', False),
        "day": int.from_bytes([msg[15]], 'little', False),
        "hour": int.from_bytes([msg[16]], 'little', False),
        "min": int.from_bytes([msg[17]], 'little', False),
        "sec": int.from_bytes([msg[18]], 'little', False),
        "valid": {
            "utcStandard": msg2bits(splitBytes(msg[19]))[0],
            "validUTC": msg2bits(splitBytes(msg[19]))[5],
            "validWKN": msg2bits(splitBytes(msg[19]))[6],
            "validTOW": msg2bits(splitBytes(msg[19]))[7]
        },
        "tAcc": int.from_bytes([msg[12], msg[13], msg[14], msg[15]], 'little', False)
    }
    return data
