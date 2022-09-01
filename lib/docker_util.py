import os.path
import pty
import select
import subprocess
import sys
import termios
import tty
from typing import List

import animation
import docker
from checksumdir import dirhash

from lib.config import INIConfig, DEFAULT_WORKING_DIR, DOCKER_ALIAS_HOME
from lib.container import Container, Command
from lib.volume import VolumeWithDriver, SimpleVolume
from subprocess import Popen

clock = ['-', '\\', '|', '/']


class DockerUtil:

    def __init__(self, quiet: bool):
        self.quiet = quiet

    client = docker.from_env()
    volume_name_pattern = 'docker_alias_{fs_location_hash}_{volume_name}'
    container_name_pattern = 'docker_alias_{fs_location_hash}_{container_name}'
    image_name_pattern = 'docker_alias_{fs_location_hash}_{container_name}:latest'
    quiet = False

    def exec_docker(self, container: Container, command: Command = None, attributes: List = None) -> int:
        if attributes is None:
            attributes = []
        container.image = self.handle_image(container)
        self.remove_container(container)
        self.create_volumes(container)
        response_code = self.exec_docker_subprocess(container, command, attributes)
        if not container.keep_volumes:
            self.remove_volumes(container)
        self.remove_container(container)
        return response_code

    def handle_image(self, container: Container) -> str:
        if container.build:
            image_name = self.get_image_name(container)
            if not self.image_exists(container) or self.image_needs_rebuild(container):
                self.build_image(container)
        else:
            image_name = container.image
            if not self.external_image_exists(container):
                self.pull_image(container)
        return image_name

    def image_needs_rebuild(self, container: Container) -> bool:
        if not container.build.context.startswith('.'):
            return False

        if not container.auto_rebuild_images:
            return False

        image_name = self.get_image_name(container)

        config = INIConfig().get_config()
        existing_hash = None
        if config.has_section('ImageBuildHashes'):
            existing_hash = config.get('ImageBuildHashes', image_name.replace(':', '_'))
        if not existing_hash:
            return True

        if existing_hash != self.hash_docker_build_dir(container):
            return True
        return False

    def image_exists(self, container: Container) -> bool:
        image_name = self.get_image_name(container)
        for image in self.client.images.list(all=True):
            if image_name in image.tags:
                return True
        return False

    def external_image_exists(self, container: Container) -> bool:
        image_name = container.image
        for image in self.client.images.list(all=True):
            if image_name in image.tags:
                return True
        return False

    def pull_image(self, container: Container):
        wait_animation = animation.Wait(clock)
        if not self.quiet and not container.quiet:
            wait_animation.start()
            print('Pulling Image ' + container.image)
        image_name = container.image
        parts = image_name.split(':')
        if len(parts) > 1:
            self.client.images.pull(parts[0], parts[1])
            wait_animation.stop()
            return
        self.client.images.pull(image_name)
        wait_animation.stop()

    def build_image(self, container: Container):
        wait_animation = animation.Wait(clock)
        image_name = self.get_image_name(container)
        if not self.quiet and not container.quiet:
            wait_animation.start()
            print('Building Image ' + image_name)
        context = self.get_image_context(container)
        try:
            self.client.images.build(
                tag=image_name,
                path=context,
                dockerfile=os.path.join(context, container.build.dockerfile),
                rm=True
            )
        except Exception as e:
            wait_animation.stop()
            print(e)
        config = INIConfig().get_config()
        if not config.has_section('ImageBuildHashes'):
            config.add_section('ImageBuildHashes')
        config.set('ImageBuildHashes', image_name.replace(':', '_'), self.hash_docker_build_dir(container))
        INIConfig().save_config(config)
        wait_animation.stop()

    def get_image_name(self, container: Container) -> str:
        return self.image_name_pattern.format(
            fs_location_hash=container.fs_location_hash,
            container_name=container.name,
        )

    @staticmethod
    def get_image_context(container: Container) -> str:
        context = container.build.context
        if container.build.context == '.':
            return container.fs_location
        if container.build.context.startswith('./'):
            return container.fs_location + context[2:]
        if container.build.context.startswith('/'):
            return container.build.context

        return os.path.join(container.fs_location, context)

    def hash_docker_build_dir(self, container: Container):
        context = self.get_image_context(container)
        path = os.path.dirname(os.path.join(context, container.build.dockerfile))
        return dirhash(path, 'md5')

    def remove_container(self, container: Container):
        container_name = self.get_container_name(container)
        for container in self.client.containers.list(all=True):
            if container_name == container.name:
                container.remove()

    def get_container_name(self, container: Container):
        return self.container_name_pattern.format(
            fs_location_hash=container.fs_location_hash,
            container_name=container.name,
        )

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
                        container_name=container.name,
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
            container: Container,
            command: Command = None,
            attributes: List = None,
            _tty: bool = True
    ) -> List[str]:
        if attributes is None:
            attributes = []

        internal_command = container.name
        if command:
            internal_command = command.name
            if command.path:
                internal_command = command.path

        cmd_base = [
            'docker',
            'run',
            '--pid=host',
            '--rm',
            '--name=' + self.get_container_name(container),
        ]
        if _tty:
            cmd_base = cmd_base + ['-it']
        cmd_base = cmd_base + self.build_docker_run_arguments(container)
        cmd_base.append(container.image)
        if container.inject_user_switcher:
            cmd_base = cmd_base + ['/switch_user']
        cmd_base.append(internal_command)
        return cmd_base + command.default_params + attributes

    def build_docker_run_arguments(self, container: Container) -> List[str]:
        arguments = []
        for volume in container.volumes:
            volume_mount_pattern = '{source}:{target}'
            if isinstance(volume, VolumeWithDriver):
                arguments.append('-v')
                arguments.append(
                    volume_mount_pattern.format(
                        source=self.volume_name_pattern.format(
                            fs_location_hash=container.fs_location_hash,
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
        if container.inject_user_switcher and os.path.isfile(user_switcher_binary):
            arguments.append('-v')
            arguments.append('{user_switcher_binary}:/switch_user'.format(user_switcher_binary=user_switcher_binary))

        if container.entrypoint:
            arguments.append('--entrypoint')
            arguments.append(container.entrypoint)

        if container.env_file:
            arguments.append('--env-file')
            arguments.append(os.path.join(container.fs_location, container.env_file))

        if container.environment:
            for environment in container.environment:
                arguments.append('-e')
                arguments.append(environment)

        arguments.append('-e')
        arguments.append("UID_HOST=" + str(os.getuid()))

        for network in self.client.networks.list():
            if network.name == container.docker_compose_project_name + "_default":
                arguments.append('--network')
                arguments.append(network.name)

        for network in container.networks:
            if not network == 'default':
                arguments.append('--network')
                arguments.append(network)

        if not container.stay_in_root:
            arguments.append('-w')
            arguments.append(self.calculate_path_segment(container))
        elif container.working_dir:
            arguments.append('-w')
            arguments.append(container.working_dir)
        else:
            arguments.append('-w')
            arguments.append(DEFAULT_WORKING_DIR)

        if container.user:
            arguments.append('--user')
            arguments.append(container.user)

        return arguments

    @staticmethod
    def calculate_path_segment(container: Container) -> str:
        current_dir = os.getcwd()
        root_dir = container.fs_location
        path_segment = current_dir.replace(root_dir, '').strip('/')

        if container.working_dir:
            return os.path.join(container.working_dir, path_segment)
        return os.path.join(DEFAULT_WORKING_DIR, path_segment)
