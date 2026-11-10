#!/usr/bin/env python3
"""Play a build in a DOSBox window with GOG's settings (svga_s3, 300 cycles, PC speaker).

    python3 tools/play.py [BUILDDIR] [--dir DIR] [--cycles N]

BUILDDIR holds the built programs as tools/build.py or tools/shift.py leave them: TARGET/FILE
for each of ultima, bootup and exodus (default build/, i.e. the identical build; build/shift for
the shifted one). The game's data files (maps, shapes, roster, party, pictures) are copied from
gamedata/ into DIR (default build/play) once, and the three programs next to them, so
gamedata/ is never written to; delete DIR to start again from GOG's roster and party.
Quit with ctrl-F9 or by closing the window.
"""
import argparse, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import dos, u3an

CONF = """[sdl]
fullscreen=false
windowresolution=original
output=surface
[dosbox]
machine=svga_s3
memsize=16
[render]
aspect=false
scaler=normal2x
[cpu]
core=simple
cputype=386_slow
cycles={cycles}
[speaker]
pcspeaker=true
[autoexec]
mount c "{dir}"
c:
ultima.com
exit
"""
DATA = ('.ULT', '.DAT', '.IBM', '.IMG')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('builddir', nargs='?', default=os.path.join(ROOT, 'build'))
    ap.add_argument('--dir', default=os.path.join(ROOT, 'build', 'play'))
    ap.add_argument('--cycles', default='300')
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    for f in os.listdir(u3an.GAMEDATA):
        if f.upper().endswith(DATA) and not os.path.exists(os.path.join(a.dir, f)):
            shutil.copy(os.path.join(u3an.GAMEDATA, f), os.path.join(a.dir, f))
    for t, d in u3an.TARGETS.items():
        src = os.path.join(a.builddir, t, d['file'])
        if not os.path.exists(src):
            sys.exit('missing %s (build it first)' % src)
        shutil.copy(src, os.path.join(a.dir, d['file']))
    fd, conf = tempfile.mkstemp(suffix='.conf')
    with os.fdopen(fd, 'w') as f:
        f.write(CONF.format(cycles=a.cycles, dir=os.path.abspath(a.dir)))
    try:
        subprocess.run([dos.DOSBOX, '-conf', conf] + (['-noconsole'] if os.name == 'nt' else []),
                       cwd=os.path.dirname(conf))
    finally:
        os.unlink(conf)


if __name__ == '__main__':
    main()
