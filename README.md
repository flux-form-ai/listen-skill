# Listen: a Claude skill that measures audio it can't hear

Claude can write a script, pick a voice and polish a recording. It has no ears. Listen gives it the next best thing: the same readouts an audio engineer watches on the meters.

Built by [Jeremy Swiller](https://flux-form.com) at Flux+Form with Claude, while making the MindRight meditation app.

## What it measures

- Loudness (and whether you're far quieter than podcasts and music)
- Frequency balance across nine bands, like an equalizer
- Background noise and how far the voice sits above it
- Every pause and how long it runs
- Speaking pace in words per minute

It also keeps a list of what it **can't** judge (warmth, sincerity, whether a read sounds like an ad) so it never pretends. A human ear still makes the final call.

## Install it in Claude

1. [Download the skill (ZIP)](https://github.com/flux-form-ai/listen-skill/archive/refs/tags/v1.0.zip).
2. In Claude, open **Settings → Capabilities → Skills** and upload the ZIP.
3. Ask Claude something like "compare these two takes" or "why does this recording sound wrong?" and attach your audio.

The skill needs a Claude setup that can run code, and it uses ffmpeg to take its measurements.

## License

MIT. Use it, change it, share it.
