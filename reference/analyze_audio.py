#!/usr/bin/env python3
"""
listen: objective acoustic analysis of an audio or video file.

Measures what a machine can measure and REFUSES to guess at what it can't.
Output is plain numbers you can hand to a voice director, a person or another skill.

Usage:
  python3 analyze_audio.py <file> [--script script.txt] [--label NAME] [--json]

Requires ffmpeg and ffprobe on the PATH.
Built by Jeremy Swiller (Flux+Form) with Claude. MIT licensed.
"""
import subprocess, json, sys, os, argparse, math, re

# ---- fixed, documented thresholds. Do not change silently: every number
# ---- below moves if you do.
SIL_DB   = -35      # dB. Pinned so results stay comparable across files.
SIL_MIN  = 0.35     # seconds
BANDS = [(45,90,'63'),(90,180,'125'),(180,355,'250'),(355,710,'500'),
         (710,1420,'1k'),(1420,2840,'2k'),(2840,5680,'4k'),(5680,11360,'8k'),
         (11360,20000,'16k')]

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def probe(path):
    o=run(f'ffprobe -v error -show_entries format=duration,bit_rate -show_entries stream=sample_rate,channels -of json "{path}"')
    d=json.loads(o.stdout or '{}')
    f=d.get('format',{}); s=(d.get('streams') or [{}])[0]
    return dict(duration=float(f.get('duration',0)), bitrate=int(f.get('bit_rate') or 0),
                sr=int(s.get('sample_rate') or 0), ch=int(s.get('channels') or 0))

def loudness(path):
    o=run(f'ffmpeg -hide_banner -nostats -i "{path}" -af "loudnorm=print_format=json" -f null - 2>&1')
    m=re.search(r'\{[^{}]*\}', o.stdout, re.S)
    if not m: return {}
    j=json.loads(m.group(0))
    return dict(lufs=float(j['input_i']), tp=float(j['input_tp']),
                lra=float(j['input_lra']), thresh=float(j['input_thresh']))

def silences(path, db=SIL_DB, mn=SIL_MIN):
    o=run(f'ffmpeg -hide_banner -nostats -i "{path}" -af "silencedetect=noise={db}dB:d={mn}" -f null - 2>&1')
    st=[float(x) for x in re.findall(r'silence_start: ([\d.]+)', o.stdout)]
    en=[float(x) for x in re.findall(r'silence_end: ([\d.]+)', o.stdout)]
    g=[]
    for a,b in zip(st,en):
        if g and a-g[-1][1] < 0.06: g[-1]=(g[-1][0], b)
        else: g.append((a,b))
    return [(a, b-a) for a,b in g]

def band_levels(path):
    """Relative energy per octave band, in dB, normalised to the loudest band."""
    out={}
    for lo,hi,name in BANDS:
        o=run(f'ffmpeg -hide_banner -nostats -i "{path}" '
              f'-af "highpass=f={lo}:poles=2,highpass=f={lo}:poles=2,'
              f'lowpass=f={hi}:poles=2,lowpass=f={hi}:poles=2,'
              f'astats=metadata=1:reset=0" -f null - 2>&1')
        m=re.findall(r'RMS level dB:\s*(-?[\d.]+|-inf)', o.stdout)
        v=[float(x) for x in m if x!='-inf']
        out[name]= max(v) if v else -120.0
    peak=max(out.values())
    return {k: round(v-peak,1) for k,v in out.items()}

def noise_floor(path, gaps, dur):
    """Level inside the longest silences = the bed/room noise under the voice."""
    long=[g for g in sorted(gaps, key=lambda x:-x[1])[:5] if g[1]>=0.8]
    if not long: return None
    vals=[]
    for start,length in long:
        s=start+0.15; d=max(0.2,length-0.3)
        o=run(f'ffmpeg -hide_banner -nostats -ss {s} -t {d} -i "{path}" -af "astats=metadata=1:reset=0" -f null - 2>&1')
        m=re.findall(r'RMS level dB:\s*(-?[\d.]+)', o.stdout)
        if m: vals.append(max(float(x) for x in m))
    return round(sum(vals)/len(vals),1) if vals else None

def analyse(path, script=None, label=None):
    p=probe(path); L=loudness(path); g=silences(path)
    dur=p['duration']; sil=sum(x[1] for x in g); speech=dur-sil
    nf=noise_floor(path,g,dur)
    bands=band_levels(path)
    r=dict(file=os.path.basename(path), label=label or os.path.basename(path),
           duration_s=round(dur,2), sample_rate=p['sr'], channels=p['ch'],
           bitrate_kbps=round(p['bitrate']/1000) if p['bitrate'] else None,
           loudness=L, speech_s=round(speech,2), silence_s=round(sil,2),
           silence_pct=round(sil/dur*100,1) if dur else None,
           pause_count=len(g),
           pauses=[dict(at=round(a,2), len=round(b,2)) for a,b in g],
           longest_pause_s=round(max([b for _,b in g]),2) if g else 0,
           noise_floor_db=nf,
           voice_to_floor_db=(round(L['lufs']-nf,1) if (nf is not None and L) else None),
           octave_bands_db=bands,
           threshold_used=dict(silence_db=SIL_DB, silence_min_s=SIL_MIN))
    if script and os.path.exists(script):
        words=len(re.sub(r'<[^>]*>','',open(script).read()).split())
        r['word_count']=words
        r['wpm_speech_only']=round(words/(speech/60),1) if speech>0 else None
        r['wpm_wall_clock']=round(words/(dur/60),1) if dur>0 else None
    return r

def report(r):
    L=r['loudness']; o=[]
    o.append(f"=== {r['label']} ===")
    o.append(f"  duration        {r['duration_s']}s   {r['sample_rate']}Hz  {r['channels']}ch  {r['bitrate_kbps']}kbps")
    if L: o.append(f"  loudness        {L['lufs']} LUFS   peak {L['tp']} dBTP   range {L['lra']} LU")
    o.append(f"  speech/silence  {r['speech_s']}s speech + {r['silence_s']}s silence  ({r['silence_pct']}% silent)")
    o.append(f"  pauses          {r['pause_count']} over {SIL_MIN}s   longest {r['longest_pause_s']}s")
    if r['noise_floor_db'] is not None:
        o.append(f"  background      {r['noise_floor_db']} dB floor   voice sits {r['voice_to_floor_db']} dB above it")
    else:
        o.append(f"  background      no pause long enough to measure a floor")
    if 'wpm_speech_only' in r:
        o.append(f"  pace            {r['wpm_speech_only']} wpm speaking / {r['wpm_wall_clock']} wpm wall-clock  ({r['word_count']} words)")
    b=r['octave_bands_db']
    o.append("  frequency balance (dB relative to loudest band):")
    o.append("     " + "  ".join(f"{k:>4}" for k,_ in b.items()))
    o.append("     " + "  ".join(f"{v:>4}" for _,v in b.items()))
    o.append("  NOT MEASURED: tone, warmth, sincerity, whether it sounds rushed.")
    o.append("                Those need a human ear. This tool does not have one.")
    return "\n".join(o)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('file'); ap.add_argument('--script'); ap.add_argument('--label'); ap.add_argument('--json',action='store_true')
    a=ap.parse_args()
    r=analyse(a.file,a.script,a.label)
    print(json.dumps(r,indent=2) if a.json else report(r))
