import datetime

def splitBytes(stream: bytes):
    """
    Riceve uno stream di bytes e crea un array contenente ciascun byte in ciascuna posizione.
    :param stream:
    :return:
    """
    splittedBytes = []
    for k in stream:
        splittedBytes.append(k.to_bytes(1, 'big'))
    return splittedBytes

def msg2bits(msgBytes: list):
    """
    Funzione che codifica ciascun byte presente nell'array "msgBytes" nel corrispettivo bit, ritornando una lista di bit.
    :param msgBytes:
    :return:
    """
    bits = []
    for n in msgBytes:
        i = int.from_bytes(n, 'little', signed=False)
        bits.append(format(i, '#010b')[2:])
    return bits


# Funzioni Custom
def ieee754double(bits):
    """
    Ritorna la cifra reale dati 64 bit seguendo lo standard IEEE754.
    :param bits:
    :return:
    """
    # rT_s = rcvTow_Bin[0:1]
    # rT_e = rcvTow_Bin[1:12]
    # rT_m = rcvTow_Bin[12:]
    # rT_f = 0
    # for j in range(len(rT_m)):
    #     rT_f += int(rT_m[j], 2) * pow(2, -(j + 1))
    #
    # rcvTow = pow(-1, int(rT_s, 2)) * (1 + rT_f) * pow(2, int(rT_e, 2) - 1023)

    s = int(bits[0:1])
    e = int(bits[1:12], 2)
    m = bits[12:]
    mant = 1
    for b in range(len(m)):
        mant += int(m[b]) * pow(2, -(b + 1))
    return pow(-1, s) * mant * pow(2, e - 1023)


def ieee754single(bits):
    """
    Ritorna la cifra reale dati 32 bit seguendo lo standard IEEE754.
    :param bits:
    :return:
    """
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
        if (where[c:(c+l)] == what[0:l]):
            corr.append(c)
        c += 1
    return corr

def find(elements, greaterThan, topK, equals=False):
    """
    Funzione che ricerca i primi topK elementi maggiori/uguali di un dato elemento all'interno di una collezione di elementi.
    :param elements: collezione di elementi
    :param greaterThan: elemento soglia
    :param topK: numero di elementi da restituire
    :param equals: gli elementi devono essere uguali o maggiori di greaterThan?
    :return:
    """
    i = []
    c = 0
    for v in range(len(elements)):
        if c < topK:
            if equals is False and greaterThan < elements[v]:
                i.append(v)
                c += 1
            elif equals is True and greaterThan == elements[v]:
                i.append(v)
                c += 1
    return i

# --------------- DECODING FUNCTIONS ---------------
def decode_NAV_TIMEBDS(msg):
    """
    Ritorna l'oggetto json decodificando il messaggio UBX-NAV-TIMEBDS
    :param msg:
    :return:
    """
    # msg = splitBytes(msg)
    data = []
    data.append("NAV-TIMEBDS")
    data.append({
        "iTOW": int.from_bytes(b"".join([msg[0], msg[1], msg[2], msg[3]]), 'little', signed=False),
        "SOW": int.from_bytes(b"".join([msg[4], msg[5], msg[6], msg[7]]), 'little', signed=False),
        "fSOW": int.from_bytes(b"".join([msg[8], msg[9], msg[10], msg[11]]), 'little', signed=True),
        "week": int.from_bytes(b"".join([msg[12], msg[13]]), 'little', signed=True),
        "leapS": int.from_bytes(b"".join([msg[14]]), 'little', signed=True),
        "valid": {
            "leapSValid": "".join(msg2bits(splitBytes(msg[15])))[5],
            "weekValid": "".join(msg2bits(splitBytes(msg[15])))[6],
            "sowValid": "".join(msg2bits(splitBytes(msg[15])))[7]
        },
        "tAcc": int.from_bytes(b"".join([msg[16], msg[17], msg[18], msg[19]]), 'little', signed=False)
    })
    return data

def decode_NAV_TIMEGAL(msg):
    """
    Ritorna l'oggetto json decodificando il messaggio UBX-NAV-TIMEGAL
    :param msg:
    :return:
    """
    # msg = splitBytes(msg)
    data = []
    data.append("NAV-TIMEGAL")
    data.append({
        "iTOW": int.from_bytes(b"".join([msg[0], msg[1], msg[2], msg[3]]), 'little', signed=False),
        "galTow": int.from_bytes(b"".join([msg[4], msg[5], msg[6], msg[7]]), 'little', signed=False),
        "fGalTow": int.from_bytes(b"".join([msg[8], msg[9], msg[10], msg[11]]), 'little', signed=True),
        "galWno": int.from_bytes(b"".join([msg[12], msg[13]]), 'little', signed=True),
        "leapS": int.from_bytes(b"".join([msg[14]]), 'little', signed=True),
        "valid": {
            "leapSValid": "".join(msg2bits(splitBytes(msg[15])))[5],
            "galWnoValid": "".join(msg2bits(splitBytes(msg[15])))[6],
            "galTowValid": "".join(msg2bits(splitBytes(msg[15])))[7]
        },
        "tAcc": int.from_bytes(b"".join([msg[16], msg[17], msg[18], msg[19]]), 'little', signed=False)
    })
    return data

def decode_NAV_TIMEGPS(msg):
    """
    Ritorna l'oggetto json decodificando il messaggio UBX-NAV-TIMEGPS
    :param msg:
    :return:
    """
    # msg = splitBytes(msg)
    data = []
    data.append("NAV-TIMEGPS")
    data.append({
        "iTOW": int.from_bytes(b"".join([msg[0], msg[1], msg[2], msg[3]]), 'little', signed=False),
        "fTOW": int.from_bytes(b"".join([msg[4], msg[5], msg[6], msg[7]]), 'little', signed=True),
        "week": int.from_bytes(b"".join([msg[8], msg[9]]), 'little', signed=True),
        "leapS": int.from_bytes(b"".join([msg[10]]), 'little', signed=True),
        "valid": {
            "leapValid": "".join(msg2bits(splitBytes(msg[11])))[5],
            "weekValid": "".join(msg2bits(splitBytes(msg[11])))[6],
            "towValid": "".join(msg2bits(splitBytes(msg[11])))[7],
        },
        "tAcc": int.from_bytes(b"".join([msg[12], msg[13], msg[14], msg[15]]), 'little', signed=False)
    })
    return data

def decode_NAV_TIMEGLO(msg):
    """
    Ritorna l'oggetto json decodificando il messaggio UBX-NAV-TIMEGLO
    :param msg:
    :return:
    """
    # msg = splitBytes(msg)
    data = []
    data.append("NAV-TIMEGLO")
    data.append({
        "iTOW": int.from_bytes(b"".join([msg[0], msg[1], msg[2], msg[3]]), 'little', signed=False),
        "TOD": int.from_bytes(b"".join([msg[4], msg[5], msg[6], msg[7]]), 'little', signed=False),
        "fTOD": int.from_bytes(b"".join([msg[8], msg[9], msg[10], msg[11]]), 'little', signed=True),
        "Nt": int.from_bytes(b"".join([msg[12], msg[13]]), 'little', signed=True),
        "N4": int.from_bytes(b"".join([msg[14]]), 'little', signed=True),
        "valid": {
            "dateValid": "".join(msg2bits(splitBytes(msg[15])))[6],
            "todValid": "".join(msg2bits(splitBytes(msg[15])))[7]
        },
        "tAcc": int.from_bytes(b"".join([msg[16], msg[17], msg[18], msg[19]]), 'little', signed=False)
    })
    return data

def decode_NAV_TIMEUTC(msg):
    """
    Ritorna l'oggetto json decodificando il messaggio UBX-NAV-TIMEUTC
    :param msg:
    :return:
    """
    # msg = splitBytes(msg)
    data = []
    data.append("NAV-TIMEUTC")
    data.append({
        "iTOW": int.from_bytes(b"".join([msg[0], msg[1], msg[2], msg[3]]), 'little', signed=False),
        "tAcc": int.from_bytes(b"".join([msg[4], msg[5], msg[6], msg[7]]), 'little', signed=False),
        "nano": int.from_bytes(b"".join([msg[8], msg[9], msg[10], msg[11]]), 'little', signed=True),
        "year": int.from_bytes(b"".join([msg[12], msg[13]]), 'little', signed=False),
        "month": int.from_bytes(b"".join([msg[14]]), 'little', signed=False),
        "day": int.from_bytes(b"".join([msg[15]]), 'little', signed=False),
        "hour": int.from_bytes(b"".join([msg[16]]), 'little', signed=False),
        "min": int.from_bytes(b"".join([msg[17]]), 'little', signed=False),
        "sec": int.from_bytes(b"".join([msg[18]]), 'little', signed=False),
        "valid": {
            "utcStandard": "".join(msg2bits(splitBytes(msg[19])))[0],
            "validUTC": "".join(msg2bits(splitBytes(msg[19])))[5],
            "validWKN": "".join(msg2bits(splitBytes(msg[19])))[6],
            "validTOW": "".join(msg2bits(splitBytes(msg[19])))[7]
        },
        "tAcc": int.from_bytes(b"".join([msg[12], msg[13], msg[14], msg[15]]), 'little', signed=False)
    })
    return data

def decode_RXM_RAWX(msg):
    """
    Ritorna l'oggetto json decodificando il messaggio UBX-RXM-RAWX
    :param msg:
    :return:
    """
    # msg = splitBytes(msg)
    data = []
    data.append("RXM-RAWX")

    msg = msg[::-1]
    rcvTow_Bin = "".join(msg2bits([msg[7],msg[6],msg[5],msg[4],msg[3],msg[2],msg[1],msg[0]]))
    rcvTow = ieee754double(rcvTow_Bin)

    data.append({
        "localPCTime": datetime.datetime.now(),
        "rcvTow": rcvTow,
        "week": int.from_bytes(b"".join([msg[8], msg[9]]), 'little', signed=False),
        "leapS": int.from_bytes(b"".join([msg[10]]), "little", signed=False),
        "numMeas": int.from_bytes(b"".join([msg[11]]), "little", signed=False),
        "recStat": {
            "clkReset": "".join(msg2bits(splitBytes(msg[12])))[6],
            "leapSec": "".join(msg2bits(splitBytes(msg[12])))[7],
        }
    })
    return data
