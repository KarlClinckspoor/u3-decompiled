#!/usr/bin/env python3
"""Apply the naming workers' proposals (phase 6 integration).

    python3 tools/applyprops.py [--dry] [FILE ...]      (default: names/proposed-*.map)

A proposal line is `OLD NEW ; SCOPE ; note`. Lines are grouped by scope (a program, or lib) and
applied with tools/rename.py's checks, scope by scope; the applied lines are written to
names/integrated-<scope>.map. Proposals whose OLD no longer exists (already renamed) are
skipped; two different proposals for the same OLD, or the same NEW for two symbols, are
reported and nothing is written for that scope.
"""
import collections, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rename, syms


def load(paths):
    out = collections.defaultdict(list)
    for p in paths:
        for n, l in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
            if not l.strip() or l.lstrip().startswith(';'):
                continue
            parts = [x.strip() for x in l.rstrip('\n').split(';')]
            f = parts[0].split()
            if len(f) != 2:
                print('%s:%d: not "OLD NEW ; SCOPE ; note": %s' % (p, n, l.rstrip()))
                continue
            scope = parts[1].lower() if len(parts) > 1 and parts[1] else ''
            if scope not in syms.PROGRAMS + ['lib']:
                scope = 'lib' if syms.scope_of(f[0]) else ''
            if not scope:
                print('%s:%d: no scope: %s' % (p, n, l.rstrip()))
                continue
            out[scope].append((f[0], f[1], '%s:%d' % (os.path.basename(p), n), parts[2] if len(parts) > 2 else ''))
    return out


def main():
    args = sys.argv[1:]
    dry = '--dry' in args
    args = [a for a in args if a != '--dry']
    paths = args or sorted(glob.glob(os.path.join(ROOT, 'names', 'proposed-*.map')))
    groups = load(paths)
    order = ['lib'] + [s for s in syms.PROGRAMS if s in groups]
    for scope in order:
        if scope not in groups:
            continue
        have = syms.shared_names() if scope == 'lib' else set(syms.table(scope))
        byold, bynew, pairs = {}, {}, []
        bad = False
        for old, new, where, note in groups[scope]:
            if old.upper() not in have:
                continue
            if old.upper() in byold and byold[old.upper()][0].upper() != new.upper():
                print('%s: %s proposed as %s (%s) and %s (%s)' % (scope, old, byold[old.upper()][0],
                                                                byold[old.upper()][1], new, where))
                bad = True
                continue
            if new.upper() in bynew and bynew[new.upper()][0].upper() != old.upper():
                print('%s: %s proposed for %s (%s) and %s (%s)' % (scope, new, bynew[new.upper()][0],
                                                                 bynew[new.upper()][1], old, where))
                bad = True
                continue
            if old.upper() in byold:
                continue
            byold[old.upper()] = (new, where)
            bynew[new.upper()] = (old, where)
            pairs.append((old, new, where, note))
        if bad:
            print('%s: conflicts, nothing applied' % scope)
            continue
        print('== %s: %d proposals' % (scope, len(pairs)))
        rename.rename(scope, [(o, n, w) for o, n, w, _ in pairs], dry)
        if not dry and pairs:
            with open(os.path.join(ROOT, 'names', 'integrated-%s.map' % scope), 'a', encoding='utf-8') as f:
                for o, n, w, note in pairs:
                    f.write('%s %s ; %s%s\n' % (o, n, w, ' ; ' + note if note else ''))


if __name__ == '__main__':
    main()
