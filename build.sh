#!/usr/bin/env bash

set -e

PYTHONPATH="$PWD/.pydeps:$PYTHONPATH"
PATH="$PWD/.pydeps/bin:$PATH"

if [ -f "./docker-alias.zip" ]; then rm "./docker-alias.zip"; fi
if [ -d "./build" ]; then rm -Rf "./build"; fi
if [ -d "./dist" ]; then rm -Rf "./dist"; fi
if [ -d "./docker-alias" ]; then rm -Rf "./docker-alias"; fi
if [ -d "./.pydeps" ]; then rm -Rf "./.pydeps"; fi
mkdir "./.pydeps"

pip3  install --target ".pydeps" --upgrade -r requirements.txt
python3 .pydeps/bin/pyinstaller -y cli.py
python3 .pydeps/bin/pyinstaller -y daemon.py

mkdir 'docker-alias'
cp -R dist/cli 'docker-alias'
cp -R dist/daemon 'docker-alias'
cp docker-alias.service 'docker-alias/daemon'
cp setup.sh 'docker-alias'

zip -r docker-alias.zip 'docker-alias'
