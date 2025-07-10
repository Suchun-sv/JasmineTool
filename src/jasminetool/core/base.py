from abc import ABC, abstractmethod
from jasminetool.config import BaseConfig

class Server(ABC):
    def __init__(self, config: BaseConfig):
        self.config = config

    @abstractmethod
    def _init(self, force: bool = False):
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

    def init(self, force: bool = False):
        self._init(force)
    
    def test(self) -> bool:
        return self._test()
    
    def check_path(self, path: str) -> bool:
        return self._check_path(path)
    
    def _check_path(self, path: str) -> bool:
        return False
    
    def sync(self):
        self._sync()
    
    def start(self, **kwargs):
        self._start(**kwargs)
    
    def install(self):
        self._install()
    
    def remove(self):
        self._remove()
