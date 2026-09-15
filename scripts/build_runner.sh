#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
libretro_include="$project_root/.local/upstream/dolphin/Externals/libretro-common/include"
output_dir="$project_root/build"

if [[ ! -f "$libretro_include/libretro.h" ]]; then
  echo "Missing $libretro_include/libretro.h. Run scripts/bootstrap_dolphin_core.sh first." >&2
  exit 1
fi

mkdir -p "$output_dir"
g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -pthread \
  -I"$libretro_include" \
  "$project_root/runner/sonic_libretro_runner.cpp" \
  -ldl \
  -o "$output_dir/sonic-libretro-runner"
