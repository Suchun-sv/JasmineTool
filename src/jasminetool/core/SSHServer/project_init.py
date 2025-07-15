from jasminetool.config import JasmineConfig, RemoteSSHConfig
from fabric import Connection
from loguru import logger

class ProjectInitializer:
    def __init__(self, global_config: JasmineConfig, connection: Connection, server_config: RemoteSSHConfig):
        self.global_config = global_config
        self.server_config = server_config
        self.conn = connection
    
    def _with_uv_xcmd_env(self, cmd: str) -> str:
        base_cmd = f'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.x-cmd.root/bin:$PATH" && {cmd} '
        for env_var, env_value in self.global_config.env_vars.items():
            base_cmd = f'export {env_var}={env_value} && {base_cmd}'
        return base_cmd


    def run(self, force: bool = False):
        logger.info(f"Initializing project on {self.conn.host}")

        # Step 1: Install x-cmd if needed
        if not self._check_and_install_x_cmd():
            return False

        # Step 2: Install uv if needed
        if not self._check_and_install_uv():
            return False

        # Step 3: Clone GitHub repo if not exists
        if not self._clone_repo(force):
            return False

        # Step 4: Setup Python environment
        # Check if init.sh exists in work_dir
        init_script_path = f"{self.server_config.work_dir}/install.sh"
        check_result = self.conn.run(f"test -f {init_script_path}", warn=True)
        
        if check_result.ok:
            logger.info(f"[{self.server_config.name}] 🔧 Running install.sh...")
            full_command = f"bash -c '{self._with_uv_xcmd_env('cd')} {self.server_config.work_dir} && chmod +x install.sh && ./install.sh'"
            result = self.conn.run(full_command, pty=True)
            if not result.ok:
                logger.error("✗ Failed to run install.sh")
                return False
        else:
            logger.debug(f"[{self.server_config.name}] install.sh not found in {self.server_config.work_dir}, skipping...")
            if not self._setup_environment():
                return False

        logger.info(f"[{self.server_config.name}] 🎉 Initialization complete!")
        return True
    
    def _check_and_install_x_cmd(self) -> bool:
        logger.info("🔧 Checking x-cmd...")
        result = self.conn.run(self._with_uv_xcmd_env("command -v x-cmd"), warn=True, hide=True)
        if result.ok:
            logger.info(f"[{self.server_config.name}] ✓ x-cmd is already installed")
            return True

        logger.warning(f"[{self.server_config.name}] ⚠ x-cmd not found. Installing...")
        install_cmd = self._with_uv_xcmd_env('eval "$(curl https://get.x-cmd.com)"')
        result = self.conn.run(install_cmd, pty=True)
        if result.ok:
            logger.info(f"[{self.server_config.name}] ✓ x-cmd installed successfully")
            return True
        else:
            logger.error(f"[{self.server_config.name}] ✗ Failed to install x-cmd")
            return False
        
    def _check_and_install_uv(self) -> bool:
        logger.info(f"[{self.server_config.name}] 🔧 Checking uv...")
        result = self.conn.run(self._with_uv_xcmd_env("command -v uv"), warn=True, hide=True)
        if result.ok:
            logger.info(f"[{self.server_config.name}] ✓ uv is already installed")
            return True
        
        logger.warning(f"[{self.server_config.name}] ⚠ uv not found. Installing...")
        install_cmd = self._with_uv_xcmd_env('curl -LsSf https://astral.sh/uv/install.sh | sh')
        result = self.conn.run(install_cmd, pty=True)
        if result.ok:
            logger.info(f"[{self.server_config.name}] ✓ uv installed successfully")
            return True
        else:
            logger.error(f"[{self.server_config.name}] ✗ Failed to install uv")
            return False
    
    def _clone_repo(self, force: bool = False) -> bool:
        # check if the repo is already cloned
        result = self.conn.run(f"ls {self.server_config.work_dir}", warn=True, hide=True)

        if result.ok and not force:
            logger.info(f"result: {result}")
            logger.warning(f"GitHub repo already exists at {self.server_config.work_dir}, use --force to override")
            # raise ValueError(f"GitHub repo already exists at {self.server_config.work_dir}, use --force to override")
            return True

        if result.ok and force:
            logger.warning(f"force remove {self.server_config.work_dir}")
            self.conn.run(f"rm -rf {self.server_config.work_dir}")

        if not result.ok:
            logger.info(f"check clone path result: {result}")

        # clone the repo
        result = self.conn.run(f"git clone {self.server_config.github_url} {self.server_config.work_dir}", pty=True)
        if result.ok:
            logger.info(f"✓ GitHub repo cloned successfully to {self.server_config.work_dir}")
            return True
        else:
            logger.error(f"✗ Failed to clone GitHub repo to {self.server_config.work_dir}")
            return False
    
    def _setup_environment(self) -> bool:
        logger.info(f"[{self.server_config.name}] 🔧 Setting up Python environment...")
        result = self.conn.run(self._with_uv_xcmd_env(f"cd {self.server_config.work_dir} && uv venv"), pty=True)
        if not result.ok:
            logger.error("✗ Failed to setup Python environment")
            return False

        result = self.conn.run(self._with_uv_xcmd_env(f"cd {self.server_config.work_dir} && uv sync"), pty=True)
        if not result.ok:
            logger.error("✗ Failed to sync Python environment")
            return False

        logger.info(f"[{self.server_config.name}] ✓ Python environment setup successfully")
        return True
