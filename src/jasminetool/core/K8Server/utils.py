from jasminetool.config import JasmineConfig, RemoteK8sConfig
from fabric import Connection
from paramiko import RSAKey
import os

def create_connection(server_config: RemoteK8sConfig) -> Connection:
    connect_kwargs = {}
    connect_kwargs["pkey"] = RSAKey.from_private_key_file(os.path.expanduser("~/.ssh/id_rsa"))
    connect_kwargs["look_for_keys"] = False

    return Connection(
        host=server_config.server_ip,
        user=server_config.user_name,
        port=server_config.server_port if server_config.server_port else None,
        gateway=server_config.proxy_ip if server_config.proxy_ip else None,
        connect_kwargs=connect_kwargs,
    )