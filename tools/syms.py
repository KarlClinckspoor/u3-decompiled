#!/usr/bin/env python3
"""Symbol table of the sources in src/, worked out from the source itself (so it survives
renaming): every name, where it is defined and what address it stands for in the original.

    python3 tools/syms.py SCOPE                  list the symbols of a scope
    python3 tools/syms.py SCOPE NAME|ADDR ...    look up names or original addresses (hex)
    python3 tools/syms.py SCOPE --refs NAME      every line that uses NAME

SCOPE is ultima, bootup, exodus, dungeon (a program's own modules) or lib (src/LIB.INC). Names
live in two kinds of namespace:
  - a program's own labels (generated as Lxxxx) belong to that program only: the same Lxxxx
    exists in several programs and means a different place in each;
  - the library's labels (Kxxxx) and the program symbols it uses (Xxxxx, defined in every
    program that links the library) are shared: lib + ultima + bootup + exodus.
A program's names must be unique (ignoring case) among its own and the shared ones.

Addresses: a code label or data label gets the ;@ address of its line or of the next tagged
line; a label right after `ORG n` (the PSP labels before ORG 100h) gets n; an EQU gets its
value (kind ABS). Library addresses are BOOTUP.BIN's (Kxxxx = address - 1E40).
As a module: table(scope) -> {NAME_UPPER: Sym}; refs(name, scope) -> [(path, lineno, text)];
modules(scope) -> [paths]; scope_of(name) -> 'lib' or a program (for renames).
"""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'src')
sys.path.insert(0, HERE)

PROGRAMS = ['ultima', 'bootup', 'exodus', 'dungeon']
SHARED = ['lib', 'ultima', 'bootup', 'exodus']          # who sees the library's names
STEMS = {'ultima': 'ULTIMA', 'bootup': 'BOOTUP', 'exodus': 'EXODUS', 'dungeon': 'DUNGEON'}

Sym = collections.namedtuple('Sym', 'name kind scope addr path lineno')
SYMDEF = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)(:|\s+label\s+(byte|word|near)\b|\s+equ\s+([^;]*)|\s+(dw|db)\b)', re.I)
TAG = re.compile(r';@([0-9A-F]{4})\s*$')
ORG = re.compile(r'^\s*ORG\s+([0-9A-F]+)h?\s*$', re.I)


def modules(scope):
    if scope == 'lib':
        return [os.path.join(SRC, 'LIB.INC')]
    lnk = os.path.join(SRC, scope, STEMS[scope] + '.lnk')
    mods = [l.split(';')[0].strip() for l in open(lnk)]
    return [os.path.join(SRC, scope, m) for m in mods if m and m.upper() != 'LIB.ASM']


def read(path):
    return open(path, 'rb').read().decode('latin1').split('\r\n')


def num(s):
    s = s.strip()
    try:
        return int(s[:-1], 16) if s.lower().endswith('h') else int(s)
    except ValueError:
        return None


def table(scope):
    syms = {}
    for path in modules(scope):
        lines = read(path)
        pending, org = [], None
        for i, l in enumerate(lines):
            o = ORG.match(l)
            if o:
                org = int(o.group(1), 16)
                continue
            d = SYMDEF.match(l)
            if d and not l.upper().startswith(('EXTRN', 'PUBLIC')):
                name = d.group(1)
                if d.group(4) is not None:
                    syms[name.upper()] = Sym(name, 'ABS', scope, num(d.group(4)), path, i + 1)
                else:
                    kind = 'NEAR' if d.group(2) == ':' else (d.group(3) or {'dw': 'WORD', 'db': 'BYTE'}[d.group(5).lower()]).upper()
                    syms[name.upper()] = Sym(name, kind, scope, None, path, i + 1)
                    if org is not None and org < 0x100:
                        syms[name.upper()] = syms[name.upper()]._replace(addr=org)
                    else:
                        pending.append(name.upper())
            t = TAG.search(l)
            if t:
                a = int(t.group(1), 16)
                for p in pending:
                    syms[p] = syms[p]._replace(addr=a)
                pending = []
                org = None
            elif o is None and org is not None and org >= 0x100 and not d:
                org = None
    return syms


def namespace(scope):
    """Every symbol a name of `scope` must not clash with (MASM ignores case): a program's own,
    plus the library's; for the library, its own plus every program's that links it."""
    out = dict(table(scope))
    others = ['lib'] if scope in ('ultima', 'bootup', 'exodus') else SHARED[1:] if scope == 'lib' else []
    for s in others:
        for k, v in table(s).items():
            out.setdefault(k, v)
    return out


def shared_names():
    """Names defined in the library, or used by it as externals (the X symbols)."""
    names = set(table('lib'))
    for l in read(os.path.join(SRC, 'LIB.INC')):
        m = re.match(r'^\s*EXTRN\s+(.*)$', l, re.I)
        if m:
            for item in m.group(1).split(','):
                names.add(item.split(':')[0].strip().upper())
    return names


def scope_of(name):
    """'lib' for a shared name (renamed everywhere), else None (a program's own)."""
    return 'lib' if name.upper() in shared_names() else None


def refs(name, scope):
    out = []
    w = re.compile(r'\b%s\b' % re.escape(name), re.I)
    scopes = SHARED if scope == 'lib' else [scope]
    for s in scopes:
        for path in modules(s):
            for i, l in enumerate(read(path)):
                if w.search(l.split(';')[0]):
                    out.append((os.path.relpath(path, SRC), i + 1, l.strip()))
    return out


def show(s):
    return '%-31s %-5s %s  %s:%d' % (s.name, s.kind, '%04X' % s.addr if s.addr is not None else '----',
                                     os.path.relpath(s.path, SRC), s.lineno)


def main():
    args = sys.argv[1:]
    if not args or args[0] not in PROGRAMS + ['lib']:
        sys.exit(__doc__)
    scope, args = args[0], args[1:]
    t = table(scope)
    if args and args[0] == '--refs':
        for name in args[1:]:
            for path, n, text in refs(name, 'lib' if scope_of(name) else scope):
                print('%s:%d: %s' % (path, n, text))
        return
    if not args:
        for s in sorted(t.values(), key=lambda s: s.addr if s.addr is not None else -1):
            print(show(s))
        return
    for q in args:
        hits = [t[q.upper()]] if q.upper() in t else []
        if not hits and re.match(r'^[0-9A-Fa-f]{1,4}$', q):
            a = int(q, 16)
            hits = [s for s in t.values() if s.addr == a]
        if not hits:
            print('%s: no such symbol in %s' % (q, scope))
        for s in hits:
            print(show(s))


if __name__ == '__main__':
    main()
