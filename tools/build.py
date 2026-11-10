#!/usr/bin/env python3
"""Build the Ultima III images from src/ with the original tools and compare them with GOG's.

    python3 tools/build.py [TARGET ...] [--out DIR]     TARGET: ultima, bootup, exodus, dungeon (default all)

For each target, src/TARGET/NAME.lnk lists the modules in link order. Each is assembled with
MASM 4.00 (ASM=MASM3 in the environment for MASM 3.00: same bytes), the objects are linked
with LINK 3.05 into an EXE whose load image starts with the 0100 bytes ORG 100h leaves free,
and the file is that image from offset 0100 (what DOS EXE2BIN would write for a COM program).
The result goes to build/TARGET/ (ULTIMA.COM, BOOTUP.BIN, EXODUS.BIN) and its sha1 is checked
against the GOG release. Exit status 0 when every target is identical.

As a module: build(target, out) -> path of the built file (exits with status 2 on errors).
"""
import hashlib, os, re, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'src')
sys.path.insert(0, HERE)
import dos, u3an

MASM = 'D:\\%s\\MASM' % os.environ.get('ASM', 'MASM4')
LINK = 'D:\\MASM4\\LINK'


def build(target, out):
    t = u3an.TARGETS[target]
    name = os.path.splitext(t['file'])[0]
    srcdir = os.path.join(SRC, target)
    mods = [l.split(';')[0].strip() for l in open(os.path.join(srcdir, name + '.lnk'))]
    mods = [m for m in mods if m]
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for f in os.listdir(srcdir):               # modules and include files
        if f.upper().endswith(('.ASM', '.INC')):
            shutil.copy(os.path.join(srcdir, f), os.path.join(out, f.upper()))
    for f in os.listdir(SRC):                  # shared include files
        if f.upper().endswith('.INC'):
            shutil.copy(os.path.join(SRC, f), os.path.join(out, f.upper()))
    stems = [os.path.splitext(m)[0].upper() for m in mods]
    cmds = ['%s %s.ASM,%s.OBJ,NUL; >> BUILD.LOG' % (MASM, s, s) for s in stems]
    open(os.path.join(out, 'LINK.RSP'), 'w', newline='').write(
        '+\r\n'.join(stems) + '\r\n%s\r\n%s/M\r\n;\r\n' % (name, name))
    cmds.append('IF EXIST %s.OBJ %s @LINK.RSP >> BUILD.LOG' % (stems[-1], LINK))
    dos.run(out, cmds)

    log = open(os.path.join(out, 'BUILD.LOG'), 'rb').read().decode('latin1').replace('\r', '')
    bad = []
    for l in log.split('\n'):
        m = re.match(r'^\s*(\d+)\s+(Warning|Severe)', l)    # MASM 4: "0 Warning Errors"
        m3 = re.match(r'^\s*(\d+)\s+(\d+)\s*$', l)          # MASM 3: "0 0" under the headings
        if (m and int(m.group(1))) or (m3 and int(m3.group(1)) + int(m3.group(2))) or re.search(
                r'Error \d|error L|Unresolved|Undefined|more than once|Out of Memory', l, re.I):
            bad.append(l)
    for s in stems:
        if not os.path.exists(os.path.join(out, s + '.OBJ')):
            bad.append('no object for ' + s)
    exe = os.path.join(out, name + '.EXE')
    if not os.path.exists(exe) or bad:
        print(log)
        print('\n'.join(bad))
        sys.exit(2)
    data = open(exe, 'rb').read()
    h = struct.unpack('<14H', data[:28])
    img = data[h[4] * 16:]
    if any(img[:0x100]):
        sys.exit('%s: the image has bytes below 0100' % target)
    path = os.path.join(out, t['file'])
    open(path, 'wb').write(img[0x100:])
    return path


def main():
    args = sys.argv[1:]
    out_root = os.path.join(ROOT, 'build')
    if '--out' in args:
        i = args.index('--out')
        out_root = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    targets = args or ['ultima', 'bootup', 'exodus', 'dungeon']
    ok = True
    for target in targets:
        t = u3an.TARGETS[target]
        path = build(target, os.path.join(out_root, target))
        data = open(path, 'rb').read()
        h = hashlib.sha1(data).hexdigest()
        same = h == t['sha1']
        ok &= same
        print('%-10s %6d bytes sha1 %s  %s' % (t['file'], len(data), h,
                                                'IDENTICAL' if same else 'DIFFERS from %s' % t['sha1']))
        if not same:
            orig = open(os.path.join(u3an.GAMEDATA, t['file']), 'rb').read()
            diffs = [i for i in range(min(len(orig), len(data))) if orig[i] != data[i]]
            print('  %d bytes differ, first at %s; sizes %d vs %d' % (
                len(diffs), ', '.join('%04X' % (d + 0x100) for d in diffs[:8]), len(data), len(orig)))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
