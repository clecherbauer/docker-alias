import os.path
import pty
import select
import subprocess
import sys
import termios
import tty
from typing import List

import docker
from checksumdir import dirhash

from lib.config import INIConfig, DEFAULT_WORKING_DIR, DOCKER_ALIAS_HOME
from lib.config_container import ConfigContainer, Command
from lib.volume import VolumeWithDriver, SimpleVolume
from subprocess import Popen


class DockerUtil:

    def __init__(self, quiet: bool):
        self.quiet = quiet

    client = docker.from_env()
    volume_name_pattern = 'docker_alias_{fs_location_hash}_{volume_name}'
    container_name_pattern = 'docker_alias_{fs_location_hash}_{container_name}'
    image_name_pattern = 'docker_alias_{fs_location_hash}_{container_name}:latest'
    quiet = False
    container_name = None

    def exec_docker(self, config_container: ConfigContainer, command: Command = None, attributes: List = None) -> int:
        if attributes is None:
            attributes = []
        config_container.image = self.handle_image(config_container)
        self.remove_container(config_container)
        self.create_volumes(config_container)
        response_code = self.exec_docker_subprocess(config_container, command, attributes)
        if not config_container.keep_volumes:
            self.remove_volumes(config_container)
        self.remove_container(config_container)
        return response_code

    def handle_image(self, config_container: ConfigContainer) -> str:
        if config_container.build:
            image_name = self.get_image_name(config_container)
            if not self.image_exists(config_container) or self.image_needs_rebuild(config_container):
                self.build_image(config_container)
        else:
            image_name = config_container.image
            if not self.external_image_exists(config_container):
                self.pull_image(config_container)
        return image_name

    def image_needs_rebuild(self, config_container: ConfigContainer) -> bool:
        if not config_container.build.context.startswith('.'):
            return False

        if not config_container.auto_rebuild_images:
            return False

        image_name = self.get_image_name(config_container)

        config = INIConfig().get_config()
        existing_hash = None
        if config.has_section('ImageBuildHashes'):
            existing_hash = config.get('ImageBuildHashes', image_name.replace(':', '_'))
        if not existing_hash:
            return True

        if existing_hash != self.hash_docker_build_dir(config_container):
            return True
        return False

    def image_exists(self, config_container: ConfigContainer) -> bool:
        image_name = self.get_image_name(config_container)
        for image in self.client.images.list(all=True):
            if image_name in image.tags:
                return True
        return False

    def external_image_exists(self, config_container: ConfigContainer) -> bool:
        image_name = config_container.image
        for image in self.client.images.list(all=True):
            if image_name in image.tags:
                return True
        return False

    def pull_image(self, config_container: ConfigContainer):
        if not self.quiet and not config_container.quiet:
            print('Pulling Image ' + config_container.image)
        image_name = config_container.image
        parts = image_name.rsplit(":", 1)
        if len(parts) > 1:
            output_streamer = self.client.api.pull(parts[0], parts[1])
            self.loop_stream(output_streamer, not self.quiet)
            return
        output_streamer = self.client.api.pull(image_name)
        self.loop_stream(output_streamer, not self.quiet)

    def build_image(self, config_container: ConfigContainer):
        image_name = self.get_image_name(config_container)
        if not self.quiet and not config_container.quiet:
            print('Building Image ' + image_name)
        context = self.get_image_context(config_container)
        low_level_api = self.client.api

        try:
            output_streamer = low_level_api.build(
                decode=True,
                tag=image_name,
                path=context,
                dockerfile=os.path.join(context, config_container.build.dockerfile),
                rm=True,
                nocache=True
            )
            self.loop_stream(output_streamer, not self.quiet)

            config = INIConfig().get_config()
            if not config.has_section('ImageBuildHashes'):
                config.add_section('ImageBuildHashes')
            config.set('ImageBuildHashes', image_name.replace(':', '_'), self.hash_docker_build_dir(config_container))
            INIConfig().save_config(config)
        except Exception as e:
            print(e)

    def get_image_name(self, config_container: ConfigContainer) -> str:
        return self.image_name_pattern.format(
            fs_location_hash=config_container.fs_location_hash,
            container_name=config_container.name,
        )

    @staticmethod
    def get_image_context(config_container: ConfigContainer) -> str:
        context = config_container.build.context
        if config_container.build.context == '.':
            return config_container.fs_location
        if config_container.build.context.startswith('./'):
            return config_container.fs_location + context[2:]
        if config_container.build.context.startswith('/'):
            return config_container.build.context

        return os.path.join(config_container.fs_location, context)

    def hash_docker_build_dir(self, config_container: ConfigContainer):
        context = self.get_image_context(config_container)
        path = os.path.dirname(os.path.join(context, config_container.build.dockerfile))
        return dirhash(path, 'md5')

    def remove_container(self, config_container: ConfigContainer):
        container_name = self.get_container_name(config_container)
        for current_container in self.client.containers.list(all=True):
            if container_name == current_container.name:
                current_container.remove()

    def get_container_name(self, config_container: ConfigContainer):
        if self.container_name is None:
            container_name = self.container_name_pattern.format(
            fs_location_hash=config_container.fs_location_hash,
            container_name=config_container.name,
            )
            count = 0
            for current_container in self.client.containers.list(all=True):
                if container_name in current_container.name:
                    count = count + 1
            self.container_name = container_name + '_' + str(count)
        return self.container_name

    def create_volumes(self, container):
        if container.volumes:
            for volume in container.volumes:
                if isinstance(volume, VolumeWithDriver):
                    volume_name = self.volume_name_pattern.format(
                        fs_location_hash=container.fs_location_hash,
                        volume_name=volume.name
                    )
                    if not self.volume_exists(volume_name):
                        self.create_volume(volume_name, volume)

    def remove_volumes(self, container):
        if container.volumes:
            for volume in container.volumes:
                if isinstance(volume, VolumeWithDriver):
                    volume_name = self.volume_name_pattern.format(
                        fs_location_hash=container.fs_location_hash,
                        container_name=self.get_container_name(container),
                        volume_name=volume.name
                    )
                    self.remove_volume(volume_name)

    def volume_exists(self, volume_name) -> bool:
        for volume in self.client.volumes.list():
            if volume.name == volume_name:
                return True
        return False

    def create_volume(self, volume_name: str, volume: VolumeWithDriver):
        self.client.volumes.create(
            volume_name,
            driver=volume.driver,
            driver_opts=volume.driver_opts
        )

    def remove_volume(self, volume_name: str):
        for volume in self.client.volumes.list():
            if volume.name == volume_name:
                volume.remove(True)

    def exec_docker_subprocess(self, container, command: Command = None, attributes: List = None) -> int:
        try:
            old_tty = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            return self.exec_docker_subprocess_tty(old_tty, container, command, attributes)
        except termios.error:
            return self.exec_docker_subprocess_stdout_pipe(container, command, attributes)

    def exec_docker_subprocess_tty(self, old_tty, container, command: Command = None, attributes: List = None):
        try:
            # open pseudo-terminal to interact with subprocess
            master_fd, slave_fd = pty.openpty()
            # use os.setsid() make it run in a new process group, or bash job control will not be enabled
            p = Popen(
                self.build_command(container, command, attributes, _tty=True),
                preexec_fn=os.setsid,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                universal_newlines=True
            )

            while p.poll() is None:
                r, w, e = select.select([sys.stdin, master_fd], [], [], 0.2)
                if sys.stdin in r:
                    d = os.read(sys.stdin.fileno(), 10240)
                    os.write(master_fd, d)
                elif master_fd in r:
                    o = os.read(master_fd, 10240)
                    if o:
                        os.write(sys.stdout.fileno(), o)
        finally:
            # restore tty settings back
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, old_tty)
        return p.poll()

    def exec_docker_subprocess_stdout_pipe(self, container, command: Command = None, attributes: List = None):
        process = subprocess.Popen(
            self.build_command(container, command, attributes, _tty=False),
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            universal_newlines=True
        )
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        return process.poll()

    def build_command(
            self,
            config_container: ConfigContainer,
            command: Command = None,
            attributes: List = None,
            _tty: bool = True
    ) -> List[str]:
        if attributes is None:
            attributes = []

        internal_command = config_container.name
        if command:
            internal_command = command.name
            if command.path:
                internal_command = command.path

        cmd_base = [
            'docker',
            'run',
            '--pid=host',
            '--rm',
            '--name=' + self.get_container_name(config_container),
        ]
        if _tty:
            cmd_base = cmd_base + ['-it']
        cmd_base = cmd_base + self.build_docker_run_arguments(config_container)
        cmd_base.append(config_container.image)
        if config_container.inject_user_switcher:
            cmd_base = cmd_base + ['/switch_user']
        cmd_base.append(internal_command)
        return cmd_base + command.default_params + attributes

    def build_docker_run_arguments(self, config_container: ConfigContainer) -> List[str]:
        arguments = []
        for volume in config_container.volumes:
            volume_mount_pattern = '{source}:{target}'
            if isinstance(volume, VolumeWithDriver):
                arguments.append('-v')
                arguments.append(
                    volume_mount_pattern.format(
                        source=self.volume_name_pattern.format(
                            fs_location_hash=config_container.fs_location_hash,
                            volume_name=volume.name
                        ),
                        target=volume.target
                    )
                )
            if isinstance(volume, SimpleVolume):
                arguments.append('-v')
                arguments.append(
                    volume_mount_pattern.format(
                        source=volume.source,
                        target=volume.target
                    )
                )

        user_switcher_binary = os.path.join(DOCKER_ALIAS_HOME, 'switch_user')
        if config_container.inject_user_switcher and os.path.isfile(user_switcher_binary):
            arguments.append('-v')
            arguments.append('{user_switcher_binary}:/switch_user'.format(user_switcher_binary=user_switcher_binary))

        if config_container.entrypoint:
            arguments.append('--entrypoint')
            arguments.append(config_container.entrypoint)

        if config_container.env_file:
            arguments.append('--env-file')
            arguments.append(os.path.join(config_container.fs_location, config_container.env_file))

        if config_container.environment:
            for environment in config_container.environment:
                arguments.append('-e')
                arguments.append(environment)

        arguments.append('-e')
        arguments.append("UID_HOST=" + str(os.getuid()))

        for network in self.client.networks.list():
            if network.name == config_container.docker_compose_project_name + "_default":
                arguments.append('--network')
                arguments.append(network.name)

        for network in config_container.networks:
            if not network == 'default':
                arguments.append('--network')
                arguments.append(network)

        for port in config_container.ports:
            arguments.append('-p')
            arguments.append(port)

        if not config_container.stay_in_root:
            arguments.append('-w')
            arguments.append(self.calculate_path_segment(config_container))
        elif config_container.working_dir:
            arguments.append('-w')
            arguments.append(config_container.working_dir)
        else:
            arguments.append('-w')
            arguments.append(DEFAULT_WORKING_DIR)

        if config_container.user:
            arguments.append('--user')
            arguments.append(config_container.user)

        if config_container.privileged:
            arguments.append('--privileged')

        return arguments

    @staticmethod
    def calculate_path_segment(config_container: ConfigContainer) -> str:
        current_dir = os.getcwd()
        root_dir = config_container.fs_location
        path_segment = current_dir.replace(root_dir, '').strip('/')

        if config_container.working_dir:
            return os.path.join(config_container.working_dir, path_segment)
        return os.path.join(DEFAULT_WORKING_DIR, path_segment)

    @staticmethod
    def loop_stream(streamer, verbose: bool):
        for chunk in streamer:
            if verbose and 'stream' in chunk:
                for line in chunk['stream'].splitlines():
                    print(line.strip('\n'))
