from dataclasses import dataclass, field, asdict
from typing import Optional, List, Type, Union, Any
from dacite import from_dict
import yaml
import os
from pathlib import Path
from loguru import logger

@dataclass
class BaseConfig:
    name: str
    mode: str
    github_url: str
    work_dir: str
    dvc_cache: str
    dvc_remote: str

@dataclass
class RemoteSSHConfig(BaseConfig):
    user_name: str
    server_ip: str
    private_key_path: str = field(default_factory=lambda: os.path.expanduser("~/.ssh/id_rsa"))
    command_runner: str = field(default_factory=lambda: "uv run")
    num_processes: int = field(default_factory=lambda: 4)
    gpu_config: Optional[str] = field(default_factory=lambda: "0")

    # Optional: proxy jump (e.g., bastion host)
    server_port: Optional[int] = None
    proxy_user: Optional[str] = None
    proxy_ip: Optional[str] = None
    proxy_port: Optional[int] = 22

@dataclass
class RemoteK8sConfig(BaseConfig):
    user_name: str
    server_ip: str

    upload_script_path: str = field(default_factory=lambda: "/root/.scripts/")
    work_script_path: str = field(default_factory=lambda: "/workspace/")
    num_processes: int = field(default_factory=lambda: 4)

    server_port: Optional[int] = None
    proxy_user: Optional[str] = None
    proxy_ip: Optional[str] = None
    proxy_port: Optional[int] = 22

    common_config: dict[str, str] = field(default_factory=lambda: {
        "QUEUE_NAME": "YOUR_QUEUE_NAME",
        "PRIORITY_CLASS": "YOUR_PRIORITY_CLASS",
        "IMAGE_NAME": "nvcr.io/nvidia/pytorch:23.12-py3",
        "WORKSPACE_PVC": "YOUR_WORKSPACE_PVC",
        "WORKSPACE_MOUNT_PATH": "/root/",
        "USER": "YOUR_USER_NAME"
    })
    gpu_candidates: dict[str, str] = field(default_factory=lambda: {
        "h200": "NVIDIA-H200", 
        "h100": "NVIDIA-H100-80GB-HBM3", 
        "a100-80g": "NVIDIA-A100-SXM4-80GB", 
        "a100-40g": "NVIDIA-A100-SXM4-40GB-MIG-3g.20gb"
    })
    submit_job_config: List[Any] = field(default_factory=lambda: [
        {
            "gpu_selector": "h100",
            "GPU_NUM": 1,
        },
        {
            "gpu_selector": "a100-80g",
            "GPU_NUM": 2,
            "CPU_NUM": 24,
            "MEMORY_NUM": 160,
        }
    ])


MODE_CLASS_MAP: dict[str, Type[BaseConfig]] = {
    "remote_ssh": RemoteSSHConfig,
    "remote_k8s": RemoteK8sConfig
}


def _init_example_remote_ssh_config() -> RemoteSSHConfig:
    return RemoteSSHConfig(
        name="Bunny",
        user_name="$USER",
        server_ip="SERVER_IP",
        server_port=None,
        mode="remote_ssh",
        github_url="https://github.com/Suchun-sv/JasmineTool.git",
        work_dir="$HOME/github/JasmineToolLocal",
        dvc_cache="$HOME/.cache/JasmineTool",
        dvc_remote="None",
    )

def _init_example_remote_k8s_config() -> RemoteK8sConfig:
    return RemoteK8sConfig(
        name="Luna",
        k8s_namespace="default",
        k8s_pod_name="jasmine-tool",
        mode="remote_k8s",
        github_url="https://github.com/Suchun-sv/JasmineTool.git",
        work_dir="/home/$USER/github/JasmineToolLocal",
        dvc_cache="/home/$USER/.cache/JasmineTool",
        dvc_remote="s3://cache/JasmineTool/",
    )   

@dataclass
class JasmineConfig:
    sweep_file_path: str = "./.jasminetool/sweep_config.log"
    src_dir: str = field(default_factory=os.getcwd)
    server_config_list: List[Union[RemoteSSHConfig, RemoteK8sConfig]] = field(default_factory=lambda: [_init_example_remote_ssh_config(), _init_example_remote_k8s_config()])
    wandb_key: Optional[str] = field(default_factory=lambda: os.getenv("WANDB_API_KEY"))
    wandb_project: Optional[str] = field(default_factory=lambda: os.path.basename(os.getcwd()))
    env_vars: Optional[dict[str, str]] = field(default_factory=lambda: {})

    def load_server_config(self, name: str) -> Union[RemoteSSHConfig, RemoteK8sConfig]:
        for server in self.server_config_list:
            if server.name == name:
                return server
        raise ValueError(f"Server config not found for name: {name}")

    @classmethod
    def from_yaml(cls, path: str) -> "JasmineConfig":
        if not Path(path).exists():
            logger.error(f"Config file not found at {path}")
        if not path.endswith(".yaml"):
            logger.error("path must end with .yaml")
        
        with open(path, "r") as f:
            raw_dict = yaml.safe_load(f)

        servers_raw = raw_dict.pop("servers", [])
        servers = []
        for item in servers_raw:
            mode = item.get("mode")
            config_cls = MODE_CLASS_MAP.get(mode)
            if not config_cls:
                raise ValueError(f"Unknown mode '{mode}' in server config.")
            servers.append(from_dict(data_class=config_cls, data=item))

        return cls(server_config_list=servers, **raw_dict)

    def to_yaml(self, path: Optional[str] = "./.jasminetool/config.yaml"):
        if not path:
            logger.error("path is not provided, using default path: ./.jasminetool/config.yaml")
            path = "./.jasminetool/config.yaml"

        if not path.endswith(".yaml"):
            raise ValueError("path must end with .yaml")

        out_dict = asdict(self)
        out_dict["servers"] = [asdict(s) for s in self.server_config_list]
        del out_dict["server_config_list"]

        with open(path, "w") as f:
            yaml.safe_dump(out_dict, f, sort_keys=False)

        logger.info(f"Saved config to {path}")

def load_config(path: str) -> "JasmineConfig":
    return JasmineConfig.from_yaml(path)

def save_config(config: "JasmineConfig", path: str):
    config.to_yaml(path)
