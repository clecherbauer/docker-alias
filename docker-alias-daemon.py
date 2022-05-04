import os.path
import sys
import time
import traceback

import click
import daemoniker
from psutil import pid_exists

from config import INIConfig, YAMLConfigUtil, FAKE_BINARY_DIR

DEFAULT_PID_FILE = os.path.join(INIConfig().get_config_dir(), "docker-alias.pid")


def get_pid_file() -> str:
    return os.environ.get("DOCKER_ALIAS_PID_FILE", DEFAULT_PID_FILE)


class Daemon:
    boot = True

    @staticmethod
    def get_fake_binary_root_path() -> str:
        return os.path.join(FAKE_BINARY_DIR)

    def create_fake_binary_root(self) -> None:
        docker_alias_binary_dir = self.get_fake_binary_root_path()
        if not os.path.isdir(docker_alias_binary_dir):
            os.mkdir(docker_alias_binary_dir)

    def create_fake_binary(self, name) -> None:
        name = name.replace('/', '')
        file_path = os.path.join(self.get_fake_binary_root_path(), name)
        if not os.path.isfile(file_path):
            with open(file_path, 'w') as file:
                file.write('#!/usr/bin/env bash\n')
                file.write('docker-alias run $0 $@\n')
                file.close()
            os.chmod(file_path, 0o775)

    def remove_fake_binary(self, name) -> None:
        file_path = os.path.join(self.get_fake_binary_root_path(), name)
        if os.path.isfile(file_path):
            os.remove(file_path)

    def get_defined_fake_binaries(self) -> []:
        ini_config = INIConfig()
        yaml_paths = ini_config.get_yaml_paths()
        defined_fake_binaries = []
        for yml_path in yaml_paths:
            if os.path.isfile(yml_path):
                yaml_config = YAMLConfigUtil().get_config(yml_path)
                if not yaml_config:
                    print('Invalid Config: ' + yaml_config.path)
                    continue
                containers = yaml_config.config.get('containers')
                if containers:
                    self.create_fake_binary_root()
                    for container_key, container in containers.items():
                        commands = container.get('commands')
                        if commands:
                            for command in commands:
                                if isinstance(command, dict):
                                    defined_fake_binaries.append(list(command.keys())[0])
                                else:
                                    defined_fake_binaries.append(command)
                        else:
                            defined_fake_binaries.append(container_key)
        return defined_fake_binaries

    def run(self) -> None:
        while True:
            try:
                defined_fake_binaries = self.get_defined_fake_binaries()
                fake_binaries = os.listdir(self.get_fake_binary_root_path())
                for fake_binary in fake_binaries:
                    if self.boot or fake_binary not in defined_fake_binaries:
                        self.remove_fake_binary(fake_binary)

                for defined_fake_binary in defined_fake_binaries:
                    self.create_fake_binary(defined_fake_binary)
                self.boot = False
                time.sleep(10)
            except Exception:
                traceback.print_exc()


@click.group()
def cli() -> None:
    pass


@cli.command("start")
@click.option("--no-daemon", is_flag=True, flag_value=True, default=False)
def start(no_daemon: bool) -> None:
    if no_daemon:
        try:
            Daemon().run()
        except KeyboardInterrupt:
            pass
    else:
        with daemoniker.Daemonizer() as (_, daemonizer):
            try:
                is_parent, *_ = daemonizer(get_pid_file())
                Daemon().run()
            except SystemExit as e:
                if str(e) == 'Unable to acquire PID file.':
                    with open(get_pid_file()) as f:
                        pid = int(f.read())
                    if pid_exists(pid):
                        sys.exit(0)
                    os.remove(get_pid_file())


@cli.command("stop")
def stop() -> None:
    if not os.path.isfile(get_pid_file()):
        print("Warning: docker-alias was not running!")
    else:
        daemoniker.send(get_pid_file(), daemoniker.SIGINT)


if __name__ == '__main__':
    cli()
