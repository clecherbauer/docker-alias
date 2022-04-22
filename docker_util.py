import os.path
import pty
import select
import sys
import termios
import tty
from typing import List

import docker
from checksumdir import dirhash

from config import INIConfig, DEFAULT_WORKING_DIR
from container import Container, Command
from volume import VolumeWithDriver, SimpleVolume
from subprocess import Popen


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
        if not self.quiet and not container.quiet:
            print('Pulling Image ' + container.image)
        image_name = container.image
        parts = image_name.split(':')
        if len(parts) > 1:
            return self.client.images.pull(parts[0], parts[1])
        return self.client.images.pull(image_name)

    def build_image(self, container: Container):
        image_name = self.get_image_name(container)
        if not self.quiet and not container.quiet:
            print('Building Image ' + image_name)
        context = self.get_image_context(container)
        self.client.images.build(
            tag=image_name,
            path=context,
            dockerfile=os.path.join(context, container.build.dockerfile),
            rm=True
        )
        config = INIConfig().get_config()
        if not config.has_section('ImageBuildHashes'):
            config.add_section('ImageBuildHashes')
        config.set('ImageBuildHashes', image_name.replace(':', '_'), self.hash_docker_build_dir(container))
        INIConfig().save_config(config)

    def get_image_name(self, container: Container) -> str:
        return self.image_name_pattern.format(
            fs_location_hash=container.fs_location_hash,
            container_name=container.name,
        )

    @staticmethod
    def get_image_context(container: Container) -> str:
        context = container.build.context
        if container.build.context.startswith('.'):
            return context[:0] + container.fs_location + context[0 + 1:]
        return context

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

    def exec_docker_subprocess(self, container: Container, command: Command = None, attributes: List = None) -> int:
        old_tty = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())

        # open pseudo-terminal to interact with subprocess
        master_fd, slave_fd = pty.openpty()
        try:
            # use os.setsid() make it run in a new process group, or bash job control will not be enabled
            p = Popen(
                self.build_command(container, command, attributes),
                preexec_fn=os.setsid,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                universal_newlines=True
            )

            while p.poll() is None:
                r, w, e = select.select([sys.stdin, master_fd], [], [], 0.5)
                if sys.stdin in r:
                    d = os.read(sys.stdin.fileno(), 10240)
                    os.write(master_fd, d)
                elif master_fd in r:
                    o = os.read(master_fd, 10240)
                    if o:
                        os.write(sys.stdout.fileno(), o)
        finally:
            # restore tty settings back
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        return p.poll()

    def build_command(self, container: Container, command: Command = None, attributes: List = None) -> List[str]:
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
            '-it',
            '--pid=host',
            '--rm',
            '--name=' + self.get_container_name(container),
        ]
        cmd_base = cmd_base + self.build_docker_run_arguments(container)
        return cmd_base + [
            container.image,
            internal_command
        ] + attributes

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

        if not container.stay_in_root:
            arguments.append('-w')
            arguments.append(self.calculate_path_segment(container))
        elif container.working_dir:
            arguments.append('-w')
            arguments.append(container.working_dir)
        else:
            arguments.append('-w')
            arguments.append(DEFAULT_WORKING_DIR)

        return arguments

    @staticmethod
    def calculate_path_segment(container: Container) -> str:
        current_dir = os.getcwd()
        root_dir = container.fs_location
        path_segment = current_dir.replace(root_dir, '').strip('/')
        if container.working_dir:
            print(container.working_dir)
            print(path_segment)
            return os.path.join(container.working_dir, path_segment)
        return os.path.join(DEFAULT_WORKING_DIR, path_segment)
