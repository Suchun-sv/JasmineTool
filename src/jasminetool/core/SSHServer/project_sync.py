from pathlib import Path
from typing import Dict
from fabric import Connection
from loguru import logger
import subprocess
from jasminetool.config import RemoteSSHConfig, JasmineConfig

class ProjectSync:
    def __init__(self, conn: Connection, server_config: RemoteSSHConfig, global_config: JasmineConfig):
        self.conn = conn
        self.server = server_config
        self.global_config = global_config
        self.src_dir = Path(global_config.src_dir)
        self.work_dir = Path(server_config.work_dir)
        self.github_url = server_config.github_url
        self.dvc_cache = server_config.dvc_cache
        self.dvc_remote = server_config.dvc_remote

    def _with_env(self, cmd: str) -> str:
        return (
            f'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.x-cmd.root/bin:$PATH" && '
            f'{cmd}'
        )

    def run(self, force: bool = False, verbose: bool = False) -> bool:
        logger.info(f"[{self.server.name}] 🔄 Starting sync...")
        
        # check if the repo is already cloned
        if not self._ensure_work_dir(): return False

        # check if the git urls match
        if not self._check_git_urls_match(): return False
        if not self._check_git_clean(): return False
        if not self._check_dvc_clean(): return False

        # get the current branch
        branch = self._get_current_branch()
        if branch is None: return False

        # sync the git branch
        if not self._sync_git(branch): return False

        # setup the dvc cache
        if not self._setup_dvc_cache(): return False

        # setup the dvc remote
        if not self._setup_dvc_remote(): return False

        # pull the dvc remote
        if not self._dvc_pull(): return False

        logger.info(f"[{self.server.name}] 🎉 Sync completed successfully on branch {branch}")
        return True
    
    def _check_dvc_clean(self) -> bool:
        res = subprocess.run(f"cd {self.work_dir} && uv run dvc status", shell=True, capture_output=True)
        logger.info(f"[{self.server.name}] 📍 DVC status:\n{res.stdout}")
        if res.stdout.strip() not in [b'Data and pipelines are up to date.', b'There are no data or pipelines tracked in this project yet.\nSee <https://dvc.org/doc/start> to get started!', b'']:
            logger.error(f"[{self.server.name}] ✗ DVC repo not clean:\n{res.stdout}")
            return False
        logger.info(f"[{self.server.name}] ✓ DVC repo is clean")
        return True

    def _check_git_urls_match(self) -> bool:
        # 获取源库和目标库 URL 并比较，可复用你已有逻辑
        # 这里假设成功
        return True

    def _check_git_clean(self) -> bool:
        # res = self.conn.run(self._with_env(f"cd {self.src_dir} && git status --porcelain"), hide=True, warn=True)
        # if res.stdout.strip():
        #     logger.error(f"[{self.server.name}] ✗ Source repo not clean:\n{res.stdout}")
        #     return False
        # logger.info(f"[{self.server.name}] ✓ Source repo is clean")
        res = subprocess.run(f"cd {self.src_dir} && git status --porcelain", shell=True, capture_output=True)
        if res.stdout.strip():
            logger.error(f"[{self.server.name}] ✗ Source repo not clean:\n{res.stdout}")
            return False
        logger.info(f"[{self.server.name}] ✓ Source repo is clean")
        return True

    def _get_current_branch(self) -> str | None:
        # res = self.conn.run(f"cd {self.src_dir} && git rev-parse --abbrev-ref HEAD",
        #                     hide=False, warn=True)
        # if not res.ok:
        #     logger.error(f"[{self.server.name}] ✗ Failed to get branch")
        #     return None
        # branch = res.stdout.strip()
        # logger.info(f"[{self.server.name}] 📍 Current branch: {branch}")
        branch = subprocess.run(f"cd {self.src_dir} && git rev-parse --abbrev-ref HEAD", shell=True, capture_output=True).stdout.decode('utf-8').strip()
        return branch

    def _ensure_work_dir(self) -> bool:
        res = self.conn.run(self._with_env(f"ls {self.work_dir}"), hide=True, warn=True)
        if not res.ok:
            logger.warning(f"[{self.server.name}] Work dir {self.work_dir} missing, please run `jt target init` to initialize")
            return False
        logger.info(f"[{self.server.name}] ✓ Work dir exists")
        return True

    def _sync_git(self, branch: str) -> bool:
        cmds = [
            f"cd {self.work_dir} && git fetch --all",
            f"cd {self.work_dir} && git checkout {branch} || git checkout -b {branch} origin/{branch}",
            f"cd {self.work_dir} && git reset --hard origin/{branch}"
        ]
        for c in cmds:
            res = self.conn.run(self._with_env(c), pty=True, warn=True)
            if not res.ok:
                logger.error(f"[{self.server.name}] ✗ Git sync failed at: {c}")
                return False
        logger.info(f"[{self.server.name}] ✓ Git branch {branch} synced")
        return True

    def _setup_dvc_cache(self) -> bool:
        if not self.dvc_cache:
            logger.info("ℹ️  No DVC cache configured, skipping")
            return True
        cmd = self._with_env(f"cd {self.work_dir} && uv run dvc cache dir --local {self.dvc_cache}")
        res = self.conn.run(cmd, pty=True, warn=True)
        if res.ok:
            logger.info(f"[{self.server.name}] ✓ DVC cache set to {self.dvc_cache}")
            return True
        else:
            logger.error(f"[{self.server.name}] ✗ Failed to set DVC cache")
            return False

    def _setup_dvc_remote(self) -> bool:
        if not self.dvc_remote:
            logger.info("ℹ️  No DVC remote configured, skipping")
            return True
        cmd = self._with_env(
            f'cd {self.work_dir} && uv run dvc remote add --local jasmine_remote "{self.dvc_remote}" --force'
        )
        res = self.conn.run(cmd, pty=True, warn=True)
        if res.ok or "already exists" in res.stderr:
            logger.info(f"[{self.server.name}] ✓ DVC remote configured")
            return True
        logger.error(f"[{self.server.name}] ✗ Failed to set DVC remote")
        return False

    def _dvc_pull(self) -> bool:
        if not self.dvc_remote:
            logger.info("ℹ️  No DVC remote set, skipping pull")
            return True
        cmd = self._with_env(f"cd {self.work_dir} && uv run dvc pull -r jasmine_remote --force")
        res = self.conn.run(cmd, pty=True, warn=True)
        if res.ok:
            logger.info(f"[{self.server.name}] ✓ DVC pull succeeded")
            return True
        logger.error(f"[{self.server.name}] ✗ Failed DVC pull")
        return False