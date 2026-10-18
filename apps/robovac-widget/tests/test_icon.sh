#!/bin/zsh
# test_icon — icon.py build draws its 16 and 32 px sizes from the small scene, and the rest from
# the option asked for (C1, C2); the icon's evening dimness is canvas.py's own, so a change to
# canvas.AMBIENT or canvas.FALLOFF reaches it (C3). It needs a Python with Playwright and Pillow, as
# requirements-dev.txt pins them: the one in $ROBOVAC_PY, or python3 when that
# is unset, as images.sh does.
# usage: [ROBOVAC_PY=<python>] test_icon.sh [widget dir]; exits 1 on a FAIL...
w=${1:-${0:a:h:h}}; tmp=$(mktemp -d); py=${ROBOVAC_PY:-python3}
cp -R $w $tmp/w; rm -rf $tmp/w/app/build $tmp/w/mac/build $tmp/w/screenshots
(cd $tmp/w && $py icon.py build sweeping >/dev/null 2>&1) || { echo "FAIL C0 icon.py build ran"; exit 1; }
iconutil -c iconset $tmp/w/mac/AppIcon.icns -o $tmp/set.iconset
$py - $tmp/set.iconset <<'PY'
import sys
from PIL import Image, ImageChops, ImageStat
d = sys.argv[1]
def diff(a, b):
    a = Image.open(f'{d}/{a}').convert('RGB'); b = Image.open(f'{d}/{b}').convert('RGB').resize(a.size, Image.LANCZOS)
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3
small, big = diff('icon_32x32@2x.png', 'icon_512x512@2x.png'), diff('icon_128x128.png', 'icon_512x512@2x.png')
ok1, ok2 = small > 8, big < 4
print(('PASS' if ok1 else 'FAIL'), f'C1 the 32 px art differs from the large art  [mean diff {small:.1f}]')
print(('PASS' if ok2 else 'FAIL'), f'C2 the 128 px art is the large art  [mean diff {big:.1f}]')
sys.exit(0 if ok1 and ok2 else 1)
PY
code=$?
(cd $tmp/w && $py - <<'PY'
import sys
import canvas, icon
canvas.AMBIENT, canvas.FALLOFF = '#123456', '#654321'
svg = icon.icon_svg('docked')
ok = '#123456' in svg and '#654321' in svg
print(('PASS' if ok else 'FAIL'), 'C3 the icon takes its evening dimness from canvas.AMBIENT and canvas.FALLOFF')
sys.exit(0 if ok else 1)
PY
) || code=1
rm -rf $tmp; exit $code
