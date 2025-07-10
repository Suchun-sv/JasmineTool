from jasminetool.core import Server
from jasminetool.config import RemoteSSHConfig, JasmineConfig
from fabric import Connection
from fabric.transfer import Transfer
from invoke.exceptions import UnexpectedExit
import sys

class SSHServer(Server):
    def __init__(self, gloabl_config: JasmineConfig, server_config: RemoteSSHConfig):
        super().__init__(server_config)
        self.gloabl_config = gloabl_config
        self.connection = self._build_connection(server_config)

    def _build_connection(self, config: RemoteSSHConfig) -> Connection:
        connect_kwargs = {}

        # Handle proxy jump via bastion if specified
        if config.proxy_ip and config.proxy_user:
            proxy_str = f"{config.proxy_user}@{config.proxy_ip}:{config.proxy_port}"
            proxy_conn = Connection(proxy_str)
            gateway = proxy_conn
        else:
            gateway = None

        conn = Connection(
            host=config.server_ip,
            user=config.user_name,
            port=config.server_port,
            connect_kwargs=connect_kwargs,
            gateway=gateway,
        )
        return conn

    def _init(self):
        try:
            result = self.connection.run("uname -a", hide=True)
            print(f"[{self.config.name}] Connected: {result.stdout.strip()}")
        except UnexpectedExit as e:
            print(f"Connection failed: {e}", file=sys.stderr)

    def _test(self):
        try:
            result = self.connection.run("echo 'Ping successful'", hide=True)
            print(result.stdout.strip())
        except Exception as e:
            print(f"Test failed: {e}")

    def _sync(self):
        # Example: push local files to remote
        transfer = Transfer(self.connection)
        transfer.put("local_dir/", remote="~/remote_dir/", recursive=True)

    def _start(self):
        # Example: run script
        self.connection.run("bash ~/remote_dir/start.sh")

    def _install(self):
        # Example: install packages
        self.connection.run("sudo apt update && sudo apt install -y python3-pip")

    def _remove(self):
        # Example: delete temp folder
        self.connection.run("rm -rf ~/remote_dir/")
