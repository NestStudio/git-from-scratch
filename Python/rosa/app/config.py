"""Git configuration management"""

import configparser
import os
from pathlib import Path
from typing import Optional


def gitconfig_read() -> configparser.ConfigParser:
    """Read Git configuration files"""
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))

    configfiles = [
        Path(xdg_config_home) / "git" / "config",
        Path.home() / ".gitconfig"
    ]

    config = configparser.ConfigParser()

    existing_files = [str(f) for f in configfiles if f.exists()]
    if existing_files:
        config.read(existing_files)

    return config


def gitconfig_user_get(config: configparser.ConfigParser) -> Optional[str]:
    """Get user information from config"""
    try:
        if "user" in config:
            if "name" in config["user"] and "email" in config["user"]:
                return f"{config['user']['name']} <{config['user']['email']}>"
    except (configparser.NoSectionError, configparser.NoOptionError, KeyError):
        pass

    return None
