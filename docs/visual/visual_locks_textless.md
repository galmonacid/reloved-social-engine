# ReLoved visual locks v1

The application builds image prompts itself. The language model never writes an
image prompt and images must not contain readable words, labels, notes, prices,
signage, receipts or logos. Slide copy is always rendered afterwards by the
local overlay module.

The three permitted scenes are `FLAT`, `STREET` and `SHOP`. Each is locked to
casual iPhone realism in recognisably British settings: natural light, ordinary
wear, slight camera grain, no staged or cinematic treatment and no American
visual cues. Scene sequences are defined per pillar in
`reloved_engine.image_prompt_builder`.

## Overlay specification

- Canvas: 1080 × 1920 pixels (9:16).
- Safe text area: x=90, y=160, width=900, maximum height=520.
- Legibility: black rounded rectangle at 45% opacity.
- Typeface: bold Arial where present, otherwise DejaVu Sans Bold.
- Size: hook up to 104px; remaining slides up to 76px; never smaller than 58px.
- Alignment: left. A draft that cannot fit in three lines is rejected rather
  than rendered unreadably.

Raw images are stored under `jobs/<date>/assets/<post-id>/raw/`; overlaid
final images are stored under the sibling `final/` directory. Both are ignored
by Git.
