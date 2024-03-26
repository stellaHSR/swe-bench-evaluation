import logging, os, platform, subprocess

from constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    INSTALL_FAIL,
    INSTALL_PASS,
    INSTALL_TIMEOUT,
    KEY_INSTANCE_ID,
    KEY_MODEL,
    MAP_REPO_TO_INSTALL,
    MAP_REPO_TO_TEST_FRAMEWORK,
    MAP_VERSION_TO_INSTALL,
    RESET_FAILED,
    TESTS_FAILED,
    TESTS_PASSED,
    TESTS_TIMEOUT,
    TESTS_ERROR,
)
from tempfile import TemporaryDirectory
from traceback import format_exc
from typing import Dict, List
from utils import (
    clone_repo,
    get_conda_env_names,
    get_environment_yml,
    get_requirements,
    get_test_directives,
)

from loguru import logger as logger_testbed



class ExecWrapper:
    def __init__(
            self,
            subprocess_args: Dict = None,
    ):
        if subprocess_args is None:
            self.subprocess_args = {}
        else:
            self.subprocess_args = subprocess_args

        import sys

        # 获取Python的主版本号、次版本号和微版本号
        major, minor, micro = sys.version_info[:3]

        logger_testbed.info(f"Python version: {major}.{minor}.{micro}")
        if minor < 9:
            self.subprocess_args.pop("capture_output")
            self.subprocess_args.pop("text")
            # self.subprocess_args["universal_newlines"] = True
            
            
        print(self.subprocess_args)

    
    def __call__(self, cmd, raise_error=True, **kwargs):
        try:
            
            
            combined_args = {**self.subprocess_args, **kwargs}
            # if combined_args.get("shell", False):
            #     cmd = ["/bin/bash", "-c", cmd]
            output = subprocess.run(cmd, **combined_args)
            return output
        except subprocess.CalledProcessError as e:
            if raise_error:
                logger_testbed.error(f"Error: {e}")
                logger_testbed.error(f"Error stdout: {e.stdout}")
                logger_testbed.error(f"Error stderr: {e.stderr}")
                logger_testbed.error(f"Error traceback: {format_exc()}")
                raise e


class TestbedContextManager:
    def __init__(
            self,
            task_instances: List,
            log_dir: str,
            path_conda: str = None,
            testbed: str = None,
            verbose: bool = False,
            timeout: int = None,
            temp_dir: str = None,
    ):
        """
        Initialize testbed context. Creates temporary directories and groups task instances
        by repo/version.

        Args:
            task_instances (list): List of task instances
            log_dir (str): Path to log directory
            path_conda (str): Path to conda installation
            testbed (str): Path to testbed directory
            verbose (bool): Whether to show logs
            timeout (int): Timeout for actions
            temp_dir (str): Path to temporary directory
        """
        logger_testbed.propagate = verbose
        self.verbose = verbose
        self.old_dir = os.getcwd()
        self.log_dir = os.path.abspath(log_dir)
        self.timeout = timeout
        self.exec = ExecWrapper(
            subprocess_args={
                "check": True,
                "shell": False,
                "capture_output": True,
                "text": True,
            }
        )
        
        # Create log, temp directories if they don't exist
        if not os.path.exists(self.log_dir):
            logger_testbed.info(f"[Testbed] Creating log directory {self.log_dir}")
            os.makedirs(self.log_dir, exist_ok=True)
        if temp_dir is not None and not os.path.exists(temp_dir):
            logger_testbed.info(f"[Testbed] Creating temp directory {temp_dir}")
            os.makedirs(temp_dir, exist_ok=True)
        temp_dir = os.path.abspath(temp_dir) if temp_dir is not None else None
        
        # Set up conda path, create in temp directory if None
        # path_conda = "/home/deepwisdom/anaconda3"
        
        if path_conda is not None:
            self.temp_dir_conda = None
            self.path_conda = os.path.abspath(path_conda)
        else:
            self.temp_dir_conda = TemporaryDirectory(dir=temp_dir)
            self.path_conda = self.temp_dir_conda.name
        logger_testbed.info(f"[Testbed] Using conda path {self.path_conda}")
        
        # Set up testbed path, create in temp directory if None
        if testbed is not None:
            self.temp_dir_work = None
            self.testbed = os.path.abspath(testbed)
        else:
            self.temp_dir_work = TemporaryDirectory(dir=temp_dir)
            self.testbed = self.temp_dir_work.name
        logger_testbed.info(
            f"[Testbed] Using working directory {self.testbed} for testbed"
        )
        
        # Sort task instances by created_at
        # logger_taskenv.info(task_instances[0])
        self.task_instances = sorted(
            task_instances, key=lambda x: x["created_at"], reverse=True
        )
        
        # Group repos by repo, then version
        self.task_instances_grouped = {}
        for instance in self.task_instances:
            # Create test command from framework + directives
            test_type = MAP_REPO_TO_TEST_FRAMEWORK[instance["repo"]]
            test_directives = get_test_directives(instance)
            instance["test_cmd"] = f"{test_type} {' '.join(test_directives)}"
            
            # Group task instances by repo, version
            repo = instance["repo"]
            version = instance["version"] if "version" in instance else None
            if repo not in self.task_instances_grouped:
                self.task_instances_grouped[repo] = {}
            if version not in self.task_instances_grouped[repo]:
                self.task_instances_grouped[repo][version] = []
            self.task_instances_grouped[repo][version].append(instance)
        
        # Log grouped task instances to be run
        self.setup_refs = {}
        for repo, map_version_to_instances in self.task_instances_grouped.items():
            logger_testbed.info(
                f"[Testbed] Repo {repo}: {len(map_version_to_instances)} versions"
            )
            
            # Determine instances to use for environment installation
            self.setup_refs[repo] = {}
            for version, instances in map_version_to_instances.items():
                logger_testbed.info(
                    f"[Testbed] \tVersion {version}: {len(instances)} instances"
                )
                self.setup_refs[repo][version] = instances[0]
        
        # Remove None versions, versions not in MAP_VERSION_TO_INSTALL
        self._custom_restraints()
    
    def __enter__(self):
        """
        Set up testbed (conda environments, git repositories)
        """
        # If path_conda not provided, create temporary miniconda3 installation
        is_osx_64 = False
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            is_osx_64 = True

        logger_testbed.info(f"[Testbed] Using conda path {self.path_conda}")
        
        # Set up conda executables, get existing environments
        self.path_conda = os.path.abspath(self.path_conda)
        conda_bin_path = os.path.join(self.path_conda, "bin")
        shellenv = os.environ.copy()
        shellenv["PATH"] = conda_bin_path + os.pathsep + shellenv["PATH"]
        self.exec.subprocess_args["env"] = shellenv
        
        path_activate = os.path.join(self.path_conda, "bin", "activate")
        exec_type = "mamba" if "mamba" in self.path_conda else "conda"
        exec_cmd = os.path.join(self.path_conda, "bin", exec_type)
        # env_list = get_conda_env_names(exec_cmd, shellenv)
        
        # Set up testbed (environment, github repo) for each repo
        
        # fixme
        return self
    
    def get_distributed_tasks(self) -> List:
        """
        Create task group (instances + keywords) for each repo/version

        Returns:
            list: List of task groups, each group containing task instances
                from the same repo with the same version
        """
        distributed_tasks = []
        for repo, map_version_to_instances in self.task_instances_grouped.items():
            repo_prefix = repo.replace("/", "__")

            for version, instances in map_version_to_instances.items():
                env_name = f"{repo_prefix}__{version}"
                print(env_name)
                task_set = {
                    "conda_path": self.path_conda,
                    "log_dir": self.log_dir,
                    "task_instances": instances,
                    "testbed": os.path.join(self.testbed, env_name),
                    "timeout": self.timeout,
                    "venv": env_name,
                    "version": version,
                    "verbose": self.verbose,
                }
                distributed_tasks.append(task_set)
        return distributed_tasks
    
    def _custom_restraints(self):
        """
        Custom restraints per repo
        """
        for repo, group in self.task_instances_grouped.items():
            if None in group:
                logger_testbed.info(f"[Testbed] Removed None version from repo {repo}")
                del group[None]
            versions = list(group.keys())
            for version in versions:
                if version not in MAP_VERSION_TO_INSTALL[repo]:
                    logger_testbed.info(
                        f"[Testbed] Removed {version} version from repo {repo} (Install instructions not given)"
                    )
                    del group[version]
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.temp_dir_work is not None:
            self.temp_dir_work.cleanup()
        if self.temp_dir_conda is not None:
            self.temp_dir_conda.cleanup()

logger_taskenv = logger_testbed


class TaskEnvContextManager:
    def __init__(
            self,
            instance: Dict,
            testbed: str,
            venv: str,
            log_dir: str,
            conda_path: str,
            verbose: bool = False,
            timeout: int = None,
            is_eval: bool = False,
            log_suffix: str = None,
    ):
        """
        Sets up execution context for a single task instance

        Args:
            instance (dict): Task instance
            testbed (str): Path to testbed directory
            venv (str): Name of conda environment (should exist in conda_path)
            log_dir (str): Path to log directory
            conda_path (str): Path to conda installation
            verbose (bool): Whether to show logs
            timeout (int): Timeout for actions
            is_eval (bool): Whether this is for evaluating a model on SWE Bench
                (Mainly for logging purposes)
        """
        logger_taskenv.propagate = verbose
        self.instance = instance
        self.conda_path = conda_path
        self.cwd = os.getcwd()
        self.is_eval = is_eval
        self.testbed = testbed
        self.testbed_name = testbed.split("/")[-1]
        self.venv = "scikit-learn__scikit-learn__0.22"
        
        # Log file naming
        log_file_name = (
            f"{instance[KEY_INSTANCE_ID]}.{instance[KEY_MODEL]}.eval.log"
            if self.is_eval
            else f"{instance[KEY_INSTANCE_ID]}.log"
        )
        if log_suffix is not None:
            log_file_name = (
                f"{instance[KEY_INSTANCE_ID]}.{instance[KEY_MODEL]}.{log_suffix}.eval.log"
                if self.is_eval
                else f"{instance[KEY_INSTANCE_ID]}.{log_suffix}.log"
            )
        self.log_file = os.path.join(log_dir, log_file_name)
        
        self.cmd_activate = (
            f"conda activate {self.venv}"
        )
        
        # Using subprocess to run the command
        
        self.timeout = timeout

        self.exec = ExecWrapper(
            subprocess_args={
                "check": True,
                "shell": False,
                "capture_output": True,
                "text": True,
                # "env": shellenv,
            }
        )
    
    def __enter__(self):
        """
        Enter task environment, set up log file
        """
        os.chdir(self.testbed)
        # os.chdir(os.path.join(self.testbed, "scikit-learn__scikit-learn__0.20"))
        with open(self.log_file, "w") as f:
            f.write(
                f"Task Metadata:\n\t- Instance ID: {self.instance[KEY_INSTANCE_ID]}\n\t- Testbed: {self.testbed}\n\t- Virtual Env.: {self.venv}\n"
            )
            if self.is_eval:
                f.write(f"\t- Evaluation Model: {self.instance[KEY_MODEL]}\n")
        return self
    
    def copy_repo(self, source_path: str, destination_path: str):
        import shutil
        
        if not os.path.isdir(source_path):
            raise ValueError("Source path does not exist or is not a directory.")

        os.makedirs(destination_path, exist_ok=True)

        # Copy the repository
        try:
            shutil.copytree(
                source_path, destination_path, dirs_exist_ok=True
            )  # For Python 3.8+, dirs_exist_ok handles existing directories
        except TypeError:
            # Fallback for Python < 3.8, where dirs_exist_ok is not available
            # if os.listdir(destination_path):  # If destination is not empty
            #     raise ValueError("Destination directory is not empty and dirs_exist_ok is not supported.")
            import subprocess
            import sys

            def copy_tree_system(src, dst):
                if sys.platform.startswith('linux') or sys.platform == 'darwin':
                    subprocess.run(['cp', '-r', src, dst])
                elif sys.platform == 'win32':
                    subprocess.run(['xcopy', src, dst, '/E', '/I', '/Q'])
                else:
                    raise NotImplementedError(f"OS not supported: {sys.platform}")
            
            copy_tree_system(source_path, destination_path)
        logger_taskenv.info(f"Repository contents from '{source_path}' copied successfully to '{destination_path}'.")

    
    def reset_task_env(self, instance: Dict):
        """
        Reset task environment + testbed and checkout base commit of given task instance

        Args:
            instance (dict): Task instance
        Returns:
            bool: True if reset successful, False otherwise
        """
        try:
            bc = instance['base_commit']
            repo = instance["repo"]
            version = instance["version"] if "version" in instance else None
            repo_prefix = repo.replace("/", "__")
            env_name = f"{repo_prefix}__{version}"
            target_dir = f"/home/{bc}"
            if not os.path.exists(target_dir):
                self.copy_repo(source_path="/repos/scikit-learn__scikit-learn__0.20", destination_path=target_dir)
            os.chdir(os.path.join(f"/home/{bc}", env_name))
            logger_taskenv.info(os.getcwd())
            # Remove all paths in .gitignore
            if os.path.exists(".gitignore"):
                self.exec(
                    "git ls-files --ignored --exclude-standard -o -z | xargs -0 -r rm -rf".split(),
                    raise_error=False,
                )
            
            # Reset git repo + checkout base commit
            self.exec("git restore .".split(" "))
            self.exec("git reset HEAD .".split(" "))
            self.exec("git clean -fdx".split(" "))
            self.exec(
                f"git -c advice.detachedHead=false checkout {instance['base_commit']}".split(
                    " "
                )
            )
            logger_taskenv.info("git restore .".split(" "))
            logger_taskenv.info("git reset HEAD .".split(" "))
            logger_taskenv.info("git clean -fdx".split(" "))
            logger_taskenv.info(f"git -c advice.detachedHead=false checkout {instance['base_commit']}")
            
            logger_taskenv.info(
                f"[{self.testbed_name}] [{instance[KEY_INSTANCE_ID]}] Reset task environment to {instance['base_commit']}"
            )
            
            return True
        except Exception as e:
            err_msg = f"{RESET_FAILED}; Failed to reset task environment to {instance['base_commit']}: {e}"
            logger_taskenv.error(f"[{self.testbed_name}] {err_msg}")
            with open(self.log_file, "a") as f:
                f.write(err_msg)
            return False


    def run_install_task(self, instance: Dict) -> bool:
        """
        Run installation for task instance
    
        Args:
            instance (dict): Task instance
        Returns:
            bool: True if installation successful, False otherwise
        """
        # Get installation instructions by repo/version
        specifications = MAP_VERSION_TO_INSTALL[instance["repo"]][instance["version"]]
        
        # Run pre-install set up if provided
        if "pre_install" in specifications:
            for pre_install in specifications["pre_install"]:
                cmd_pre_install = f"{self.cmd_activate} && {pre_install}"
                logger_taskenv.info(
                    f"[{self.testbed_name}] [{instance[KEY_INSTANCE_ID]}] Running pre-install setup command: {cmd_pre_install}"
                )
                out_pre_install = self.exec(
                    cmd_pre_install, timeout=self.timeout, shell=True
                )
                with open(self.log_file, "a") as f:
                    f.write(f"Pre-installation Command: {cmd_pre_install}\n")
                    f.write(f"Std. Output: {out_pre_install.stdout}\n")
                    f.write(f"Std. Error: {out_pre_install.stderr}\n")
                if out_pre_install.returncode != 0:
                    logger_taskenv.error(
                        f"[{self.testbed_name}] [{instance[KEY_INSTANCE_ID]}] Pre-install setup failed"
                    )
                    with open(self.log_file, "a") as f:
                        f.write(f"\n{INSTALL_FAIL}\n")
                    return False
        
        # Skip installation if no instructions provided
        if "install" not in specifications:
            return True

        file_suffix = '.c'

        # 获取当前执行路径
        current_path = os.path.join(os.getcwd(), "sklearn", "__check_build")
        logger_taskenv.info(f"current_path is {current_path}")
        # 遍历当前路径下的所有文件
        file_exists = any(fname.endswith(file_suffix) for fname in os.listdir(current_path))
        logger_taskenv.info(f"file_exists is {file_exists}")
        
        if not file_exists:
            cmd_install = "pip install -v --no-use-pep517 --no-build-isolation -e ."
            out_install = self.exec(
                cmd_install, shell=True, timeout=self.timeout, check=False
            )
        # cmd_install = f"{self.cmd_activate}"
        logger_taskenv.info(
            f"[{self.testbed_name}] [{instance[KEY_INSTANCE_ID]}] Installing with command: {cmd_install}"
        )

        # # 执行命令
        
        # Installation successful
        logger_taskenv.info(
            f"[{self.testbed_name}] [{instance[KEY_INSTANCE_ID]}] Installation successful"
        )
        with open(self.log_file, "a") as f:
            f.write(f"\n{INSTALL_PASS}\n")
            
            
        
        return True
    
    
    def apply_patch(
            self, patch: str, patch_type: str = "", revert: bool = False
    ) -> bool:
        """
        Apply patch to task environment
    
        Args:
            patch (str): Plaintext of patch to apply
            patch_type (str): Type of patch (e.g. "eval", "test")
        Returns:
            bool: True if patch applied successfully, False otherwise
        """
        # If patch is `None`, indicate in log and skip
        if patch is None:
            logger_taskenv.error(
                f"[{self.testbed_name}] [{self.instance[KEY_INSTANCE_ID]}] Patch is `None` ({patch_type})"
            )
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; Prediction patch is `None`")
            return False
        
        # Write patch to temporary patch file in parent directory
        patch_path = os.path.join(
            os.path.dirname(self.testbed.rstrip("/")),
            f"temp_{self.instance[KEY_INSTANCE_ID]}_{patch_type}.patch",
        )
        with open(patch_path, "w", encoding="utf-8") as f:
            f.write(patch)
        
        # Apply patch to testbed directory
        apply_cmd = (
            f"git apply -v -R {patch_path}" if revert else f"git apply -v {patch_path}"
        )
        out_patch = self.exec(apply_cmd.split(" "), raise_error=False, check=False)
        os.remove(patch_path)
        
        log_cmd = "Revert" if revert else "Apply"
        if out_patch.returncode != 0:
            # Patch apply failed
            logger_taskenv.error(
                f"[{self.testbed_name}] [{self.instance[KEY_INSTANCE_ID]}] {log_cmd} patch failed ({patch_type})"
            )
            
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; ({patch_type})\nOutput:\n")
                f.write(out_patch.stdout if out_patch.stdout is not None else "")
                f.write(out_patch.stderr if out_patch.stderr is not None else "")
            return False
        
        # Patch apply succeeded
        logger_taskenv.info(
            f"[{self.testbed_name}] [{self.instance[KEY_INSTANCE_ID]}] {log_cmd} patch successful ({patch_type})"
        )
        with open(self.log_file, "a") as f:
            f.write(f"{APPLY_PATCH_PASS} ({patch_type})\n")
        return True
    
    
    def run_tests_task(self, instance: Dict):
        """
        Run tests for task instance
    
        Args:
            instance (dict): Task instance
        Returns:
            bool: True if test script ran successfully, False otherwise
        """
        
        bc = instance["base_commit"]
        repo = instance["repo"]
        version = instance["version"] if "version" in instance else None
        repo_prefix = repo.replace("/", "__")
        env_name = f"{repo_prefix}__{version}"
        
        os.chdir(os.path.join(f"/home/{bc}", env_name))
        working_dir = os.getcwd()
        
        logger_testbed.info(f"Working directory: {working_dir}")
        try:
            # Run test command for task instance
            
            
            # test_cmd = f"{self.cmd_activate} && {instance['test_cmd']}"
            
            test_cmd = f"{instance['test_cmd']}"
            
            logger_testbed.info(f"check instance['base_commit']:{instance['base_commit']}")
            
            with open(self.log_file, "a") as f:
                f.write(f"Test Script: {test_cmd};\n")

            logger_taskenv.info(test_cmd)

            # import pdb;pdb.set_trace()

            out_test = self.exec(
                test_cmd, shell=True, timeout=self.timeout, check=False
            )
            

            # Write test results to log file
            with open(self.log_file, "a") as f:
                f.write(f"Output:\n")
                f.write(out_test.stdout if out_test.stdout is not None else "")
                f.write(out_test.stderr if out_test.stderr is not None else "")

                
                # print("这将会写入到 'output.log' 文件中")
                
                if out_test.returncode != 0:
                    logger_testbed.info(f"\n{TESTS_FAILED}\n")
                    f.write(f"\n{TESTS_FAILED}\n")
                else:
                    logger_testbed.info(f"\n{TESTS_PASSED}\n")
                    f.write(f"\n{TESTS_PASSED}\n")
                
            logger_taskenv.info(
                f"[{self.testbed_name}] [{instance[KEY_INSTANCE_ID]}] Test script run successful"
            )
            return True
        except subprocess.TimeoutExpired:
            # Test command run timed out
            logger_taskenv.error(
                f"[{self.testbed_name}] [{instance[KEY_INSTANCE_ID]}] Test script run time out {self.timeout}"
            )
            with open(self.log_file, "a") as f:
                f.write(f"{TESTS_TIMEOUT} after {self.timeout} seconds\n")
            return False
        except Exception as e:
            # Test command run failed
            logger_taskenv.error(
                f"[{self.testbed_name}] [{instance[KEY_INSTANCE_ID]}] Test script run failed"
            )
            with open(self.log_file, "a") as f:
                f.write(f"{TESTS_ERROR}: {e}")
            return False
    
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self.cwd)
