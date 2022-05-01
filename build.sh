#!/usr/bin/env bash
set -e

ZIP_DIR="docker-alias"
ZIP_LINUX64="docker-alias.linux64.zip"

function cleanup() {
    if [ -f "docker-alias.spec" ]; then rm "docker-alias.spec"; fi
    if [ -d "./build" ]; then rm -Rf "./build"; fi
    if [ -d "./dist" ]; then rm -Rf "./dist"; fi
    if [ -d "./$ZIP_DIR" ]; then rm -Rf "./$ZIP_DIR"; fi
    if [ -d "./.pydeps" ]; then rm -Rf "./.pydeps"; fi
    mkdir "./.pydeps"
}

function build_linux() {
    cleanup
    pip3 install --target ".pydeps" --upgrade -r requirements.txt
    pyinstaller -y --clean --noupx -F docker-alias.py
    pyinstaller -y --clean --noupx -F docker-alias-daemon.py

    mkdir "$ZIP_DIR"
    cp -R dist/docker-alias "$ZIP_DIR"
    cp -R dist/docker-alias-daemon "$ZIP_DIR"
    cp linux/setup.sh "$ZIP_DIR"
    zip -r "$ZIP_LINUX64" "$ZIP_DIR"
}

if [ "$1" == "all" ]; then
    if [ -f "./$ZIP_LINUX64" ]; then rm "./$ZIP_LINUX64"; fi
    build_linux
fi