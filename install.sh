#!/bin/bash
repo=tmc-chopper-tune
script_path=$(realpath $(echo $0))
repo_path=$(dirname $script_path)

# Not a root check
if [ "$(id -u)" = "0" ]; then
    echo "Script must run from non-root !!!"
    exit 1
fi

# Result data creation
result_folder=~/printer_data/config/tmc-chopper-tune
if [ ! -d "$result_folder" ]; then
    mkdir -p "$result_folder"
    echo "Make $result_folder direction successfully complete"
fi

# Klipper extras addition
g_shell_path=~/klipper/klippy/extras/
g_shell_name=gcode_shell_command.py
if [ -f "$g_shell_path/$g_shell_name" ]; then
    echo "Including $g_shell_name aborted, $g_shell_name already exists in $g_shell_path"
else
    cp "$repo_path/$g_shell_name" $g_shell_path
    echo "Copying $g_shell_name to $g_shell_path successfully complete"
fi

# Config hardlink
cfg_name=tmc_chopper_tune.cfg
cfg_path=~/printer_data/config/
ln -srf "$repo_path/$cfg_name" $cfg_path

cfg_incl_path=~/printer_data/config/printer.cfg

# Including hardlinked config to the printer.cfg
if [ -f "$cfg_incl_path" ]; then
    if ! grep -q "^\[include $cfg_name\]$" "$cfg_incl_path"; then
        sudo service klipper stop
        sed -i "1i\[include $cfg_name]" "$cfg_incl_path"
        echo "Including $cfg_name to $cfg_incl_path successfully complete"
        sudo service klipper start
    else
        echo "Including $cfg_name aborted, $cfg_name already exists in $cfg_incl_path"
    fi
fi

# Restarting klipper
sudo service klipper stop
sudo service klipper start

blk_path=~/printer_data/config/moonraker.conf
# Moonraker update confing
if [ -f "$blk_path" ]; then
    if ! grep -q "^\[update_manager $repo\]$" "$blk_path"; then
        sudo service moonraker stop
        sed -i "\$a \ " "$blk_path"
        sed -i "\$a [update_manager $repo]" "$blk_path"
        sed -i "\$a type: git_repo" "$blk_path"
        sed -i "\$a path: $repo_path" "$blk_path"
        sed -i "\$a origin: https://github.com/anton-vinogradov/$repo.git" "$blk_path"
        sed -i "\$a primary_branch: main" "$blk_path"
        sed -i "\$a managed_services: klipper" "$blk_path"
        echo "Including [update_manager] to $blk_path successfully complete"
        sudo service moonraker start
    fi
fi

sudo apt update
sudo apt-get install libatlas-base-dev libopenblas-dev

python -m venv --system-site-packages $repo_path/.venv
source $repo_path/.venv/bin/activate

pip install -r $repo_path/requirements.txt
