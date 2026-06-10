#!/usr/bin/env bash
# Detach a command from the terminal (macOS + Linux).
set -euo pipefail
LOG=$1
shift
: > "$LOG"
nohup "$@" >> "$LOG" 2>&1 </dev/null &
echo $!
disown -h $! 2>/dev/null || true
