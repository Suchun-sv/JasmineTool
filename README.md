# JasmineTool

Automated multi‑GPU/multi‑host orchestration via `SSH` (or other methods) to remotely launch parallel Wandb Sweep agents.


## Usage

## init

```bash
jt init
```
init the config file in .jasminetool/config.yaml
set the src_dir to the current directory


## -t target
```bash
jt -t test_ubuntu init
jt -t test_ubuntu config
jt -t test_ubuntu update
jt -t test_ubuntu start
```

### init
if not exist $work_dir, git clone $github_url $work_dir
if not install "x", eval "$(curl https://get.x-cmd.com)"
if not install "uv", curl -LsSf https://astral.sh/uv/install.sh | sh
cd $work_dir
if init.sh, run init.sh
else
   uv venv
   uv sync
ask if use update 

### config
display the config file

### sync
# 先检查src_dir的github_url是否与target的$github_url一致, 不一致则退出
# 如果一致，需要强制检查当前git是否已经clean，并且dvc 是否clean, 不clean则退出
# 记下当前的branch，
进入到target的work_dir下
if exist $dvc_cache, dvc cache dir --local "$dvc_cache"
if exist $dvc_remote, dvc remote add --local jasmine_remote" $dvc_remote"
if exist $dvc_remote:
    dvc pull -r jasmine_remote

### start

### status
