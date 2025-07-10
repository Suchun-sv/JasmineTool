from abc import ABC, abstractmethod
from jasminetool.config import BaseConfig

class Server(ABC):
    def __init__(self, config: BaseConfig):
        self.config = config

    @abstractmethod
    def _init(self):
        pass

    @abstractmethod
    def _test(self) -> bool:
        pass

    @abstractmethod
    def _sync(self):
        pass

    @abstractmethod
    def _start(self):
        pass
    
    @abstractmethod
    def _install(self):
        pass

    @abstractmethod
    def _remove(self):
        pass

    def init(self):
        self._init()
    
    def test(self) -> bool:
        return self._test()
    
    def sync(self):
        self._sync()
    
    def start(self):
        self._start()
    
    def install(self):
        self._install()
    
    def remove(self):
        self._remove()
