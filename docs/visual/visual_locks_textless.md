# ReLoved visual locks v1

The application builds image prompts itself. The language model never writes an
image prompt and images must not contain readable words, labels, notes, prices,
signage, receipts or logos. Slide copy is always rendered afterwards by the
local overlay module.

The three permitted scenes are `FLAT`, `STREET` and `SHOP`. Each is locked to
casual iPhone realism in recognisably Milton Keynes settings: natural light,
ordinary wear, slight camera grain, no staged or cinematic treatment and no
American visual cues. Street scenes use plausible local cues such as mixed
red-brick and modern housing, green verges, broad pavements and redway-style
shared paths. They do not depend on landmarks or readable place signage.
Scene sequences are defined per pillar in
`reloved_engine.image_prompt_builder`.

For backwards compatibility, `FLAT` remains the scene-plan key, but its visual
lock represents a typical modest Milton Keynes family home. Interiors are
comfortably cluttered with the believable accumulation of busy family life—such
as coats, shoes, toys, laundry, post and crowded shelves—without appearing dirty
or hoarded. Minimalist, luxury and show-home styling are explicitly excluded so
unused household items feel natural in the setting.

The closing slide has an additional ReLoved mood lock: bright, warm and quietly
optimistic late-afternoon light, with cream, honey and soft green tones. Visible
weather must be clear and dry. Cloudy skies, flat grey or blue-grey light,
gloom, harsh contrast and artificial saturation are explicitly excluded.

## Cost control

The engine generates three unique visuals for source slides 1, 3 and 6. It
reuses them locally across slide pairs 1–2, 3–4 and 5–6, preserving the
six-slide carousel while halving API image requests. The default model is
`gpt-image-1-mini` at explicit `medium` quality so a provider `auto` setting
cannot silently select a more expensive tier.

## Overlay specification

- Canvas: 1080 × 1920 pixels (9:16).
- Safe text area: x=90, y=300, width=900, maximum height=520. The 300px top
  inset keeps Reel copy below Instagram's account and audio overlays.
- Legibility: black rounded rectangle at 45% opacity.
- Typeface: bold Arial where present, otherwise DejaVu Sans Bold.
- Size: hook up to 104px; remaining slides up to 76px; never smaller than 58px.
- Alignment: left. A draft that cannot fit in three lines is rejected rather
  than rendered unreadably.

Raw images are stored under `jobs/<date>/assets/<post-id>/raw/`; overlaid
final images are stored under the sibling `final/` directory. Both are ignored
by Git.
