from jasminetool.config import JasmineConfig, RemoteSSHConfig, RemoteK8sConfig
from jasminetool.core.SSHServer import SSHServer
from jasminetool.core.K8Server import K8sServer
from jasminetool.core import Server

def load_server(name: str, global_config: JasmineConfig) -> Server:
    server_config = global_config.load_server_config(name)
    if server_config.mode == "remote_ssh":
        if not isinstance(server_config, RemoteSSHConfig):
            raise ValueError(f"Server config is not a RemoteSSHConfig: {server_config}")
        return SSHServer(global_config, server_config)
    elif server_config.mode == "remote_k8s":
        if not isinstance(server_config, RemoteK8sConfig):
            raise ValueError(f"Server config is not a RemoteK8sConfig: {server_config}")
        return K8sServer(global_config, server_config)
    else:
        raise ValueError(f"Invalid server type: {server_config.mode}")
    