# Visualisation

This is the visualisation part of the RobotRace game. It takes the recorded game
(positions, health, gold pots, mines) and turns it into an animated gif.

## How to run

The visualisation runs automatically when you pass a `--viz` filename to the game:

```
python runRobotRace.py --viz game.gif --number 200 --theme desert
```

Useful flags:
- `--viz` : output filename for the gif
- `--number` : number of rounds
- `--framerate` : speed of the gif (lower = slower playback)
- `--theme` : visual theme (see below)

## Themes

There are five themes: `default`, `desert`, `forest`, `garden` and `island`.
Each theme defines its own wall, mine and gold images plus a floor colour. The
`default` theme uses plain shapes and no images.

If a theme is picked but one of its images can't be loaded (missing file, wrong
path, etc.) it falls back to the `default` theme instead of crashing. The default
theme is meant to always work, even if no image assets are present at all.

## What's shown

- **Walls** are drawn once at the start and saved as a background image, so they
  don't get redrawn every frame. This keeps the animation fast even on big maps.
- **Players** are little robot images. Instead of making a separate picture for
  each colour, there is one greyscale robot that gets tinted per player in the
  code (see `tint_image`). The tint only colours the light parts so the outline
  stays sharp.
- **Player colours** come from a hand-picked palette of distinct colours. If
  there are more players than colours in the palette, the rest are filled in from
  an hsv colourmap so we never run out.
- **Health** is shown as a small bar above each robot that shrinks as the player
  takes damage.
- **Gold pots** are images with a pulsing glow behind them (the glow speeds up
  the older the pot gets).
- **Mines** are images that appear and disappear as mines are set and expire.
- **Legend** at the bottom shows each robot in its colour with its name. It wraps
  to a new row after four players and shrinks the robots when there are many, so
  it still fits.
- **Counter** in the top left shows the current round.

## Updates

- All image paths are relative to the script itself, so the game can be run from
  any working directory (e.g. the repo root, not just the `Game` folder).
- The background image is written to a temporary file and deleted again, so no
  leftover files are created.


## Assets

All images live in the `illustrations/` folder.
