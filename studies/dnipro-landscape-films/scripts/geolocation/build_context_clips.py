"""Extract original-film context for gallery frames with location results."""
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANDSCAPE = ROOT / 'outputs/landscape'
OUT = LANDSCAPE / 'geolocation/clips'
# Sequence boundaries inspected in contact sheets. These are footage context,
# not a claim that every adjacent shot depicts the same filming location.
SEQUENCES = {
    '1_seek_002205.000s.jpg': (2183, 2209),
    '1_seek_002805.000s.jpg': (2789, 2809),
    '1_seek_002955.000s.jpg': (2910, 2960),
    '3_seek_000225.000s.jpg': (189, 241),
    '3_seek_000195.000s.jpg': (189, 241),
    # Video 1 clips start at the in-film location intertitle that introduces the shot.
    '1_seek_000135.000s.jpg': (86, 144),    # "Nenasytets" rapid card, then "Catherine's Throne" card
    '1_seek_000165.000s.jpg': (155, 166),   # "Cliff of Love" card
    '1_seek_000735.000s.jpg': (701, 760),   # "Here ... Europe's greatest power station" cards
    '1_seek_002145.000s.jpg': (2130, 2160), # "workers' compound" card
    '3_seek_001895.500s.jpg': (1888, 1960), # new village on the hilltop: carpenter, then wide views over the Dnipro
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    geo = {r['filename']: r for r in json.loads((LANDSCAPE / 'geolocation/predictions.json').read_text())}
    with (LANDSCAPE / 'geolocation/zainali/results.csv').open(encoding='utf-8-sig') as file:
        fallback = {r['filename'] for r in csv.DictReader(file) if r['status'] == 'done'}
    previous_path = OUT / 'manifest.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    durations, manifest = {}, {}
    for frame in json.loads((LANDSCAPE / 'predictions.json').read_text()):
        name = frame['filename']
        if not geo.get(name, {}).get('location') and name not in fallback:
            continue
        source = ROOT / frame['video']
        if source.name not in durations:
            durations[source.name] = float(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=nw=1:nk=1', str(source)], text=True))
        timestamp = float(frame['requested_seek_seconds'])
        start, end = SEQUENCES.get(name, (timestamp - 15, timestamp + 15))
        start, end = max(0, start), min(durations[source.name], end)
        destination = OUT / (Path(name).stem + '.mp4')
        item = {'file': str(destination.relative_to(LANDSCAPE)), 'video': source.name,
                'start_seconds': start, 'end_seconds': end,
                'frame_offset_seconds': timestamp - start,
                'selection': 'inspected_sequence' if name in SEQUENCES else 'nearby_context',
                'source_size': source.stat().st_size, 'source_mtime_ns': source.stat().st_mtime_ns,
                'encoding': 'h264-aac-960-crf23-v1'}
        if previous.get(name) != item or not destination.exists():
            temporary = destination.with_suffix('.part.mp4')
            subprocess.run([
                'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-ss', str(start), '-i', str(source), '-t', str(end - start),
                '-map', '0:v:0', '-map', '0:a?',
                '-vf', "scale='min(960,iw)':-2", '-c:v', 'libx264', '-threads', '2',
                '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(temporary)], check=True)
            temporary.replace(destination)
        manifest[name] = item
        print(f'{name}: {start:g}–{end:g}s', flush=True)
    previous_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Ready: {len(manifest)} original-film clips.', flush=True)


if __name__ == '__main__':
    main()
