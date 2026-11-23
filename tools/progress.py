#!/usr/bin/env python3
"""progress.py: progress card (docs/progress.svg) and numbers (docs/progress.json).

U3 is hand-written assembly: there is no compiler output to match, and the sources in src/
already rebuild the four files byte for byte (tools/build.py). What is left to "decompile" is
the reading of each routine as C (c/, a reading aid, not byte-matching, as in U2), so one tile is
one routine of src/ (a code label under a ;---- header), in the order ULTIMA, BOOTUP, EXODUS,
DUNGEON and then the shared library (src/LIB.INC, counted once although all three programs link
it), and its status is:

  matched  the routine has a C reading: an `/* asm: NAME @ADDR` anchor in c/<program>/*.c
           (c/lib/ for the library); tools/ccheck.py checks the anchors, data, calls and tables,
           this script only counts
  attempt  reserved (a draft that is not anchored yet)
  open     the routine has no C reading
  aside    reserved for code that is not Ultima III's own: none

The percentage is matched / (matched + attempt + open). The script only reads the sources; the
byte-identical rebuild is checked by tools/build.py.

    python3 tools/progress.py            # writes docs/progress.svg and docs/progress.json
    python3 tools/progress.py --check    # exit 1 if the committed files are stale
"""
import argparse, json, os, re, sys
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
NAME = 'u3-decompiled'
PROGRAMS = [('ULTIMA', 'ultima'), ('BOOTUP', 'bootup'), ('EXODUS', 'exodus'), ('DUNGEON', 'dungeon')]
CAPTION = ('Function map: 1 routine per tile, in order ULTIMA, BOOTUP, EXODUS, DUNGEON, '
           'then the shared library (once), by address')
COLORS = dict(matched='#2a8c3c', attempt='#b8860b', open='#64748b', aside='#3b5b8a')
HEADLINE = 'routines with a C reading'
LABELS = dict(matched='C reading', attempt='Attempt', open='Open', aside='Aside')
RULE = re.compile(r'^;-{20,}')
ANCHOR = re.compile(r'^/\*\s*asm:\s*(\w+)\s*@([0-9A-Fa-f]{4})', re.M)   # as tools/ccheck.py
TAG = re.compile(r';@([0-9A-F]{4})\s*$')


def lines_of(path):
    with open(path, 'rb') as f:
        return f.read().decode('latin1').split('\r\n')


def routines(path):
    """(name, address) of the code labels under a ;---- / comments / ;---- header."""
    lines = lines_of(path)
    rules = [i for i, l in enumerate(lines) if RULE.match(l)]
    out = []
    for k in range(1, len(rules) - len(rules) % 2, 2):
        for j in range(rules[k] + 1, min(rules[k] + 6, len(lines))):
            m = re.match(r'^(\w+):', lines[j])
            if m:
                addr = 0
                for l in lines[j:j + 4]:
                    t = TAG.search(l)
                    if t:
                        addr = int(t.group(1), 16)
                        break
                out.append((m.group(1), addr))
                break
            if lines[j].strip() and not lines[j].startswith(';'):
                break
    return out


def modules(scope):
    base = os.path.join(SRC, scope)
    out = []
    with open(os.path.join(base, scope.upper() + '.lnk'), encoding='latin1') as f:
        listing = f.read().splitlines()
    for line in listing:
        name = line.split(';')[0].strip().replace('+', '').strip()
        if name.upper().endswith('.ASM') and name.upper() != 'LIB.ASM':
            out.append(os.path.join(base, name))
    return out


def anchored(scope):
    """Upper-case names anchored in c/SCOPE/*.c (the routines with a C reading)."""
    names = set()
    folder = os.path.join(ROOT, 'c', scope)
    if os.path.isdir(folder):
        for fn in sorted(os.listdir(folder)):
            if fn.endswith('.c'):
                with open(os.path.join(folder, fn), encoding='latin1', newline='') as f:
                    names |= {m.group(1).upper() for m in ANCHOR.finditer(f.read().replace('\r\n', '\n'))}
    return names


def classify():
    flat = []
    groups = [(label, s, modules(s)) for label, s in PROGRAMS]
    groups.append(('LIB', 'lib', [os.path.join(SRC, 'LIB.INC')]))
    for label, scope, files in groups:
        done = anchored(scope)
        for path in files:
            rows = sorted((a, n) for n, a in routines(path))
            for a, n in rows:
                flat.append(dict(program=label, module=os.path.basename(path), addr=a, name=n,
                                 status='matched' if n.upper() in done else 'open'))
    return flat


def summary(rows):
    c = {k: 0 for k in COLORS}
    for r in rows:
        c[r['status']] += 1
    total = c['matched'] + c['attempt'] + c['open']
    return dict(c, total=total, percent=round(100.0 * c['matched'] / total, 1) if total else 100.0)


def svg(flat):
    s = summary(flat)
    n = len(flat)
    W, PAD = 840, 20
    inner = W - 2 * PAD
    cols = 1
    for cols_try in range(20, 200):      # square tiles of at least 11 px
        if inner / cols_try < 11:
            break
        cols = cols_try
    cell = inner / cols
    top = 160
    H = int(top + -(-n // cols) * cell + 22)
    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
      'font-family="Roboto, Helvetica, Arial, sans-serif" role="img" aria-label="%s">'
      % (W, H, W, H, escape('Decompilation progress: %d of %d %s' % (s['matched'], s['total'], HEADLINE))))
    a('<rect width="%d" height="%d" rx="14" fill="#0f172a"/>' % (W, H))
    a('<text x="%d" y="38" font-size="21" fill="#ffffff">Decompilation progress</text>' % PAD)
    a('<text x="%d" y="38" font-size="15" fill="#ffffff" text-anchor="end">%s</text>' % (W - PAD, escape(NAME)))
    a('<text x="%d" y="62" font-size="15" fill="#e5e7eb">%s / %s %s (%.1f%%)</text>'
      % (PAD, format(s['matched'], ','), format(s['total'], ','), HEADLINE, s['percent']))
    a('<rect x="%d" y="74" width="%d" height="18" rx="5" fill="#334155"/>' % (PAD, inner))
    if s['total']:
        a('<rect x="%d" y="74" width="%.2f" height="18" rx="5" fill="%s"/>'
          % (PAD, inner * s['matched'] / s['total'], COLORS['matched']))
    for x, k in zip([PAD, 232, 430, 628], ['matched', 'attempt', 'open', 'aside']):
        a('<rect x="%d" y="104" width="10" height="10" fill="%s"/>' % (x, COLORS[k]))
        a('<text x="%d" y="113" font-size="12" fill="#e5e7eb">%s: %s</text>' % (x + 14, LABELS[k], format(s[k], ',')))
    a('<text x="%d" y="140" font-size="11" fill="#e5e7eb">%s</text>' % (PAD, escape(CAPTION)))
    for i, r in enumerate(flat):
        x, y = PAD + (i % cols) * cell, top + (i // cols) * cell
        a('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="#0f172a" stroke-width="1">'
          '<title>%s %s %04X %s (%s)</title></rect>'
          % (x, y, cell, cell, COLORS[r['status']], r['program'], r['module'], r['addr'], escape(r['name']), r['status']))
    a('</svg>')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    flat = classify()
    result = {}
    for label in [p for p, _ in PROGRAMS] + ['LIB']:
        result[label] = summary([r for r in flat if r['program'] == label])
    result['all'] = summary(flat)
    js = json.dumps(result, indent=1) + '\n'
    paths = {os.path.join(ROOT, 'docs', 'progress.json'): js, os.path.join(ROOT, 'docs', 'progress.svg'): svg(flat)}
    if args.check:
        stale = [p for p, t in paths.items() if not os.path.exists(p) or open(p, encoding='utf-8', newline='').read().replace('\r\n', '\n') != t]
        if stale:
            print('stale:', *stale)
            sys.exit(1)
        return
    for p, t in paths.items():
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(t)
    for k, r in result.items():
        print('%-8s matched %3d  open %d  -> %.1f%% of %d' % (k, r['matched'], r['open'], r['percent'], r['total']))


if __name__ == '__main__':
    main()
