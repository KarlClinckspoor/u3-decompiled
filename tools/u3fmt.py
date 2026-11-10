#!/usr/bin/env python3
"""Readers and renderers for Ultima III's data files (docs/FORMATS.md).

    python3 tools/u3fmt.py shapes [OUT.png]          the 80 tiles of SHAPES.ULT, numbered
    python3 tools/u3fmt.py chars  [OUT.png]          the 128 characters of CHARSET.ULT
    python3 tools/u3fmt.py cga FILE.IBM [OUT.png]    a raw CGA screen (BLANK.IBM, EXOD.IBM)
    python3 tools/u3fmt.py map FILE.ULT [OUT.png]    an overworld, town or castle map + its tables
    python3 tools/u3fmt.py dungeon FILE.ULT [OUT.png] the eight levels of a dungeon + its messages
    python3 tools/u3fmt.py combat FILE.ULT|FILE.IMG [OUT.png]   a combat map (176 bytes) or picture map (121)
    python3 tools/u3fmt.py demo [OUT.png]            the title-screen strip (DEMO.ULT)
    python3 tools/u3fmt.py animate [OUT.png]         the intro's party-and-dragon sprites (ANIMATE.DAT)
    python3 tools/u3fmt.py name [OUT.png]            the title screen's wave line (NAME.DAT)
    python3 tools/u3fmt.py moves                     the title-screen script (MOVES.ULT), step by step
    python3 tools/u3fmt.py party [FILE]              PARTY.ULT, field by field
    python3 tools/u3fmt.py roster [FILE]             ROSTER.ULT, every used slot, field by field

Files are read from gamedata/ (or the path given). PNGs are written to build/formats/ when no
OUT is given. As a module: Shapes(), Charset(), cga_image(data), TownMap(data), ... below.
"""
import os, struct, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMEDATA = os.path.join(ROOT, 'gamedata')
OUTDIR = os.path.join(ROOT, 'build', 'formats')

# CGA mode 4, palette 1 (cyan, magenta, white), as ULTIMA.COM sets it (int 10h AH=0Bh BH=1 BL=1)
PALETTE = [(0, 0, 0), (0, 170, 170), (170, 0, 170), (170, 170, 170)]


# ---------------------------------------------------------------------------- PNG
def write_png(path, width, height, rows, palette=PALETTE):
    """rows: list of bytearrays of palette indices (one per pixel row). 8-bit paletted PNG."""
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b''.join(b'\0' + bytes(r) for r in rows)
    pal = b''.join(bytes(c) for c in palette)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 3, 0, 0, 0)))
        f.write(chunk(b'PLTE', pal))
        f.write(chunk(b'IDAT', zlib.compress(raw, 9)))
        f.write(chunk(b'IEND', b''))


class Canvas:
    def __init__(self, w, h, bg=0):
        self.w, self.h = w, h
        self.rows = [bytearray([bg]) * w for _ in range(h)]

    def blit(self, x, y, img, scale=1):
        """img: list of rows of pixel values."""
        for j, row in enumerate(img):
            for s in range(scale):
                dst = self.rows[y + j * scale + s]
                for i, v in enumerate(row):
                    for t in range(scale):
                        dst[x + i * scale + t] = v

    def save(self, path, palette=PALETTE):
        write_png(path, self.w, self.h, self.rows, palette)


def unpack2(b):
    """bytes -> list of 2-bit pixels, high bits first (CGA)."""
    out = []
    for v in b:
        out += [v >> 6, (v >> 4) & 3, (v >> 2) & 3, v & 3]
    return out


# ---------------------------------------------------------------------------- graphics
def tile_image(data, n):
    """Tile n of SHAPES.ULT: 16x16 pixels, 4 bytes a row, the eight even scan lines first,
    then the eight odd ones (the screen's two CGA banks), 64 bytes."""
    t = data[n * 64:n * 64 + 64]
    rows = [None] * 16
    for k in range(8):
        rows[2 * k] = unpack2(t[k * 4:k * 4 + 4])
        rows[2 * k + 1] = unpack2(t[32 + k * 4:32 + k * 4 + 4])
    return rows


def char_image(data, n):
    """Character n of CHARSET.ULT: 8x8 pixels, 2 bytes a row, even lines first, 16 bytes."""
    t = data[n * 16:n * 16 + 16]
    rows = [None] * 8
    for k in range(4):
        rows[2 * k] = unpack2(t[k * 2:k * 2 + 2])
        rows[2 * k + 1] = unpack2(t[8 + k * 2:8 + k * 2 + 2])
    return rows


def cga_image(data):
    """A raw CGA screen: bank 0 (even lines) 8000 bytes + 192 unused, then bank 1."""
    rows = []
    for y in range(200):
        base = (y & 1) * 0x2000 + (y >> 1) * 80
        rows.append(unpack2(data[base:base + 80]))
    return rows


def read(name):
    p = name if os.path.exists(name) else os.path.join(GAMEDATA, name)
    return open(p, 'rb').read()


# ---------------------------------------------------------------------------- maps
# TILES: the shape number of a map byte is byte >> 2 (the low two bits are not used by the
# program's tile lookup); shapes above 63 are not map tiles.
class TownMap:
    """SOSARIA/AMBROSIA/BRITISH... .ULT: 4648 bytes, loaded at 0100 by EXODUS.BIN."""
    SIZE = 4648

    def __init__(self, data):
        assert len(data) == self.SIZE, len(data)
        self.data = data
        self.tiles = data[:4096]                    # 64 x 64, row by row
        # the offset table is as long as the first offset says (the first string follows it)
        first = struct.unpack('<H', data[0x1000:0x1002])[0]
        self.text_table = struct.unpack('<%dH' % (first // 2), data[0x1000:0x1000 + first]) if first else ()
        self.text = data[0x1000:0x1180]             # the offset table, then the speeches (NUL ended)
        self.npc_tile = data[0x1180:0x11A0]         # 32 slots; 16 used in a town
        self.npc_move = data[0x11A0:0x11C0]       # movement code (high nibble ...)
        self.npc_x = data[0x11C0:0x11E0]
        self.npc_y = data[0x11E0:0x1200]
        self.npc_talk = data[0x1200:0x1220]
        self.state = data[0x1220:0x1228]            # moons (overworld) - see FORMATS.md

    def speeches(self):
        """The speeches the offset table points to (offsets are from the start of the text
        area, 0x1000 in the file; a town has 4 to 8)."""
        out = []
        for o in self.text_table:
            if o:
                e = self.text.index(0, o)
                out.append(self.text[o:e].decode('latin1'))
        return out


class Dungeon:
    """DARDIN/FIRE/MINE/PERINIAN/TIME/M/P .ULT: 2192 bytes, loaded at 0900."""
    SIZE = 2192

    def __init__(self, data):
        assert len(data) == self.SIZE, len(data)
        self.levels = [data[i * 256:(i + 1) * 256] for i in range(8)]   # 16 x 16 each
        self.extra = data[0x800:]
        self.text_table = struct.unpack('<8H', self.extra[:16])        # offsets from 0x800

    def messages(self):
        out = []
        for o in self.text_table:
            e = self.extra.index(0, o)
            out.append(self.extra[o:e].decode('latin1'))
        return out


class Combat:
    """CNFLCT_*.ULT: 176 bytes, loaded at 24C4: an 11x11 map (shape numbers) plus the start
    positions of the monsters and the party. The four .IMG files are only the 121-byte map."""
    def __init__(self, data):
        assert len(data) in (121, 176), len(data)
        self.tiles = data[:121]
        self.extra = data[121:]

    def arrays(self):
        e = self.extra
        if not e:
            return {}
        return {'unknown': e[0:7], 'monster_x': e[7:15], 'monster_y': e[15:23], 'monster_5': e[23:31],
                'monster_6': e[31:39], 'pc_x': e[39:43], 'pc_y': e[43:47], 'pc_a': e[47:51], 'pc_b': e[51:55]}


# ---------------------------------------------------------------------------- characters
RACES = {'H': 'Human', 'E': 'Elf', 'D': 'Dwarf', 'B': 'Bobbit', 'F': 'Fuzzy'}
CLASSES = {'F': 'Fighter', 'C': 'Cleric', 'W': 'Wizard', 'T': 'Thief', 'P': 'Paladin', 'L': 'Lark',
           'B': 'Barbarian', 'D': 'Druid', 'I': 'Illusionist', 'A': 'Alchemist', 'R': 'Ranger'}
SEXES = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
STATUS = {'G': 'Good', 'P': 'Poisoned', 'D': 'Dead', 'A': 'Ashes'}
WEAPONS = ['Hand', 'Dagger', 'Mace', 'Sling', 'Axe', 'Bow', 'Sword', '2-H-Swd', '+2 Axe', '+2 Bow',
           '+2 Swd', 'Gloves', '+4 Axe', '+4 Bow', '+4 Swd', 'Exotic']
ARMOURS = ['Skin', 'Cloth', 'Leather', 'Chain', 'Plate', '+2 Chain', '+2 Plate', 'Exotic']


def bcd(b):
    """Packed BCD bytes, least significant byte first -> int (None if a nibble is not a digit)."""
    v = 0
    for x in reversed(b):
        if (x >> 4) > 9 or (x & 15) > 9:
            return None
        v = v * 100 + (x >> 4) * 10 + (x & 15)
    return v


class Character:
    """One 64-byte record (ROSTER.ULT has 20; PARTY.ULT carries 4 after its 18-byte header)."""
    SIZE = 64

    def __init__(self, r):
        assert len(r) == 64
        self.r = r

    def name(self):
        return self.r[:10].split(b'\0')[0].decode('latin1')

    def fields(self):
        r = self.r
        L = lambda o: chr(r[o]) if 32 <= r[o] < 127 else '%02X' % r[o]
        return [
            ('00-09 name (9 letters + NUL)', self.name()),
            ('0A-0D', r[0x0A:0x0E].hex(' ')),
            ('0E marks (bits 7-4) cards (3-0)', '%02X' % r[0x0E]),
            ('0F torches', bcd(r[0x0F:0x10])),
            ('10 party flag', {0: 'not in party', 255: 'in party'}.get(r[0x10], '%02X' % r[0x10])),
            ('11 status', '%s (%s)' % (L(0x11), STATUS.get(chr(r[0x11]), '?'))),
            ('12 strength', bcd(r[0x12:0x13])),
            ('13 dexterity', bcd(r[0x13:0x14])),
            ('14 intelligence', bcd(r[0x14:0x15])),
            ('15 wisdom', bcd(r[0x15:0x16])),
            ('16 race', '%s (%s)' % (L(0x16), RACES.get(chr(r[0x16]), '?'))),
            ('17 class', '%s (%s)' % (L(0x17), CLASSES.get(chr(r[0x17]), '?'))),
            ('18 sex', '%s (%s)' % (L(0x18), SEXES.get(chr(r[0x18]), '?'))),
            ('19 magic points', bcd(r[0x19:0x1A])),
            ('1A-1B hit points', bcd(r[0x1A:0x1C])),
            ('1C-1D max hit points', bcd(r[0x1C:0x1E])),
            ('1E-1F experience', bcd(r[0x1E:0x20])),
            ('20 food, hundredths', bcd(r[0x20:0x21])),
            ('21-22 food', bcd(r[0x21:0x23])),
            ('23-24 gold', bcd(r[0x23:0x25])),
            ('25 gems', bcd(r[0x25:0x26])),
            ('26 keys', bcd(r[0x26:0x27])),
            ('27 powders', bcd(r[0x27:0x28])),
            ('28 armour worn', ARMOURS[r[0x28]] if r[0x28] < 8 else '%02X' % r[0x28]),
            ('29-2F armours owned', ' '.join('%d' % bcd(r[0x29 + i:0x2A + i]) if bcd(r[0x29 + i:0x2A + i]) is not None else '??' for i in range(7))),
            ('30 weapon readied', WEAPONS[r[0x30]] if r[0x30] < 16 else '%02X' % r[0x30]),
            ('31-3F weapons owned', ' '.join('%d' % bcd(r[0x31 + i:0x32 + i]) if bcd(r[0x31 + i:0x32 + i]) is not None else '??' for i in range(15))),
        ]


class Party:
    """PARTY.ULT: 274 bytes = an 18-byte header and four character records."""
    SIZE = 274

    def __init__(self, data):
        assert len(data) == self.SIZE, len(data)
        self.head = data[:18]
        self.chars = [Character(data[18 + 64 * i:18 + 64 * (i + 1)]) for i in range(4)]

    def fields(self):
        h = self.head
        return [
            ('00 transport (tile)', '%02X' % h[0]),
            ('01', '%02X' % h[1]),
            ('02 location', {0: 'Sosaria', 1: 'dungeon', 0xFF: 'Ambrosia'}.get(h[2], '%02X (see FORMATS.md)' % h[2])),
            ('03-06 move counter (BCD, 8 digits)', bcd(h[3:7])),
            ('07 party size', h[7]),
            ('08-09 x, y', '%d, %d' % (h[8], h[9])),
            ('0A-0D', h[10:14].hex(' ')),
            ('0E-11 flags gating the top weapon/armour menu entries (FF = not found)', h[14:18].hex(' ')),
        ]


# ---------------------------------------------------------------------------- title screen files
def animate_images():
    """ANIMATE.DAT: 4 images (the party facing the dragon) x 4 copies shifted by one pixel each
    (so the program can move them in steps of a pixel) x 16 rows x 23 bytes (92 pixels)."""
    a = read('ANIMATE.DAT')
    return [[[unpack2(a[(i * 4 + s) * 368 + r * 23:(i * 4 + s) * 368 + (r + 1) * 23]) for r in range(16)]
             for s in range(4)] for i in range(4)]


def name_points():
    """NAME.DAT: (x, y) pairs up to the first x = 0 (266 of them), plotted two cells wide by
    ULTIMA.COM at 5E68 with y counted from the bottom (192 - y)."""
    d = read('NAME.DAT')
    pts = []
    for i in range(0, len(d), 2):
        if d[i] == 0:
            break
        pts.append((d[i], d[i + 1]))
    return pts


def moves_script():
    """MOVES.ULT: 512 steps. Step i: cell = data[i], value = data[512 + i]. cell 0xFF = pause of
    `value` rounds; otherwise DEMO strip cell `cell` becomes value >> 1 (redrawn when >= 8)."""
    d = read('MOVES.ULT')
    return [(d[i], d[512 + i]) for i in range(512)]


# ---------------------------------------------------------------------------- rendering
def sheet(path, data, n, kind):
    cols = 16 if kind == 'tile' else 16
    size = 16 if kind == 'tile' else 8
    rows = (n + cols - 1) // cols
    sc = 2
    cell = size * sc + 2
    c = Canvas(cols * cell, rows * cell, 0)
    for i in range(n):
        img = tile_image(data, i) if kind == 'tile' else char_image(data, i)
        c.blit((i % cols) * cell + 1, (i // cols) * cell + 1, img, sc)
    c.save(path)


def render_map(path, m, scale=1):
    sh = read('SHAPES.ULT')
    c = Canvas(64 * 16 * scale, 64 * 16 * scale)
    cache = {}
    for y in range(64):
        for x in range(64):
            t = m.tiles[y * 64 + x] >> 2
            if t not in cache:
                cache[t] = tile_image(sh, t) if t < 80 else [[0] * 16] * 16
            c.blit(x * 16 * scale, y * 16 * scale, cache[t], scale)
    for i in range(32):                          # the monsters/NPCs of the file
        if m.npc_tile[i]:
            t = m.npc_tile[i] >> 2
            if t < 80:
                x, y = m.npc_x[i], m.npc_y[i]
                if x < 64 and y < 64:
                    c.blit(x * 16 * scale, y * 16 * scale, tile_image(sh, t), scale)
    c.save(path)


def render_grid(path, grid, w, h, scale=2):
    """A w x h map of shape numbers (combat maps), drawn with the tiles."""
    sh = read('SHAPES.ULT')
    c = Canvas(w * 16 * scale, h * 16 * scale)
    for y in range(h):
        for x in range(w):
            t = grid[y * w + x]
            if t < 80:
                c.blit(x * 16 * scale, y * 16 * scale, tile_image(sh, t), scale)
    c.save(path)


def render_dungeon(path, d):
    """Each level as a 16x16 grid of the byte values in hex (no graphics for them are known)."""
    # small 3x5 digit font
    F = {'0': '111101101101111', '1': '010110010010111', '2': '111001111100111', '3': '111001111001111',
         '4': '101101111001001', '5': '111100111001111', '6': '111100111101111', '7': '111001001001001',
         '8': '111101111101111', '9': '111101111001111', 'A': '111101111101101', 'B': '110101110101110',
         'C': '111100100100111', 'D': '110101101101110', 'E': '111100110100111', 'F': '111100110100100'}
    cell, sc = 9, 2
    W = 4 * (16 * cell * sc + 8)
    H = 2 * (16 * cell * sc + 8)
    c = Canvas(W, H)
    for lv in range(8):
        ox = (lv % 4) * (16 * cell * sc + 8)
        oy = (lv // 4) * (16 * cell * sc + 8)
        for y in range(16):
            for x in range(16):
                v = d.levels[lv][y * 16 + x]
                col = 0 if v == 0 else 3 if v == 0x80 else 1 if v & 0x80 == 0 else 2
                for k, ch in enumerate('%02X' % v):
                    g = F[ch]
                    img = [[col if g[j * 3 + i] == '1' else 0 for i in range(3)] for j in range(5)]
                    c.blit(ox + (x * cell + k * 4) * sc, oy + (y * cell + 1) * sc, img, sc)
    c.save(path)


# ---------------------------------------------------------------------------- command line
def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    cmd, rest = a[0], a[1:]
    out = lambda default: (rest[-1] if rest and rest[-1].lower().endswith('.png') else os.path.join(OUTDIR, default))
    if cmd == 'shapes':
        p = out('shapes.png')
        sheet(p, read('SHAPES.ULT'), 80, 'tile')
        print(p)
    elif cmd == 'chars':
        p = out('charset.png')
        sheet(p, read('CHARSET.ULT'), 128, 'char')
        print(p)
    elif cmd == 'cga':
        data = read(rest[0])
        rows = cga_image(data)
        p = out(os.path.splitext(os.path.basename(rest[0]))[0].lower() + '.png')
        write_png(p, 320, 200, [bytearray(r) for r in rows])
        print(p)
    elif cmd == 'map':
        m = TownMap(read(rest[0]))
        p = out(os.path.splitext(os.path.basename(rest[0]))[0].lower() + '.png')
        render_map(p, m)
        print(p)
        print('text offsets:', ' '.join('%04X' % o for o in m.text_table))
        for i, s in enumerate(m.speeches()):
            print('  speech %d: %r' % (i, s))
        print('npc tile :', m.npc_tile[:16].hex(' '))
        print('npc move :', m.npc_move[:16].hex(' '))
        print('npc x    :', m.npc_x[:16].hex(' '))
        print('npc y    :', m.npc_y[:16].hex(' '))
        print('npc talk :', m.npc_talk[:16].hex(' '))
        print('state    :', m.state.hex(' '))
    elif cmd == 'dungeon':
        d = Dungeon(read(rest[0]))
        p = out(os.path.splitext(os.path.basename(rest[0]))[0].lower() + '.png')
        render_dungeon(p, d)
        print(p)
        for i, s in enumerate(d.messages()):
            print('  message %d: %r' % (i, s))
        print('tail after the messages:', d.extra[d.extra.rindex(b'!') + 1:].hex(' ') if b'!' in d.extra else '')
    elif cmd == 'combat':
        c = Combat(read(rest[0]))
        p = out(os.path.splitext(os.path.basename(rest[0]))[0].lower() + '.png')
        render_grid(p, c.tiles, 11, 11)
        print(p)
        for k, v in c.arrays().items():
            print('  %-10s %s' % (k, v.hex(' ')))
    elif cmd == 'demo':
        p = out('demo.png')
        render_grid(p, read('DEMO.ULT'), 19, 6)
        print(p)
    elif cmd == 'animate':
        imgs = animate_images()
        c = Canvas(4 * 98 * 2, 4 * 19 * 2)
        for i in range(4):
            for sft in range(4):
                c.blit(sft * 98 * 2, i * 19 * 2, imgs[i][sft], 2)
        p = out('animate.png')
        c.save(p)
        print(p)
    elif cmd == 'name':
        pts = name_points()
        c = Canvas(260 * 2, 40 * 2)
        for x, y in pts:
            for dx in (0, 1):
                if x + dx < 260 and 0 <= y - 20 < 40:
                    c.rows[(y - 20) * 2][(x + dx) * 2] = 3
        p = out('name.png')
        c.save(p)
        print(p, len(pts), 'points')
    elif cmd == 'moves':
        for i, (cell, val) in enumerate(moves_script()):
            print('%3d  %s' % (i, 'pause %d' % val if cell == 0xFF else 'cell %3d <- %02X' % (cell, val >> 1)))
    elif cmd == 'check':
        # every data file parses, with the sizes the programs load (docs/FORMATS.md)
        n = 0
        for f in sorted(os.listdir(GAMEDATA)):
            u = f.upper()
            if not u.endswith(('.ULT', '.IMG', '.DAT', '.IBM')) or u.startswith('UNINS'):
                continue
            d = read(f)
            if u.startswith('CNFLCT') or u.endswith('.IMG'):
                Combat(d)
            elif u == 'PARTY.ULT':
                Party(d)
            elif u == 'ROSTER.ULT':
                assert len(d) == 1280
                [Character(d[i * 64:i * 64 + 64]).fields() for i in range(20)]
            elif u in ('SHAPES.ULT',):
                assert len(d) == 80 * 64
            elif u == 'CHARSET.ULT':
                assert len(d) == 128 * 16
            elif u.endswith('.IBM'):
                assert len(d) == 16384
            elif u == 'DEMO.ULT':
                assert len(d) == 19 * 6
            elif u == 'MOVES.ULT':
                assert len(d) == 1024
            elif u == 'NAME.DAT':
                assert len(name_points()) == 266
            elif u == 'ANIMATE.DAT':
                assert len(d) == 5888
            elif u == 'DUNGEON.DAT':
                assert d[0] == 0xE9      # a jmp: code, not data
            elif len(d) == 4648:
                m = TownMap(d)
                if any(m.text_table):
                    m.speeches()
            elif len(d) == 2192:
                Dungeon(d).messages()
            else:
                print('unknown', f, len(d))
                continue
            n += 1
        print('%d data files parse' % n)
    elif cmd == 'party':
        pt = Party(read(rest[0] if rest else 'PARTY.ULT'))
        for k, v in pt.fields():
            print('  %-34s %s' % (k, v))
        for i, ch in enumerate(pt.chars):
            print('character %d: %r' % (i + 1, ch.name()))
    elif cmd == 'roster':
        data = read(rest[0] if rest else 'ROSTER.ULT')
        for i in range(20):
            ch = Character(data[i * 64:(i + 1) * 64])
            if not any(ch.r):
                continue
            print('slot %d' % (i + 1))
            for k, v in ch.fields():
                print('  %-24s %s' % (k, v))
        if not any(data):
            print('(all 20 slots empty)')
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
