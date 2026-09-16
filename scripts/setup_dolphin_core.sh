#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
local_root="$project_root/.local"
source_dir="$project_root/third_party/dolphin-libretro"
core_dir="$local_root/core"
system_dir="$local_root/runtime/system/dolphin-emu"
core_archive="$local_root/downloads/dolphin_libretro.so.zip"

if [[ ! -f "$source_dir/Externals/libretro-common/include/libretro.h" ]]; then
  echo "Missing Dolphin-libretro submodule. Run: git submodule update --init --recursive" >&2
  exit 1
fi

mkdir -p "$core_dir" "$local_root/downloads" "$system_dir"
if [[ ! -f "$core_dir/dolphin_libretro.so" ]]; then
  curl --fail --location --silent --show-error \
    --output "$core_archive" \
    https://buildbot.libretro.com/nightly/linux/x86_64/latest/dolphin_libretro.so.zip
  unzip -o "$core_archive" -d "$core_dir"
fi
if [[ ! -f "$system_dir/Sys/codehandler.bin" ]]; then
  cp -a "$source_dir/Data/Sys" "$system_dir/Sys"
fi

printf 'Dolphin-libretro source: '
git -C "$source_dir" rev-parse HEAD
sha256sum "$core_dir/dolphin_libretro.so"
