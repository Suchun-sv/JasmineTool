from ..base import Server
from jasminetool.config import RemoteK8sConfig, JasmineConfig

class K8sServer(Server):
    def __init__(self, global_config: JasmineConfig, server_config: RemoteK8sConfig):
        super().__init__(server_config)
        self.global_config = global_config

    def _init(self):
        """
        similar to SSH server, will clone the repo and install the dependencies
        also will install the env vars to the k8s secret
        """
        pass

    def _test(self):
        """
        will do nothing for now
        """
        pass

    def _sync(self):
        """
        will do nothing for now
        """
        pass

    def _start(self):
        """
        core function, will assemble the commands and submit to the job
        """
        pass

    def _install(self):
        pass

    def _remove(self):
        pass