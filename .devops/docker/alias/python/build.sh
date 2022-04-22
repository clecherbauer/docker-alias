#!/bin/bash
# shellcheck disable=SC1091
# shellcheck disable=SC1090
# shellcheck disable=SC2001
set -e

SOURCE_ROOT="/var/source"
cp "$SOURCE_ROOT/.devops/docker/alias/python/config/entrypoint.sh" /usr/local/bin

pip3 install pyinstaller autopep8 flake8
