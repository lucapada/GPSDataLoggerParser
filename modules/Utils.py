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

# --------------- DECODING FUNCTIONS ---------------
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
                            if classId == b"\x01":  # NAV
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
