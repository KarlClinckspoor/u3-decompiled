#!/usr/bin/env python3
"""Check the C reading in c/ against the assembly in src/ (adapted from ../u2-decompiled/tools/ccheck.py).

    python3 tools/ccheck.py [--cc gcc] [--fix-addrs] [FILE.c ...]        (default: every c/*/*.c)

c/ mirrors src/: c/lib/*.c reads src/LIB.INC (counted once, although three programs link it),
c/ultima, c/bootup, c/exodus, c/dungeon read src/<same>/ and each C file reads the assembly module
of the same name (c/exodus/combat.c = src/exodus/COMBAT.ASM; c/lib/lib.c = src/LIB.INC). The
directory is the scope of the names (tools/syms.py): a program's own names plus the library's.

--fix-addrs rewrites the @ADDR of every anchor to the symbol's real address first (write the name,
let the tool find the address).

--cc COMPILER also runs `COMPILER -std=c99 -Wall -Wextra -Wpedantic -fsyntax-only -I c` on each
file, which catches typos and type errors (nothing is linked or run).

The C is an interpretation, not a build, so this checks only what is mechanical. Every C function
or table is anchored with a comment line

    /* asm: NAME @ADDR [options] ... */

and the check is:
  - NAME is a symbol of the module's scope and ADDR is its original address (the ;@ tags);
  - a FUNCTION: U3 prints through pointers to strings (`lea si, MsgX / call PrintMsg`), not inline
    text, so instead of comparing texts the check demands that every data symbol (a label of a
    table or variable, not an equate) that the routine's instructions mention is mentioned in the
    C function, and that every routine the assembly calls or jumps to (outside the routine itself)
    is called from the C function at least as many times (the C may call more: helpers; ALIASES
    maps renamed ones). `jmp MainLoop` is ignored (it is the end of the turn: the C returns).
    Options after `@ADDR`:
      also: @ADDR...     another label of the routine (when the assembly puts other code between)
      returns: NAME...   a jump to these means "return" in this function (not demanded as a call)
      unrolled: NAME-N   where a C loop replaces repeated assembly: N calls fewer are demanded
      ignore: NAME...    asm names (routines or data) the C legitimately does not mention
      to: NAME           (tables) the table runs on through the labels in between up to NAME
      check: none        anchors an item without checking its body
  - a TABLE (an initialised C array or scalar, or an array without initialiser that stands for a
    buffer the assembly fills with zeros) holds the same bytes as the assembly's db/dw lines:
    `db 20h,41h`, `db 48 dup (0)`, `dw 1234h`. A string literal is its bytes with the final zero
    left out (the C adds it); numbers are the bytes (for a `u16` table the words). A table of
    `dw Name` (addresses of routines or data) is checked by the NAMES: the C initialiser lists the
    same identifiers in the same order.
It also lists, per module, the routines (a label under a ;---- header) and the data labels that
have no C yet. What it cannot check: the logic, the numbers, the order of the calls.
Exit status 1 on any error.

The routine's extent in the assembly runs from its label to the next `;----` rule line or to the
next anchored label of the same module, whichever comes first.
"""
import collections, glob, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import syms

ALIASES = {}                                      # asm name -> the C name that stands for it
IGNORED_CALLEES = {'MainLoop'}                    # a jump there ends the turn: the C returns
REGISTERS = {'AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'BP', 'SP', 'AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH'}
KEYWORDS = {'if', 'while', 'for', 'switch', 'return', 'sizeof', 'else', 'do', 'case', 'goto'}
ANCHOR = re.compile(r'^/\*\s*asm:\s*(\w+)\s*@([0-9A-Fa-f]{4})([^\n]*)', re.M)
RULE = re.compile(r'^;-{20,}')
SCOPES = ['lib', 'ultima', 'bootup', 'exodus', 'dungeon']
SYMDEF = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)(:|\s+label\s+(byte|word|near)\b|\s+equ\s|\s+(dw|db)\b)', re.I)
DATALINE = re.compile(r'^\s*(?:[A-Za-z_]\w*\s+)?(db|dw)\s', re.I)


# ---- the assembly ---------------------------------------------------------------------------

_tables = {}


def scope_table(scope):
    """syms.table(scope) plus the library's names (a program sees both)."""
    if scope not in _tables:
        t = dict(syms.table(scope))
        if scope != 'lib':
            for k, v in syms.table('lib').items():
                t.setdefault(k, v)
        _tables[scope] = t
    return _tables[scope]


def asm_lines(path):
    return syms.read(path)


def module_path(scope, stem):
    if scope == 'lib':
        return os.path.join(ROOT, 'src', 'LIB.INC')
    for p in syms.modules(scope):
        if os.path.splitext(os.path.basename(p))[0].lower() == stem.lower():
            return p
    return None


def num(tok):
    tok = tok.strip()
    if tok.lower().endswith('h'):
        return int(tok[:-1], 16)
    return int(tok)


def data_items(line):
    """The list of ('b', value) / ('w', value|name) items of a db/dw line, dup expanded."""
    code = line.split(';')[0]
    m = re.search(r'\b(db|dw)\s+(.*)$', code, re.I)
    kind = 'b' if m.group(1).lower() == 'db' else 'w'
    out = []
    for part in re.split(r',(?![^(]*\))', m.group(2)):
        part = part.strip()
        d = re.match(r'^(\w+)\s+dup\s*\(\s*(\w+|\?)\s*\)$', part, re.I)
        if d:
            out += [(kind, 0 if d.group(2) == '?' else num(d.group(2)))] * num(d.group(1))
        elif re.match(r'^[0-9][0-9A-Fa-f]*h?$', part):
            out.append((kind, num(part)))
        else:
            out.append((kind, part))                 # a symbol (dw Name)
    return out


def asm_data(lines, first, stop_label=None):
    """Items of the data at lines[first] (the label's line) and the lines after it, up to the next
    label (or to `stop_label`, exclusive) / non-data line."""
    items, i = [], first
    stop = stop_label.upper() if stop_label else None
    while i < len(lines):
        l = lines[i]
        d = SYMDEF.match(l)
        if i > first and d and not l.upper().startswith(('EXTRN', 'PUBLIC')):
            if stop is None or d.group(1).upper() == stop:
                break
        elif i > first and l.strip() and not DATALINE.match(l) and not l.startswith(';'):
            break
        if DATALINE.match(l) and (i > first or re.search(r'\b(db|dw)\s', l.split(';')[0], re.I)):
            items += data_items(l)
        i += 1
    return items


def routines(lines):
    """Labels that follow a ;---- / comments / ;---- header."""
    rules = [i for i, l in enumerate(lines) if RULE.match(l)]
    out = []
    if len(rules) % 2:
        return None
    for k in range(1, len(rules), 2):
        for l in lines[rules[k] + 1:rules[k] + 6]:
            m = re.match(r'^(\w+):', l)
            if m:
                out.append(m.group(1))
                break
            if l.strip() and not l.startswith(';'):
                break
    return out


def data_labels(lines, routine_names):
    """Labels of the module that name data (label byte/word, or a label on a db/dw line)."""
    out = []
    for i, l in enumerate(lines):
        d = SYMDEF.match(l)
        if not d or l.upper().startswith(('EXTRN', 'PUBLIC')):
            continue
        if d.group(2) == ':' or (d.group(3) or '').lower() == 'near' or d.group(2).lower().startswith(' equ'):
            continue
        if d.group(1).lower() in routine_names:
            continue
        out.append(d.group(1))
    return out


def asm_calls(region, own):
    """Counter of call/jmp targets outside the region."""
    labels = {m.group(1).upper() for l in region for m in [re.match(r'^(\w+)(?::|\s+label)', l)] if m}
    out = collections.Counter()
    for l in region:
        code = l.split(';')[0].rstrip()
        m = re.match(r'^(?:\w+:)?\s*(?:call|jmp)\s+(?:short\s+|near\s+)?([A-Za-z_]\w*)\s*$', code, re.I)
        if m:
            n = m.group(1)
            if n.upper() not in labels and n not in IGNORED_CALLEES and n.upper() not in REGISTERS:
                out[n] += 1
    return out


def asm_data_refs(region, table):
    """Data symbols (byte/word labels) the instructions of the region mention."""
    out = collections.Counter()
    for l in region:
        code = l.split(';')[0]
        if not code.strip() or DATALINE.match(l):
            continue
        code = re.sub(r"^\w+:", '', code.strip())
        if re.match(r'^(call|jmp|j[a-z]+|loop[a-z]*)\b', code, re.I):
            continue
        for w in re.findall(r'[A-Za-z_]\w*', code):
            s = table.get(w.upper())
            if s and s.kind in ('BYTE', 'WORD'):
                out[s.name] += 1
    return out


# ---- the C ----------------------------------------------------------------------------------

def blank_comments(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '"' or c == "'":
            j = i + 1
            while s[j] != c:
                j += 2 if s[j] == '\\' else 1
            out.append(s[i:j + 1])
            i = j + 1
        elif s.startswith('/*', i):
            j = s.index('*/', i) + 2
            out.append(''.join(ch if ch == '\n' else ' ' for ch in s[i:j]))
            i = j
        elif s.startswith('//', i):
            j = s.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i))
            i = j
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def parse_literal(s, i):
    i += 1
    out = []
    while s[i] != '"':
        c = s[i]
        if c != '\\':
            out.append(ord(c))
            i += 1
            continue
        i += 1
        c = s[i]
        if c in 'nrt':
            out.append({'n': 10, 'r': 13, 't': 9}[c])
            i += 1
        elif c in '\\\'"?':
            out.append(ord(c))
            i += 1
        elif c in '01234567':
            v, k = 0, 0
            while k < 3 and s[i] in '01234567':
                v, i, k = v * 8 + int(s[i]), i + 1, k + 1
            out.append(v & 255)
        elif c == 'x':
            i += 1
            j = i
            while s[j] in '0123456789abcdefABCDEF':
                j += 1
            out.append(int(s[i:j], 16) & 255)
            i = j
        else:
            raise ValueError('unsupported escape \\%s' % c)
    return out, i + 1


def literals(s, i):
    parts = []
    while True:
        while i < len(s) and s[i].isspace():
            i += 1
        if i < len(s) and s[i] == '"':
            v, i = parse_literal(s, i)
            parts += v
        else:
            return parts, i


def item_extent(clean, pos):
    """('function', start, end), ('table', start, end) (after '='), ('declaration', i, i) for the C item after pos."""
    i = pos
    depth = 0
    while True:
        c = clean[i]
        if c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        elif depth == 0 and c in '{=;':
            break
        i += 1
    if clean[i] == ';':
        return 'declaration', pos, i
    if clean[i] == '=':
        j = i + 1
        while clean[j] != ';':
            if clean[j] == '"':
                _, j = parse_literal(clean, j)
            else:
                j += 1
        return 'table', i + 1, j
    depth, j = 0, i
    while True:
        c = clean[j]
        if c == '"' or c == "'":
            k = j + 1
            while clean[k] != c:
                k += 2 if clean[k] == '\\' else 1
            j = k + 1
            continue
        depth += (c == '{') - (c == '}')
        j += 1
        if depth == 0:
            return 'function', i, j


def c_callees(body):
    stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '""', body)
    return collections.Counter(m.group(1) for m in re.finditer(r'\b([A-Za-z_]\w*)\s*\(', stripped)
                               if m.group(1) not in KEYWORDS)


def c_idents(body):
    stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '""', body)
    return collections.Counter(re.findall(r'[A-Za-z_]\w*', stripped))


def parse_options(rest):
    opts = {'also': [], 'returns': [], 'unrolled': {}, 'ignore': [], 'to': None, 'none': False}
    parts = re.split(r'\b(also|returns|unrolled|ignore|to|check):', rest)
    for k in range(1, len(parts) - 1, 2):
        key, val = parts[k], parts[k + 1].split('*/')[0].split('--')[0]
        if key == 'also':
            opts['also'] = [int(x, 16) for x in re.findall(r'@([0-9A-Fa-f]{4})', val)]
        elif key in ('returns', 'ignore'):
            opts[key] = re.findall(r'[A-Za-z_]\w*', val)
        elif key == 'unrolled':
            opts['unrolled'] = {n: int(v) for n, v in re.findall(r'(\w+)-(\d+)', val)}
        elif key == 'to':
            m = re.search(r'[A-Za-z_]\w*', val)
            opts['to'] = m.group(0) if m else None
        elif key == 'check':
            opts['none'] = val.strip().startswith('none')
    return opts


def c_table_values(body):
    """('bytes', [..]) / ('words', [..]) / ('names', [..]) for a C initialiser, or None."""
    b = body.strip()
    if b.startswith('"'):
        v, _ = literals(b, 0)
        return 'str', v
    if b.startswith('{'):
        inner = b[1:b.rindex('}')]
        vals = [x.strip() for x in inner.split(',') if x.strip()]
        if all(re.match(r'^(0[xX][0-9A-Fa-f]+|\d+)$', x) for x in vals):
            return 'nums', [int(x, 0) for x in vals]
        return 'names', [int(y, 0) if re.match(r'^(0[xX][0-9A-Fa-f]+|\d+)$', y) else y
                         for y in (re.sub(r'^\(\w+\s*\*?\)\s*|^&', '', x) for x in vals)]
    if re.match(r'^(0[xX][0-9A-Fa-f]+|\d+)$', b):
        return 'nums', [int(b, 0)]
    m = re.match(r'^&?([A-Za-z_]\w*)$', b)
    if m:
        return 'names', [m.group(1)]
    return None


def check(path, errors, stats):
    rel = os.path.relpath(path, ROOT)
    scope = os.path.basename(os.path.dirname(path))
    if scope not in SCOPES:
        errors.append('%s: not in a scope directory c/%s/' % (rel, '|'.join(SCOPES)))
        return
    table = scope_table(scope)
    stem = os.path.splitext(os.path.basename(path))[0]
    mpath = module_path(scope, stem)
    if mpath is None:
        errors.append('%s: no assembly module %s in src/%s' % (rel, stem, scope))
        return
    text = open(path, encoding='utf-8').read()
    clean = blank_comments(text)
    lines = asm_lines(mpath)
    anchors = []
    for m in ANCHOR.finditer(text):
        name, addr = m.group(1), int(m.group(2), 16)
        end = text.index('*/', m.start()) + 2
        anchors.append((name, addr, m.start(), end, parse_options(m.group(3))))
    placed = []
    for name, addr, _, _, opts in anchors:
        s = table.get(name.upper())
        if s and s.path == mpath:
            placed.append(s.lineno)
            for a in opts['also']:
                e = label_at(table, mpath, a)
                if e:
                    placed.append(e.lineno)
    covered = set()
    for name, addr, start, end, opts in anchors:
        where = '%s: %s @%04X' % (rel, name, addr)
        s = table.get(name.upper())
        if not s or s.path != mpath:
            errors.append('%s: not a symbol of %s' % (where, os.path.basename(mpath)))
            continue
        if s.addr != addr:
            errors.append('%s: the assembly puts it at %s' % (where, '%04X' % s.addr if s.addr is not None else '?'))
            continue
        covered.add(name.upper())
        if opts['none']:
            print('ok  %-34s anchored, body not checked' % (name + ' @%04X' % addr))
            continue
        kind, b0, b1 = item_extent(clean, end)
        first = s.lineno - 1
        if kind == 'declaration':
            # a buffer / variable declared without initialiser: all zeros in the assembly
            decl = clean[end:b1]
            items = asm_data(lines, first, opts['to'])
            m = re.search(r'\[\s*(\w+|)\s*\]\s*$', decl.strip())
            if not items or any(v != 0 for _, v in items if not isinstance(v, str)):
                errors.append('%s: a declaration without initialiser, but the assembly data is not all zero' % where)
                continue
            size = sum(1 if k == 'b' else 2 for k, _ in items)
            ctype = re.match(r'^\s*(?:static\s+)?(?:const\s+)?(\w+)', decl).group(1)
            esz = {'u8': 1, 'u16': 2, 'char': 1, 'int': 2, 'i8': 1, 'i16': 2}.get(ctype, 1)
            n = None
            if m and m.group(1):
                try:
                    n = int(m.group(1), 0)
                except ValueError:
                    n = None
            elif not m:
                n = 1
            if n is not None and n * esz != size:
                errors.append('%s: size differs (asm %d bytes, C %d)' % (where, size, n * esz))
            else:
                print('ok  %-34s buffer, %d bytes' % (name + ' @%04X' % addr, size))
            continue
        if kind == 'table':
            decl_text = clean[end:b0 - 1]
            items = asm_data(lines, first, opts['to'])
            body = clean[b0:b1]
            words = bool(re.search(r'\bu16\b|\bint16_t\b|\bunsigned\s+short\b', decl_text))
            try:
                cv = c_table_values(body)
            except (ValueError, IndexError) as e:
                errors.append('%s: cannot read the table (%s)' % (where, e))
                continue
            if cv is None:
                errors.append('%s: cannot read the table initialiser' % where)
                continue
            ckind, got = cv
            if any(isinstance(v, str) for _, v in items):                      # table of names
                want = [v for _, v in items]
                if ckind != 'names' or got != want:
                    errors.append('%s: table of names differs\n    asm: %s\n    C:   %s' % (where, want, got))
                else:
                    print('ok  %-34s table of %d names' % (name + ' @%04X' % addr, len(want)))
                continue
            if words:
                want = []
                for k, v in items:
                    if k == 'w':
                        want.append(v)
                    else:
                        want.append(('b', v))
                if any(isinstance(w, tuple) for w in want):
                    errors.append('%s: u16 table over db data' % where)
                    continue
                if ckind != 'nums' or got != want:
                    errors.append('%s: table differs\n    asm: %s\n    C:   %s'
                                  % (where, ' '.join('%04X' % b for b in want), ' '.join('%04X' % b for b in got)))
                else:
                    print('ok  %-34s table, %d words' % (name + ' @%04X' % addr, len(want)))
                continue
            want = []
            for k, v in items:
                want += [v] if k == 'b' else [v & 255, v >> 8]
            if ckind == 'str':
                got = got + [0]
            if got != want:
                errors.append('%s: table differs\n    asm: %s\n    C:   %s'
                              % (where, ' '.join('%02X' % b for b in want), ' '.join('%02X' % b for b in got)))
            else:
                print('ok  %-34s table, %d bytes' % (name + ' @%04X' % addr, len(want)))
            continue
        # function
        body = clean[b0:b1]
        starts = [first]
        bad = False
        for a in opts['also']:
            e = label_at(table, mpath, a)
            if e is None:
                errors.append('%s: no label at @%04X in %s' % (where, a, os.path.basename(mpath)))
                bad = True
            else:
                starts.append(e.lineno - 1)
                covered.add(e.name.upper())
        if bad:
            continue
        region = []
        for f in starts:
            stop = len(lines)
            for j in range(f + 1, len(lines)):
                if RULE.match(lines[j]) or (j + 1) in placed:
                    stop = j
                    break
            region += lines[f:stop]
        ok = True
        have = c_callees(body)
        ids = c_idents(body)
        calls = asm_calls(region, name)
        for k, v in opts['unrolled'].items():
            calls[k] -= v
        for k in opts['returns'] + opts['ignore']:
            calls.pop(k, None)
        got_n = lambda c: have[c] + (have[ALIASES[c]] if c in ALIASES else 0)
        missing = ['%s (%d, C has %d)' % (c, n, got_n(c)) for c, n in sorted(calls.items()) if got_n(c) < n]
        if missing:
            ok = False
            errors.append('%s: the assembly calls more often: %s' % (where, ', '.join(missing)))
        refs = asm_data_refs(region, table)
        for k in opts['ignore']:
            refs.pop(k, None)
        unused = sorted(r for r in refs if ids[r] == 0 and ids.get(ALIASES.get(r, ''), 0) == 0)
        if unused:
            ok = False
            errors.append('%s: data the assembly uses but the C does not mention: %s' % (where, ', '.join(unused)))
        if ok:
            print('ok  %-34s %d calls, %d data names' % (name + ' @%04X' % addr, sum(calls.values()), len(refs)))
    # what has no C yet
    rs = routines(lines)
    if rs is None:
        print('--  %s: odd number of rule lines, coverage not listed' % os.path.basename(mpath))
        return
    rnames = {r.lower() for r in rs}
    todo = [r for r in rs if r.upper() not in covered and ALIASES.get(r) is None]
    dl = data_labels(lines, rnames)
    dtodo = [d for d in dl if d.upper() not in covered]
    stats[(scope, os.path.basename(mpath))] = (len(rs), len(rs) - len(todo), len(dl), len(dl) - len(dtodo))
    print('--  %s: %d of %d routines have C%s; %d of %d data labels%s' % (
        os.path.basename(mpath), len(rs) - len(todo), len(rs),
        (' (missing: ' + ', '.join(todo) + ')') if todo else '', len(dl) - len(dtodo), len(dl),
        (' (missing: ' + ', '.join(dtodo[:12]) + (' ...' if len(dtodo) > 12 else '') + ')') if dtodo else ''))


def label_at(table, mpath, addr):
    best = None
    for s in table.values():
        if s.path == mpath and s.addr == addr and s.kind == 'NEAR':
            if best is None or s.lineno < best.lineno:
                best = s
    return best


def compile_check(cc, path, errors):
    r = subprocess.run([cc, '-std=c99', '-Wall', '-Wextra', '-Wpedantic', '-fsyntax-only',
                        '-I', os.path.join(ROOT, 'c'), '-I', os.path.dirname(os.path.abspath(path)), path],
                       capture_output=True, text=True)
    if r.returncode or r.stderr.strip():
        errors.append('%s: the compiler objects:\n%s' % (os.path.relpath(path, ROOT), (r.stderr or r.stdout).rstrip()))
    else:
        print('ok  %s compiles (%s -std=c99 -Wall -Wextra -Wpedantic)' % (os.path.relpath(path, ROOT), cc))


def fix_addresses(files):
    """--fix-addrs: rewrite every anchor's @ADDR to the symbol's real address (names must exist)."""
    for path in files:
        scope = os.path.basename(os.path.dirname(path))
        table = scope_table(scope)
        text = open(path, encoding='utf-8').read()

        def sub(m):
            s = table.get(m.group(1).upper())
            if s and s.addr is not None:
                return '/* asm: %s @%04X' % (m.group(1), s.addr)
            return m.group(0)
        new = re.sub(r'/\*\s*asm:\s*(\w+)\s*@[0-9A-Fa-f]{4}', sub, text)
        if new != text:
            open(path, 'w', encoding='utf-8', newline='\n').write(new)


def status_table():
    """--table: the markdown status table of c/README.md (anchors only; run the full check for the rest)."""
    rows = ['| scope | module | C file | routines | with C | data labels | with C |', '|---|---|---|---|---|---|---|']
    tot = [0, 0, 0, 0]
    for scope in SCOPES:
        mods = [os.path.join(ROOT, 'src', 'LIB.INC')] if scope == 'lib' else syms.modules(scope)
        for mp in mods:
            lines = asm_lines(mp)
            rs = routines(lines) or []
            dl = data_labels(lines, {r.lower() for r in rs})
            stem = os.path.splitext(os.path.basename(mp))[0].lower()
            cp = os.path.join(ROOT, 'c', scope, stem + '.c')
            names = set()
            if os.path.exists(cp):
                t = open(cp, encoding='utf-8').read()
                for m in ANCHOR.finditer(t):
                    names.add(m.group(1).upper())
                    for a in parse_options(m.group(3))['also']:
                        e = label_at(scope_table(scope), mp, a)
                        if e:
                            names.add(e.name.upper())
            a = sum(1 for r in rs if r.upper() in names)
            b = sum(1 for d in dl if d.upper() in names)
            rows.append('| %s | %s | %s | %d | %d | %d | %d |' % (
                scope, os.path.basename(mp), ('`c/%s/%s.c`' % (scope, stem)) if os.path.exists(cp) else '-',
                len(rs), a, len(dl), b))
            tot = [tot[0] + len(rs), tot[1] + a, tot[2] + len(dl), tot[3] + b]
    rows.append('| | **total** | | **%d** | **%d** | **%d** | **%d** |' % tuple(tot))
    return '\n'.join(rows)


def main():
    args = sys.argv[1:]
    if '--table' in args:
        print(status_table())
        return
    fix = '--fix-addrs' in args
    if fix:
        args.remove('--fix-addrs')
    cc = None
    if '--cc' in args:
        k = args.index('--cc')
        cc = args[k + 1]
        del args[k:k + 2]
    files = args or sorted(glob.glob(os.path.join(ROOT, 'c', '*', '*.c')))
    if fix:
        fix_addresses(files)
    errors, stats = [], {}
    for f in files:
        check(f, errors, stats)
        if cc:
            compile_check(cc, f, errors)
    if len(files) > 1 or not args:
        done = sum(v[1] for v in stats.values())
        total = sum(v[0] for v in stats.values())
        print('routines with C in the modules checked: %d of %d; data labels: %d of %d' % (
            done, total, sum(v[3] for v in stats.values()), sum(v[2] for v in stats.values())))
    if errors:
        print()
        print('\n'.join(errors))
        sys.exit('ccheck: %d problem(s)' % len(errors))
    print('ccheck: OK')


if __name__ == '__main__':
    main()
