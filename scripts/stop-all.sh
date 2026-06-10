#!/usr/bin/env bash
set -euo pipefail
API_PORT="${ORCHESTRATOR_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

screen_stop() {
  local name=$1
  if screen -ls | grep -q "[0-9]*\.${name}[[:space:]]"; then
    screen -S "$name" -X quit 2>/dev/null || true
  fi
}

if [ "$(uname -s)" = "Darwin" ]; then
  launchctl bootout "gui/$(id -u)/com.ideaforge.api" 2>/dev/null || true
  launchctl bootout "gui/$(id -u)/com.ideaforge.web" 2>/dev/null || true
fi

screen_stop ideaforge-api
screen_stop ideaforge-web
screen_stop ideaforge-tunnel

pids=$(lsof -t -i:"$API_PORT" 2>/dev/null || true)
[ -n "$pids" ] && kill $pids 2>/dev/null || true
pids=$(lsof -t -i:"$WEB_PORT" 2>/dev/null || true)
[ -n "$pids" ] && kill $pids 2>/dev/null || true

echo "Stopped IdeaForge services"
