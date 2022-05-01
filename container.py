import hashlib
import os
from copy import copy
from dataclasses import dataclass
from typing import List

from config import YAMLConfig, YAMLConfigUtil, DEFAULT_WORKING_DIR
from volume import Volume, VolumeWithDriver, SimpleVolume


@dataclass
class Build:
    context: str
    dockerfile: str


@dataclass
class Command:
    name: str
    path: str


@dataclass
class Container:
    auto_rebuild_images: bool
    build: Build
    commands: List[Command]
    entrypoint: str
    env_file: str
    environment: List[str]
    image: str
    keep_volumes: bool
    name: str
    fs_location: str
    fs_location_hash: str
    post_exec_hook_command: str
    pre_exec_hook_command: str
    quiet: bool
    stay_in_root: bool
    volumes: List[Volume]
    working_dir: str
    user: str


class ContainerUtil:
    def resolve_containers(self) -> List[Container]:
        yaml_configs = YAMLConfigUtil().find_yaml_configs()
        containers = self.build_containers_from_yaml_configs(yaml_configs)
        return containers

    def build_containers_from_yaml_configs(self, yaml_configs: List[YAMLConfig]) -> List[Container]:
        containers = []
        for yaml_config in yaml_configs:
            containers = containers + self.build_containers_from_yaml_config(yaml_config)
        return containers

    def build_containers_from_yaml_config(self, yaml_config: YAMLConfig) -> List[Container]:
        containers = []
        global_volumes = {}
        for volume_key, global_volume in yaml_config.config.get('volumes', {}).items():
            if global_volume.get('driver'):
                global_volume = VolumeWithDriver(
                    name=volume_key,
                    driver=global_volume.get('driver'),
                    driver_opts=global_volume.get('driver_opts'),
                    target=None
                )
                global_volumes[volume_key] = global_volume

        configured_containers = yaml_config.config.get('containers', {})
        for container_name, configured_container in configured_containers.items():
            build = None
            if configured_container.get('build', {}):
                build = Build(
                    context=configured_container.get('build').get('context'),
                    dockerfile=configured_container.get('build').get('dockerfile')
                )

            fs_location = os.path.dirname(os.path.realpath(yaml_config.path))
            fs_location_hash = int(hashlib.sha1(fs_location.encode('utf-8')).hexdigest(), 16) % (10 ** 8)

            container = Container(
                auto_rebuild_images=bool(configured_container.get('auto_rebuild_images', True)),
                build=build,
                commands=self.build_commands(configured_container),
                entrypoint=configured_container.get('entrypoint'),
                env_file=configured_container.get('env_file'),
                image=configured_container.get('image'),
                keep_volumes=bool(yaml_config.config.get('keep_volumes', False)),
                name=container_name,
                post_exec_hook_command=configured_container.get('post_exec_hook_command'),
                pre_exec_hook_command=configured_container.get('pre_exec_hook_command'),
                quiet=bool(configured_container.get('quiet', False)),
                stay_in_root=bool(configured_container.get('stay_in_root', False)),
                working_dir=configured_container.get('working_dir', DEFAULT_WORKING_DIR),
                volumes=self.build_volumes(configured_container, global_volumes),
                environment=configured_container.get('environment', []),
                fs_location=fs_location,
                fs_location_hash=fs_location_hash,
                user=configured_container.get('user', None),
            )
            containers.append(container)
        return containers

    @staticmethod
    def build_commands(configured_container) -> List[Command]:
        commands = []
        if configured_container.get('commands'):
            for configured_command in configured_container.get('commands'):
                command = None
                if isinstance(configured_command, str):
                    command = Command(
                        name=configured_command,
                        path=None
                    )

                if isinstance(configured_command, dict):
                    command = Command(
                        name=list(configured_command.keys())[0],
                        path=list(configured_command.values())[0].get('path')
                    )
                if command:
                    commands.append(command)
        return commands

    @staticmethod
    def build_volumes(configured_container, global_volumes: dict) -> List[Volume]:
        volumes = []
        if configured_container.get('volumes'):
            for configured_volume in configured_container.get('volumes'):
                volume = None
                volume_partials = configured_volume.split(':')
                if volume_partials[0] in global_volumes.keys():
                    for key, global_volume in global_volumes.items():
                        if key == volume_partials[0]:
                            volume = copy(global_volume)
                            volume.target = volume_partials[1]
                else:
                    volume = SimpleVolume(
                        source=volume_partials[0],
                        target=volume_partials[1]
                    )
                if volume:
                    volumes.append(volume)
        return volumes
