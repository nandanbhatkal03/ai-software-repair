#!/usr/bin/env bash
set -euo pipefail
exec aisr localize "$1" --metric "${2:-ochiai}"
