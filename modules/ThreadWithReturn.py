import sys
from threading import Thread

# determino automaticamente quale versione di Python è in esecuzione
python_version, *_ = sys.version_info
if python_version >= 3:
    _thread_target, _thread_args, _thread_kwargs = ('_target', '_args', '_kwargs')
else:
    _thread_target, _thread_args, _thread_kwargs = ('_Thread_target', '_Thread_args', '_Thread_kwargs')


class ThreadWithReturn(Thread):
    """
    Classe che estende la classe Thread. Crea un Thread indicando una funzione target passata come argomento del costruttore.
    """
    # chiamata al costruttore padre
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDaemon(True)

    def run(self):
        """
        override del metodo run(), necessario perché run chiama solo la funzione target.
        :return:
        """
        target_function = getattr(self, _thread_target)
        # controlla se esiste la funzione target, e nel caso la chiama passandogli gli argomenti del thread.
        if target_function:
            self._return = target_function(*getattr(self, _thread_args), **getattr(self, _thread_kwargs))

    def join(self, *args, **kwargs):
        """
        # Chiamata al join padre
        :param args:
        :param kwargs:
        :return:
        """
        super().join(*args, **kwargs)
        return self._return

    def stop(self, nameTS):
        """
        Variazione dell'attributo running per l'interruzione forzata del thread.
        :param nameTS: data e ora dell'acquisizioni da aggiungere al nome del file quando l'acquisizioni termina.
        :return:
        """
        setattr(self, "running", False)
        setattr(self, "nameTS", nameTS)
