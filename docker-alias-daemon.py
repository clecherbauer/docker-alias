import os.path
import sys
import time
import traceback

import click
import daemoniker
from psutil import pid_exists

from lib.config import INIConfig
from lib.fake_binary import FakeBinaryManager, collect_defined_fake_binaries

DEFAULT_PID_FILE = os.path.join(INIConfig().get_config_dir(), "docker-alias.pid")


def get_pid_file() -> str:
    return os.environ.get("DOCKER_ALIAS_PID_FILE", DEFAULT_PID_FILE)


class Daemon:
    def __init__(self) -> None:
        self._fake_binary_manager = FakeBinaryManager()

    def run(self) -> None:
        while True:
            try:
                ini_config = INIConfig()

                if not ini_config.is_enabled():
                    self._fake_binary_manager.remove_all()
                    time.sleep(10)
                    continue

                defined_fake_binaries = collect_defined_fake_binaries(ini_config)
                self._fake_binary_manager.sync(defined_fake_binaries)

                if not ini_config.is_enabled():
                    # Handle case where configuration toggled while syncing
                    self._fake_binary_manager.remove_all()
                    continue
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
