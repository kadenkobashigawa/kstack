#!/bin/sh
# images — the house's generated images (app/build), shipped as one pack on a kstack GitHub release
# so a user's build needs no Python or Playwright. The pack is named for a hash of the files that
# generate it, and images.lock holds that name with the pack's own checksum. app/build/.key holds
# that hash for the files the images were drawn from.
#
#   images.sh current   exit 0 when app/build may stand: the fetched pack images.lock names, or a
#                       build whose .key is these generator files', or, with no .key, a local build
#                       no generator file is newer than
#   images.sh fetch     download and check the pack these generator files make, into app/build
#   images.sh build     the maintainer's command: widget.py build app with the Python in $ROBOVAC_PY
#                       (python3 unless set; it needs Playwright and Pillow), then write .key
#   images.sh publish   pack app/build, release it, and write images.lock (the maintainer, after
#                       images.sh build)

set -e
here=$(cd "$(dirname "$0")" && pwd)
widget="$here/.."
lock="$here/images.lock"

# the files whose content decides what widget.py build draws: the modules it imports, through furnish
# and plans, and the pinned rooms (tests/test_pack.sh K22 holds the list whole)...
generators="pen.py canvas.py furniture.py decor.py vacuum.py planks.py rules.py layout.py furnish.py plans.py widget.py pins.json"
key=$(cd "$widget" && cat $generators | shasum -a 256 | cut -c1-12)
name="robovac-images-$key"

# the first generator file newer than app/build's data.js, which a build writes last...
newer() {
  for f in $generators; do
    if [ "$widget/$f" -nt "$widget/app/build/data.js" ]; then
      echo "$f"
      return
    fi
  done
}

# the key recorded beside the images, when it is as new as they are: widget.py build run on its
# own leaves an older key behind, and that one says nothing about these images...
recorded() {
  if [ -f "$widget/app/build/.key" ] && ! [ "$widget/app/build/data.js" -nt "$widget/app/build/.key" ]; then
    cat "$widget/app/build/.key"
  fi
}

case "$1" in
current)
  [ -f "$widget/app/build/data.js" ] || exit 1
  if [ -f "$widget/app/build/.pack" ]; then
    [ "$(cat "$widget/app/build/.pack")" = "$(cut -d' ' -f1 "$lock")" ]
    exit
  fi
  if [ -n "$(recorded)" ]; then
    [ "$(recorded)" = "$key" ]
    exit
  fi
  [ -z "$(newer)" ]
  ;;
build)
  # the old key goes first, so a build that stops partway leaves no key behind...
  rm -f "$widget/app/build/.key"
  "${ROBOVAC_PY:-python3}" "$widget/widget.py" build "$widget/app"
  echo "$key" > "$widget/app/build/.key"
  echo "images: built $name"
  ;;
fetch)
  [ -f "$lock" ] || { echo "images: no images.lock; run images.sh build, then images.sh publish" >&2; exit 1; }
  read -r locked sum < "$lock"
  if [ "$locked" != "$name" ]; then
    echo "images: no published pack matches these generator files yet ($name); a maintainer runs" \
      "images.sh build, then images.sh publish" >&2
    exit 1
  fi
  # the download unpacks beside app/build, on its volume, so the swap below is a rename...
  mkdir -p "$here/build"
  tmp=$(mktemp -d "$here/build/fetch.XXXXXX")
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL -o "$tmp/$name.tar.gz" "https://github.com/kadenkobashigawa/kstack/releases/download/$name/$name.tar.gz" ||
    { echo "images: could not download $name.tar.gz" >&2; exit 1; }
  echo "$sum  $tmp/$name.tar.gz" | shasum -a 256 -c - >/dev/null ||
    { echo "images: $name.tar.gz does not match images.lock's checksum" >&2; exit 1; }

  # unpacked aside with its name beside it, then swapped in whole, so build.sh never keeps half...
  tar -xzf "$tmp/$name.tar.gz" -C "$tmp"
  echo "$name" > "$tmp/build/.pack"
  echo "$key" > "$tmp/build/.key"
  [ -d "$widget/app/build" ] && mv "$widget/app/build" "$tmp/old"
  mv "$tmp/build" "$widget/app/build"
  echo "images: $name"
  ;;
publish)
  [ -f "$widget/app/build/data.js" ] || { echo "images: no app/build; run images.sh build" >&2; exit 1; }

  # a fetched pack is already published, and a pack is named for its generator files, so a build
  # drawn from other ones, by its key or, with none, by file times, is refused...
  if [ -f "$widget/app/build/.pack" ]; then
    echo "images: app/build is the fetched pack $(cat "$widget/app/build/.pack"); run images.sh build" >&2
    exit 1
  fi
  if [ -n "$(recorded)" ]; then
    if [ "$(recorded)" != "$key" ]; then
      echo "images: app/build was drawn from other generator files ($(recorded), now $key); run images.sh build first" >&2
      exit 1
    fi
  else
    stale=$(newer)
    if [ -n "$stale" ]; then
      echo "images: $stale is newer than app/build; run images.sh build first" >&2
      exit 1
    fi
  fi

  # widget.py writes data.js last, so an image newer than it is a build that stopped partway...
  if [ -n "$(find "$widget/app/build" -type f ! -name .pack ! -name .key ! -name .DS_Store \
      -newer "$widget/app/build/data.js" | head -1)" ]; then
    echo "images: app/build holds images newer than its data.js, a build that stopped; run it again" >&2
    exit 1
  fi
  mkdir -p "$here/build"
  tmp=$(mktemp -d "$here/build/publish.XXXXXX")
  trap 'rm -rf "$tmp"' EXIT
  tar -czf "$tmp/$name.tar.gz" -C "$widget/app" build
  sum=$(shasum -a 256 "$tmp/$name.tar.gz" | cut -d' ' -f1)
  gh release create "$name" "$tmp/$name.tar.gz" --repo kadenkobashigawa/kstack \
    --title "Robovac images $key" --notes "The house images for the Robovac app, fetched by mac/build.sh."
  echo "$name $sum" > "$lock"
  echo "images: published $name"
  ;;
*)
  sed -n '2,14p' "$0"
  exit 2
  ;;
esac
