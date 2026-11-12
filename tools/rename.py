#!/usr/bin/env python3
"""Rename symbols across src/, all at once, after checking the new names.

    python3 tools/rename.py SCOPE MAP [MAP ...] [--dry] [--only MODULE]

SCOPE is the program whose own labels the map renames (ultima, bootup, exodus, dungeon), or
lib for the shared names: the library's (Kxxxx) and the program symbols it uses (Xxxxx), which
are renamed in src/LIB.INC and in every program that links it (tools/syms.py explains the
namespaces). A map has one rename per line: `OLD NEW` (anything after `;` is a comment; blank
lines and lines starting with `;` are skipped). OLD must be defined in the scope; NEW must be a
valid MASM name: letters, digits and `_`, not starting with a digit, at most 31 characters
(MASM's significant length), not a MASM reserved word, and unique ignoring case (MASM ignores
case) in every namespace the rename touches. Every whole-word occurrence of OLD in the scope's
files is replaced, in comments too, so comments that mention a symbol stay right. Nothing is
written if any check fails. --only MODULE refuses renames of symbols used outside MODULE (for
working on one module while others are edited in parallel).
After renaming, run tools/build.py: names never change the bytes, so it must stay identical.
"""
import argparse, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import syms

RESERVED = set('''
AAA AAD AAM AAS ADC ADD AND CALL CBW CLC CLD CLI CMC CMP CMPS CMPSB CMPSW CWD DAA DAS DEC DIV
ESC HLT IDIV IMUL IN INC INT INTO IRET JA JAE JB JBE JC JCXZ JE JG JGE JL JLE JMP JNA JNAE JNB
JNBE JNC JNE JNG JNGE JNL JNLE JNO JNP JNS JNZ JO JP JPE JPO JS JZ LAHF LDS LEA LES LOCK LODS
LODSB LODSW LOOP LOOPE LOOPNE LOOPNZ LOOPZ MOV MOVS MOVSB MOVSW MUL NEG NOP NOT OR OUT POP POPF
PUSH PUSHF RCL RCR REP REPE REPNE REPNZ REPZ RET RETF RETN ROL ROR SAHF SAL SAR SBB SCAS SCASB
SCASW SHL SHR STC STD STI STOS STOSB STOSW SUB TEST WAIT XCHG XLAT XLATB XOR
BOUND ENTER LEAVE INS INSB INSW OUTS OUTSB OUTSW PUSHA POPA ARPL CLTS LAR LGDT LIDT LLDT LMSW
LSL LTR SGDT SIDT SLDT SMSW STR VERR VERW
AH AL AX BH BL BP BX CH CL CS CX DH DI DL DS DX ES SI SP SS
ASSUME COMMENT DB DD DQ DT DW DUP ELSE END ENDIF ENDM ENDP ENDS EQU EVEN EXITM EXTRN GROUP IF
IF1 IF2 IFB IFDEF IFDIF IFE IFIDN IFNB IFNDEF INCLUDE IRP IRPC LABEL LOCAL MACRO NAME ORG PAGE
PROC PUBLIC PURGE RECORD REPT SEGMENT STRUC SUBTTL TITLE RADIX ALIGN DOSSEG INCLUDELIB
AND EQ GE GT HIGH LE LENGTH LOW LT MASK MOD NE NOT OFFSET OR PTR SEG SHL SHR SHORT SIZE THIS TYPE
WIDTH XOR BYTE WORD DWORD QWORD TBYTE NEAR FAR ABS AT COMMON MEMORY PARA PUBLIC STACK
LIST NOLIST XLIST LALL SALL XALL CREF XCREF TFCOND SFCOND LFCOND ERR ERR1 ERR2 ERRE ERRNZ ERRDEF
ERRNDEF ERRB ERRNB ERRIDN ERRDIF CODE PROG_ULTIMA PROG_BOOTUP PROG_EXODUS
'''.split())
NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
LIMIT = 120                    # longest line (tools/lint.py checks the same)
TAGGED = re.compile(r'^(.*?)(\s*;@[0-9A-F]{4}\s*)$')


def wrap(prefix, text, width):
    lines, cur = [], ''
    for w in text.split():
        if cur and len((prefix + cur + ' ' + w).expandtabs(8)) > width:
            lines.append(prefix + cur)
            cur = w
        else:
            cur = cur + ' ' + w if cur else w
    lines.append(prefix + cur)
    return lines


def reflow(line):
    """A line that renaming made too long, with only its comment re-wrapped (CRLF-joined);
    EXTRN/PUBLIC lists are split. Code is never changed."""
    if len(line.expandtabs(8)) <= LIMIT:
        return line
    m = re.match(r'^(\s*)(EXTRN|PUBLIC)\s+([^;]*)$', line, re.I)
    if m:
        out, cur = [], []
        for item in [x.strip() for x in m.group(3).split(',') if x.strip()]:
            cand = '%s%s %s' % (m.group(1), m.group(2), ', '.join(cur + [item]))
            if cur and len(cand.expandtabs(8)) > LIMIT:
                out.append('%s%s %s' % (m.group(1), m.group(2), ', '.join(cur)))
                cur = [item]
            else:
                cur.append(item)
        out.append('%s%s %s' % (m.group(1), m.group(2), ', '.join(cur)))
        return '\r\n'.join(out)
    m = re.match(r'^(\s*;\s*)(.*)$', line)
    if m and not TAGGED.match(line):
        return '\r\n'.join(wrap(m.group(1), m.group(2), LIMIT - 2))
    t = TAGGED.match(line)
    body, tag = (t.group(1), t.group(2)) if t else (line, '')
    if ';' in body:
        code, comment = body.split(';', 1)
        return '\r\n'.join(wrap('; ', comment.strip(), LIMIT - 2) + [code.rstrip() + tag])
    return line


def load_maps(paths):
    pairs = []
    for p in paths:
        for n, l in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
            s = l.split(';')[0].strip()
            if not s:
                continue
            f = s.split()
            if len(f) != 2:
                raise SystemExit('%s:%d: expected "OLD NEW": %s' % (p, n, l.rstrip()))
            pairs.append((f[0], f[1], '%s:%d' % (p, n)))
    return pairs


def rename(scope, pairs, dry=False, only=None):
    """Check and apply [(old, new, where)]; returns the number of replacements (exits on errors)."""
    shared = syms.shared_names()
    own = syms.table(scope)
    errs = []
    olds = {}
    for old, new, where in pairs:
        if scope == 'lib':
            if old.upper() not in shared:
                errs.append('%s: %s is not a shared (library) name' % (where, old))
        elif old.upper() not in own:
            errs.append('%s: %s is not defined in %s' % (where, old, scope))
        elif old.upper() in shared:
            errs.append('%s: %s is a shared name: rename it with scope lib' % (where, old))
        if old.upper() in olds:
            errs.append('%s: %s is renamed twice (also %s)' % (where, old, olds[old.upper()][1]))
        olds[old.upper()] = (new, where)
        if not NAME.match(new):
            errs.append('%s: %s is not a valid name' % (where, new))
        if len(new) > 31:
            errs.append('%s: %s is longer than 31 characters' % (where, new))
        if new.upper() in RESERVED:
            errs.append('%s: %s is a MASM reserved word' % (where, new))
    # uniqueness in every namespace the renames touch
    spaces = syms.SHARED if scope == 'lib' else [scope]
    for sp in spaces:
        final = {}
        for k, s in syms.namespace(sp).items():
            nm = olds[k][0] if k in olds else s.name
            if nm.upper() in final and final[nm.upper()] != s.name:
                errs.append('%s: name %s would be used twice (%s and %s)' % (sp, nm, final[nm.upper()], s.name))
            final[nm.upper()] = s.name
    if only:
        o = only.upper().replace('.ASM', '') + '.ASM'
        for old, new, where in pairs:
            outside = sorted({p for p, _, _ in syms.refs(old, scope) if os.path.basename(p).upper() != o})
            if outside:
                errs.append('%s: %s is used outside %s (%s)' % (where, old, o, ', '.join(outside)))
    if errs:
        print('\n'.join(errs))
        sys.exit('rename: nothing written (%d problems)' % len(errs))
    if not pairs:
        return 0
    pat = re.compile(r'\b(%s)\b' % '|'.join(re.escape(o) for o, _, _ in pairs), re.I)
    rep = {o.upper(): n for o, n, _ in pairs}
    total, out = 0, []
    files = []
    for sp in spaces:
        files += syms.modules(sp)
    for path in files:
        text = open(path, 'rb').read().decode('latin1')
        new, n = pat.subn(lambda m: rep[m.group(1).upper()], text)
        new = '\r\n'.join(reflow(l) for l in new.split('\r\n'))
        too_long = [l for l in new.split('\r\n') if len(l.expandtabs(8)) > LIMIT]
        if too_long:
            sys.exit('rename: nothing written: %s would get a line longer than %d characters: %s'
                     % (path, LIMIT, too_long[0]))
        if n:
            out.append((path, new))
            total += n
            print('%-24s %5d replacements' % (os.path.relpath(path, syms.SRC), n))
    if not dry:
        for path, new in out:
            open(path, 'wb').write(new.encode('latin1'))
    print('rename: %d symbols, %d replacements%s' % (len(pairs), total, ' (dry run)' if dry else ''))
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scope', choices=syms.PROGRAMS + ['lib'])
    ap.add_argument('maps', nargs='+')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--only')
    a = ap.parse_args()
    rename(a.scope, load_maps(a.maps), a.dry, a.only)


if __name__ == '__main__':
    main()
