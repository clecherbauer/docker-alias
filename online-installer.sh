#!/usr/bin/env bash
set -e

DOCKER_ALIAS_VERSION="2.0.0-beta"
SOURCE_FILE="docker-alias.zip"
SOURCE_DIR="docker-alias"

if [ ! -f "$SOURCE_FILE" ]; then
  wget -O "$SOURCE_FILE" "https://github.com/clecherbauer/docker-alias/releases/download/$DOCKER_ALIAS_VERSION/$SOURCE_FILE"
fi

unzip -o "$SOURCE_FILE"
(
  cd "$SOURCE_DIR"
  ./setup.sh
)

rm -Rf "$SOURCE_DIR"
