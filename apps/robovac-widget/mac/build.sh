#!/bin/sh
# build — compiles the app, bundles the house page and the icon in a temporary folder, and installs
# it as ~/Applications/Robovac.app, the only copy, so Spotlight and Launchpad list one Robovac. The
# house images come from the release pack images.sh fetches whenever app/build is not current;
# images.sh build remakes them.

set -e
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
app="$work/Robovac.app"
installed="$HOME/Applications/Robovac.app"

# images a pull has outdated, fetched or local, are fetched over; a local build newer than its
# generator files is kept...
sh "$here/images.sh" current || sh "$here/images.sh" fetch

# a copy an older build.sh left beside this script goes, so Spotlight lists one Robovac...
rm -rf "$here/build/Robovac.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
swiftc -O -swift-version 5 -parse-as-library -framework Cocoa -framework WebKit \
  "$here/Robovac.swift" "$here/Runs.swift" -o "$app/Contents/MacOS/Robovac"
cp "$here/Info.plist" "$app/Contents/Info.plist"
cp "$here/AppIcon.icns" "$app/Contents/Resources/AppIcon.icns"
rsync -a --delete --exclude '*.svg' "$here/../app/" "$app/Contents/Resources/app/"
codesign --force --sign - "$app" >/dev/null

# replace the installed copy whole and tell Launch Services, so Spotlight and the Dock see the icon...
mkdir -p "$HOME/Applications"
rm -rf "$installed"
ditto "$app" "$installed"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$installed"
echo "$installed"
