#!/bin/sh
# demo — records the README's hero loop: a fresh copy of the app, centred on the screen, opens on a
# run already going in house 1's corner suite, its camera following the robot as it sweeps along the
# round dining table by the windows; the inside of the window is filmed and cut into a looping GIF.
# Turn notifications off before running it, or one may land in the film.
#
#   demo.sh [app]   records with ~/Applications/Robovac.app unless another bundle is named, and
#                   writes screenshots/robovac.gif, keeping the raw film as mac/build/demo-raw.mov

set -e
here=$(cd "$(dirname "$0")" && pwd)
app=${1:-$HOME/Applications/Robovac.app}
shots="$here/../screenshots"
work=$(mktemp -d)
log="$work/runs.jsonl"
bid=$(defaults read "$app/Contents/Info" CFBundleIdentifier)
pid=""
saved=""
wrote=""

# however the script ends, the app stops and, once it was changed, the window frame comes back...
restore() {
  if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; fi
  if [ -z "$wrote" ]; then
    rm -rf "$work"
    return
  fi
  if [ -n "$saved" ]; then
    defaults write "$bid" "NSWindow Frame RobovacWindow" "$saved"
  else
    defaults delete "$bid" "NSWindow Frame RobovacWindow" 2>/dev/null || true
  fi
  rm -rf "$work"
}
trap restore EXIT

# a run that began 92 s ago puts the robot at the dining table's edge as filming starts...
printf '{"session": "demo-a", "project": "demo", "event": "start", "t": %s}\n' \
  "$(($(date +%s) - 92))" > "$log"
mkdir -p "$shots"

# the window opens centred at 720 by 540, and the frame it had before comes back afterwards...
cat > "$work/screen.swift" <<'EOF'
import AppKit
let f = NSScreen.main!.frame
print(Int(f.width), Int(f.height))
EOF
set -- $(swift "$work/screen.swift")
saved=$(defaults read "$bid" "NSWindow Frame RobovacWindow" 2>/dev/null || true)
wrote=1
defaults write "$bid" "NSWindow Frame RobovacWindow" \
  "$((($1 - 720) / 2)) $((($2 - 540) / 2)) 720 540 0 0 $1 $2"

# the window's id and its frame in points, by the app's process...
cat > "$work/frame.swift" <<'EOF'
import CoreGraphics
let pid = Int(CommandLine.arguments[1])!
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as! [[String: Any]]
for w in list where (w[kCGWindowOwnerPID as String] as? Int) == pid && (w[kCGWindowLayer as String] as? Int) == 0 {
    let b = w[kCGWindowBounds as String] as! [String: Double]
    print(Int(b["X"]!), Int(b["Y"]!), Int(b["Width"]!), Int(b["Height"]!))
}
EOF
swiftc -O "$work/frame.swift" -o "$work/frame"

ROBOVAC_RUNS="$log" ROBOVAC_HOUSE=1 ROBOVAC_KEYS="0.3:ArrowRight" "$app/Contents/MacOS/Robovac" &
pid=$!
frame=""
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  frame=$("$work/frame" "$pid" | head -1)
  [ -n "$frame" ] && break
  sleep 0.25
done
[ -n "$frame" ] || { echo "demo: the window never showed" >&2; exit 1; }
set -- $frame
region="$(($1 + 16)),$(($2 + 32)),$(($3 - 32)),$(($4 - 48))"

# twelve seconds of the robot sweeping, once the camera has settled on it...
sleep 2
screencapture -v -V 12 -x -R "$region" "$work/raw.mov"

mkdir -p "$here/build"
cp "$work/raw.mov" "$here/build/demo-raw.mov"
ffmpeg -loglevel error -y -ss 1 -i "$work/raw.mov" -t 8 -filter_complex \
  "fps=12,scale=640:-2:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff:max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -loop 0 -final_delay 120 "$work/robovac.gif"

# the GIF replaces the old one only once it is whole...
mv "$work/robovac.gif" "$shots/robovac.gif"
ls -la "$shots/robovac.gif"
