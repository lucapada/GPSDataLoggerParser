from lib import Codici

class MessaggioUBX:
    # il messaggio inizia sempre con questi due bytes
    SYNC_CHAR_1 = b'\xb5'
    SYNC_CHAR_2 = b'\x62'

    # ai due bytes si aggiungono sempre classe e id
    def __init__(self, classId: str, msgId: str):
        (classHex, msgHex) = Codici.ublox_UBX_codes(classId, msgId)
        self.messaggio = [self.SYNC_CHAR_1, self.SYNC_CHAR_2, classHex, msgHex]

    def getMessaggio(self, toString=False):
        if toString:
            return b''.join(self.messaggio)
        else:
            return self.messaggio

    def aggiungiByte(self, valore):
        self.messaggio.append(valore)

    def aggiungiBytes(self, valore):
        for b in valore:
            self.aggiungiByte(b)

    def calcola_checksum(self):
        '''Funzione che calcola il checksum, secondo l'algoritmo indicato nel manuale UBX, ritornando i due bytes da appendere al messaggio'''
        chk_A = 0
        chk_B = 0

        for c in self.messaggio:
            chk_A += int.from_bytes(c, 'little')
            chk_A &= 0xFF
            chk_B += chk_A
            chk_B &= 0xFF

        return bytes([chk_A, chk_B])