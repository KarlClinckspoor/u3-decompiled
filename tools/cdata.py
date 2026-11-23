#!/usr/bin/env python3
"""Generate the C for the data of src/ (tables, strings, buffers, variables), byte for byte.

    python3 tools/cdata.py defs SCOPE MODULE [NAME ...]   C definitions of the module's data labels
    python3 tools/cdata.py header SCOPE                   write c/SCOPE/SCOPE_data.h (extern declarations)
    python3 tools/cdata.py sync [FILE.c ...]              rewrite the data block of each C file between its
                                                          markers, and all headers (do this after editing types.txt)
    python3 tools/cdata.py header --all                   all five scopes

SCOPE is lib, ultima, bootup, exodus or dungeon; MODULE the assembly module (TITLE, COMBAT, LIB ...).
Every data label (`X label byte|word`, or a label on a db/dw line) becomes one C object preceded by
its anchor comment `/* asm: X @ADDR */` (tools/ccheck.py checks the bytes):

  - one `db` byte         u8 X = 0x12;          one `dw` word    u16 X = 0x1234;
  - NUL-ended text        u8 X[] = "text\\n";    (the final NUL is the C's)
  - all zeros             u8 X[N];              (a buffer the program fills)
  - other bytes           u8 X[] = {0x12, ...};  words (`dw` numbers)  u16 X[] = {...};
  - dw of routine names   Proc X[] = {(Proc)A, ...}; of data names  const u8 *X[] = {A, ...};

c/SCOPE/types.txt overrides the representation of a label, one per line, `NAME: TYPE` with TYPE
u8, u16, u8[N] or u16[N] (the bytes are regrouped), optionally `u8[] to LABEL` (the object runs on
through the labels in between up to LABEL: the labels it swallows are then `NAME: alias [u8|u16]
BASE+OFFSET`, a macro for a place inside the object, `check: none` anchors); `#` starts a comment. The header and the
definitions both read it, so they always agree. Never edit the generated *_data.h by hand.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import syms, ccheck

SCOPES = ['lib', 'ultima', 'bootup', 'exodus', 'dungeon']


def overrides(scope):
    p = os.path.join(ROOT, 'c', scope, 'types.txt') if scope != 'lib' else os.path.join(ROOT, 'c', 'lib', 'types.txt')
    out = {}
    if os.path.exists(p):
        for l in open(p, encoding='utf-8'):
            l = l.split('#')[0].strip()
            if ':' in l:
                k, v = l.split(':', 1)
                out[k.strip()] = v.strip()
    return out


def raw_bytes(items):
    out = []
    for k, v in items:
        out += [v] if k == 'b' else [v & 255, v >> 8]
    return out


def is_text(bs):
    if len(bs) < 3 or bs[-1] != 0 or 0 in bs[:-1]:
        return False
    body = bs[:-1]
    good = sum(1 for b in body if 0x20 <= b < 0x7F or b == 0x0A)
    return good * 10 >= len(body) * 7


def esc(bs):
    out = []
    for b in bs:
        c = chr(b)
        if c == '\\':
            out.append('\\\\')
        elif c == '"':
            out.append('\\"')
        elif c == '\n':
            out.append('\\n')
        elif 0x20 <= b < 0x7F:
            out.append(c)
        else:
            out.append('\\%03o' % b)
    return ''.join(out)


def numlines(vals, fmt, per):
    rows = []
    for i in range(0, len(vals), per):
        rows.append('\t' + ', '.join(fmt % v for v in vals[i:i + per]))
    return ',\n'.join(rows)


def describe(name, items, table, ov):
    """(extern declaration, definition) of one data label."""
    if any(isinstance(v, str) for _, v in items):
        tail = [v for k, v in items if k == 'b']             # db bytes mixed into a table of addresses
        names = [v for k, v in items if k == 'w']
        note = ''
        if tail:
            note = '\n/* the db bytes that follow in the assembly (not in this array): %s */' % ' '.join('%02X' % b for b in tail)
        kinds = {(table.get(n.upper()).kind if table.get(n.upper()) else '?') for n in names if isinstance(n, str)}
        proc = kinds == {'NEAR'}

        def cell(n):
            if isinstance(n, str):
                return ('(Proc)' if proc else '') + n
            return '0' if n == 0 else ('(Proc)0x%X' % n if proc else '(const u8 *)0x%X' % n)
        body = ',\n'.join('\t' + ', '.join(cell(n) for n in names[i:i + 4]) for i in range(0, len(names), 4))
        if proc:
            return ('extern Proc %s[%d];' % (name, len(names)), 'Proc %s[] = {\n%s\n};%s' % (name, body, note))
        return ('extern const u8 *%s[%d];' % (name, len(names)), 'const u8 *%s[] = {\n%s\n};%s' % (name, body, note))
    bs = raw_bytes(items)
    allw = all(k == 'w' for k, _ in items)
    t = ov.get(name)
    if t is not None:
        t = t.split(' to ')[0].strip()
    if t is None:
        if len(items) == 1 and items[0][0] == 'b':
            t = 'u8'
        elif len(items) == 1 and items[0][0] == 'w':
            t = 'u16'
        elif allw and any(v for _, v in items) and not all(v == 0 for _, v in items):
            t = 'u16[%d]' % len(items)
        else:
            t = 'u8[%d]' % len(bs)
    m = re.match(r'^(u8|u16)(?:\[(\d*)\])?$', t)
    et, cnt = m.group(1), m.group(2)
    esize = 1 if et == 'u8' else 2
    if et == 'u16':
        vals = [bs[i] | (bs[i + 1] << 8) for i in range(0, len(bs) - 1, 2)]
        fmt = '0x%04X'
    else:
        vals = bs
        fmt = '0x%02X'
    if cnt is None and '[' not in t:
        return 'extern %s %s;' % (et, name), '%s %s = %s;' % (et, name, fmt % vals[0])
    n = len(vals)
    ext = 'extern %s %s[%d];' % (et, name, n)
    if all(v == 0 for v in vals):
        return ext, '%s %s[%d];' % (et, name, n)
    if et == 'u8' and is_text(bs):
        return ext.replace('[%d]' % n, '[%d]' % n), 'u8 %s[] = "%s";' % (name, esc(bs[:-1]))
    return ext, '%s %s[] = {\n%s\n};' % (et, name, numlines(vals, fmt, 16 if et == 'u8' else 8))


def labels_of(scope, mod):
    path = ccheck.module_path(scope, mod)
    lines = syms.read(path)
    rs = {r.lower() for r in (ccheck.routines(lines) or [])}
    return path, lines, ccheck.data_labels(lines, rs)


ALIAS = re.compile(r'^alias\s+(?:(u8|u16)\s+)?(\w+)\s*\+\s*(\w+)$')


def entry(scope, name, table, lines, ov):
    """(anchor options, extern declaration, definition) of the data label, or None (no data)."""
    s = table[name.upper()]
    o = ov.get(name, '')
    m = ALIAS.match(o)
    if m:                                    # a label inside a bigger object: a macro, no storage
        ty, base, off = m.groups()
        view = '(*(%s *)(%s + %s))' % (ty, base, off) if ty else '(%s + %s)' % (base, off)
        return (' check: none', '#define %s %s' % (name, view),
                'enum { %s_offset = %s };   /* %s is %s + %s: see the object it lies in */' % (name, off, name, base, off))
    stop = None
    if ' to ' in o:
        stop = o.split(' to ')[1].strip()
    items = ccheck.asm_data(lines, s.lineno - 1, stop)
    if not items:
        return None
    ext, d = describe(name, items, table, ov)
    mixed = any(k == 'b' for k, _ in items) and any(isinstance(v, str) for _, v in items)
    opts = (' to: ' + stop if stop else '') + (' check: none' if mixed else '')
    return opts, ext, d


def defs(scope, mod, only):
    table = ccheck.scope_table(scope)
    path, lines, labels = labels_of(scope, mod)
    ov = overrides(scope)
    out = []
    for name in labels:
        if only and name not in only:
            continue
        e = entry(scope, name, table, lines, ov)
        if e:
            out.append('/* asm: %s @%04X%s */\n%s\n' % (name, table[name.upper()].addr or 0, e[0], e[2]))
    return '\n'.join(out)


def header(scope):
    table = ccheck.scope_table(scope)
    ov = overrides(scope)
    mods = [os.path.join(ROOT, 'src', 'LIB.INC')] if scope == 'lib' else syms.modules(scope)
    out = ['/* %s_data.h: GENERATED by tools/cdata.py header %s (types: c/%s/types.txt). Do not edit. */' % (scope, scope, scope),
           '#ifndef U3_%s_DATA_H' % scope.upper(), '#define U3_%s_DATA_H' % scope.upper(), '#include "../u3.h"', '']
    for p in mods:
        mod = os.path.splitext(os.path.basename(p))[0]
        _, lines, labels = labels_of(scope, mod)
        out.append('/* %s */' % os.path.basename(p))
        for name in labels:
            e = entry(scope, name, table, lines, ov)
            if e:
                out.append(e[1])
        out.append('')
    out.append('#endif')
    return '\n'.join(out) + '\n'


BEGIN = '/* ---- data: generated by tools/cdata.py sync (types: c/%s/types.txt), do not edit between the markers ---- */'
END = '/* ---- end of generated data ---- */'


def sync(files):
    """Replace, in each C file that has the markers, the block between them by the module's data."""
    for path in files:
        scope = os.path.basename(os.path.dirname(path))
        mod = os.path.splitext(os.path.basename(path))[0]
        text = open(path, encoding='utf-8').read()
        a = text.find('/* ---- data: generated by tools/cdata.py sync')
        b = text.find(END)
        if a < 0 or b < 0:
            print('%s: no markers, skipped' % path)
            continue
        new = text[:a] + BEGIN % scope + '\n\n' + defs(scope, mod, set()) + '\n' + text[b:]
        if new != text:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(new)
    for sc in SCOPES:
        with open(os.path.join(ROOT, 'c', sc, '%s_data.h' % sc), 'w', encoding='utf-8', newline='\n') as f:
            f.write(header(sc))


def main():
    a = sys.argv[1:]
    if a and a[0] == 'sync':
        import glob
        sync([os.path.abspath(x) for x in a[1:]] or sorted(glob.glob(os.path.join(ROOT, 'c', '*', '*.c'))))
        return
    if len(a) >= 3 and a[0] == 'defs':
        sys.stdout.write(defs(a[1], a[2], set(a[3:])))
    elif len(a) == 2 and a[0] == 'header':
        for sc in (SCOPES if a[1] == '--all' else [a[1]]):
            d = os.path.join(ROOT, 'c', sc)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, '%s_data.h' % sc), 'w', encoding='utf-8', newline='\n') as f:
                f.write(header(sc))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
