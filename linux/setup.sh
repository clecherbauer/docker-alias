#!/usr/bin/env bash
set -e

USER_BIN_DIR="$HOME/.local/bin"
DOCKER_ALIAS_ROOT="$HOME/.local/docker-alias"
DOCKER_ALIAS_BINARY_ROOT="$DOCKER_ALIAS_ROOT/bin"
DOCKER_ALIAS_CONFIG_ROOT="$HOME/.config/docker-alias"
DOCKER_ALIAS_CLI_BINARY="$DOCKER_ALIAS_ROOT/docker-alias"
DOCKER_ALIAS_CLI_SYMLINK="$USER_BIN_DIR/docker-alias"
DOCKER_ALIAS_DAEMON_BINARY="$DOCKER_ALIAS_ROOT/docker-alias-daemon"
DOCKER_ALIAS_DAEMON_SYMLINK="$USER_BIN_DIR/docker-alias-daemon"
SHELLS="zsh bash"
DOCKER_ALIAS_PATH="PATH=\$HOME/.local/docker-alias/bin:\$PATH"


function install() {
    if [ -x "$(command -v docker-alias-daemon)" ]; then
        docker-alias-daemon stop
    fi
    if [ -d "$DOCKER_ALIAS_ROOT" ]; then rm -Rf "$DOCKER_ALIAS_ROOT"; fi
    if [ ! -d "$USER_BIN_DIR" ]; then mkdir "$USER_BIN_DIR"; fi
    if [ ! -d "$DOCKER_ALIAS_ROOT" ]; then mkdir "$DOCKER_ALIAS_ROOT"; fi
    if [ ! -d "$DOCKER_ALIAS_CONFIG_ROOT" ]; then mkdir "$DOCKER_ALIAS_CONFIG_ROOT"; fi
    if [ ! -d "$DOCKER_ALIAS_BINARY_ROOT" ]; then mkdir "$DOCKER_ALIAS_BINARY_ROOT"; fi
    if [ -L "$DOCKER_ALIAS_CLI_SYMLINK" ]; then rm "$DOCKER_ALIAS_CLI_SYMLINK"; fi
    if [ -L "$DOCKER_ALIAS_DAEMON_SYMLINK" ]; then rm "$DOCKER_ALIAS_DAEMON_SYMLINK"; fi

    cp -r . "$DOCKER_ALIAS_ROOT"
    chmod +x "$DOCKER_ALIAS_CLI_BINARY"
    chmod +x "$DOCKER_ALIAS_DAEMON_BINARY"
    ln -s "$DOCKER_ALIAS_CLI_BINARY" "$DOCKER_ALIAS_CLI_SYMLINK"
    ln -s "$DOCKER_ALIAS_DAEMON_BINARY" "$DOCKER_ALIAS_DAEMON_SYMLINK"

    (
        for _SHELL in $SHELLS
        do
            SHELLRC="$HOME/.$_SHELL"rc
            if [ -f "$SHELLRC" ]; then
                if ! grep -Fxq "$DOCKER_ALIAS_PATH" "$SHELLRC"; then
                    echo "$DOCKER_ALIAS_PATH" >> "$SHELLRC"
                fi
            fi
        done
    )
}

function uninstall() {
    if [ -x "$(command -v docker-alias-daemon)" ]; then
        docker-alias-daemon stop
    fi
    if [ -d "$DOCKER_ALIAS_ROOT" ]; then rm -Rf "$DOCKER_ALIAS_ROOT"; fi
    if [ ! -d "$DOCKER_ALIAS_ROOT" ]; then rm -Rf "$DOCKER_ALIAS_ROOT"; fi
    if [ ! -d "$DOCKER_ALIAS_CONFIG_ROOT" ]; then rm -Rf "$DOCKER_ALIAS_CONFIG_ROOT"; fi
    if [ ! -d "$DOCKER_ALIAS_BINARY_ROOT" ]; then rm -Rf "$DOCKER_ALIAS_BINARY_ROOT"; fi
    if [ -L "$DOCKER_ALIAS_CLI_SYMLINK" ]; then rm "$DOCKER_ALIAS_CLI_SYMLINK"; fi
    if [ -L "$DOCKER_ALIAS_DAEMON_SYMLINK" ]; then rm "$DOCKER_ALIAS_DAEMON_SYMLINK"; fi

    (
        for _SHELL in $SHELLS
        do
            SHELLRC="$HOME/.$_SHELL"rc
            if [ -f "$SHELLRC" ]; then
                if grep -Fxq "$DOCKER_ALIAS_PATH" "$SHELLRC"; then
                    sed -i "/$DOCKER_ALIAS_PATH/d" "$SHELLRC"
                fi
            fi
        done
    )
}

if [ "$1" == "install" ]; then
    install
fi

if [ "$1" == "uninstall" ]; then
    uninstall
fi