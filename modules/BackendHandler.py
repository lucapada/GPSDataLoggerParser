from . import ThreadWithReturn
from . import SerialParser
from . import Logger

class Handler(object):
    """
    Per ogni ricevitore viene creata una classe Handler. Questa classe si occupa di creare tutti gli oggetti necessari per gestire la connessione con la periferica, lo scarico e la richiesta dei dati e svolgere il tutto all'interno di un thread.
    """

    def __init__(self, mainWindow, port: str, baudrate = 9600, gnss: dict = {}, filePath: str = ".", weekChanges: bool = False):
        """
        Costruttore della classe.

        :param mainWindow: finestra principale (GUI)
        :param port: nome della porta a cui il ricevitore è connesso
        :param baudrate: baudrate con cui configurare la connessione
        :param gnss: dizionario contenente i GNSS da cui ricevere dati
        :param filePath: percorso in cui salvare i file
        :param weekChanges: parametro booleano per considerare le week nell'elaborazione del file relativo alla sincronizzazione dei tempi
        """
        self.baudrate = baudrate
        self.connection = SerialParser.SerialParser(mainWindow, port, self.baudrate)
        self.logger = Logger.Logger(mainWindow, self.connection, filePath, gnss, weekChanges)
        self.thread = ThreadWithReturn.ThreadWithReturn(target=self.logger.logData)

    def isActive(self):
        """
        Ritorna true se la connessione è attiva, altrimenti false.
        :return:
        """
        return self.logger.serial.isOpen()

    def handleData(self):
        """
        Lancia il thread per l'acquisizione dei dati avente logData come funzione target.
        :return:
        """
        self.thread.start()

    def stop(self, nameTS):
        """
        Interrompe la corsa del thread agendo su un parametro della classe.
        :param nameTS: data e ora dell'acquisizione da aggiungere al nome del files quando l'acquisizione termina.
        :return:
        """
        self.thread.stop(nameTS)

    def join(self):
        """
        Metodo che viene invocato alla chiusura del thread. Chiude la connessione con la periferica e attende l'esecuzione del thread.
        :return:
        """
        self.connection.close()
        self.thread.join()
