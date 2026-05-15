#!/usr/bin/env bash
set -euo pipefail

BOT1=${1:-"python3 /work/examplebot.py"}
BOT2=${2:-"python3 /work/examplebot.py"}
SEED=${3:-1}
LEAGUE=${LEAGUE:-3}
LOG=${LOG:-}
SERVER=${SERVER:-0}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="trollfarm-runner:local"
JAR="Troll-Farm/troll-farm-1.0-SNAPSHOT.jar"
CONTAINER_LOG="$LOG"

if [[ -n "$CONTAINER_LOG" && "$CONTAINER_LOG" != /* ]]; then
    CONTAINER_LOG="/work/$CONTAINER_LOG"
fi

if [[ ! -f "$ROOT/$JAR" ]]; then
    echo "Missing $JAR. Download it from the Troll-Farm release first." >&2
    exit 1
fi

docker image inspect "$IMAGE" >/dev/null 2>&1 \
    || docker build -f "$ROOT/tools/Dockerfile.trollfarm-runner" -t "$IMAGE" "$ROOT"

args=(
    java -jar troll-farm-1.0-SNAPSHOT.jar
    -p1 "$BOT1"
    -p2 "$BOT2"
    -seed "$SEED"
    -league "$LEAGUE"
)

if [[ -n "$CONTAINER_LOG" ]]; then
    args+=(-l "$CONTAINER_LOG")
fi

if [[ "$SERVER" == "1" ]]; then
    args+=(-s)
fi

docker run --rm \
    -v "$ROOT:/work" \
    -w /work/Troll-Farm \
    $([[ "$SERVER" == "1" ]] && echo "-p 8888:8888") \
    "$IMAGE" \
    "${args[@]}"
