from ..base import Server
from jasminetool.config import RemoteK8sConfig, JasmineConfig

class K8sServer(Server):
    def __init__(self, global_config: JasmineConfig, server_config: RemoteK8sConfig):
        super().__init__(server_config)
        self.global_config = global_config

    def _init(self):
        pass

    def _test(self):
        pass

    def _sync(self):
        pass

    def _start(self):
        pass

    def _install(self):
        pass

    def _remove(self):
        pass