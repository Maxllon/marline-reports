#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="${KERNEL_MANIFEST:-$ROOT_DIR/materials/kernels/manifest.csv}"
DATA_DIR="${KERNEL_DATA_DIR:-$ROOT_DIR/materials/kernels/data}"
TARBALL_DIR="$DATA_DIR/tarballs"
SRC_DIR="$DATA_DIR/src"
MODE="${1:---all}"

usage() {
    cat <<'EOF'
Usage: fetch_kernel_dataset.sh [MODE]

Modes:
  --check      validate manifest and remote Content-Length values
  --download   download and verify tarballs
  --extract    extract tarballs and create duplicate copy
  --all        check, download, and extract (default)
  --help       show this help

Environment:
  KERNEL_MANIFEST  path to manifest.csv
  KERNEL_DATA_DIR  target directory for tarballs and sources
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf 'missing required command: %s\n' "$1" >&2
        exit 1
    fi
}

manifest_rows() {
    tail -n +2 "$MANIFEST"
}

check_manifest() {
    if [[ ! -f "$MANIFEST" ]]; then
        printf 'manifest not found: %s\n' "$MANIFEST" >&2
        exit 1
    fi

    local header
    header="$(head -n 1 "$MANIFEST")"
    if [[ "$header" != "version,series,role,tarball_url,sha256,size_bytes,license,notes" ]]; then
        printf 'unexpected manifest header: %s\n' "$header" >&2
        exit 1
    fi

    local count=0
    local version series role url sha size license notes
    while IFS=, read -r version series role url sha size license notes; do
        [[ -n "$version" ]] || continue
        count=$((count + 1))

        if [[ ! "$version" =~ ^[0-9A-Za-z._-]+$ ]]; then
            printf 'invalid version: %s\n' "$version" >&2
            exit 1
        fi
        if [[ ! "$sha" =~ ^[0-9a-f]{64}$ ]]; then
            printf 'invalid sha256 for %s: %s\n' "$version" "$sha" >&2
            exit 1
        fi
        if [[ ! "$size" =~ ^[0-9]+$ ]]; then
            printf 'invalid size for %s: %s\n' "$version" "$size" >&2
            exit 1
        fi
        if [[ "$role" != "sequence" && "$role" != "duplicate" ]]; then
            printf 'invalid role for %s: %s\n' "$version" "$role" >&2
            exit 1
        fi
        if [[ "$url" != https://cdn.kernel.org/pub/linux/kernel/* ]]; then
            printf 'invalid url for %s: %s\n' "$version" "$url" >&2
            exit 1
        fi
    done < <(manifest_rows)

    if [[ "$count" -eq 0 ]]; then
        printf 'manifest is empty\n' >&2
        exit 1
    fi
    printf 'manifest ok: %d rows\n' "$count"
}

check_remote() {
    require_cmd curl
    require_cmd awk

    local checked=0
    local version series role url sha size license notes
    local remote_size
    while IFS=, read -r version series role url sha size license notes; do
        [[ -n "$version" ]] || continue
        if [[ "$role" == "duplicate" ]]; then
            continue
        fi

        remote_size="$(curl -fsSLI --retry 3 --retry-delay 2 "$url" \
            | tr -d '\r' \
            | awk 'tolower($1) == "content-length:" {print $2}' \
            | tail -n 1)"

        if [[ "$remote_size" != "$size" ]]; then
            printf 'size mismatch for %s: expected %s, got %s\n' \
                "$version" "$size" "${remote_size:-<empty>}" >&2
            exit 1
        fi
        checked=$((checked + 1))
        printf 'remote ok: %s (%s bytes)\n' "$version" "$remote_size"
    done < <(manifest_rows)
    printf 'remote check ok: %d tarballs\n' "$checked"
}

tarball_for() {
    printf '%s/%s' "$TARBALL_DIR" "${1##*/}"
}

verify_tarball() {
    local path="$1"
    local sha="$2"
    printf '%s  %s\n' "$sha" "$path" | sha256sum -c - >/dev/null
}

download_tarballs() {
    require_cmd curl
    require_cmd sha256sum
    mkdir -p "$TARBALL_DIR"

    local version series role url sha size license notes
    local path
    while IFS=, read -r version series role url sha size license notes; do
        [[ -n "$version" ]] || continue
        if [[ "$role" == "duplicate" ]]; then
            continue
        fi

        path="$(tarball_for "$url")"
        if [[ -f "$path" ]]; then
            if verify_tarball "$path" "$sha"; then
                printf 'exists and verified: %s\n' "$path"
                continue
            fi
            printf 'removing invalid tarball: %s\n' "$path" >&2
            rm -f "$path"
        fi

        printf 'downloading %s\n' "$url"
        curl -fL --retry 5 --retry-delay 2 --continue-at - -o "$path" "$url"
        verify_tarball "$path" "$sha"
        printf 'verified: %s\n' "$path"
    done < <(manifest_rows)
}

extract_tarballs() {
    require_cmd tar
    require_cmd xz
    require_cmd sha256sum
    mkdir -p "$SRC_DIR"

    local version series role url sha size license notes
    local path
    local dest
    while IFS=, read -r version series role url sha size license notes; do
        [[ -n "$version" ]] || continue
        if [[ "$role" == "duplicate" ]]; then
            continue
        fi

        path="$(tarball_for "$url")"
        if [[ ! -f "$path" ]]; then
            printf 'missing tarball: %s\n' "$path" >&2
            exit 1
        fi
        verify_tarball "$path" "$sha"

        dest="$SRC_DIR/linux-$version"
        if [[ -d "$dest" ]]; then
            printf 'already extracted: %s\n' "$dest"
            continue
        fi

        printf 'extracting %s\n' "$path"
        tar -xJf "$path" -C "$SRC_DIR"
        if [[ ! -d "$dest" ]]; then
            printf 'expected directory not found: %s\n' "$dest" >&2
            exit 1
        fi
    done < <(manifest_rows)

    while IFS=, read -r version series role url sha size license notes; do
        [[ -n "$version" ]] || continue
        [[ "$role" == "duplicate" ]] || continue

        local source_version="${url##*/linux-}"
        source_version="${source_version%.tar.xz}"
        local source_dir="$SRC_DIR/linux-$source_version"
        local duplicate_dir="$SRC_DIR/linux-$version"

        if [[ ! -d "$source_dir" ]]; then
            printf 'missing duplicate source: %s\n' "$source_dir" >&2
            exit 1
        fi
        if [[ -e "$duplicate_dir" ]]; then
            printf 'already present: %s\n' "$duplicate_dir"
            continue
        fi

        printf 'creating duplicate: %s -> %s\n' "$source_dir" "$duplicate_dir"
        cp -a "$source_dir" "$duplicate_dir"
    done < <(manifest_rows)

    printf 'dataset ready: %s\n' "$SRC_DIR"
}

case "$MODE" in
    --check)
        check_manifest
        check_remote
        ;;
    --download)
        check_manifest
        download_tarballs
        ;;
    --extract)
        check_manifest
        extract_tarballs
        ;;
    --all)
        check_manifest
        check_remote
        download_tarballs
        extract_tarballs
        ;;
    --help|-h)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
