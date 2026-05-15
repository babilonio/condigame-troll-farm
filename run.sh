#!/usr/bin/env bash
# Run a Troll Farm match using Docker
# Usage: ./run.sh [bot1] [bot2] [seed] [league]
#   bot1, bot2: commands to run each bot (default: python3 /work/examplebot.py)
#   seed: random seed (default: 1)
#   league: league level 1-4 (default: 3, which is Bronze with all rules)
set -euo pipefail

BOT1=${1:-"python3 /work/examplebot.py"}
BOT2=${2:-"python3 /work/examplebot.py"}
SEED=${3:-1}
LEAGUE=${4:-3}
LOG=${LOG:-}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="trollfarm-runner:local"
JAR="Troll-Farm/troll-farm-1.0-SNAPSHOT.jar"

if [[ ! -f "$ROOT/$JAR" ]]; then
    echo "Missing $JAR. Download it from the Troll-Farm GitHub releases." >&2
    exit 1
fi

# Build Docker image if not present
docker image inspect "$IMAGE" >/dev/null 2>&1 \
    || docker build -f "$ROOT/tools/Dockerfile.trollfarm-runner" -t "$IMAGE" "$ROOT"

CONTAINER_LOG="$LOG"
if [[ -n "$CONTAINER_LOG" && "$CONTAINER_LOG" != /* ]]; then
    CONTAINER_LOG="/work/$CONTAINER_LOG"
fi

docker run --rm \
    -v "$ROOT:/work" \
    -w /work/Troll-Farm \
    $([[ "${SERVER:-0}" == "1" ]] && echo "-p 8888:8888") \
    "$IMAGE" \
    java -jar troll-farm-1.0-SNAPSHOT.jar \
    -p1 "$BOT1" \
    -p2 "$BOT2" \
    -seed "$SEED" \
    -league "$LEAGUE" \
    ${CONTAINER_LOG:+-l "$CONTAINER_LOG"} \
    ${SERVER:+-s}