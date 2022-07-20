#!/usr/bin/env bash
set -e

ZIP_DIR="docker-alias"
ZIP_LINUX64="docker-alias.linux64.zip"
ZIP_WIN64="docker-alias.win64.zip"

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
    cp -R switch_user "$ZIP_DIR"
    cp linux/setup.sh "$ZIP_DIR"
    zip -r "$ZIP_LINUX64" "$ZIP_DIR"
}

function build_windows() {
    cleanup
    pyinstaller-windows -y --clean --hiddenimport win32timezone --hiddenimport --runtime-tmpdir=. --onefile docker-alias.py
    mkdir "$ZIP_DIR"
    cp -R dist/docker-alias.exe "$ZIP_DIR/docker-alias.exe"
    #cp windows/setup.ps1 "$ZIP_DIR"
    zip -r "$ZIP_WIN64" "$ZIP_DIR"
}

if [ "$1" == "all" ]; then
    if [ -f "./$ZIP_LINUX64" ]; then rm "./$ZIP_LINUX64"; fi
    build_linux
    build_windows
fi

if [ "$1" == "linux" ]; then
    if [ -f "./$ZIP_LINUX64" ]; then rm "./$ZIP_LINUX64"; fi
    build_linux
fi

if [ "$1" == "windows" ]; then
    if [ -f "./$ZIP_WIN64" ]; then rm "./$ZIP_WIN64"; fi
    build_windows
fi