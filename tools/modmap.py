#!/usr/bin/env python3
"""Markdown table of the modules of every program (from src/, link order, with their address
range and size, and the comments of `modules` in tools/u3an.py).

    python3 tools/modmap.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import u3an

SRC = open(os.path.join(HERE, 'u3an.py')).read()


def describe(name):
    m = re.search(r"'%s'[,}\s]*#\s*(.*)" % name, SRC)
    return m.group(1).strip() if m else ''


def main():
    for t, d in u3an.TARGETS.items():
        name = os.path.splitext(d['file'])[0]
        lnk = os.path.join(ROOT, 'src', t, name + '.lnk')
        print('### %s (`src/%s/`)\n' % (d['file'], t))
        print('| module | image range | bytes | what |\n|---|---|---|---|')
        for l in open(lnk):
            l = l.split(';')[0].strip()
            if not l:
                continue
            txt = open(os.path.join(ROOT, 'src', t, l), 'rb').read().decode('latin1')
            m = re.search(r'Module \d+ of \d+: ([0-9A-F]{4})-([0-9A-F]{4})', txt) or re.search(r'; (\w+): .*?\(([0-9A-F]{4})-([0-9A-F]{4})\)', txt)
            if m and len(m.groups()) == 2:
                lo, hi = int(m.group(1), 16), int(m.group(2), 16)
            elif m:
                lo, hi = int(m.group(2), 16), int(m.group(3), 16)
            else:
                lo = hi = 0
            stem = os.path.splitext(l)[0]
            if stem == 'LIB':
                import genlib
                lo, hi = genlib.RANGE[t][1], genlib.RANGE[t][2]
            elif not hi:
                lo, hi = 0x100, u3an.analyse(t).end
            desc = 'the shared library (src/LIB.INC)' if stem == 'LIB' else describe(stem)
            print('| %s | %s | %s | %s |' % (l, '%04X-%04X' % (lo, hi) if hi else '', hi - lo if hi else '', desc))
        print()


if __name__ == '__main__':
    main()
