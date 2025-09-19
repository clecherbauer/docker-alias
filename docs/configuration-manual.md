# Configuration Manual
This guide explains how `docker-alias` interprets `docker-alias.yml`, how shim binaries are generated, and how to model common scenarios.

## File discovery and registration
- `docker-alias.yml` files are discovered upwards from your current working directory. Parent directories can contribute configurations.
- Only files registered via `docker-alias add [--path]` are considered. Paths are stored in `~/.config/docker-alias/config.ini`.
- All containers defined across registered files are merged into the active command set. Later (deeper) directories take precedence when ambiguous.

## Top-level keys
`docker-alias.yml` accepts three keys at the root level:

| Key | Type | Description |
| --- | --- | --- |
| `volumes` | map | Defines reusable named volumes (often driver-based) that containers can reference. |
| `containers` | map | Declares each runnable environment. Every entry becomes one or more commands. |
| `keep_volumes` | boolean (default `false`) | When `true`, volumes created by `docker-alias` are kept after each run instead of being cleaned up automatically. |

Example:
```yaml
volumes:
  shared-cache:
    driver: local
    driver_opts:
      type: none
      device: "/tmp/docker-alias-cache"
      o: bind
keep_volumes: false
containers:
  node:
    image: node:20
    volumes:
      - $YAML_LOCATION_DIR:$DEFAULT_WORKING_DIR
      - shared-cache:/cache
```

## Global volumes
Named volumes behave similarly to docker-compose. Define them once under `volumes` and reference them in containers using the key name as the source segment:
```yaml
containers:
  builder:
    volumes:
      - shared-cache:/workspace/cache
```
When a volume includes a `driver`, `docker-alias` pre-creates it with a deterministic name so multiple commands can reuse it.

## Container definition
Every entry in `containers` represents a runnable Docker container.

| Key | Type | Default | Purpose |
| --- | --- | --- | --- |
| `image` | string | – | External image to run. Required when `build` is omitted. |
| `build` | object | – | Build instructions with `context` and `dockerfile`. Creates images named `docker_alias_<hash>_<container>` automatically. |
| `auto_rebuild_images` | boolean | `true` | Rebuild the image when local Dockerfile contents change. Disable if you manage builds manually. |
| `commands` | list | – | Commands exposed as shims. Strings map directly; dict entries can override `path` and `default_params`. If omitted, the container name becomes the command. |
| `entrypoint` | string | – | Overrides the image entrypoint (passed to `docker run --entrypoint`). |
| `env_file` | string | – | Relative path (from the YAML file) to a Docker-compatible env file. |
| `environment` | list | – | Inline environment variables (`VAR=value`). |
| `volumes` | list | – | Array of `<source>:<target>` strings. Sources may reference global volumes. |
| `working_dir` | string | `/app` | Container working directory base. Relative paths from the host are appended unless `stay_in_root` is `true`. |
| `stay_in_root` | boolean | `false` | Keep the working directory fixed (no path mapping based on the host cwd). |
| `user` | string | – | User passed to `docker run --user`. Interpolations like `$UID` are supported. |
| `inject_user_switcher` | boolean | `false` | Mounts `switch_user` helper and makes it the initial command, aligning container user/groups with the host. Useful when `user` alone is insufficient. |
| `privileged` | boolean | `true` | Controls `--privileged`. Disable for security-sensitive workloads. |
| `networks` | list | – | Additional Docker networks to attach. The compose-style default network is auto-discovered when present. |
| `ports` | list | – | `docker run -p` arguments. |
| `quiet` | boolean | `false` | Suppress informational logs (image pull/build output still appears unless `docker-alias --quiet` is used). |
| `pre_exec_hook_command` | string | – | Reserved for future use. Currently no-op. |
| `post_exec_hook_command` | string | – | Reserved for future use. Currently no-op. |

### Command declarations
Each list item under `commands` can take one of two forms:
```yaml
commands:
  - node            # Exposes a shim named "node"
  - npm             # Exposes a shim named "npm"
  - jest:
      path: $DEFAULT_WORKING_DIR/node_modules/.bin/jest
      default_params:
        - --runInBand
```
When a `path` is provided, the shim still uses the command name (`jest`) but executes the target path inside the container. `default_params` are placed before user-supplied arguments.

### Build configuration
When `build` is set, the container image is built from local sources.
```yaml
build:
  context: .
  dockerfile: Dockerfile
```
- `context` accepts `.`, relative folders (`./docker`), or absolute paths.
- Hashes of the Docker context are cached in `~/.config/docker-alias/config.ini` under `ImageBuildHashes` to decide when rebuilds are needed.

## Conditional overrides
Use `command_pattern_conditional_config` to tweak settings when a command is called with specific prefixes.
```yaml
command_pattern_conditional_config:
  - "pytest":
      environment:
        - PYTEST_ADDOPTS=--maxfail=1
      volumes:
        - shared-cache:/workspace/tests
  - "pytest --debug":
      quiet: true
```
- The pattern matches the raw command string (including default parameters).
- Supported override keys mirror container attributes (`entrypoint`, `environment`, `volumes`, `user`, `networks`, `ports`, `stay_in_root`, etc.).
- Overrides extend lists (e.g. additional environments) and replace scalar values.

## Path handling
By default the working directory inside the container mirrors the relative path from the `.yml` location to your current directory. For example, running a command inside `project/app` when the YAML sits in `project` results in `/app/app`. Set `stay_in_root: true` to keep a fixed `working_dir`.

## Variable interpolation
Prior to parsing, the YAML content is processed with:
- All environment variables available in your shell
- `$YAML_LOCATION_DIR` – absolute path to the directory containing the YAML file
- `$UID` – numeric UID of the calling user
- `$DEFAULT_WORKING_DIR` – defaults to `/app`
This allows portable mounts such as `$YAML_LOCATION_DIR:$DEFAULT_WORKING_DIR`.

## Configuration state and toggles
- Registered YAML paths live in `~/.config/docker-alias/config.ini` under the `YamlPaths` section.
- Disable or re-enable shim generation without losing registration using `docker-alias disable` / `docker-alias enable`. When disabled, the daemon deletes all generated shims until re-enabled.

## Sample configuration
```yaml
volumes:
  shared-cache:
    driver: local
    driver_opts:
      type: none
      device: "/tmp/docker-alias-cache"
      o: bind

containers:
  python:
    image: registry.gitlab.com/clecherbauer/docker-images/python:3.8-debian-bullseye
    volumes:
      - $YAML_LOCATION_DIR:$DEFAULT_WORKING_DIR
      - $SSH_AUTH_SOCK:/ssh-auth.sock
      - shared-cache:/cache
    commands:
      - python
      - pip3
      - flake8
      - pyinstaller:
          path: $DEFAULT_WORKING_DIR/.pydeps/bin/pyinstaller
    environment:
      - SSH_AUTH_SOCK=/ssh-auth.sock
      - PYTHONPATH=$DEFAULT_WORKING_DIR/.pydeps
      - PATH=$DEFAULT_WORKING_DIR/.pydeps/bin:\$PATH
    user: "$UID"

  pyinstaller-windows:
    image: registry.gitlab.com/clecherbauer/docker-images/pyinstaller-windows:python-3.8-ubuntu-20.04
    volumes:
      - shared-cache:$DEFAULT_WORKING_DIR
    commands:
      - pyinstaller-windows
    environment:
      - REQUIREMENTS_TXT=requirements.txt
```
This example publishes `python`, `pip3`, `flake8`, `pyinstaller`, and `pyinstaller-windows` commands. User permissions mirror the host, SSH agent forwarding works via volume bind, and cached artefacts can be shared between containers through the named volume.

## Best practices
- Keep YAML files close to the projects they configure to benefit from directory-based discovery.
- Use environment files for secrets rather than embedding passwords into the YAML.
- Set `privileged: false` unless the command requires elevated container capabilities.
- Combine `auto_rebuild_images: false` with CI pipelines that publish images to a registry when you want strict reproducibility.
- When sharing configurations, document required environment variables (`SSH_AUTH_SOCK`, custom tokens, etc.).
