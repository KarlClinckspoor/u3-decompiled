# Notes of worker bu (BOOTUP: BDATA, TITLE, ORGANIZE, CREATE; ULTIMA: UDATA, INTRO)

## Corrections to the docs

- **NAME.DAT is the "Lord British" signature**, not a wavy line: its 266 points span x 107-235,
  y 129-144 on the screen, the handwritten "Lord British" after "by" under "Ultima III" in
  EXOD.IBM. DrawSignature (ULTIMA 5E68) writes it point by point (FORMATS.md 7, MAP.md).
- **New characters get one Dagger and one Cloth** (BOOTUP 1B1B: +31h = 1, 1B1F: +29h = 1),
  not Hand/Skin: EXODUS indexes the counts as `[bx+di+30h]` / `[bx+di+28h]` with the kind in
  DI (EQUIP 8140, PARTY 6F1C), so +31h is weapon kind 1 and +29h armour kind 1. Readied
  weapon (+30h) and worn armour (+28h) stay 0 (Hand, Skin). FORMATS.md 6 says Skin/Hand.
- **The status key string at BOOTUP 0D5D is "GPDP"**, not "GPDA" (typo in the game). It
  still works: a letter not found gives the last name, "Ashes".
- **lib-core.map: ReadLine returns the length in BX**, not CX (LIB 45E2 `sub bx, cx`; CX is
  saved; BOOTUP 1BDF and the library's ReadNumber 49B9 use BX).
- BOOTUP's L01C6 (PARTY.ULT header +0A-0D) holds the **roster numbers (1-20) of the four
  members**: FORMATS.md 6 says "not read directly" (true for EXODUS only).

## Things the code shows

- **The scenario-disk prompt in BOOTUP is disabled by a patched byte**: L1DC6, called at
  start-up, is a `ret` (C3) written over the B6 of `mov dh, 17h`. The dead rest (1DC7-1E0B)
  prints "<Insert Scenario Disk>" (0C90, after "CHARSET.ULT"), calls DiskCheckStub into L01B9
  and lets the player pick drive 1-4 / A-D (DOS 0Eh). So L01B9 stays 0 and "(Strange Disk)"
  cannot appear. Together with ULTIMA's stub returning 0 this is the whole protection removal.
- **FormParty's "No Active Players" test is misplaced or reversed** (BOOTUP 182A): AnyAlive
  runs before RosterToParty, on the old party records (zero after Disperse), and refuses if
  one of them is alive. A party of dead characters can therefore be formed; JourneyOnward
  then refuses it with "(No Active Players)".
- FormParty: a bad entry ("No one there", "Already Selected", a number over 20) cancels the
  whole party being chosen, not just that entry. EnterCharacter: points not spent are lost
  (wisdom only has to be at most what is left).
- The intro: "Exodus" and "Ultima III" dissolve in with speaker static (CopyPicture with a
  pseudo-random threshold, ULTIMA 5F6C); the party (BLANK.IBM already shows party and dragon)
  walks right, left, right (AnimateParty, 3 phases); the dragon's fire (EXOD.IBM lines
  168-183) with a roar of random speaker toggles; then picture lines 152-167 (a dragon not
  breathing, empty ground) replace it: the party is gone. Every step stops on a key.
- DrawAnimFrame's x is in 2-pixel units (pixel = 2x+20), so only shifts 0 and 2 of the four
  one-pixel shifts in ANIMATE.DAT are ever used.
- SetGraphicsMode (ULTIMA 607E): on a mono adapter it tests B800 RAM and the BIOS equipment
  word, then switches the initial-video bits from mono to 80x25 colour; failure prints
  "Unable to access graphics display." and hangs (with ES still pushed; harmless).
- BOOTUP never sets a video mode or clears the screen: it draws its frame (text rows 10-23)
  under the intro's "Exodus" title, which stays visible (probably intended).
- Both programs set the library's location byte (X01BE) to 1 so KeyReady does not run the
  tile animations; BOOTUP animates the title explicitly (AnimateDemo). Form saves PARTY.ULT
  with location 0 and sets it back to 1.
- The int 24h handler in BOOTUP is `mov al,1` at the end of BDATA (1207) falling into the
  `iret` that starts TITLE (1209).
- ExamineRegister 1974 `mov bl, al` has no effect. LookAtChar's party lookup falls back to
  party slot 4 if the number is not found (cannot happen in practice).

## Open questions

- K2AD8 (choose from a list: CX keys at DI, names at SI, shows the name, Enter confirms,
  Backspace/Left retries; AL = the key) and K2BA0 (save CX bytes at BX as the file at DX):
  my reading, names for the library owner.
- What ReadNumber/ParseNumber return for an empty line (FormParty ends the list on AL = 0).
- Why PARTY.ULT could hold living records while the party size is 0 (the only case where
  FormParty's AnyAlive test bites).
