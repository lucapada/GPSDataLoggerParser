import time

import serial, serial.tools.list_ports
from lib import MessaggioUBX, UBX

# OK - TEST
def printLog(messaggio, device=None):
    '''Funzione che stampa messaggio di Log, specifico di un ricevitore (se passato).'''
    if (device is not None):
        dev = device
    else:
        dev = ""
    print(dev + messaggio + "\n")

# OK - TEST
def splitBytes(stream):
    '''
    Riceve uno stream dy bytes e crea un array contenente ciascun byte in ciascuna posizione.
    '''
    splittedBytes = []
    for k in stream:
        splittedBytes.append(k.to_bytes(1, 'big'))
    return splittedBytes

# OK - TEST
def msg2bits(msgBytes):
    '''
    Funzione che codifica ciascun byte presente nell'array "msgBytes" nel corrispettivo bit, ritornando una lista di bit.
    '''
    bits = []
    for n in msgBytes:
        i = int.from_bytes(n, 'little', signed=False)
        bits.append(format(i, '#010b')[2:])
    return bits

def ismember(A: list, B: list):
    '''
    Returns an array of size A. If elements of A is contained in B returns True for that element, otherwise False.
    You can control all the elements are False by using not any(ismember(A,B))
    '''
    out = []
    for a in A:
        if(a in B):
            out.append(True)
        else: out.append(False)
    return out

# OK - TEST
def ublox_COM_find():
    '''
    Funzione che ricerca il ricevitore/i ricevitori UBX connessi al pc.
    Invia un messaggio di richiesta RAW e sulla base della risposta ricevuta lo aggiunge o meno alla collection delle porte, che poi restituisce.
    '''
    COMPort = []
    printLog("Detecting u-blox COM port...");
    ports = serial.tools.list_ports.comports()
    for p in ports:
        s = serial.Serial(p.device, UBX.BAUD_RATE)
        # TODO: non so come settare InputBufferSize a 16384
        try:
            if(s.is_open == False):
                s.open()
        except serial.SerialException as e:
            printLog("Error opening serial port: " + e)
            break

        ubx = UBX.UBX(s)
        ubx.ublox_poll_message("RXM", "RAWX", 0)

        bytes_1 = 0
        bytes_2 = 0
        while (bytes_1 != bytes_2 or bytes_1 == 0):
            bytes_1 = s.in_waiting
            time.sleep(0.5)
            bytes_2 = s.in_waiting

        replyBIN = ''.join(msg2bits(splitBytes(s.read(bytes_1))))
        msg = MessaggioUBX.MessaggioUBX("RXM", "RAWX")
        msgBIN = ''.join(msg2bits(msg.getMessaggio()))
        pos = strfind(msgBIN, replyBIN)
        if (len(pos) > 0):
            l = int(replyBIN[(pos[0] + 32):(pos[0] + 39)], 2) + (
                        int(replyBIN[(pos[0] + 40):(pos[0] + 47)], 2) * pow(2, 8))
            if l != 0:
                printLog("u-blox receiver detected on port " + p.device)
                COMPort.append(p.device)
                # s.close()
                break

        s.close()

    if len(COMPort) == 0:
        printLog("u-blox receiver could not be detected. Try to connect the device and then restart the software.")

    return COMPort


# Porting di funzioni MATLAB
# OK - TEST
def strfind(what: bytes, where: bytes):
    '''
    Funzione che trova la stringa "what" nella stringa "where" e restituisce un array di corrispondenze
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

def weektime2tow(week, time):
    '''
    Conversion from GPS time in continuous format (similar to datenum) to GPS time in week, seconds-of-week.
    '''
    return time - week*7*86400

def check_t(time):
    half_week = 302400
    corrTime = time
    if time > half_week:
        corrTime = time - 2 * half_week
    elif time < -half_week:
        corrTime = time + 2 * half_week
    return corrTime
