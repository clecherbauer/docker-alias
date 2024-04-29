#!/usr/bin/env bash
set -e

VERSION="v.2.4.3"
SOURCE_FILE="docker-alias.linux64.zip"
SOURCE_DIR="docker-alias"


URL=$(wget -q -O - "https://gitlab.com/api/v4/projects/31019107/releases/"$VERSION"/assets/links" | grep -Po '"direct_asset_url":*\K"[^"]*"' | grep "$SOURCE_FILE" | sed 's/"//g')
wget $URL

unzip -o "$SOURCE_FILE"
(
    cd "$SOURCE_DIR"
    ./setup.sh install
)

rm -Rf "$SOURCE_DIR"
