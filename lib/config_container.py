import hashlib
import os
from copy import copy
from dataclasses import dataclass
from typing import List

from lib.config import YAMLConfig, YAMLConfigUtil, DEFAULT_WORKING_DIR
from lib.volume import Volume, VolumeWithDriver, SimpleVolume


@dataclass
class Build:
    context: str
    dockerfile: str


@dataclass
class Command:
    name: str
    path: str
    default_params: List[str]


@dataclass
class AbstractConfigContainer:
    entrypoint: str
    env_file: str
    environment: List[str]
    post_exec_hook_command: str
    pre_exec_hook_command: str
    quiet: bool
    stay_in_root: bool
    volumes: List[Volume]
    working_dir: str
    user: str
    inject_user_switcher: bool
    networks: List[str]
    ports: List[str]


@dataclass
class ConditionalConfigContainer:
    command_pattern: str
    overwrite: dict


@dataclass
class ConfigContainer(AbstractConfigContainer):
    auto_rebuild_images: bool
    image: str
    privileged: bool
    build: Build
    commands: List[Command]
    docker_compose_project_name: str
    keep_volumes: bool
    name: str
    fs_location: str
    fs_location_hash: str
    conditional_config_containers: List[ConditionalConfigContainer]


class ConfigContainerUtil:
    def resolve_config_containers(self) -> List[ConfigContainer]:
        yaml_configs = YAMLConfigUtil().find_yaml_configs()
        containers = self.build_config_containers_from_yaml_configs(yaml_configs)
        return containers

    def build_config_containers_from_yaml_configs(self, yaml_configs: List[YAMLConfig]) -> List[ConfigContainer]:
        containers = []
        for yaml_config in yaml_configs:
            containers = containers + self.build_config_containers_from_yaml_config(yaml_config)
        return containers

    def build_config_containers_from_yaml_config(self, yaml_config: YAMLConfig) -> List[ConfigContainer]:
        config_containers = []
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

        configs = yaml_config.config.get('containers', {})
        for container_name, config in configs.items():
            build = None
            if config.get('build', {}):
                build = Build(
                    context=config.get('build').get('context'),
                    dockerfile=config.get('build').get('dockerfile')
                )

            fs_location = os.path.dirname(os.path.realpath(yaml_config.path))
            fs_location_hash = int(hashlib.sha1(fs_location.encode('utf-8')).hexdigest(), 16) % (10 ** 8)

            docker_compose_project_name = os.path.basename(fs_location)

            config_container = ConfigContainer(
                auto_rebuild_images=bool(config.get('auto_rebuild_images', True)),
                privileged=bool(config.get('privileged', True)),
                build=build,
                commands=self.build_commands(config),
                docker_compose_project_name=docker_compose_project_name,
                entrypoint=config.get('entrypoint'),
                env_file=config.get('env_file'),
                image=config.get('image'),
                keep_volumes=bool(yaml_config.config.get('keep_volumes', False)),
                name=container_name,
                post_exec_hook_command=config.get('post_exec_hook_command'),
                pre_exec_hook_command=config.get('pre_exec_hook_command'),
                quiet=bool(config.get('quiet', False)),
                stay_in_root=bool(config.get('stay_in_root', False)),
                working_dir=config.get('working_dir', DEFAULT_WORKING_DIR),
                volumes=self.build_volumes(config, global_volumes),
                environment=config.get('environment', []),
                fs_location=fs_location,
                fs_location_hash=fs_location_hash,
                user=config.get('user', None),
                inject_user_switcher=bool(config.get('inject_user_switcher', False)),
                networks=config.get('networks', []),
                ports=config.get('ports', []),
                conditional_config_containers=self.build_conditional_config_container(
                    global_volumes,
                    config
                )
            )
            config_containers.append(config_container)
        return config_containers

    @staticmethod
    def build_commands(config) -> List[Command]:
        commands = []
        if config.get('commands'):
            for configured_command in config.get('commands'):
                command = None
                if isinstance(configured_command, str):
                    command = Command(
                        name=configured_command,
                        path=None,
                        default_params=[]
                    )

                if isinstance(configured_command, dict):
                    command = Command(
                        name=list(configured_command.keys())[0],
                        path=list(configured_command.values())[0].get('path'),
                        default_params=list(configured_command.values())[0].get('default_params', [])
                    )
                if command:
                    commands.append(command)
        return commands

    @staticmethod
    def build_volumes(config, global_volumes: dict) -> List[Volume]:
        volumes = []
        if config.get('volumes'):
            for configured_volume in config.get('volumes'):
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

    def build_conditional_config_container(self, global_volumes, config)\
            -> List[ConditionalConfigContainer]:
        conditional_config_containers = []
        if config.get('command_pattern_conditional_config'):
            for conditional_config in config.get('command_pattern_conditional_config', []):
                pattern = list(conditional_config.keys())[0]
                conditional_config = conditional_config

                overwrite = {}
                if 'entrypoint' in conditional_config.keys():
                    overwrite['entrypoint'] = conditional_config.get('entrypoint')

                if 'env_file' in conditional_config.keys():
                    overwrite['env_file'] = conditional_config.get('env_file')

                if 'post_exec_hook_command' in conditional_config.keys():
                    overwrite['post_exec_hook_command'] = conditional_config.get('post_exec_hook_command')

                if 'pre_exec_hook_command' in conditional_config.keys():
                    overwrite['pre_exec_hook_command'] = conditional_config.get('pre_exec_hook_command')

                if 'quiet' in conditional_config.keys():
                    overwrite['quiet'] = bool(conditional_config.get('quiet', False))

                if 'working_dir' in conditional_config.keys():
                    overwrite['working_dir'] = conditional_config.get('working_dir', DEFAULT_WORKING_DIR)

                if 'volumes' in conditional_config.keys():
                    overwrite['volumes'] = self.build_volumes(conditional_config, global_volumes)

                if 'environment' in conditional_config.keys():
                    overwrite['environment'] = conditional_config.get('environment', [])

                if 'user' in conditional_config.keys():
                    overwrite['user'] = conditional_config.get('user', None)

                if 'inject_user_switcher' in conditional_config.keys():
                    overwrite['inject_user_switcher'] = bool(conditional_config.get('inject_user_switcher', False))

                if 'networks' in conditional_config.keys():
                    overwrite['networks'] = conditional_config.get('networks', [])

                if 'ports' in conditional_config.keys():
                    overwrite['ports'] = conditional_config.get('ports', [])

                if 'stay_in_root' in conditional_config.keys():
                    overwrite['stay_in_root'] = bool(conditional_config.get('stay_in_root', False))

                conditional_config_container = ConditionalConfigContainer(
                    command_pattern=pattern,
                    overwrite=overwrite
                )
                conditional_config_containers.append(conditional_config_container)
        return conditional_config_containers

    def merge_config_containers(self, config_container: ConfigContainer, command: str):
        for conditional_config_container in config_container.conditional_config_containers:
            if command.startswith(conditional_config_container.command_pattern):
                return self._merge_config_containers(config_container, conditional_config_container)
        return config_container

    @staticmethod
    def _merge_config_containers(
            config_container: ConfigContainer,
            conditional_config_container: ConditionalConfigContainer
    ) -> ConfigContainer:
        for attribute_name, attribute_value in conditional_config_container.overwrite.items():
            if attribute_value:
                config_container.__setattr__(attribute_name, attribute_value)
        return config_container
