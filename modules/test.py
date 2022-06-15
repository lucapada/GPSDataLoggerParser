import numpy as numpy
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

# print(stringa[9:2])
info = b"\x00\x12\x13"
print(info)
bigE = int.from_bytes(info, "big", signed=False)
print(splitBytes(bigE.to_bytes(3, "little")))
print(msg2bits(splitBytes(bigE)))