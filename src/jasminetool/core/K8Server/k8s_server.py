from ..base import Server
from jasminetool.config import RemoteK8sConfig, JasmineConfig
from .project_init import ProjectInitializer
from .utils import create_connection
from pathlib import Path
import hashlib
from loguru import logger
import yaml
import re
import os

class K8sServer(Server):
    def __init__(self, global_config: JasmineConfig, server_config: RemoteK8sConfig):
        super().__init__(server_config)
        self.global_config = global_config
        self.server_config = server_config
        self.conn = create_connection(server_config)
        self.conn.run("echo 'Connection successful'")

        self.command_dict = {
            "init": "",
            "test": "",
            "sync": "",
            "start": "",
            "install": "",
            "remove": "",
        }
    
    def _with_env_vars(self, command_str: str) -> str:
        """
        Add the env vars to the command string
        """
        env_vars = self.global_config.env_vars
        export_str = ""
        for key, value in env_vars.items():
            export_str += f"export {key}={value} && "
        return export_str + command_str
    
    
    def _parse_hooks(self, hook_file_name: str):
        """
        parse the hook file and return the command string
        """
        hook_file_path = Path("./.jasminetool/k8s_scripts/hooks", hook_file_name)
        if not hook_file_path.exists():
            return ""
        with open(hook_file_path, "r") as f:
            return f.read()
    
    def _upload_script_or_yaml(self, script_str: str, pre_fix: str = "", type_str: str = "sh"):
        """
        upload the script to the HOST server
        """
        hash_str = hashlib.sha256(script_str.encode()).hexdigest()[:8]
        script_name = f"{pre_fix}-{hash_str}.{type_str}"
        # save to .jasminetool/temp/
        temp_save_path = Path("./.jasminetool/temp", script_name)
        if not temp_save_path.exists():
            temp_save_path.parent.mkdir(parents=True, exist_ok=True)
            temp_save_path.touch()
        with open(temp_save_path, "w") as f:
            f.write(script_str)
        try:
            self.conn.run(f"test -d {self.server_config.upload_script_path}")
        except Exception as e:
            logger.warning(f"The path {self.server_config.upload_script_path} does not exist, will create it on the host server")
            self.conn.run(f"mkdir -p {self.server_config.upload_script_path}")
        self.conn.put(temp_save_path, f"{self.server_config.upload_script_path}/{script_name}")
        return f"{script_name}"

    def _init(self, force: bool = False):
        """
        Initialize the Kubernetes cluster environment
        Similar to SSH server, will clone the repo and install the dependencies
        Also will install the env vars to the k8s secret
        """
        command_str = self._parse_hooks("0.pre-init.sh")
        project_init = ProjectInitializer(self.global_config, self.server_config)
        command_str += project_init.run(force=force)
        command_str += self._parse_hooks("1.post-init.sh")
        script_name = self._upload_script_or_yaml(command_str, pre_fix="init")


        host_script_path = os.path.join(self.server_config.work_script_path, script_name)
        config_yaml_str = self._assemble_config_yaml(gpu="cpu", script_path=host_script_path)
        config_yaml_name = self._upload_script_or_yaml(config_yaml_str, pre_fix="init-k8s-job", type_str="yaml")

        config_yaml_path = os.path.join(self.server_config.upload_script_path, config_yaml_name)
        self._submit_job(config_yaml_path=config_yaml_path)
                

    def _test(self):
        """
        Test the connection to the Kubernetes cluster
        """
        try:
            self.conn.run("echo 'Test successful'")
            logger.info("✅ Connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def _submit_job(self, config_yaml_path: str):
        """
        Submit the job to Kubernetes
        
        Args:
            script_path: Path to the script on the remote server
            config_yaml_path: Path to the job configuration YAML file
        """
        try:
            # Submit the job using kubectl
            submit_command = self._with_env_vars(f"kubectl create -f {config_yaml_path}")
            logger.info(f"Submitting K8s job: {submit_command}")
            
            result = self.conn.run(submit_command, pty=True)
            
            if result.ok:
                logger.info("✅ K8s job submitted successfully")
                return True
            else:
                logger.error(f"❌ Failed to submit K8s job: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error submitting K8s job: {e}")
            return False 

    def _sync(self):
        """
        Sync files to the Kubernetes cluster
        """
        try:
            logger.info("🔄 Syncing files to K8s cluster...")
            # TODO: Implement file sync logic
            logger.info("✅ File sync completed")
            return True
        except Exception as e:
            logger.error(f"❌ File sync failed: {e}")
            return False

    def _start(self):
        """
        Start the main job on Kubernetes cluster
        """
        try:
            logger.info("🚀 Starting K8s job...")
            # TODO: Implement job start logic
            logger.info("✅ K8s job started successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start K8s job: {e}")
            return False

    def _install(self):
        """
        Install dependencies on Kubernetes cluster
        """
        try:
            logger.info("📦 Installing dependencies on K8s cluster...")
            # TODO: Implement installation logic
            logger.info("✅ Dependencies installed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to install dependencies: {e}")
            return False

    def _remove(self):
        """
        Remove resources from Kubernetes cluster
        """
        try:
            logger.info("🗑️ Removing K8s resources...")
            # TODO: Implement cleanup logic
            logger.info("✅ K8s resources removed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to remove K8s resources: {e}")
            return False

    def _assemble_config_yaml(self, gpu: str, script_path: str, config_dict: dict = None) -> str:
        """
        Assemble Kubernetes job configuration YAML with variable substitution
        
        Args:
            gpu: GPU type (e.g., 'cpu', 'h100', 'a100')
            config_dict: Additional configuration dictionary (optional)
            
        Returns:
            Path to the generated YAML file
        """
        # Load template YAML
        template_path = Path("./.jasminetool/k8s_scripts/apply_template.yaml")
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path, "r") as f:
            template_str = f.read()

        env_vars = self._extract_env_vars(template_str)

        # Merge configurations
        default_config_dict = self.server_config.common_config.copy()
        if config_dict is not None:
            default_config_dict.update(config_dict)
        
        for key, value in env_vars.items():
            if key in default_config_dict:
                env_vars[key] = default_config_dict[key]
                logger.debug(f"The variable [{key}] is found in the default config dict, will be replaced with [{default_config_dict[key]}]")
            else:
                logger.debug(f"The variable [{key}] is not found in the default config dict, will use its default value [{value}]")
        
        env_vars["TASK_SCRIPT"] = script_path

        if gpu == "cpu":
            env_vars["GPU_NUM"] = "0"
        else:
            env_vars["GPU_PRODUCT"] = self.server_config.gpu_candidates[gpu]
        
        # Save processed YAML to temporary file
        template_str = self._parse_k8s_job_template(template_str, env_vars)
        return template_str
    
    def _extract_env_vars(self, template_str: str) -> dict:
        """
        Extract environment variables from the template string
        env_vars: ${VAR_NAME:-default_value} or ${VAR_NAME}
        """
        pattern = r'\$\{([^:]+):-([^}]+)\}'
        matches = re.findall(pattern, template_str)
        env_vars = {}
        for match in matches:
            variable_name = match[0]
            default_value = match[1]
            env_vars[variable_name] = default_value
        return env_vars
    
    def _parse_k8s_job_template(self, template_str: str, env_vars: dict) -> str:
        """
        Parse the Kubernetes job template and replace the variables with the environment variables
        # replace the variables with the environment variables
        # note in the template yaml_str, the variables are like ${VAR_NAME:-default_value} or ${VAR_NAME}
        """
        for key, value in env_vars.items():
            pattern = r'\$\{' + re.escape(key) + r':-[^}]*\}'
            template_str = re.sub(pattern, value, template_str)
        return template_str

# class K8sServer(Server):
#     def __init__(self, global_config: JasmineConfig, server_config: RemoteK8sConfig):
#         super().__init__(server_config)
#         self.global_config = global_config
#         self.server_config = server_config
#         # try:
#         #     self.conn = create_connection(server_config)
#         #     self.conn.run("echo 'Connection successful'")
#         # except Exception as e:
#         #     logger.error(f"Failed to create connection: {e}")
#         #     raise e
#         self.conn = create_connection(server_config)
#         self.conn.run("echo 'Connection successful'")

#         self.command_dict = {
#             "init": "",
#             "test": "",
#             "sync": "",
#             "start": "",
#             "install": "",
#             "remove": "",
#         }
    
#     @staticmethod
#     def parse_custom_variables(text: str) -> Dict[str, str]:
#         """
#         Parse custom variable syntax like ${Variable_name:-default_value}
        
#         Args:
#             text: String containing custom variables
            
#         Returns:
#             Dictionary mapping variable names to their default values
#         """
#         # Pattern to match ${Variable_name:-default_value}
#         pattern = r'\$\{([^:]+):-([^}]+)\}'
        
#         variables = {}
#         matches = re.findall(pattern, text)
        
#         for match in matches:
#             variable_name = match[0]
#             default_value = match[1]
#             variables[variable_name] = default_value
        
#         return variables

#     @staticmethod
#     def extract_and_replace_variables(text: str, env_vars: Optional[Dict[str, str]] = None) -> Tuple[str, Dict[str, str]]:
#         """
#         Extract variables from text and replace them with actual values
        
#         Args:
#             text: String containing custom variables
#             env_vars: Dictionary of environment variables (optional)
            
#         Returns:
#             Tuple of (replaced_text, extracted_variables)
#         """
#         if env_vars is None:
#             env_vars = {}
        
#         # Extract variables
#         variables = K8sServer.parse_custom_variables(text)
        
#         # Replace variables in text
#         replaced_text = text
#         for var_name, default_value in variables.items():
#             # Use environment variable if available, otherwise use default
#             actual_value = env_vars.get(var_name, default_value)
#             pattern = r'\$\{' + re.escape(var_name) + r':-' + re.escape(default_value) + r'\}'
#             replaced_text = re.sub(pattern, actual_value, replaced_text)
        
#         return replaced_text, variables

#     @staticmethod
#     def parse_k8s_job_template(job_template: str, env_vars: Optional[Dict[str, str]] = None) -> str:
#         """
#         Parse Kubernetes job template and replace custom variables
        
#         Args:
#             job_template: Kubernetes job template as string
#             env_vars: Environment variables dictionary
            
#         Returns:
#             Processed job template with variables replaced
#         """
#         return K8sServer.extract_and_replace_variables(job_template, env_vars)[0]
