import configparser
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml

VERSION = 'v2.4.5'
YAML_CONFIG_FILE_NAME = 'docker-alias.yml'
INI_CONFIG_FILE_NAME = 'config.ini'
DOCKER_ALIAS_HOME = os.path.join(str(Path.home()), '.local', 'docker-alias')
FAKE_BINARY_DIR = os.path.join(DOCKER_ALIAS_HOME, 'bin')
INI_CONFIG_DIR = os.path.join(str(Path.home()), '.config', 'docker-alias')
INI_CONFIG_FILE_PATH = os.path.join(INI_CONFIG_DIR, INI_CONFIG_FILE_NAME)
DEFAULT_WORKING_DIR = '/app'


class INIConfig:
    yml_section_name = 'YamlPaths'

    @staticmethod
    def get_config_dir():
        if not os.path.isdir(INI_CONFIG_DIR):
            os.mkdir(INI_CONFIG_DIR)
        return INI_CONFIG_DIR

    def get_config_file_path(self):
        return os.path.join(self.get_config_dir(), INI_CONFIG_FILE_NAME)

    def get_config(self):
        config_dir = self.get_config_dir()
        config = configparser.ConfigParser()
        config_path = self.get_config_file_path()
        if not os.path.isfile(config_path):
            Path(config_path).touch()
        config.read(os.path.join(config_dir, INI_CONFIG_FILE_NAME))
        return config

    def get_yaml_paths(self) -> List[str]:
        config = self.get_config()

        path_list = []
        if config.has_section(self.yml_section_name):
            path_list_json = config.get(self.yml_section_name, 'list')
            if path_list_json:
                path_list = json.loads(path_list_json)
        return path_list

    def add_yaml_path(self, path: str):
        path_list = self.get_yaml_paths()
        path_list.append(path)
        self.save_path_list(path_list)

    def remove_yaml_path(self, path: str):
        path_list = self.get_yaml_paths()
        new_path_list = []
        for _path in path_list:
            if not _path == path:
                new_path_list.append(path)
        self.save_path_list(new_path_list)

    def save_path_list(self, path_list: List[str]):
        config = self.get_config()
        if not config.has_section(self.yml_section_name):
            config.add_section(self.yml_section_name)

        path_list = list(set(path_list))  # deduplicate list
        config.set(self.yml_section_name, 'list', json.dumps(path_list))
        self.save_config(config)

    def save_config(self, config):
        with open(self.get_config_file_path(), 'w') as file:
            config.write(file)
            file.close()


@dataclass
class YAMLConfig:
    path: str
    config: dict


class YAMLConfigUtil:
    def get_config(self, yaml_path) -> YAMLConfig:
        with open(yaml_path, 'r') as stream:
            yaml_string = self.replace_variables(yaml_path, stream.read())
            try:
                return YAMLConfig(
                    path=yaml_path,
                    config=yaml.safe_load(yaml_string)
                )
            except yaml.YAMLError:
                return None

    @staticmethod
    def replace_variables(yaml_path: str, yaml_string: str) -> str:
        for environment_variable in os.environ:
            yaml_string = yaml_string.replace('$' + environment_variable, os.getenv(environment_variable))

        yaml_string = yaml_string.replace('$YAML_LOCATION_DIR', os.path.dirname(os.path.realpath(yaml_path)))
        yaml_string = yaml_string.replace('$UID', str(os.getuid()))
        yaml_string = yaml_string.replace('$DEFAULT_WORKING_DIR', DEFAULT_WORKING_DIR)
        return yaml_string

    def find_yaml_configs(self) -> List[YAMLConfig]:
        config_list = self.find_yaml_configs_recursive(Path(os.getcwd()))
        config_list = sorted(config_list, key=lambda x: len(x.path), reverse=True)
        return config_list

    def find_yaml_configs_recursive(self, path: Path) -> List[YAMLConfig]:
        if path.parent.absolute() == path:
            return []

        yaml_configs = []
        yaml_path = os.path.join(path, YAML_CONFIG_FILE_NAME)
        if os.path.isfile(yaml_path):
            yaml_configs.append(self.get_config(yaml_path))

        if path.parent.absolute():
            yaml_configs = yaml_configs + self.find_yaml_configs_recursive(path.parent.absolute())

        return yaml_configs
