#!/usr/bin/env bash
# setup_blender.sh — install a working headless Blender + the repo's Python helpers.
#
# Designed for sandboxes: no root required, no display required, no package manager
# required (it falls back to downloading .deb files and unpacking them locally when
# shared libraries are missing).
#
#   bash tools/setup_blender.sh                    # install to ~/.local/blender
#   BLENDER_VERSION=4.5.3 bash tools/setup_blender.sh
#   BLENDER_PREFIX=/opt/blender bash tools/setup_blender.sh   (needs write access)
#
# When it finishes it prints the two lines to add to your shell, and writes
# <prefix>/activate.sh so later steps can just `source` it.
#
# Exit codes: 0 = blender works, 1 = installation failed (read the message; it tells
# you the next thing to try). Never conclude "there is no Blender in this sandbox"
# before running this script.

set -uo pipefail

VERSION="${BLENDER_VERSION:-4.2.23}"
CHANNEL="${BLENDER_CHANNEL:-Blender4.2}"
PREFIX="${BLENDER_PREFIX:-$HOME/.local/blender}"
CACHE="${BLENDER_CACHE:-$HOME/.cache/3dmodels}"
WORK="$PREFIX/blender-$VERSION-linux-x64"
BIN="$WORK/blender"
DEPS="$PREFIX/deps"

say()  { printf '\033[1m[setup]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[setup] WARNING:\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[setup] FAILED:\033[0m %s\n' "$*" >&2; exit 1; }

# --------------------------------------------------------------------------- #
# 0. Already installed?
# --------------------------------------------------------------------------- #
if command -v blender >/dev/null 2>&1; then
  if blender --version >/dev/null 2>&1; then
    say "blender already available: $(blender --version | head -1) ($(command -v blender))"
    exit 0
  fi
  warn "a 'blender' binary is on PATH but it does not run; installing a private copy instead"
fi

say "installing Blender $VERSION into $PREFIX (no root needed)"

mkdir -p "$PREFIX" "$CACHE" || die "cannot create $PREFIX / $CACHE (check permissions / disk space)"
FREE_KB=$(df -Pk "$PREFIX" | awk 'NR==2 {print $4}')
if [ "${FREE_KB:-0}" -lt 2000000 ]; then
  warn "only $((FREE_KB/1024)) MB free at $PREFIX; Blender needs ~1.5 GB unpacked"
fi

# --------------------------------------------------------------------------- #
# 1. Download (with a couple of mirrors / versions to try)
# --------------------------------------------------------------------------- #
TARBALL="$CACHE/blender-$VERSION-linux-x64.tar.xz"
if [ ! -s "$TARBALL" ]; then
  URLS=(
    "https://download.blender.org/release/$CHANNEL/blender-$VERSION-linux-x64.tar.xz"
    "https://mirror.clarkson.edu/blender/release/$CHANNEL/blender-$VERSION-linux-x64.tar.xz"
    "https://ftp.nluug.nl/pub/graphics/blender/release/$CHANNEL/blender-$VERSION-linux-x64.tar.xz"
  )
  ok=0
  for url in "${URLS[@]}"; do
    say "downloading $url"
    if command -v curl >/dev/null 2>&1; then
      curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -o "$TARBALL.part" "$url" && ok=1
    elif command -v wget >/dev/null 2>&1; then
      wget -q --tries=3 --timeout=20 -O "$TARBALL.part" "$url" && ok=1
    else
      die "neither curl nor wget is available; cannot download Blender"
    fi
    if [ "$ok" = "1" ]; then mv "$TARBALL.part" "$TARBALL"; break; fi
    warn "download failed from this mirror, trying the next"
  done
  [ "$ok" = "1" ] || die "could not download Blender from any mirror.
  If the network is restricted, try: pip download bpy (needs Python 3.11),
  or use any DCC you do have, and record the toolchain in the package README."
else
  say "using cached tarball $TARBALL"
fi

# --------------------------------------------------------------------------- #
# 2. Extract
# --------------------------------------------------------------------------- #
if [ ! -x "$BIN" ]; then
  say "extracting to $PREFIX (this takes ~20 s)"
  # note: do NOT unpack into /tmp — it is often a small tmpfs and the extract will
  # fill it and fail with 'No space left on device'
  tar -xf "$TARBALL" -C "$PREFIX" || die "extraction failed (out of disk space?)"
fi
[ -x "$BIN" ] || die "expected $BIN after extraction; the archive layout may have changed"

# --------------------------------------------------------------------------- #
# 3. Shared libraries (the usual sandbox blocker)
# --------------------------------------------------------------------------- #
# map "missing soname" -> "debian package that provides it"
pkg_for() {
  case "$1" in
    libxkbcommon.so.0)        echo libxkbcommon0 ;;
    libxkbcommon-x11.so.0)    echo libxkbcommon-x11-0 ;;
    libX11.so.6)              echo libx11-6 ;;
    libXext.so.6)             echo libxext6 ;;
    libXrender.so.1)          echo libxrender1 ;;
    libXfixes.so.3)           echo libxfixes3 ;;
    libXi.so.6)               echo libxi6 ;;
    libXxf86vm.so.1)          echo libxxf86vm1 ;;
    libXinerama.so.1)         echo libxinerama1 ;;
    libXrandr.so.2)           echo libxrandr2 ;;
    libXcursor.so.1)          echo libxcursor1 ;;
    libSM.so.6)               echo libsm6 ;;
    libICE.so.6)              echo libice6 ;;
    libGL.so.1)               echo libgl1 ;;
    libEGL.so.1)              echo libegl1 ;;
    libGLU.so.1)              echo libglu1-mesa ;;
    libgomp.so.1)             echo libgomp1 ;;
    libstdc++.so.6)           echo libstdc++6 ;;
    libxcb.so.1)              echo libxcb1 ;;
    libxcb-*.so.*)            echo libxcb1 ;;
    libXau.so.6)              echo libxau6 ;;
    libXdmcp.so.6)            echo libxdmcp6 ;;
    *) echo "" ;;
  esac
}

resolve_libs() {
  local round=0 missing pkgs pkg got=0
  while [ "$round" -lt 4 ]; do
    missing=$(LD_LIBRARY_PATH="$DEPS/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}" \
              ldd "$BIN" 2>/dev/null | awk '/not found/ {print $1}' | sort -u)
    [ -z "$missing" ] && { [ "$got" = "0" ] && say "all shared libraries present"; return 0; }
    pkgs=""
    for soname in $missing; do
      pkg=$(pkg_for "$soname")
      if [ -n "$pkg" ]; then pkgs="$pkgs $pkg"; else warn "no known package for $soname"; fi
    done
    [ -z "${pkgs// /}" ] && return 1
    say "fetching missing libraries:$(echo "$pkgs" | tr ' ' '\n' | sort -u | tr '\n' ' ')"
    mkdir -p "$CACHE/debs"
    ( cd "$CACHE/debs" && apt-get download $pkgs >/dev/null 2>&1 ) || {
      warn "apt-get download failed (no apt or no network access to the distro archive)"; return 1; }
    for deb in "$CACHE"/debs/*.deb; do
      [ -e "$deb" ] || continue
      dpkg-deb -x "$deb" "$DEPS" 2>/dev/null || warn "could not unpack $deb"
    done
    round=$((round + 1)); got=1
  done
  missing=$(LD_LIBRARY_PATH="$DEPS/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}" \
            ldd "$BIN" 2>/dev/null | awk '/not found/ {print $1}' | sort -u)
  [ -z "$missing" ] && return 0
  warn "still missing: $missing"
  return 1
}

mkdir -p "$DEPS"
if ! resolve_libs; then
  warn "some libraries are still missing. Options:
  - on Debian/Ubuntu with root:  sudo apt-get install -y libxkbcommon0 libgl1 libxi6 libxrender1 libxext6 libsm6 libice6 libgomp1
  - without root: this script's apt-get download path already tried that;
    if it failed, check network access to the distro mirror, or add the missing
    sonames to the pkg_for() map above and re-run."
fi

# --------------------------------------------------------------------------- #
# 4. Activation script + verification
# --------------------------------------------------------------------------- #
cat > "$PREFIX/activate.sh" <<EOF
# source this to use the Blender installed by tools/setup_blender.sh
export BLENDER_HOME="$WORK"
export LD_LIBRARY_PATH="$DEPS/usr/lib/x86_64-linux-gnu:$DEPS/usr/lib/x86_64-linux-gnu/blender:\${LD_LIBRARY_PATH:-}"
export PATH="$WORK:\$PATH"
EOF
# shellcheck disable=SC1090
source "$PREFIX/activate.sh"

if ! "$BIN" --version >/dev/null 2>&1; then
  die "Blender still does not run. Last error:
$(LD_LIBRARY_PATH="$LD_LIBRARY_PATH" "$BIN" --version 2>&1 | head -3)
Report this exact message instead of giving up: the fix is usually one more library
in pkg_for()."
fi

say "OK — $("$BIN" --version | head -1)"

# --------------------------------------------------------------------------- #
# 5. Python helpers used by the repo tools
# --------------------------------------------------------------------------- #
say "checking Python helpers (optional, tools degrade gracefully without them)"
if command -v python3 >/dev/null 2>&1; then
  for mod in numpy PIL; do
    if python3 -c "import $mod" >/dev/null 2>&1; then
      say "  python3 -c 'import $mod' -> ok"
    else
      pip_ok=0
      for flags in "" "--break-system-packages" "--user --break-system-packages"; do
        # shellcheck disable=SC2086
        if python3 -m pip install --quiet $flags $( [ "$mod" = "PIL" ] && echo pillow || echo numpy ) >/dev/null 2>&1; then
          pip_ok=1; break
        fi
      done
      [ "$pip_ok" = "1" ] && say "  installed $mod" \
        || warn "  could not pip install $mod — tools will skip the checks that need it (numpy ships inside Blender anyway)"
    fi
  done
else
  warn "no python3 on PATH; the repo tools need it (python3 -V to check)"
fi

say "Blender ships its own numpy; the render rig works without any pip install."
cat <<EOF

Add this to your shell (or prefix every command with it):

    source $PREFIX/activate.sh

Then verify the whole chain:

    blender --version
    blender -b --factory-startup --python-expr "import bpy; print('bpy', bpy.app.version_string)"

Render the required set for a package:

    blender -b model/<name>.blend --python tools/render_rig.py -- --res 1600 --samples 96 --out renders
EOF
