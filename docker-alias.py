import argparse
import os.path
import sys

from lib.config import INIConfig, YAML_CONFIG_FILE_NAME, INI_CONFIG_FILE_PATH, VERSION
from lib.docker_util import DockerUtil
from lib.config_container import ConfigContainerUtil


class DockerAliasCLI(object):
    ini_config = INIConfig()
    add_description = 'Adds a new {yaml_config_file} to {ini_config_file}'.format(
        yaml_config_file=YAML_CONFIG_FILE_NAME,
        ini_config_file=INI_CONFIG_FILE_PATH
    )
    remove_description = 'Removes a {yaml_config_file} from {ini_config_file}'.format(
        yaml_config_file=YAML_CONFIG_FILE_NAME,
        ini_config_file=INI_CONFIG_FILE_PATH
    )
    list_description = 'List all containers and their commands'
    run_description = 'Runs an command in an container'
    build_description = 'Builds container-images'
    usage = '''
docker-alias <command> [<args>]

Available Commands:
   add      {add_description}
   build    {build_description} [ all || <container_name> ]
   list     {list_description}
   remove   {remove_description}
   run      {run_description} [ <container_name> || <command_name> ]

Version: {version}
'''

    quiet = False

    def __init__(self):
        parser = argparse.ArgumentParser(
            description='docker-alias cli',
            usage=self.usage.format(
                add_description=self.add_description,
                build_description=self.build_description,
                list_description=self.list_description,
                remove_description=self.remove_description,
                run_description=self.run_description,
                version=VERSION
            )
        )
        parser.add_argument('command', help='Subcommand to run')
        parser.add_argument(
            '--quiet',
            default=False,
            action='store_true',
            help='outputs only std-out and std-err from docker-subprocess'
        )
        args = parser.parse_args(sys.argv[1:2])
        self.quiet = args.quiet
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            sys.exit(1)
        getattr(self, args.command)()

    def add(self):
        parser = argparse.ArgumentParser(
            description=self.add_description
        )
        parser.add_argument('--path', help='optional path')
        args = parser.parse_args(sys.argv[2:])
        path = os.path.join(os.getcwd(), YAML_CONFIG_FILE_NAME)
        if args.path:
            path = args.path

        if not path.endswith(YAML_CONFIG_FILE_NAME):
            print('--path does not contain ' + YAML_CONFIG_FILE_NAME + '!')
            sys.exit(1)

        if not os.path.isfile(path):
            print(YAML_CONFIG_FILE_NAME + ' does not exist!')
            sys.exit(1)

        self.ini_config.add_yaml_path(path)
        print('Added ' + path + ' to config.ini')

    def remove(self):
        parser = argparse.ArgumentParser(
            description=self.remove_description
        )
        parser.add_argument('--path', help='optional path')
        args = parser.parse_args(sys.argv[2:])
        path = os.path.join(os.getcwd(), YAML_CONFIG_FILE_NAME)
        if args.path:
            path = args.path

        if not path.endswith(YAML_CONFIG_FILE_NAME):
            print('--path does not contain ' + YAML_CONFIG_FILE_NAME + '!')
            sys.exit(1)

        if not os.path.isfile(path):
            print(YAML_CONFIG_FILE_NAME + ' does not exist!')
            sys.exit(1)

        self.ini_config.remove_yaml_path(path)
        print('Removed ' + path + ' from config.ini')

    def list(self):
        config_container_util = ConfigContainerUtil()
        argparse.ArgumentParser(description=self.list_description)

        config_containers = config_container_util.resolve_config_containers()
        config_containers.reverse()
        command_list = {}

        for config_container in config_containers:
            if not config_container.image:
                config_container.image = DockerUtil.image_name_pattern.format(
                    fs_location_hash=config_container.fs_location_hash,
                    container_name=config_container.name
                )
            if config_container.commands:
                for command in config_container.commands:
                    command_list[command.name] = " ".join(
                        DockerUtil(self.quiet).build_command(config_container, command=command)
                    )
            else:
                command_list[config_container] = " ".join(DockerUtil(self.quiet).build_command(config_container))

        for key, cmd in command_list.items():
            print(key + ": " + cmd + "\n")

    def run(self):
        config_container_util = ConfigContainerUtil()
        parser = argparse.ArgumentParser(description=self.run_description, add_help=False)
        args, unknown = parser.parse_known_args(sys.argv[2:])
        if len(unknown) > 0:
            wanted_container = unknown[0]
            if '/' in wanted_container:
                wanted_container = wanted_container.split('/')[-1]
            unknown.pop(0)
            attributes = unknown
            for config_container in config_container_util.resolve_config_containers():
                config_container = config_container_util.merge_config_containers(
                    config_container,
                    ' '.join([wanted_container] + attributes)
                )

                if config_container.commands:
                    for command in config_container.commands:
                        if command.name == wanted_container:
                            sys.exit(DockerUtil(self.quiet).exec_docker(
                                config_container, command=command, attributes=attributes)
                            )
                if config_container.name == wanted_container:
                    sys.exit(DockerUtil(self.quiet).exec_docker(config_container, attributes=attributes))
            if not self.quiet:
                print('Container ' + wanted_container + ' not found!')
            sys.exit(1)

    def build(self):
        config_container_util = ConfigContainerUtil()
        parser = argparse.ArgumentParser(description=self.build_description)
        parser.add_argument('container')
        args = parser.parse_args(sys.argv[2:])
        if args.container == 'all':
            for config_container in config_container_util.resolve_config_containers():
                if config_container.build:
                    DockerUtil(self.quiet).build_image(config_container)

        else:
            for config_container in config_container_util.resolve_config_containers():
                if config_container.build and config_container.name == args.container:
                    DockerUtil(self.quiet).build_image(config_container)


if __name__ == '__main__':
    try:
        DockerAliasCLI()
    except KeyboardInterrupt:
        pass
