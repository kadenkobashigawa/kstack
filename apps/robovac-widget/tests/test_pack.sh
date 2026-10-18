#!/bin/zsh
# test_pack — when build.sh fetches the image pack, and what images.sh fetch and publish leave
# behind. K1 to K4 and K12 decide when build.sh fetches. K5 and K6 download the pack, so they need the
# network; the rest stub what they call. K7 to K10: publish refuses a fetched pack, fetch a pack
# that fails its checksum, and publish images older than their generators or from a build that
# stopped partway. K11 runs build.sh through its install with the compiler stubbed, into a temp
# HOME, and unregisters what it installed. K13 holds that a failed release leaves nothing behind.
# K14 to K19 hold the key images.sh build and fetch record beside the images, and that current and
# publish compare it, so an edit with a backdated file time does not pass; they stub Python, curl and gh.
# K20 holds that every ROBOVAC_ variable the app reads has a runner in mac/demo.sh, K21 the usage text,
# K22 that images.sh lists every module widget.py build imports.
# usage: test_pack.sh [widget dir]; exits 1 on any FAIL...
w=${1:-${0:a:h:h}}; tmp=$(mktemp -d); fails=0; installed=""

# however the test ends, its temp folder goes, and so does any app K11 registered...
cleanup() { [ -n "$installed" ] && /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -u $installed 2>/dev/null; rm -rf $tmp; }
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
check() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1  [got $2, want $3]"; fails=1; fi }
mkdir -p $tmp/bin; printf '#!/bin/sh\nexit 9\n' > $tmp/bin/swiftc; chmod +x $tmp/bin/swiftc
# the files whose content decides what widget.py build draws, as images.sh lists them (K22 holds the list whole)...
gens=(pen.py canvas.py furniture.py decor.py vacuum.py planks.py rules.py layout.py furnish.py plans.py widget.py pins.json)
copy() { rm -rf $tmp/w; mkdir -p $tmp/w/mac $tmp/w/app; for f in $gens; do cp $w/$f $tmp/w/; done; cp $w/mac/{build.sh,images.sh,images.lock} $tmp/w/mac/; }
decide() {
  copy; mv $tmp/w/mac/images.sh $tmp/w/mac/images-real.sh
  printf '#!/bin/sh\n[ "$1" = fetch ] && exit 7\nexec sh "$(dirname "$0")/images-real.sh" "$@"\n' > $tmp/w/mac/images.sh
  case $1 in
    none) ;;
    same) mkdir -p $tmp/w/app/build; touch $tmp/w/app/build/data.js; cut -d' ' -f1 $tmp/w/mac/images.lock > $tmp/w/app/build/.pack ;;
    old)  mkdir -p $tmp/w/app/build; touch $tmp/w/app/build/data.js; echo robovac-images-000000000000 > $tmp/w/app/build/.pack ;;
    local) mkdir -p $tmp/w/app/build; touch $tmp/w/app/build/data.js ;;
    stale) mkdir -p $tmp/w/app/build; touch -t 202001010000 $tmp/w/app/build/data.js ;;
  esac
  HOME=$tmp PATH=$tmp/bin:$PATH sh $tmp/w/mac/build.sh >/dev/null 2>&1; code=$?
  [ $code = 7 ] && echo fetched || { [ $code = 9 ] && echo kept || echo "exit $code"; }
}
check 'K1 no images: fetched' "$(decide none)" fetched
check 'K2 the locked pack: kept' "$(decide same)" kept
check 'K3 an older pack: fetched' "$(decide old)" fetched
check 'K4 a local build: kept' "$(decide local)" kept
check 'K12 a local build older than the files that draw it: fetched' "$(decide stale)" fetched

# the real fetch leaves the pack's name beside it...
copy; [ -n "$IMAGES_SH" ] && cp $IMAGES_SH $tmp/w/mac/images.sh
sh $tmp/w/mac/images.sh fetch >/dev/null 2>&1
check 'K5 fetch writes the images' "$([ -f $tmp/w/app/build/data.js ] && echo yes)" yes
check 'K6 fetch records the pack it is' "$(cat $tmp/w/app/build/.pack 2>/dev/null)" "$(cut -d' ' -f1 $tmp/w/mac/images.lock)"

# publish, with gh stubbed, refuses a fetched pack, which is published already...
copy; mkdir -p $tmp/w/app/build; echo fetched > $tmp/w/app/build/data.js; echo robovac-images-x > $tmp/w/app/build/.pack
printf '#!/bin/sh\nexit 0\n' > $tmp/bin/gh; chmod +x $tmp/bin/gh
PATH=$tmp/bin:$PATH sh $tmp/w/mac/images.sh publish >/dev/null 2>&1; code=$?
check 'K7 publish refuses a fetched pack' "$code $(cut -d' ' -f1 $tmp/w/mac/images.lock)" "1 $(cut -d' ' -f1 $w/mac/images.lock)"
# a pack whose checksum is not the lock's is refused, and the images there stay...
copy; mkdir -p $tmp/w/app/build $tmp/bad/build; echo keep > $tmp/w/app/build/data.js
key=$(cd $tmp/w && cat $gens | shasum -a 256 | cut -c1-12)
echo tampered > $tmp/bad/build/data.js; tar -czf $tmp/bad.tar.gz -C $tmp/bad build
echo "robovac-images-$key $(printf '0%.0s' {1..64})" > $tmp/w/mac/images.lock
printf '#!/bin/sh\nwhile [ "$1" != -o ]; do shift; done\ncp %s "$2"\n' $tmp/bad.tar.gz > $tmp/bin/curl; chmod +x $tmp/bin/curl
PATH=$tmp/bin:$PATH sh $tmp/w/mac/images.sh fetch >/dev/null 2>&1; code=$?
check 'K8 a pack that fails its checksum is refused, the images there stay, and its download goes' "$code $(cat $tmp/w/app/build/data.js) $(find $tmp/w/mac/build -maxdepth 1 -name "fetch.*" 2>/dev/null | wc -l | tr -d ' ')" "1 keep 0"

# publish refuses images older than a generator file...
copy; mkdir -p $tmp/w/app/build; touch -t 202001010000 $tmp/w/app/build/data.js
printf '#!/bin/sh\nexit 0\n' > $tmp/bin/gh; chmod +x $tmp/bin/gh
PATH=$tmp/bin:$PATH sh $tmp/w/mac/images.sh publish >/dev/null 2>&1; code=$?
check 'K9 publish refuses images older than the files that draw them' "$code $([ -e $tmp/w/app/build/.pack ] && echo marked || echo none)" "1 none"
# and refuses a build that stopped partway: an image newer than its data.js...
copy; mkdir -p $tmp/w/app/build; echo built > $tmp/w/app/build/data.js; sleep 1; echo half > $tmp/w/app/build/x.png
PATH=$tmp/bin:$PATH sh $tmp/w/mac/images.sh publish >/dev/null 2>&1; code=$?
check 'K10 publish refuses a build that stopped partway' "$code $(cut -d' ' -f1 $tmp/w/mac/images.lock)" "1 $(cut -d' ' -f1 $w/mac/images.lock)"
# a release that fails leaves the lock as it was and no pack behind...
copy; mkdir -p $tmp/w/app/build; echo built > $tmp/w/app/build/data.js
printf '#!/bin/sh\nexit 1\n' > $tmp/bin/gh; chmod +x $tmp/bin/gh
PATH=$tmp/bin:$PATH sh $tmp/w/mac/images.sh publish >/dev/null 2>&1; code=$?
check 'K13 a failed release keeps the lock and leaves no pack behind' "$code $(cut -d' ' -f1 $tmp/w/mac/images.lock) $(find $tmp/w/mac/build -maxdepth 1 -name "publish.*" 2>/dev/null | wc -l | tr -d ' ')" "1 $(cut -d' ' -f1 $w/mac/images.lock) 0"
# images.sh build, with Python stubbed to draw one file, records the key of the files that drew it;
# a build that fails records none, and one that failed after an earlier good build clears the old...
copy; rm -rf $tmp/stub; mkdir $tmp/stub
printf '#!/bin/sh\nmkdir -p "$3/build"\necho built > "$3/build/data.js"\n' > $tmp/stub/py
printf '#!/bin/sh\nexit 1\n' > $tmp/stub/bad; chmod +x $tmp/stub/py $tmp/stub/bad
key=$(cd $tmp/w && cat $gens | shasum -a 256 | cut -c1-12)
ROBOVAC_PY=$tmp/stub/py sh $tmp/w/mac/images.sh build >/dev/null 2>&1; code=$?
check 'K14 build draws the images and records the key of the files that drew them' "$code $(cat $tmp/w/app/build/.key 2>/dev/null)" "0 $key"
ROBOVAC_PY=$tmp/stub/bad sh $tmp/w/mac/images.sh build >/dev/null 2>&1; code=$?
check 'K15 a build that fails leaves no key beside its images' "$code $([ -e $tmp/w/app/build/.key ] && echo kept || echo none)" "1 none"
# a backdated edit to a generator file makes the build not current, and publish refuses it...
ROBOVAC_PY=$tmp/stub/py sh $tmp/w/mac/images.sh build >/dev/null 2>&1
sh $tmp/w/mac/images.sh current; same=$?
echo '# edited' >> $tmp/w/pen.py; touch -t 202001010000 $tmp/w/pen.py
sh $tmp/w/mac/images.sh current; edited=$?
printf '#!/bin/sh\nexit 0\n' > $tmp/bin/gh; chmod +x $tmp/bin/gh
PATH=$tmp/bin:$PATH sh $tmp/w/mac/images.sh publish >/dev/null 2>&1; code=$?
check 'K16 a backdated edit to a generator file is not current, and publish refuses it' "$same $edited $code $(cut -d' ' -f1 $tmp/w/mac/images.lock)" "0 1 1 $(cut -d' ' -f1 $w/mac/images.lock)"
# publish takes a build images.sh made, with the key beside its images...
copy; ROBOVAC_PY=$tmp/stub/py sh $tmp/w/mac/images.sh build >/dev/null 2>&1
key=$(cd $tmp/w && cat $gens | shasum -a 256 | cut -c1-12)
PATH=$tmp/bin:$PATH sh $tmp/w/mac/images.sh publish >/dev/null 2>&1; code=$?
check 'K17 publish takes a build whose key is the files that draw it' "$code $(cut -d' ' -f1 $tmp/w/mac/images.lock)" "0 robovac-images-$key"
# a key older than its images is a build made some other way, so the files' times decide...
copy; ROBOVAC_PY=$tmp/stub/py sh $tmp/w/mac/images.sh build >/dev/null 2>&1; echo robovac-images-0 > $tmp/w/app/build/.key
touch -t 202001010000 $tmp/w/app/build/.key
sh $tmp/w/mac/images.sh current; kept=$?
touch $tmp/w/pen.py; sleep 1; touch $tmp/w/pen.py; sh $tmp/w/mac/images.sh current; newer=$?
check 'K18 a key older than the images it sits beside is ignored, and the files own times decide' "$kept $newer" "0 1"
# fetch records the key beside the pack's name...
copy; mkdir -p $tmp/good/build; echo pack > $tmp/good/build/data.js; tar -czf $tmp/good.tar.gz -C $tmp/good build
key=$(cd $tmp/w && cat $gens | shasum -a 256 | cut -c1-12)
echo "robovac-images-$key $(shasum -a 256 $tmp/good.tar.gz | cut -d' ' -f1)" > $tmp/w/mac/images.lock
printf '#!/bin/sh\nwhile [ "$1" != -o ]; do shift; done\ncp %s "$2"\n' $tmp/good.tar.gz > $tmp/bin/curl; chmod +x $tmp/bin/curl
PATH=$tmp/bin:$PATH sh $tmp/w/mac/images.sh fetch >/dev/null 2>&1; code=$?
check 'K19 fetch records the key beside the pack it unpacks' "$code $(cat $tmp/w/app/build/.key 2>/dev/null)" "0 $key"
# every ROBOVAC_ variable the app reads has a runner in mac/demo.sh, so none sits unused...
unrun=""; for v in $(grep -o 'ROBOVAC_[A-Z_]*' $w/mac/Robovac.swift | sort -u); do grep -q "$v" $w/mac/demo.sh || unrun="$unrun $v"; done
check 'K20 every ROBOVAC_ variable Robovac.swift reads is set by mac/demo.sh' "${unrun:-none}" none
# the usage text names every command, build as the maintainer's, and exits 2...
copy; usage=$(sh $tmp/w/mac/images.sh 2>&1); code=$?
check 'K21 images.sh with no command prints all four commands, build marked for the maintainer, and exits 2' "$code $(printf '%s\n' "$usage" | grep -c "images.sh \(current\|fetch\|build\|publish\) ") $(printf '%s\n' "$usage" | grep -c "maintainer's command")" "2 4 1"
# build.sh, with the compiler and signer stubbed, leaves one app: the one it installs into HOME...
rm -rf $tmp/b; mkdir -p $tmp/b/w/mac/build/Robovac.app $tmp/b/home $tmp/b/bin
rsync -a --exclude build $w/app/ $tmp/b/w/app/; cp $w/mac/{build.sh,images.sh,images.lock,Info.plist,AppIcon.icns} $tmp/b/w/mac/
plutil -replace CFBundleIdentifier -string com.kstack.robovac-test-pack $tmp/b/w/mac/Info.plist
installed=$tmp/b/home/Applications/Robovac.app
mkdir -p $tmp/b/w/app/build; echo stub > $tmp/b/w/app/build/data.js; cut -d' ' -f1 $w/mac/images.lock > $tmp/b/w/app/build/.pack
printf '#!/bin/sh\nwhile [ "$1" != -o ]; do shift; done\ntouch "$2"\n' > $tmp/b/bin/swiftc
printf '#!/bin/sh\nexit 0\n' > $tmp/b/bin/codesign; chmod +x $tmp/b/bin/*
HOME=$tmp/b/home PATH=$tmp/b/bin:$PATH sh $tmp/b/w/mac/build.sh >/dev/null 2>&1; code=$?
check 'K11 build.sh installs one app and leaves no copy beside it' "$code $([ -d $installed ] && echo installed) $([ -e $tmp/b/w/mac/build/Robovac.app ] && echo leftover || echo clean)" "0 installed clean"
# the generator list holds every module widget.py build imports, through furnish and plans, and pins.json:
# a module left off it could change the images without changing their name...
missing=$(python3 - $w <<'PY'
import ast, re, sys
from pathlib import Path
w = Path(sys.argv[1])
listed = set(re.search(r'^generators="([^"]*)"', (w / 'mac/images.sh').read_text(), re.M).group(1).split())
todo, seen = ['widget'], set()
while todo:
    name = todo.pop()
    if name in seen or not (w / f'{name}.py').exists():
        continue
    seen.add(name)
    for node in ast.walk(ast.parse((w / f'{name}.py').read_text())):
        if isinstance(node, ast.Import):
            todo += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            todo.append(node.module)
print(' '.join(sorted(({f'{n}.py' for n in seen} | {'pins.json'}) ^ listed)) or 'none')
PY
)
check 'K22 images.sh lists every module widget.py build imports, and pins.json, and no other file' "$missing" none
exit $fails
