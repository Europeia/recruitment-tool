#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="/home/europeia/recruitment-tool"
PID_FILE="$PROJECT_DIR/.asperta.pid"
LOG_FILE="$PROJECT_DIR/asperta.log"
ENTRYPOINT="$PROJECT_DIR/main.py"
PULL=true
HELP=false

while getopts "hn" option; do
    case "$option" in
        h)
            HELP=true
            ;;
        n)
            PULL=false
            ;;
        \?)
            echo "unknown option, exiting"
            exit 1
            ;;
    esac
done

if $HELP; then
  echo "./deploy.sh"
  echo "asperta deployment script"
  echo "USAGE:"
  echo "  deploy.sh -h: display this message"
  echo "  deploy.sh -n: start bot without pulling from git"
  exit 0
fi

cd "$PROJECT_DIR"

if $PULL; then
  echo "pulling origin"
  git pull origin main
fi

echo "waiting for MySQL"

for _ in {1..30}; do
    if systemctl is-active --quiet mysql; then
        echo "MySQL is running"
        break
    fi

    echo "MySQL not ready yet"
    sleep 2
done

if ! systemctl is-active --quiet mysql; then
    echo "ERROR: MySQL failed to start"
    exit 1
fi

if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")

    if kill -0 "$PID" 2>/dev/null; then
        echo "stopping existing process ($PID)"
        kill "$PID"

        for _ in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        if kill -0 "$PID" 2>/dev/null; then
            echo "force killing process"
            kill -9 "$PID"
        fi
    fi

    rm -f "$PID_FILE"
fi

echo "starting asperta"

nohup uv run "$ENTRYPOINT" >"$LOG_FILE" 2>&1 &
PID=$!

echo "$PID" > "$PID_FILE"

echo "started with PID: $PID"