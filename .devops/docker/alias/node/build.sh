#!/bin/bash
# shellcheck disable=SC1091
# shellcheck disable=SC1090
# shellcheck disable=SC2001
set -e

#disable SSH Host-Key Verification for gitlab
echo -e "Host gitlab.com\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile=/dev/null\n" >> /etc/ssh/ssh_config

npm install -g npx @vue/cli --force
npm config set unsafe-perm true
