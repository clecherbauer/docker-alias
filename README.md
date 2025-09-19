# docker-alias
Run containerised tooling as if it were installed natively.

`docker-alias` manages small helper binaries that forward every invocation into a Docker container. The project keeps your host clean, provides reproducible environments and handles user/permission issues so that containerised tools feel native.

## Highlights
- One command per tool: map frequently-used commands to dedicated containers and run them like local binaries
- Automatic user handling: optionally inject a user-switcher so files created in containers match your host permissions
- Config-driven workflow: describe containers, volumes, and overrides in a YAML file; reloads are handled by the daemon
- Smart image management: rebuild images when Dockerfiles change, or opt-out per container when you manage images yourself
- Shell-friendly: `$PATH` integration through generated shim binaries, support for per-command defaults, environment files, and conditional overrides

## Requirements
- Docker Engine >= 20.x
- Systemd (used by the installer to register the daemon)

## Installation
Choose the option that best matches your environment.

### Online installer (recommended)
```bash
wget -q -O - "https://gitlab.com/clecherbauer/tools/docker-alias/-/raw/v2.4.8/linux/online-installer.sh" | bash
```
The script downloads the latest release, installs binaries under `~/.local/docker-alias`, links `docker-alias` and `docker-alias-daemon` into `~/.local/bin`, and amends your shell rc files so the generated shims are on `PATH`.

### Install from source
```bash
git clone https://gitlab.com/clecherbauer/tools/docker-alias.git
cd docker-alias/docker-alias
./setup.sh install
```
This copies the project into `~/.local/docker-alias` and prepares the CLI/daemon just like the online installer.

### Upgrading or uninstalling
- Re-run either installer to upgrade in place; existing configuration files are preserved.
- Remove everything with `~/.local/docker-alias/setup.sh uninstall`.

## Getting Started
1. **Start the daemon:** `docker-alias-daemon start` (add `--no-daemon` for foreground mode).
2. **Create a configuration:** write a `docker-alias.yml` describing your containers and volumes (see [`docs/configuration-manual.md`](docs/configuration-manual.md)).
3. **Register the configuration:** `docker-alias add` (optionally use `--path /path/to/docker-alias.yml`).
4. **Verify commands:** `docker-alias list` prints all generated commands and their backing docker invocations.
5. **Run your tooling:** execute the command name directly (for example `node` or `pyinstaller`). The generated shim forwards the call into the configured container.

## CLI reference
- `docker-alias add [--path <file>]` – Register a `docker-alias.yml` so the daemon can generate shim binaries.
- `docker-alias remove [--path <file>]` – Deregister a configuration file.
- `docker-alias list` – Show all tool commands and their resolved docker run syntax.
- `docker-alias run <container|command> [args…]` – Run a container or command once without needing the shim.
- `docker-alias build [all|<container>]` – Trigger an image build for all or selected containers defined in the YAML file.
- `docker-alias enable|disable` – Toggle generation of fake binaries without deleting configuration.

The daemon accepts `start [--no-daemon]` and `stop`. On Linux the PID file defaults to `~/.config/docker-alias/docker-alias.pid` and can be overridden with `DOCKER_ALIAS_PID_FILE`.

## Configuration
- `docker-alias.yml` files are discovered from the working directory upwards. Each registered file contributes containers and commands.
- Global volumes, per-container volumes, networks, environment variables, command defaults, and conditional overrides are supported.
- Variables such as `$YAML_LOCATION_DIR`, `$UID`, `$DEFAULT_WORKING_DIR`, and environment variables are interpolated before Docker sees the configuration.

A full breakdown of the YAML structure, available attributes, and advanced features lives in the [configuration manual](docs/configuration-manual.md).

## Data locations
- Shim binaries: `~/.local/docker-alias/bin`
- CLI/daemon binaries: `~/.local/docker-alias`
- Configuration & state: `~/.config/docker-alias`

Keep these directories under version control or backup if you rely on customised defaults.

## Support & contributing
Issues and merge requests are welcome. Start by opening an issue in the project repository with your scenario, environment information, and relevant YAML snippets.
