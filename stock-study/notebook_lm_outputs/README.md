# NotebookLM Outputs

Drop the audio overviews, slide decks, and videos you generate from
[NotebookLM](https://notebooklm.google.com) into the matching subfolder.

## Convention

One subfolder per source text file. Inside each, drop whatever NotebookLM
generates. Suggested naming:

```
focused-large-cap/
├── audio.mp3          ← Audio Overview (the 2-host podcast)
├── deck.pdf           ← Slide deck export
├── transcript.txt     ← (optional) if you save the transcript
└── video.mp4          ← Video Overview
```

## Folders

| Folder | Source text | Typical use |
|---|---|---|
| `focused-large-cap/` | `audio_source/focused-large-cap.txt` | 34 highest-conviction names |
| `large-cap/` | `audio_source/large-cap.txt` | 62-name full large-cap guide |
| `mid-cap/` | `audio_source/mid-cap.txt` | 83-name mid-cap guide |
| `small-cap/` | `audio_source/small-cap.txt` | 90-name small-cap guide |
| `micro-cap/` | `audio_source/micro-cap.txt` | 79-name micro-cap guide |
| `district-tour/` | `audio_source/all-funds-district-tour.txt` | Short overview of the whole city |
| `universe/` | `audio_source/all-funds-universe.txt` | Every company across all funds |

## Not in git

This folder is `.gitignore`d for audio/video/PDF files — those are
regeneratable from the text source and would bloat the repo. The folder
structure itself and this README are committed so the convention is
documented, but your actual MP3s/MP4s/PDFs stay on your machine only.

If you ever need to regenerate from scratch:

1. Re-export source text: `cd stock-study && python3 scripts/export_audio_text.py`
2. Upload a `.txt` from `audio_source/` to NotebookLM
3. Generate Audio Overview / Slide Deck / Video Overview
4. Download the outputs and drop them into the matching subfolder here

## Version tracking

NotebookLM outputs are tied to a specific snapshot of the source text
(which is tied to a specific snapshot of the holdings CSVs). If you
regenerate an asset after holdings change, the old one is no longer
accurate. Two options:

- **Overwrite** — simplest, always have the latest
- **Archive** — rename old files with a date suffix before regenerating:
  ```
  audio-2026-04-23.mp3  ← older
  audio.mp3             ← latest
  ```

No strong recommendation either way — depends on whether you ever want
to hear an older version of the story.
