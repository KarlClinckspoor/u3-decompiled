#!/usr/bin/env python3
"""Names defined more than once (ignoring case) in a program's namespace (its own modules plus
the library), and labels still named after their address.

    python3 tools/dups.py [SCOPE ...]

MASM only rejects duplicates inside one module; across modules a duplicate local label links
fine but makes the source ambiguous to read and to rename. Exit status 1 when there is one.
"""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import syms


def defs(scope):
    out = collections.defaultdict(list)
    for path in syms.modules(scope):
        for i, l in enumerate(syms.read(path), 1):
            d = syms.SYMDEF.match(l)
            if d and not l.upper().startswith(('EXTRN', 'PUBLIC')):
                out[d.group(1).upper()].append('%s:%d' % (os.path.relpath(path, syms.SRC), i))
    return out


def main():
    scopes = sys.argv[1:] or ['lib'] + syms.PROGRAMS
    bad = 0
    lib = defs('lib')
    for s in scopes:
        d = defs(s)
        if s in ('ultima', 'bootup', 'exodus'):
            for k, v in lib.items():
                d[k] = d[k] + v
        for k, v in sorted(d.items()):
            if len(v) > 1:
                print('%s: %s defined %d times: %s' % (s, k, len(v), ', '.join(v)))
                bad += 1
        left = sorted(k for k in defs(s) if re.match(r'^[LKX][0-9A-F]{4}$', k))
        print('%s: %d labels still named after their address%s' % (s, len(left), (': ' + ' '.join(left[:12]) + (' ...' if len(left) > 12 else '')) if left else ''))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
