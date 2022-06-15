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
    # repeated block for each word
    for w in range(numWords):
        wS = 8 + 4 * w
        dwrd = int.from_bytes(msg2bits([msg[wS], msg[wS+1], msg[wS+2], msg[wS+3]]), 'little', signed=False)
        # data word is different GNSS by GNSS.
        if gnssId == 0 and numWords == 10:
            '''
            GPS L1C/A
            comprende 10 parole. Ora sto decodificando la "wS"-esima.
            '''

        # elif gnssId ==


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

    # week time - 8bytes in IEE754 double precision format
    tow = ieee754double(''.join(msg2bits([msg[0], msg[1], msg[2], msg[3], msg[4], msg[5], msg[6], msg[7]])))

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

        # pseudorange measurament
        prMes = ieee754double(''.join(msg2bits(
            [msg[cS], msg[cS + 1], msg[cS + 2], msg[cS + 3], msg[cS + 4], msg[cS + 5], msg[cS + 6], msg[cS + 7]])))

        cS += 8
        # carrier phase measurament cycles
        cpMes = ieee754double(''.join(msg2bits(
            [msg[cS], msg[cS + 1], msg[cS + 2], msg[cS + 3], msg[cS + 4], msg[cS + 5], msg[cS + 6], msg[cS + 7]])))

        cS += 8
        # doppler measurament
        doMes = ieee754single(''.join(msg2bits([msg[cS], msg[cS + 1], msg[cS + 2], msg[cS + 3]])))

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
