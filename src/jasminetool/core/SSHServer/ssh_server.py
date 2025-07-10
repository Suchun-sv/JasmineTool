from jasminetool.core import Server
from jasminetool.config import RemoteSSHConfig, JasmineConfig
from fabric import Connection, Config
from fabric.transfer import Transfer
from paramiko import RSAKey
from invoke.exceptions import UnexpectedExit
from rich.prompt import Confirm
from loguru import logger
from .project_init import ProjectInitializer

class SSHServer(Server):
    def __init__(self, gloabl_config: JasmineConfig, server_config: RemoteSSHConfig):
        super().__init__(server_config)
        self.gloabl_config = gloabl_config
        self.server_config = server_config
        self.connection = self._build_connection(server_config)

    def _build_connection(self, config: RemoteSSHConfig) -> Connection:
        connect_kwargs = {}
        connect_kwargs["pkey"] = RSAKey.from_private_key_file(config.private_key_path)
        connect_kwargs["look_for_keys"] = False

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
            port=config.server_port if config.server_port else None,
            gateway=gateway,
            connect_kwargs=connect_kwargs,
        )
        return conn

    def _init(self, force: bool = False):
        ProjectInitializer(self.gloabl_config, self.connection, self.server_config).run(force)

    def _test(self) -> bool:
        try:
            result = self.connection.run("echo 'Ping successful'", hide=True)
            logger.info(f"[{self.config.name}] {result.stdout.strip()}")
        except Exception as e:
            logger.error(f"[{self.config.name}] Connection failed: {e}")
            return False
        return True

    def _sync(self):
        # Example: push local files to remote
        pass

    def _start(self):
        # Example: run script
        self.connection.run("bash ~/remote_dir/start.sh")

    def _install(self):
        # Example: install packages
        self.connection.run("sudo apt update && sudo apt install -y python3-pip")

    def _remove(self):
        # Example: delete temp folder
        logger.info(f"[{self.config.name}] Removing work dir: {self.server_config.work_dir}")
        # It is a dangerous operation, so we need to confirm
        confirm = Confirm.ask(f"Are you sure you want to remove [bold red] [{self.config.name}]:{self.server_config.work_dir}[/bold red]?")
        if not confirm:
            logger.info(f"[{self.config.name}] Skipping work dir removal")
            return
        self.connection.run(f"rm -rf {self.server_config.work_dir}")
