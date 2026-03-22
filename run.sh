#!/usr/bin/env bash
# run.sh — Build and run the photo frame in Docker for local testing.
#
# Usage:
#   ./run.sh                        # uses ./photos as the photo source
#   ./run.sh /path/to/your/photos   # custom photo directory
#   ./run.sh --rebuild              # force image rebuild then run
#   ./run.sh --shell                # drop into a bash shell instead of running the app
#
# Requirements: Docker (desktop or engine), no display needed on host.

set -euo pipefail

IMAGE_NAME="photo-frame-test"
CONTAINER_NAME="photo-frame"
PHOTOS_DIR="$(pwd)/photos"
FORCE_REBUILD=false
SHELL_MODE=false

# --- Parse args ---
for arg in "$@"; do
    case $arg in
        --rebuild) FORCE_REBUILD=true ;;
        --shell)   SHELL_MODE=true ;;
        /*)        PHOTOS_DIR="$arg" ;;   # absolute path to photos
        *)         PHOTOS_DIR="$(pwd)/$arg" ;;
    esac
done

# --- Ensure photos directory exists ---
mkdir -p "$PHOTOS_DIR"

echo "┌─────────────────────────────────────────┐"
echo "│        Photo Frame — Docker Test        │"
echo "└─────────────────────────────────────────┘"
echo "  Photos dir : $PHOTOS_DIR"
echo "  Image      : $IMAGE_NAME"
echo ""

# --- Build image if needed ---
if [[ "$FORCE_REBUILD" == true ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "▶  Building Docker image..."
    docker build -t "$IMAGE_NAME" .
    echo "✔  Build complete."
else
    echo "✔  Using cached image (pass --rebuild to force a fresh build)."
fi
echo ""

# --- Stop any existing container ---
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "▶  Stopping existing container..."
    docker rm -f "$CONTAINER_NAME" >/dev/null
fi

# --- Run ---
if [[ "$SHELL_MODE" == true ]]; then
    echo "▶  Dropping into shell inside container..."
    echo "   Run 'python3 main.py' to start the frame manually."
    echo ""
    docker run -it --rm \
        --name "$CONTAINER_NAME" \
        -v "$PHOTOS_DIR:/app/photos:ro" \
        -e DOCKER_TEST=1 \
        --entrypoint bash \
        "$IMAGE_NAME"
else
    echo "▶  Starting photo frame..."
    echo "   Press Ctrl+C to stop."
    echo ""
    docker run -it --rm \
        --name "$CONTAINER_NAME" \
        -v "$PHOTOS_DIR:/app/photos:ro" \
        -e DOCKER_TEST=1 \
        "$IMAGE_NAME"
fi
