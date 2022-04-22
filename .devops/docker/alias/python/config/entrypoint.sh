#!/bin/bash
# shellcheck disable=SC2044

set -e

export PYTHONPATH="$PWD:$PWD/plugins:$PWD/.pydeps"
export PATH=$PATH:"$PWD/.pydeps/bin"

exec "$@"
