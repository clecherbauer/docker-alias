import os
from typing import Iterable, List, Optional, Set

from lib.config import SHIM_BINARY_DIR, INIConfig, YAMLConfigUtil


class ShimBinaryManager:
    def __init__(self, root_path: str = SHIM_BINARY_DIR) -> None:
        self._root_path = root_path

    def get_root_path(self) -> str:
        return self._root_path

    def ensure_root_exists(self) -> None:
        os.makedirs(self._root_path, exist_ok=True)

    def list_binaries(self) -> List[str]:
        if not os.path.isdir(self._root_path):
            return []
        return sorted(os.listdir(self._root_path))

    def _normalize_name(self, name: str) -> str:
        return name.replace('/', '')

    def create(self, name: str) -> None:
        normalized_name = self._normalize_name(name)
        if not normalized_name:
            return
        self.ensure_root_exists()
        file_path = os.path.join(self._root_path, normalized_name)
        if os.path.isfile(file_path):
            return
        with open(file_path, 'w') as file:
            file.write('#!/usr/bin/env bash\n')
            file.write('docker-alias run $0 $@\n')
        os.chmod(file_path, 0o775)

    def remove(self, name: str) -> None:
        normalized_name = self._normalize_name(name)
        if not normalized_name:
            return
        file_path = os.path.join(self._root_path, normalized_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

    def remove_all(self) -> None:
        for shim_binary in self.list_binaries():
            self.remove(shim_binary)

    def sync(self, defined_shim_binaries: Iterable[str]) -> None:
        normalized_defined: Set[str] = {
            self._normalize_name(name)
            for name in defined_shim_binaries
            if self._normalize_name(name)
        }
        existing = set(self.list_binaries())
        for shim_binary in existing - normalized_defined:
            self.remove(shim_binary)
        for shim_binary in normalized_defined:
            self.create(shim_binary)


def collect_defined_shim_binaries(ini_config: Optional[INIConfig] = None) -> List[str]:
    ini_config = ini_config or INIConfig()
    yaml_paths = ini_config.get_yaml_paths()
    yaml_config_util = YAMLConfigUtil()
    defined_shim_binaries: List[str] = []
    for yml_path in yaml_paths:
        if not os.path.isfile(yml_path):
            continue
        yaml_config = yaml_config_util.get_config(yml_path)
        if not yaml_config:
            print('Invalid Config: ' + yml_path)
            continue
        containers = yaml_config.config.get('containers') if yaml_config.config else None
        if not containers:
            continue
        for container_key, container in containers.items():
            commands = container.get('commands') if isinstance(container, dict) else None
            if commands:
                for command in commands:
                    if isinstance(command, dict):
                        defined_shim_binaries.append(list(command.keys())[0])
                    else:
                        defined_shim_binaries.append(command)
            else:
                defined_shim_binaries.append(container_key)
    return defined_shim_binaries
