---
name: listen
description: Objectively measure an audio or video file's acoustics: loudness, frequency balance (EQ), background noise, every pause, speech-to-silence ratio and speaking pace. Use when comparing a recording to a reference, when a take "sounds wrong" and you need to know what actually differs, before re-recording AI voiceover or narration, or when building a target profile from example files. Triggers on: analyze this audio, why does this sound wrong, compare these takes, match this reference, check the EQ, how fast is this, measure the pauses, background noise, what changed between these two files.
---

# listen: measure a recording, don't guess at it

## Read this first: what this skill cannot do

**Claude has no audio input.** This skill does not listen. It runs `ffmpeg`
measurements and reports numbers, the way an engineer reads an equalizer.

It **can** measure: duration, sample rate, bitrate, integrated loudness (LUFS),
true peak, loudness range, frequency balance across nine octave bands,
background noise floor, how far the voice sits above that floor, every pause
and its length, speech-to-silence ratio, and speaking pace in words per minute.

It **cannot** measure: tone, warmth, sincerity, accent, whether a voice sounds
rushed, whether a read sounds like an ad, or whether a sound bed sounds real.
Those need a person. **Never report them as if they were measured**, and never
tell the user Claude listened to something.

## The rule that makes the numbers trustworthy

Pause detection depends entirely on where you draw the silence threshold.
The same file measured at −40 dB and −50 dB can report 159 wpm and 121 wpm,
two verdicts that contradict each other.

**This skill pins the threshold at −35 dB over 0.35 s** and prints it in every
report.

Three rules follow:
1. **Never change the threshold to make a result look better.** If you change
   it, re-measure everything it is being compared against.
2. **Level-match before comparing two files.** An absolute dB threshold on
   files at different loudness is not a comparison. Normalize both to the same
   LUFS first, or the quieter file will report far more "silence".
3. **Prefer wall-clock pace over speaking pace when the script adds ellipses
   or breaks.** Punctuation-driven micro-gaps get scored as silence, which
   inflates the speaking-only figure. The report prints both. Say which you
   used.

## Requirements

`ffmpeg` and `ffprobe` installed and on the PATH. Python 3, standard library only.

## Usage

```bash
python3 reference/analyze_audio.py <file> [--script script.txt] [--label NAME] [--json]
```

- `--script` supplies the spoken text so pace can be computed. Without it,
  everything except words per minute still works.
- `--json` emits the full structure including every pause position, for
  diffing two takes or building a target profile.
- Works on video files too; `ffmpeg` reads the audio track directly.

## Workflow: building a target profile from reference material

1. Get two or three reference files of the style you want onto disk.
2. Run the analyzer on each.
3. Take the median of each metric. That is the target.
4. Run it on the current take. Diff against the target.
5. Turn the diff into direction: voice settings, script punctuation, pause
   lengths, EQ. Give the direction the measured delta, not an adjective.

## Workflow: diagnosing a rejected take

Run it on the rejected take *and* the previous version, level-matched, then
read the deltas. Typical complaints and where they show up:

| Complaint | Look at | Signature |
|---|---|---|
| "speed-reading" | `wpm_speech_only` | up vs the reference |
| "feels rushed" | `pause_count`, `longest_pause_s` | pauses short or missing |
| "sounds clinical / dead" | `noise_floor_db` | floor far lower than reference |
| "muffled" / "dull" | `octave_bands_db` at 4k to 16k | rolled off vs reference |
| "harsh" / "sibilant" | `octave_bands_db` at 4k to 8k | raised vs reference |
| "thin" | `octave_bands_db` at 63 to 250 | low vs reference |
| "inconsistent" | `loudness.lra` | loudness range much wider |
| "too quiet next to other apps" | `loudness.lufs` | well below about −16 LUFS |

These are leads, not verdicts. When the numbers and a human ear disagree,
the ear wins and the measurement gets checked.

## Getting a word count when there is no script

Pace needs a word count. If there is no script, transcribe the file first with
any speech-to-text tool that returns the text, then pass it with `--script`.

## Credits

Built by Jeremy Swiller ([Flux+Form](https://flux-form.com)) with Claude,
while making the MindRight meditation app. MIT licensed: use it, change it,
share it.
