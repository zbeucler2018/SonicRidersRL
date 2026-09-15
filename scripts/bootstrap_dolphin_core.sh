#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
local_root="$project_root/.local"
source_dir="$local_root/upstream/dolphin"
core_dir="$local_root/core"
system_dir="$local_root/runtime/system/dolphin-emu"
core_archive="$local_root/downloads/dolphin_libretro.so.zip"

mkdir -p "$local_root/upstream" "$core_dir" "$local_root/downloads" "$system_dir"
if [[ ! -d "$source_dir/.git" ]]; then
  git clone --depth=1 https://github.com/libretro/dolphin.git "$source_dir"
fi
if [[ ! -f "$core_dir/dolphin_libretro.so" ]]; then
  curl --fail --location --silent --show-error \
    --output "$core_archive" \
    https://buildbot.libretro.com/nightly/linux/x86_64/latest/dolphin_libretro.so.zip
  unzip -o "$core_archive" -d "$core_dir"
fi
if [[ ! -f "$system_dir/Sys/codehandler.bin" ]]; then
  cp -a "$source_dir/Data/Sys" "$system_dir/Sys"
fi
sha256sum "$core_archive" "$core_dir/dolphin_libretro.so"
