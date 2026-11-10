#!/usr/bin/env python3
"""Find word tables in the program modules: indexed word loads `mov r16, word ptr T[reg]` (and
`lea`/`add` forms) from a table T in the image. For each T, print its first words and what they
point to, to decide whether it holds addresses (then its words must be dw labels, phase 3).

    python3 tools/ptrtabs.py [TARGET ...]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u3an, genlib


def main():
    for t in [a for a in sys.argv[1:]] or ['ultima', 'bootup', 'exodus']:
        a = u3an.analyse(t)
        pad, lo, hi = genlib.RANGE[t]
        jt = set(u3an.TARGETS[t]['tables'])
        tabs = {}
        for pc, ins in sorted(a.insn.items()):
            if pad <= pc < hi or u3an.is_branch(ins):
                continue
            for op in u3an.operands(ins):
                if (op.type == 'mem' and op.size == 2 and op.disp_size == 2 and (op.base or op.index)
                        and 0x100 <= op.disp < a.end and not pad <= op.disp < hi and op.disp not in jt):
                    tabs.setdefault(op.disp, []).append(pc)
        print('==== %s' % t)
        for tb in sorted(tabs):
            words = [a.img[tb + 2 * i] | a.img[tb + 2 * i + 1] << 8 for i in range(12)]
            def what(v):
                if v in a.insn:
                    return 'c'
                if 0x100 <= v < a.end:
                    s = a.img[v:v + 8]
                    if all(32 <= c < 127 or c in (0, 10, 13) for c in s):
                        return 's'
                    return 'd'
                return '-'
            print('  %04X used at %s' % (tb, ' '.join('%04X' % p for p in tabs[tb][:4])))
            print('     ' + ' '.join('%04X%s' % (w, what(w)) for w in words))


if __name__ == '__main__':
    main()
