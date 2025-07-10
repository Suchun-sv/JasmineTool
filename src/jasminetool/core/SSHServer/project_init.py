from jasminetool.config import JasmineConfig, RemoteSSHConfig
from fabric import Connection

class ProjectInitializer:
    def __init__(self, global_config: JasmineConfig, connection: Connection, server_config: RemoteSSHConfig):
        self.global_config = global_config
        self.server_config = server_config
        self.conn = connection

    def run(self):
        print(f"\n🚀 Initializing project on {self.conn.host}")

        # Step 1: Install x-cmd if needed
        if not self._check_and_install_x_cmd():
            return False

        # Step 2: Install uv if needed
        if not self._check_and_install_uv():
            return False

        # Step 3: Clone GitHub repo if not exists
        if not self._clone_repo():
            return False

        # Step 4: Setup Python environment
        if not self._setup_environment():
            return False

        print("\n🎉 Initialization complete!")
        return True
    
    def _check_and_install_x_cmd(self) -> bool:
        print("\n🔧 Checking x-cmd...")
        result = self.conn.run("command -v x", warn=True, hide=True)
        if result.ok:
            print("✓ x-cmd is already installed")
            return True

        print("⚠ x-cmd not found. Installing...")
        install_cmd = 'eval "$(curl https://get.x-cmd.com)"'
        result = self.conn.run(install_cmd, pty=True)
        if result.ok:
            print("✓ x-cmd installed successfully")
            return True
        else:
            print("✗ Failed to install x-cmd")
            return False
        
    def _check_and_install_uv(self) -> bool:
        print("\n🔧 Checking uv...")
        result = self.conn.run("command -v uv", warn=True, hide=True)
        if result.ok:
            print("✓ uv is already installed")
            return True
        
        print("⚠ uv not found. Installing...")
        install_cmd = 'curl -LsSf https://astral.sh/uv/install.sh | sh'
        result = self.conn.run(install_cmd, pty=True)
        if result.ok:
            print("✓ uv installed successfully")
            return True
        else:
            print("✗ Failed to install uv")
            return False
