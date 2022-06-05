from struct import unpack


def decode_ublox(msg, costellazioni):
    '''
    Funzione che decodifica il messaggio proveniente dall'ublox.
    Distingue NMEA o UBX e alla fine ritorna entrambi.
    '''
    if (costellazioni is None):
        costellazioni = Costellazione()

    messaggioUBX = [MessaggioUBX.SYNC_CHAR_1, MessaggioUBX.SYNC_CHAR_2]  # b5 62
    posUBX = strfind(messaggioUBX, msg)

    messaggioNMEA = [b"\x24", b"\x47", b"\x4e"]  # $ G N
    posNMEA = strfind(messaggioNMEA, msg)

    # variabili che conterranno quello che andrò ad esportare
    data = []
    NMEA_sentences = []
    NMEA_string = ""

    # capisco il punto di partenza del messaggio
    # indice di partenza del messaggio
    if (len(posUBX) > 0 and len(posNMEA) > 0):
        if (posUBX[0] < posNMEA[0]):
            pos = posUBX[0]
        else:
            pos = posNMEA[0]
    elif (len(posUBX) > 0):
        pos = posUBX[0]
    elif (len(posNMEA) > 0):
        pos = posNMEA[0]
    else:
        return

    # inizio la fase di decodifica del messaggio
    i = 0
    # che io abbia UBX o NMEA i primi 2/3 frammenti
    while (pos + 2 <= len(msg)):
        # controllo se ho l'header UBX
        if (msg[pos:(pos + 1)] == messaggioUBX[0:1]):
            # aumento il contatore
            i += 1
            # salto i primi due bytes di intestazione del messaggio
            pos += 2
            # ora dovrei avere classe, id e lunghezza del payload
            if (pos + 4 <= len(msg)):
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

                if (LEN != 0):
                    # subito dopo la lunghezza ho il payload lungo LEN, poi due byte di fine stream (checksum)
                    if (pos + LEN + 2 <= len(msg)):
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

                        CK_A = mod(CK_A, 256)
                        CK_B = mod(CK_B, 256)
                        CK_A_rec = int.from_bytes(msg[pos + LEN + 1], 'little', signed=False)
                        CK_B_rec = int.from_bytes(msg[pos + LEN + 2], 'little', signed=False)

                        # controllo se il checksum corrisponde
                        if (CK_A == CK_A_rec and CK_B == CK_B_rec):
                            # posso analizzare il messaggio nel dettaglio, esaminando il payload con l'opportuna funzione in base a id, classe
                            if (classId == b"\x0b"):  # AID
                                if (msgId == b"\x31"):  # AID-EPH
                                    data[i] = decode_AID_EPH(msg[pos:(pos + LEN)], costellazioni)
                                elif (msgId == b"\x02"):  # AID-HUI
                                    data = decode_AID_HUI(msg[pos:(pos + LEN)], costellazioni)
                            elif (classId == b"\x02"):  # RXM
                                if (msgId == b"\x15"):  # RXM-RAWX
                                    data = decode_RXM_RAWX(msg[pos:(pos + LEN)], costellazioni)
                                elif (msgId == b"\x15"):  # RXM-RAWX
                                    data = decode_RXM_SFRBX(msg[pos:(pos + LEN)], costellazioni)
                            elif (classId == b"\x01"):  # NAV
                                if (msgId == b"\x24"):  # NAV-TIMEBDS
                                    data = decode_NAV_TIMEBDS(msg[pos:(pos + LEN)])
                                elif (msgId == b"\x25"):  # NAV-TIMEGAL
                                    data = decode_NAV_TIMEGAL(msg[pos:(pos + LEN)])
                                elif (msgId == b"\x20"):  # NAV-TIMEGPS
                                    data = decode_NAV_TIMEGPS(msg[pos:(pos + LEN)])
                                elif (msgId == b"\x23"):  # NAV-TIMEGLO
                                    data = decode_NAV_TIMEGLO(msg[pos:(pos + LEN)])
                                elif (msgId == b"\x21"):  # NAV-TIMEUTC
                                    data = decode_NAV_TIMEUTC(msg[pos:(pos + LEN)])
                        else:
                            printLog("Checksum error.")
                            # salto il messaggio troncato
                            if (posRem > 0 and mod(posRem, 8) != 0 and (LEN + 4) > posRem):
                                printLog("Truncated UBX message, detected and skipped")
                                pos = posNext
                                continue

                        pos += LEN
                        pos += 2
                    else:
                        break
            else:
                break

        # controllo se ho l'header NMEA
        elif ((pos + 4 <= len(msg)) and (msg[pos:(pos + 3)] == messaggioNMEA[0:2])):
            # cerco la fine del messaggio (CRLF)
            # NMEA0183 solitamente è lungo 82, ma al fine di evitare lunghezze non valide sono usati un massimo di 100 caratteri.
            if ((len(msg) - pos) < 99):
                posFineNMEA = strfind(msg[pos:], [b"\x0d", b"\x0a"])
            else:
                posFineNMEA = strfind(msg[pos:(pos + 99)], [b"\x0d", b"\x0a"])

            if (len(posFineNMEA) != 0):
                # salvo la stringa
                while (msg[pos] != b"\x0d"):
                    bits = "".join(msg2bits([msg[pos]]))
                    binary_int = int(bits, 2)
                    byte_number = binary_int.bit_length() + 7 // 8
                    binary_array = binary_int.to_bytes(byte_number, "big")
                    ascii_text = binary_array.decode()

                    NMEA_string += ascii_text
                    pos += 1

                pos += 1
                # salvo soltanto l'LF
                bits = "".join(msg2bits([msg[pos]]))
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
            pos = posUBX(find(posUBX, pos, 1))
            if (len(pos) == 0):
                break

    return (data, NMEA_sentences)


# TODO: a meno di conversioni da risistemare, dovremmo esserci
def decode_RXM_RAWX(msg: bytes, costellazioni=None):
    '''
    Funzione che decodifica un messaggio binario di tipo RXM-RAWX.
    Parte dal payload!
    '''

    # se non sono state passate costellazioni, ne creo una
    if (costellazioni is None):
        costellazioni = Costellazione(1, 0, 0, 0, 0, 0, 0)

    data = []
    data[0] = "RXM-RAWX"

    msgBin = (msg)

    # week time - 8bytes in IEE754 double precision format
    towB = [msgBin[0], msgBin[1], msgBin[2], msgBin[3], msgBin[4], msgBin[5], msgBin[6], msgBin[7]]
    towBS = b''.join(towB)
    towN = unpack(b'>d', towBS)
    tow = format(towN[0], '.18f') / 1000

    # GPS week number - 2bytes (unsigned int)
    weekB = [msgBin[8], msgBin[9]]
    week = int.from_bytes(b''.join(weekB), 'little', signed=False)

    # GPS leap seconds
    leapS = int.from_bytes(msgBin[10], 'little', signed=True)

    # number of measurements
    numMeas = int.from_bytes(msgBin[11], 'little', signed=False)

    # receiver tracking status bitfields
    recStat = Utils.msg2bits(msgBin[12])
    clkReset = recStat[6]
    leapSec = recStat[7]

    # version
    version = msgBin[13]

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
        prMesB = [msgBin[cS], msgBin[cS + 1], msgBin[cS + 2], msgBin[cS + 3], msgBin[cS + 4], msgBin[cS + 5],
                  msgBin[cS + 6], msgBin[cS + 7]]
        prMesBS = b''.join(prMesB)
        prMesN = unpack(b'>d', prMesBS)
        prMes = format(prMesN[0], '.18f')

        cS += 8
        # carrier phase measurament cycles
        cpMesB = [msgBin[cS], msgBin[cS + 1], msgBin[cS + 2], msgBin[cS + 3], msgBin[cS + 4], msgBin[cS + 5],
                  msgBin[cS + 6], msgBin[cS + 7]]
        cpMesBS = b''.join(cpMesB)
        cpMesN = unpack(b'>d', cpMesBS)
        cpMes = format(cpMesN[0], '.18f')

        cS += 8
        # doppler measurament
        doMesB = [msgBin[cS], msgBin[cS + 1], msgBin[cS + 2], msgBin[cS + 3]]
        doMesBS = b''.join(doMesB)
        doMesN = unpack(b'>f', doMesBS)
        doMes = format(doMesN[0], '.9f')

        cS += 4
        # gnssId
        gnssId = int.from_bytes(msgBin[cS], 'little', signed=False)
        cS += 1

        # svId
        svId = int.from_bytes(msgBin[cS], 'little', signed=False)
        cS += 1

        # sigId
        sigId = int.from_bytes(msgBin[cS], 'little', signed=False)
        cS += 1

        # freqId
        freqId = int.from_bytes(msgBin[cS], 'little', signed=False)
        cS += 1

        # locktime
        gnssId = int.from_bytes([msgBin[cS], msgBin[cS + 1]], 'little', signed=False)
        cS += 2

        # cno
        cno = int.from_bytes(msgBin[cS], 'little', signed=False)
        cS += 1

        # prStdev
        # TODO: occhio alla scala! il manuale dice: 0.01*2^n
        prStdev = 0
        prStdev_bit = Utils.msg2bits(msgBin[cS])
        prStdev += int(prStdev_bit[7]) * pow(2, 0)
        prStdev += int(prStdev_bit[6]) * pow(2, 1)
        prStdev += int(prStdev_bit[5]) * pow(2, 2)
        prStdev += int(prStdev_bit[4]) * pow(2, 3)
        prStdev = 0.01 * pow(2, prStdev)
        cS += 1

        # cpStdev
        # TODO: occhio alla scala! Il manuale dice: 0.004
        cpStdev = 0
        cpStdev_bit = Utils.msg2bits(msgBin[cS])
        cpStdev += int(cpStdev_bit[7]) * pow(2, 0)
        cpStdev += int(cpStdev_bit[6]) * pow(2, 1)
        cpStdev += int(cpStdev_bit[5]) * pow(2, 2)
        cpStdev += int(cpStdev_bit[4]) * pow(2, 3)
        cpStdev = cpStdev * 0.004
        cS += 1

        # doStdev
        # TODO: occhio alla scala! Il manuale dice: 0.002*2^n
        doStdev = 0
        doStdev_bit = Utils.msg2bits(msgBin[cS])
        doStdev += int(doStdev_bit[7]) * pow(2, 0)
        doStdev += int(doStdev_bit[6]) * pow(2, 1)
        doStdev += int(doStdev_bit[5]) * pow(2, 2)
        doStdev += int(doStdev_bit[4]) * pow(2, 3)
        doStdev = 0.002 * pow(2, doStdev)
        cS += 1

        # trkStat
        trkStat_bit = Utils.msg2bits(msgBin[cS])
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
            # TODO: MQI e LLI come li trovo?
            # "MQI": #, quale delle 3 deviazioni?!
            "CNO": cno,
            # "LLI":
        })

    return data
