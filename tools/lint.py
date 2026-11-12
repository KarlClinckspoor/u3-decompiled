#!/usr/bin/env python3
"""Check (and fix line ends of) the sources in src/.

    python3 tools/lint.py [FILE ...] [--code-unchanged REV]

For each file (default: src/LIB.INC and every module of every program): rewrites it with CRLF
line ends (MASM needs them; an editor may have inserted bare LFs), then checks that no line is
longer than 120 characters (MASM 4.00 drops what follows an over-long line) and that a `;@ADDR`
tag is only ever the last thing on its line, once.
--code-unchanged REV also checks that the code is the same as in git revision REV, apart from
names: the sequence of code parts (each line up to its first `;`, whitespace normalised, every
identifier replaced by a placeholder) must be equal, so only comments, blank lines and names
differ. (Renames are checked by the build; this catches an edit that changes an instruction.)
Exit status 1 on any problem.
"""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import syms

KEEP = set('''byte word ptr offset near short dup label equ extrn public org code segment ends
assume end db dw cs ds es ss ax bx cx dx si di bp sp al ah bl bh cl ch dl dh ifdef else endif
include'''.split()) | {m.lower() for m in syms.__dict__.get('MNEMONICS', [])}


def code_seq(text):
    out = []
    for l in text.replace('\r\n', '\n').split('\n'):
        c = ' '.join(l.split(';')[0].split())
        if not c or c.upper().startswith(('EXTRN', 'PUBLIC')):
            continue
        toks = re.split(r'(\W+)', c)
        norm = []
        for k, t in enumerate(toks):
            if re.match(r'^[A-Za-z_]\w*$', t) and not re.match(r'^[0-9A-F]+h$', t, re.I):
                # the first word is the mnemonic or a label definition; keep mnemonics
                rest = c[len(t):].lower()
                label_def = k == 0 and rest.startswith((':', ' label', ' equ', ' dw', ' db'))
                norm.append(t.lower() if t.lower() in KEEP or (k == 0 and not label_def) else 'N')
            else:
                norm.append(t)
        out.append(''.join(norm))
    return out


def files():
    out = [os.path.join(syms.SRC, 'LIB.INC')]
    for p in syms.PROGRAMS:
        out += syms.modules(p)
    return out


def main():
    args = sys.argv[1:]
    rev = None
    if '--code-unchanged' in args:
        k = args.index('--code-unchanged')
        rev = args[k + 1]
        del args[k:k + 2]
    paths = [os.path.abspath(a) for a in args] or files()
    bad = 0
    for path in paths:
        rel = os.path.relpath(path, syms.SRC).replace('\\', '/')
        raw = open(path, 'rb').read()
        text = raw.decode('latin1').replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')
        if lines and lines[-1] == '':
            lines.pop()
        fixed = ('\r\n'.join(lines) + '\r\n').encode('latin1')
        if fixed != raw:
            open(path, 'wb').write(fixed)
            print('%s: line ends normalised to CRLF' % rel)
        for i, l in enumerate(lines, 1):
            if len(l.expandtabs(8)) > 120:
                print('%s:%d: longer than 120 characters' % (rel, i))
                bad += 1
            n = l.count(';@')
            if n > 1 or (n == 1 and not re.search(r';@[0-9A-F]{4}\s*$', l)):
                print('%s:%d: ;@ tag not alone at the end of the line' % (rel, i))
                bad += 1
        if rev:
            try:
                old = subprocess.run(['git', 'show', '%s:src/%s' % (rev, rel)], cwd=ROOT, check=True,
                                     capture_output=True).stdout.decode('latin1')
            except subprocess.CalledProcessError:
                print('%s: not in %s' % (rel, rev))
                bad += 1
                continue
            a, b = code_seq(old), code_seq(fixed.decode('latin1'))
            if a != b:
                k = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]), min(len(a), len(b)))
                print('%s: code differs from %s at code line %d: %r -> %r' % (
                    rel, rev, k + 1, a[k] if k < len(a) else None, b[k] if k < len(b) else None))
                bad += 1
    if bad:
        sys.exit('lint: %d problems' % bad)
    print('lint: OK (%d files)' % len(paths))


if __name__ == '__main__':
    main()
