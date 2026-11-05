# Under the crossing, a May morning now (speculative), 5 November 2026

The user's idea: a speculative soundscape of the bed under the Enerhodar crossing now, the one line connected humming
in the background while the rewilded bed's birds and other animals call; 30 s, sound only, near the storyboard's end
(shot `under-the-crossing`, after `forest-or-reactor`). The picture is still to be speculated on.

`under_the_crossing.wav` (48 kHz stereo, 16 bit), `under_the_crossing.mp4` (the same on black, for the storyboard),
`under_the_crossing.json` (every layer: recording, segment, place, date, recordist, licence, distance, pan, level).
Made by `scripts/mix.py`; the recordings checked first by `scripts/spectro.py` (`check_spectrograms.png`) and
`scripts/screen.py` (`check_screen.json`).

**What it is:** a montage, said to be one. No one has recorded at the crossing since the breach (reports/Kakhovka bed
nature sounds.md), so nothing here is the crossing's own sound.
- 0-2.5 s the line alone fades in; 2.5-27.5 s the birds come in over it and go; 27.5-30 s the line alone again.
- Never more than three recordings at once (the user, 5 November 2026: the first mix, up to eight at once round
  13-24 s, was too busy). One near nightingale leads throughout; behind it three handovers: the reeds (2.5-12.5 s),
  the frog and a far nightingale answering (11.5-21 s), the chorus with a cuckoo and one hoopoe (20-27 s).
- The line: Ferosplavna-1 (330 kV), the one line the record has connected since 24 March 2026, synthesized with
  `hum.py`'s 330 kV voice (100 Hz and its harmonics, the 6th stressed, corona hiss and cracks). Centred, as from under
  the span. Its crackle is a little denser than the Hum's (6 cracks a second, not 3.5): a dewy morning, a design
  choice. It is about 7 dB under the birds and never reacts to them.
- The season is a morning in mid-May, the bed's one published soundscape: "hundreds of nightingales" (TSN, May 2026).

| Layer | What it holds | Recording | Where, when | Licence |
|---|---|---|---|---|
| reeds | great reed warbler, coot, bee-eater | iNat sound 1950258 (obs 361639437, 361639473, 361466739) | Mar'ianske, on the bed, 14 May 2026, ~50 km downstream | CC BY, Oleksii Vasyliuk |
| nightingale near | thrush nightingale | 1950271 (361637893) | the same | CC BY, Vasyliuk |
| chorus | nightingale, great reed and reed warblers, cuckoo | 1950176 (361639097, 361639110, 361639062, 361639005) | the same | CC BY, Vasyliuk |
| hoopoe | hoopoe | 1950256 (361466662) | the same | CC BY, Vasyliuk |
| nightingale far | thrush nightingale, a blue tit | xeno-canto XC1016141 | near Marhanets, north bank, 16 April 2025, ~9 km | CC0, Ekaterina Kormina |
| frog | marsh frog | iNat sound 997953 (obs 211010127) | near Kryvyi Rih, 28 April 2024, ~97 km, **not the bed** | CC BY, W.D. Keeper |

- The frog is the guess: no frog has been recorded or described on the bed. Keep it, swap it, or drop it.
- Processing: cut, high-passed at 250 Hz (the recorders' wind rumble), levelled, panned, faded; the birds' bus
  peak-limited, the whole at about -20 dBFS RMS, peaks under -1 dBFS. Never pitched, stretched, looped or reverberated.
- Left out since the first mix: a second nightingale on the bed (1950269) and the Savi's warbler (1950255).
- Screened: no second with a broadband transient (handling, wingbeats or a distant bang) is used. 1950255's 75-85 s
  (a broad hump of noise, possibly an engine) was never used, nor the drone-flagged 361467377 and 361134120 and the
  report's check-by-ear five. Checked by spectrogram; the user listened to the first mix (too busy at 13-24 s, so thinned).
- The downloads are in `raw/` (one folder per sound, `clips.tsv` with each observation's credit and URL).
- To credit on screen or in the credits: "Oleksii Vasyliuk (CC BY), Ekaterina Kormina (CC0), W.D. Keeper (CC BY), via
  iNaturalist and xeno-canto; the line synthesized".
