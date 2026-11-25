#!/usr/bin/env bash
# Build Credo OS inside a privileged Fedora container (works from any Linux with podman or docker).
#   ./build/build-container.sh [--releasever 43] [--with-library]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASEVER=43
ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --releasever) RELEASEVER="$2"; ARGS+=("$1" "$2"); shift 2 ;;
        *) ARGS+=("$1"); shift ;;
    esac
done
ENGINE="$(command -v podman || command -v docker || true)"
[ -n "$ENGINE" ] || { echo "Install podman or docker first." >&2; exit 1; }

exec sudo "$ENGINE" run --rm --privileged -v /dev:/dev \
    -v "$HERE:/src:Z" -w /src \
    "registry.fedoraproject.org/fedora:$RELEASEVER" \
    bash /src/build/build.sh --releasever "$RELEASEVER" --out /src/out "${ARGS[@]}"
