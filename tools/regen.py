#!/usr/bin/env python3
"""Re-derive one image's source from the original: gen.py -> MASM (with listings) -> LINK ->
compare the image with the original, and repeat, adding every instruction that assembles
differently to the force file (written as db), until the image is identical.

    python3 tools/regen.py TARGET [WORKDIR] [MASM4|MASM3]      (ITER env: max iterations, 40)

TARGET is ultima, bootup or exodus; TARGETS[TARGET]['limit'] in tools/u3an.py splits a large
image into modules (MASM runs out of memory on EXODUS.BIN as one). WORKDIR defaults to
build/regen/TARGET and gets the modules, their listings, NAME.ins and NAME.force (seeded from
tools/NAME.force when there is one). src/ is the source of truth once frozen; this tool
re-derives pieces and never writes to src/.
"""
import bisect, os, re, shutil, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import dos as dosmod
import u3an

target = sys.argv[1]
T = u3an.TARGETS[target]
NAME = os.path.splitext(T['file'])[0]
work = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'build', 'regen', target)
asm = sys.argv[3] if len(sys.argv) > 3 else 'MASM4'
os.makedirs(work, exist_ok=True)
ffile = os.path.join(work, NAME + '.force')
seed = os.path.join(HERE, NAME + '.force')
if not os.path.exists(ffile) and os.path.exists(seed):
    shutil.copy(seed, ffile)

oimg = u3an.load(target)               # 0100 zero bytes + the file
END = len(oimg)


def listing_rows(lst, lo, hi):
    """(listing offset, original address, text) for the tagged lines of one module, plus an
    end sentinel; lo/hi are the module's original bounds."""
    rows = []
    for l in open(lst, 'rb').read().decode('latin1').split('\n'):
        m = re.match(r'^\s*([0-9A-F]{4})\s.*;@([0-9A-F]{4})', l)
        if m:
            rows.append((int(m.group(1), 16), int(m.group(2), 16), l.strip()))
    rows.sort(key=lambda r: r[1])
    if rows:
        rows.append((rows[-1][0] + (hi - rows[-1][1]), hi, 'end'))
    return rows


for it in range(int(os.environ.get('ITER', '40'))):
    for f in os.listdir(work):
        if f.upper().endswith(('.ASM', '.OBJ', '.EXE', '.LST', '.LOG', '.MAP')):
            os.unlink(os.path.join(work, f))
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'gen.py'), target, work, ffile,
                    str(T.get('limit', 0))], check=True)
    mods = [l.strip() for l in open(os.path.join(work, NAME + '.lnk')) if l.strip()]
    stems = [os.path.splitext(m)[0] for m in mods]
    cmds = ['D:\\%s\\MASM %s.ASM,%s.OBJ,%s.LST; >> ASM.LOG' % (asm, s, s, s) for s in stems]
    open(os.path.join(work, 'LINK.RSP'), 'w', newline='').write(
        '+\r\n'.join(stems) + '\r\n%s\r\nNUL\r\n;\r\n' % NAME)
    cmds.append('IF EXIST %s.OBJ D:\\MASM4\\LINK @LINK.RSP > LNK.LOG' % stems[-1])
    dosmod.run(work, cmds, timeout=900)
    log = open(os.path.join(work, 'ASM.LOG'), 'rb').read().decode('latin1')
    exe = os.path.join(work, NAME + '.EXE')
    if not os.path.exists(exe) or any(not os.path.exists(os.path.join(work, s + '.OBJ')) for s in stems):
        print(log[-3000:])
        lnk = os.path.join(work, 'LNK.LOG')
        if os.path.exists(lnk):
            print(open(lnk, 'rb').read().decode('latin1'))
        sys.exit('no EXE')
    lnklog = open(os.path.join(work, 'LNK.LOG'), 'rb').read().decode('latin1')
    if re.search(r'error|Unresolved', lnklog, re.I):
        print(lnklog)
    new = open(exe, 'rb').read()
    h = struct.unpack('<14H', new[:28])
    nimg = new[h[4] * 16:]
    print('iter %d: %d modules, built image %X bytes, orig %X' % (it, len(mods), len(nimg), END))
    n = min(len(nimg), END)
    diffs = [i for i in range(0x100, n) if nimg[i] != oimg[i]]
    print('  differing bytes', len(diffs), 'first', ['%04X' % d for d in diffs[:12]])
    if not diffs and len(nimg) == END:
        print('IDENTICAL image')
        break
    force = set(open(ffile).read().split()) if os.path.exists(ffile) else set()
    st = [int(x) for x in open(os.path.join(work, NAME + '.ins')).read().split()]
    stset = set(st)
    bounds = []
    for s in stems:
        head = open(os.path.join(work, s + '.ASM'), 'rb').read(600).decode('latin1')
        m = re.search(r'Module \d+ of \d+: ([0-9A-F]{4})-([0-9A-F]{4})', head)
        bounds.append((int(m.group(1), 16), int(m.group(2), 16)) if m else (0x100, END))
    bad = []
    for s, (lo, hi) in zip(stems, bounds):
        rows = listing_rows(os.path.join(work, s + '.LST'), lo, hi)
        bad += [(r1, r2) for r1, r2 in zip(rows, rows[1:]) if r2[0] - r1[0] != r2[1] - r1[1]]
    added = 0
    if bad:
        print('  %d lines assemble to a different size, e.g.' % len(bad))
        for r1, r2 in bad[:6]:
            print('    %s  (want %d, got %d)' % (r1[2], r2[1] - r1[1], r2[0] - r1[0]))
        for r1, r2 in bad:
            k = '%04X' % r1[1]
            if r1[1] in stset and k not in force:
                force.add(k)
                added += 1
        if not added:
            print('  cannot fix automatically:')
            for r1, r2 in bad[:10]:
                print('   ', r1[2])
            break
    else:
        for d in diffs:
            k = '%04X' % st[bisect.bisect_right(st, d) - 1]
            if k not in force:
                force.add(k)
                added += 1
    open(ffile, 'w').write(' '.join(sorted(force)) + '\n')
    print('  forced +%d (total %d)' % (added, len(force)))
    if not added:
        break
