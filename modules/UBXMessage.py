from modules.UBXCodes import ublox_UBX_codes

class UBXMessage():
    """
    Classe che permette l'assemblaggio di un messaggio UBX.
    """
    # il messaggio inizia sempre con questi due bytes
    SYNC_CHAR_1 = b'\xb5'
    SYNC_CHAR_2 = b'\x62'

    # ai due bytes si aggiungono sempre classe e id
    def __init__(self, classId: str, msgId: str):
        """
        Costruttore. Crea un messaggio e lo riempie con i caratteri di SYNC, classe e id. Sostanzialmente, i primi 4 byte.
        :param classId:
        :param msgId:
        """
        (classHex, msgHex) = ublox_UBX_codes(classId, msgId)
        self.messaggio = [self.SYNC_CHAR_1, self.SYNC_CHAR_2, classHex, msgHex]

    def getMessaggio(self, toString=False):
        """
        Ritorna il messaggio in formato stringa o come array di byte.
        :param toString:
        :return:
        """
        if toString:
            return b''.join(self.messaggio)
        else:
            return self.messaggio

    def aggiungiByte(self, valore):
        """
        Aggiunge il byte passato come parametro al messaggio.
        :param valore:
        :return:
        """
        self.messaggio.append(valore)

    def aggiungiBytes(self, valore):
        """
        Aggiunge un elenco di bytes passato come parametro al messaggio.
        :param valore:
        :return:
        """
        if (isinstance(valore, bytes)):
            valore = list(valore)
        if (isinstance(valore, list)):
            for v in valore:
                if (isinstance(v, int)):
                    v = v.to_bytes(1, 'little')
                self.aggiungiByte(v)

    def calcola_checksum(self):
        """
        Funzione che calcola il checksum, secondo l'algoritmo indicato nel manuale UBX, ritornando i due bytes da appendere al messaggio.
        :return:
        """
        chk_A = 0
        chk_B = 0
        startCK = 2  # devo calcolare il checksum a partire dalla lunghezza del payload (2° byte)
        k = 0
        for c in self.messaggio:
            if (k >= startCK):
                cB = int.from_bytes(c, 'little')
                chk_A += cB
                chk_A &= 0xFF
                chk_B += chk_A
                chk_B &= 0xFF
            k += 1
        return [chk_A.to_bytes(1, 'little'), chk_B.to_bytes(1, 'little')]
