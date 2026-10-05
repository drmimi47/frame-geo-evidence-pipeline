"""Render the local galleries without rerunning inference."""
import csv
import json
from html import escape
from pathlib import Path
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1]
COLORS={'trees':'#199141','plants':'#96dc2d','field':'#e1be2d','water':'#1e91f0','terrain':'#a06941','built surfaces':'#afafb9','unknown':'#d4d4d4'}
CSS='''
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#000;color:#eee}*{box-sizing:border-box}body{margin:0;background:#000}a{color:#a8cfff;text-underline-offset:4px}button,input,select{font:inherit}button,select{color:#eee;background:#141414;border:1px solid #424242;border-radius:8px;padding:9px 13px}button{cursor:pointer}button:hover{background:#262626}button:focus-visible,select:focus-visible,a:focus-visible,input:focus-visible{outline:2px solid #fff;outline-offset:4px}.shell{max-width:1450px;margin:auto;padding:48px 32px}.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#a3a3a3}h1{font-size:clamp(30px,4vw,48px);letter-spacing:-.045em;font-weight:600;margin:12px 0 16px}header p{max-width:850px;line-height:1.7;color:#aaa;font-size:15px}nav{display:flex;flex-wrap:wrap;gap:20px;margin:24px 0 32px;font-size:14px}.filters{border:1px solid #303030;border-radius:14px;padding:22px;background:#0a0a0a;display:grid;grid-template-columns:180px 1fr;gap:24px}fieldset{border:0;padding:0;margin:0;min-width:0}legend{font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#aaa;padding:0;margin-bottom:14px}.options{display:flex;flex-wrap:wrap;gap:10px}.check{display:inline-flex;align-items:center;gap:9px;padding:9px 12px;border:1px solid #323232;border-radius:8px;cursor:pointer;font-size:14px;background:#111}.check:has(input:checked){border-color:#777;background:#1b1b1b}.check input{width:16px;height:16px;margin:0;accent-color:#fff;cursor:pointer}.filter-footer{grid-column:1/-1;display:flex;align-items:center;flex-wrap:wrap;gap:14px;border-top:1px solid #282828;padding-top:18px;font-size:13px;color:#aaa}.filter-footer label{display:flex;align-items:center;gap:10px}.filter-footer button{margin-left:auto}.results-bar{display:flex;justify-content:space-between;align-items:center;margin:28px 0 16px;color:#aaa;font-size:14px}.results-bar strong{color:#eee}.gallery{display:grid;gap:24px}.frame{border:1px solid #292929;border-radius:14px;overflow:hidden;background:#080808;content-visibility:auto;contain-intrinsic-size:auto 750px}.frame-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:20px 22px;border-bottom:1px solid #252525}.frame-head h2{font-size:18px;font-weight:600;margin:0}.frame-meta{font-size:13px;color:#aaa;display:flex;gap:16px}.images{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#262626}figure{margin:0;min-width:0;background:#000}figcaption{padding:11px 18px;color:#999;font-size:11px;text-transform:uppercase;letter-spacing:.12em}figure a{display:block}figure img{display:block;width:100%;height:clamp(230px,32vw,470px);object-fit:contain;background:#000}.details{padding:20px 22px}.label-line{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:0 0 13px}.label-name{color:#999;font-size:12px;min-width:142px}.tags{display:flex;gap:8px;flex-wrap:wrap}.tag{color:var(--label-color);font-size:14px;font-weight:600;padding:4px 9px;border:1px solid currentColor;border-radius:5px;background:#000}.muted{font-size:13px;color:#999}.review{font-size:13px;line-height:1.6;color:#aaa;margin:18px 0 10px;padding-top:15px;border-top:1px solid #252525}.filename{font-size:11px;color:#777;overflow-wrap:anywhere;font-family:ui-monospace,monospace}.empty{padding:60px 20px;text-align:center;border:1px dashed #444;border-radius:14px;color:#aaa}.empty h2{color:white}footer{font-size:12px;line-height:1.7;color:#888;margin-top:32px;max-width:950px}[hidden]{display:none!important}@media(max-width:700px){.shell{padding:28px 15px}.filters{grid-template-columns:1fr;gap:20px}.filter-footer button{margin-left:0}.images{grid-template-columns:1fr}.frame-head{align-items:flex-start}.frame-meta{flex-direction:column;gap:3px;text-align:right}figure img{height:auto;max-height:460px}.label-name{min-width:100%;margin-top:6px}.details{padding:18px}.results-bar{gap:15px}.check{padding:10px}.filter-footer{align-items:flex-start;flex-direction:column}}
'''

CSS += """
.mode-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:0;border-bottom:1px solid #363636;margin-bottom:24px}.mode-tabs button{border:0;border-radius:0;background:#000;color:#888;padding:17px;font-size:18px;border-bottom:3px solid transparent}.mode-tabs button[aria-selected=true]{color:#fff;border-bottom-color:#fff}.editor-toolbar{display:none;padding:18px;border:1px solid #444;border-radius:12px;margin-bottom:24px;background:#101010}.editor-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.editor-toolbar p{font-size:14px;color:#aaa;line-height:1.6}.editor-panel{display:none;padding:20px 22px;border-top:1px solid #333;background:#111}.editor-panel .options{margin:12px 0 18px}.editing-tip{font-size:13px;color:#aaa}.error{color:#ff9999!important}body[data-mode=editing] .editor-toolbar,body[data-mode=editing] .editor-panel{display:block}.has-draft{border-color:#d6b55f}.primary-save{background:#eee;color:#111;font-weight:600}.primary-save:hover{background:#fff}button:disabled{opacity:.45;cursor:default}.your-labels{display:flex;gap:8px;flex-wrap:wrap}
.location-line{margin:16px 0 0;padding-top:15px;border-top:1px solid #252525;font-size:13px;color:#aaa;line-height:1.6}.location-line strong{color:#eee}.location-status{display:inline-block;margin-left:8px;padding:2px 7px;border:1px solid #444;border-radius:999px;color:#bbb;font-size:11px;text-transform:uppercase;letter-spacing:.06em}
figure video{display:block;width:100%;height:clamp(230px,32vw,470px);object-fit:contain;background:#000}.clip-note{padding:10px 18px;font-size:12px;line-height:1.5;color:#aaa;margin:0}.clip-note a{display:inline}@media(max-width:700px){figure video{height:auto;max-height:460px;aspect-ratio:4/3}}
"""
CSS += (ROOT/'scripts/history_timeline.css').read_text()
JS='''
function matchesFilters(video, labels, selectedVideos, selectedLabels, mode) {
  if (!selectedVideos.includes(video)) return false;
  if (!selectedLabels.length) return true;
  return mode === 'any' ? selectedLabels.some(label => labels.includes(label)) : selectedLabels.every(label => labels.includes(label));
}
const videos = [...document.querySelectorAll('input[name="video"]')];
const categories = [...document.querySelectorAll('input[name="category"]')];
const cards = [...document.querySelectorAll('.frame')].map(element => ({element,video:element.dataset.video,labels:JSON.parse(element.dataset.labels)}));
const mode = document.getElementById('match-mode');
const geoSuitability = document.getElementById('geo-suitability');
function applyFilters(){
  const selectedVideos=videos.filter(input=>input.checked).map(input=>input.value);
  const selectedLabels=categories.filter(input=>input.checked).map(input=>input.value);
  let visible=0;
  for(const card of cards){const tier=card.element.dataset.geoTier;const selection=geoSuitability.value;const geoMatch=selection==='all'||(selection==='worth'?(tier==='strong'||tier==='possible'):tier===selection);const show=geoMatch&&matchesFilters(card.video,card.labels,selectedVideos,selectedLabels,mode.value);card.element.hidden=!show;if(show)visible++;}
  document.getElementById('result-count').textContent=`${visible} of ${cards.length} frames`;
  document.getElementById('empty-state').hidden=visible!==0;
  document.getElementById('filter-hint').textContent=selectedLabels.length ? (mode.value==='all'?'Frames must contain every selected category.':'Frames may contain any selected category.') : 'No categories selected: show all categories.';
}
for(const input of [...videos,...categories])input.addEventListener('change',applyFilters);
mode.addEventListener('change',applyFilters);
geoSuitability.addEventListener('change',applyFilters);
function resetFilters(){videos.forEach(input=>input.checked=true);categories.forEach(input=>input.checked=false);mode.value='all';geoSuitability.value='all';applyFilters();}
document.querySelectorAll('[data-reset]').forEach(button=>button.addEventListener('click',resetFilters));
applyFilters();

'''
JS += (ROOT/'scripts/landscape_editor.js').read_text()
JS += (ROOT/'scripts/history_timeline.js').read_text()

def tags(labels):
    return '<div class="tags">'+''.join(f'<span class="tag" style="--label-color:{COLORS.get(label,"#d4d4d4")}">{escape(label)}</span>' for label in labels)+'</div>'
def film_time(seconds):
    seconds=int(seconds)
    return f'{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}'
def history_location_tables(rows):
    by_filename={row['filename']:row for row in rows}
    films=json.loads((ROOT/'scripts/history_film_locations.json').read_text())
    parts=['<section class="history-locations" aria-labelledby="history-locations-title"><div class="eyebrow">Film geography</div><h2 id="history-locations-title">Important locations in the films</h2><p>Choose a frame to open its Gallery card and geolocation evidence. Probable and contextual places are research leads, not exact camera positions.</p>']
    for film in films:
        parts.append(f'<section class="history-film" aria-label="{escape(film["film"],quote=True)} locations"><div class="history-film-head"><h3>{escape(film["film"])}</h3><span>{escape(film["subtitle"])}</span></div><div class="history-table-scroll"><table><thead><tr><th scope="col">Place</th><th scope="col">Gallery frames</th><th scope="col">Evidence</th><th scope="col">Why it matters</th></tr></thead><tbody>')
        for item in film['locations']:
            links=[]
            for filename in item['frames']:
                if filename not in by_filename:raise ValueError(f'History location frame is missing from the gallery: {filename}')
                row=by_filename[filename]
                frame_id=escape(row['landscape_id'],quote=True)
                links.append(f'<a href="#frame-{frame_id}" data-history-frame-link="{frame_id}">{escape(row["landscape_id"])}</a>')
            parts.append(f'<tr><th scope="row">{escape(item["place"])}</th><td class="history-frame-links">{" ".join(links)}</td><td>{escape(item["evidence"])}</td><td>{escape(item["note"])}</td></tr>')
        parts.append('</tbody></table></div></section>')
    parts.append('<p class="history-location-note">Location assessments come from the project’s <code>claude/README.md</code> summary and <code>geolocation/predictions.json</code>. Hrushivka is a story prototype, not a claimed filming site.</p></section>')
    return ''.join(parts)
def page(rows,title,uncertain=False):
    geo_path=ROOT/'outputs/landscape/geolocation/predictions.json'
    geo_rows=json.loads(geo_path.read_text()) if geo_path.exists() else []
    geolocation={r['filename']:r for r in geo_rows}
    clips_path=ROOT/'outputs/landscape/geolocation/clips/manifest.json'
    clips=json.loads(clips_path.read_text()) if clips_path.exists() else {}
    zainali_path=ROOT/'outputs/landscape/geolocation/zainali/results.csv'
    zainali={}
    if zainali_path.exists():
        with zainali_path.open(encoding='utf-8-sig',newline='') as file:
            zainali={r['filename']:r for r in csv.DictReader(file) if r['status']=='done'}
    suitability_path=ROOT/'outputs/landscape/geolocation/suitability.json'
    suitability={r['filename']:r for r in json.loads(suitability_path.read_text())} if suitability_path.exists() else {}
    video_names=sorted({r['video'] for r in rows})
    video_options=''.join(f'<label class="check"><input type="checkbox" name="video" value="{escape(video)}" checked>Video {escape(video.split(".")[0])}</label>' for video in video_names)
    label_options=''.join(f'<label class="check"><input type="checkbox" name="category" value="{escape(name)}"><span style="color:{color}">{escape(name)}</span></label>' for name,color in COLORS.items())
    links='<a href="../index.html">All landscape frames</a><a href="review.csv">Review CSV</a>' if uncertain else '<a href="uncertain/index.html">Uncertain results</a><a href="labels.csv">Download labels</a><a href="screening/screening.csv">Screening decisions</a>'
    history_tab = '<button id="tab-history" role="tab" aria-controls="history-workspace" aria-selected="false" tabindex="-1" data-tab="history">History</button>' if not uncertain else ''
    html=[f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>{CSS}</style></head><body data-mode="gallery" data-gallery-view="film"><main class="shell"><div class="mode-tabs" role="tablist" aria-label="Workspace mode"><button id="tab-gallery" role="tab" aria-controls="gallery-workspace" aria-selected="true" data-tab="gallery">Gallery</button><button id="tab-editing" role="tab" aria-controls="frames-panel" aria-selected="false" tabindex="-1" data-tab="editing">Editing</button>{history_tab}</div><div id="gallery-workspace"><div class="film-view"><header><div class="eyebrow">Landscape study / B0</div><h1>{escape(title)}</h1><p>Explore original frames alongside film sequences for location results, or segmentation overlays for other frames. Location predictions retain their evidence status. Saved human corrections take precedence for landscape labels.</p><nav aria-label="Gallery links">{links}</nav></header><section class="editor-toolbar" aria-label="Save label edits"><div class="editor-actions"><button id="save-all" class="primary-save" disabled>Save changes</button><button id="discard-drafts" disabled>Discard unsaved changes</button><span id="draft-count" class="muted"></span></div><p>Check every label present in a frame. Use its Save labels button to confirm a model suggestion, or Save changes to save all modified frames. Saving updates image labels; segmentation overlays stay unchanged.</p><p id="editor-status" role="status" aria-live="polite"></p></section><section class="filters" aria-label="Filter frames"><fieldset><legend>Video</legend><div class="options">{video_options}</div></fieldset><fieldset><legend>Landscape categories</legend><div class="options">{label_options}</div></fieldset><div class="filter-footer"><label for="geo-suitability">Geolocation potential<select id="geo-suitability"><option value="all">All frames</option><option value="worth">Worth geolocating</option><option value="strong">Strong candidates</option><option value="possible">Possible candidates</option><option value="low">Low priority</option></select></label><label for="match-mode">Match<select id="match-mode"><option value="all">All selected categories</option><option value="any">Any selected category</option></select></label><span id="filter-hint">No categories selected: show all categories.</span><button type="button" data-reset>Reset filters</button></div></section><div class="results-bar"><strong id="result-count" role="status" aria-live="polite">{len(rows)} of {len(rows)} frames</strong><span>Filters use saved human labels where available</span></div><noscript><p>Enable JavaScript to use the filters. All frames are shown below.</p></noscript><div id="empty-state" class="empty" hidden><h2>No matching frames</h2><p>Select a video, remove a category, or switch to “Any selected category.”</p><button type="button" data-reset>Reset filters</button></div><section id="frames-panel" role="tabpanel" aria-labelledby="tab-gallery" class="gallery" aria-label="Landscape frames">''']
    for r in rows:
        seconds=int(r['requested_seek_seconds']);timestamp=f'{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}'
        filename=escape(r['filename']);labels_attr=escape(json.dumps(r['labels']),quote=True)
        human=tags(r['human_labels']) if r['human_labels'] else '<span class="muted">Not reviewed</span>'
        edit_options=''.join(f'<label class="check"><input class="edit-label" type="checkbox" value="{escape(label)}" disabled><span style="color:{color}">{escape(label)}</span></label>' for label,color in COLORS.items())
        review=escape('; '.join(r['review_reasons']) or 'No uncertainty rule triggered; predictions may still contain errors.')
        screening=suitability.get(r['filename'],{})
        geo_tier=screening.get('tier','unassessed')
        screening_html=f'<p class="location-line"><span class="label-name">Geolocation potential</span> <strong>{escape(geo_tier.capitalize())}</strong><br>{escape(screening.get("reason","Not assessed"))}</p>'
        geo=geolocation.get(r['filename'],{})
        fallback=zainali.get(r['filename']) if not geo.get('location') else None
        if geo.get('location'):
            location_text=f"<strong>{escape(geo['location'])}</strong>"
        elif fallback:
            location_text=f"<strong>{escape(fallback['place'])}</strong>"
        elif geo.get('candidates'):
            names=[]
            for candidate in geo['candidates']:
                if candidate.get('place') not in names:names.append(candidate.get('place'))
            prefix='Unverified visual candidate: ' if geo.get('method')=='visual_investigation' else 'Mentioned nearby: '
            location_text=prefix+escape(', '.join(names[:4]))
        else:
            location_text='Not yet located'
        geo_status=escape(geo.get('status','unlocated').replace('_',' '))
        geo_note=escape(geo.get('method_note','No transcript or visual location evidence has been attached.'))
        if geo.get('evidence_report'):
            report_prefix='../' if uncertain else ''
            geo_note+=f' <a href="{report_prefix}{escape(geo["evidence_report"],quote=True)}">View geolocation evidence</a>'
        if geo.get('location'):
            geo_note='Source: Geo-sleuth (preferred evidence assessment). '+geo_note
        elif fallback:
            geo_status='Zainali · unverified prediction'
            geo_note='Source: Zainali. No evidence-supported Geo-sleuth location is available. '
            if fallback.get('reported_probability'):
                geo_note+=f'Service-reported confidence: {float(fallback["reported_probability"]):.0%}. '
            geo_note+='Predicted pin; exact camera position is unverified.'
            if fallback.get('latitude') and fallback.get('longitude'):
                query=urlencode({'api':1,'query':fallback['latitude']+','+fallback['longitude']})
                geo_note+=f' <a href="https://www.google.com/maps/search/?{escape(query,quote=True)}">View predicted pin</a>'
            report_prefix='../' if uncertain else ''
            geo_note+=f' <a href="{report_prefix}geolocation/zainali/index.html">View Zainali results</a>'
            if geo.get('evidence_report'):
                geo_note+=f' <a href="{report_prefix}{escape(geo["evidence_report"],quote=True)}">View Geo-sleuth assessment</a>'
        location_html=f'<p class="location-line"><span class="label-name">Location evidence</span> {location_text}<span class="location-status">{geo_status}</span><br>{geo_note}</p>'
        right_media=f'<figure><figcaption>B0 segmentation</figcaption><a href="overlays/{filename}"><img loading="lazy" src="overlays/{filename}" alt="B0 segmentation overlay for {escape(r["landscape_id"])}"></a></figure>'
        clip=clips.get(r['filename']) if geo.get('location') or fallback else None
        if clip and (ROOT/'outputs/landscape'/clip['file']).is_file():
            clip_url=escape(('../' if uncertain else '')+clip['file'],quote=True)
            clip_range=film_time(clip['start_seconds'])+'–'+film_time(clip['end_seconds'])
            context_note=('Selected film sequence' if clip['selection']=='inspected_sequence' else 'Nearby film context')
            right_media=(f'<figure><figcaption>{context_note} · {clip_range}</figcaption>'
                         f'<video controls playsinline preload="none" poster="{"../" if uncertain else ""}frames/{filename}" aria-label="Film context for {escape(r["landscape_id"],quote=True)}">'
                         f'<source src="{clip_url}" type="video/mp4"><a href="{clip_url}">Open film clip</a></video>'
                         f'<p class="clip-note">Original frame appears {clip["frame_offset_seconds"]:g}s into this clip. '
                         f'Adjacent shots may show other locations. <a href="{clip_url}">Open clip</a></p></figure>')
        html.append(f'''<article id="frame-{escape(r['landscape_id'],quote=True)}" tabindex="-1" class="frame" data-geo-tier="{escape(geo_tier)}" data-filename="{filename}" data-video="{escape(r['video'])}" data-labels="{labels_attr}"><div class="frame-head"><h2>{escape(r['landscape_id'])}</h2><div class="frame-meta"><span>Video {escape(r['video'].split('.')[0])}</span><time>{timestamp}</time></div></div><div class="images"><figure><figcaption>Original frame</figcaption><a href="frames/{filename}"><img loading="lazy" src="frames/{filename}" alt="Original landscape frame {escape(r['landscape_id'])}"></a></figure>{right_media}</div><div class="details"><div class="label-line"><span class="label-name">Model prediction</span>{tags(r['model_labels'])}</div><div class="label-line"><span class="label-name">Your labels</span><div class="your-labels">{human}</div><span class="muted">{escape(r.get('previous_review_id',''))}</span></div>{screening_html}{location_html}<p class="review">{review}</p><div class="filename">{filename}</div></div><div class="editor-panel"><fieldset><legend>Choose labels for {escape(r['landscape_id'])}</legend><p class="editing-tip edit-source"></p><div class="options">{edit_options}</div></fieldset><button type="button" class="save-frame primary-save" disabled>Save labels</button></div></article>''')
    html.append('</section><footer>Plants includes grass. Unknown includes sky and is left uncolored in overlays. Frames were sampled every 30 seconds and screened for landscape context. Image labels and overlays are not validated land-cover measurements.</footer></div></div>')
    if not uncertain:
        dams=json.loads((ROOT/'scripts/history_dams.json').read_text())
        history_data=json.dumps(dams,ensure_ascii=False).replace('<','\\u003c')
        history_html='''<section id="history-workspace" class="history-view" role="tabpanel" aria-labelledby="tab-history" hidden><header class="history-intro"><div class="eyebrow">Dnipro / 1927–1975</div><h1>Engineering the river</h1><p>Follow the six main hydroelectric stations as construction spread through the Dnipro basin. Drag the year, select a milestone, or choose a station on the schematic map to see when it was built and began generating power.</p></header><div class="history-layout"><section class="history-panel" aria-live="polite"><div class="history-kicker">Selected year</div><div id="history-year" class="history-year">1927</div><p id="history-count" class="history-stat"></p><div id="history-phase" class="history-kicker"></div><div id="history-card" class="history-card"></div></section><div class="history-map-wrap"><div class="history-map-title">The Dnipro cascade · north to south</div><svg class="history-map" viewBox="0 0 640 590" role="img" aria-label="Schematic Dnipro river with six selectable hydroelectric stations"><path class="history-river" d="M120 25 C125 65 150 75 170 91 S205 134 255 166 S282 217 346 259 S375 302 443 344 S480 390 458 430 S420 480 375 521 L335 567"/><path class="history-river-core" d="M120 25 C125 65 150 75 170 91 S205 134 255 166 S282 217 346 259 S375 302 443 344 S480 390 458 430 S420 480 375 521 L335 567"/><text class="map-label" x="76" y="54">UPSTREAM</text><text class="map-label" x="300" y="573">DOWNSTREAM</text><g id="history-markers"></g></svg><div class="history-map-note">Schematic river diagram for sequence and approximate relative location; no historical shoreline or reservoir boundaries are drawn.</div></div></div><section class="history-timeline" aria-label="Dnipro hydropower timeline"><div class="history-timeline-header"><h2>Move through time</h2><span>Drag the slider or choose a construction milestone</span></div><label class="sr-only" for="history-year-slider">Year</label><input id="history-year-slider" class="history-slider" type="range" min="1927" max="1975" value="1927" step="1"><div class="history-range-ends"><span>1927</span><span>1975</span></div><div id="history-events" class="history-events"></div><div class="history-legend"><span><i class="operating"></i>Operating</span><span><i class="building"></i>Under construction</span><span><i class="future"></i>Future</span><span><i class="selected"></i>Selected station</span></div></section><p class="history-sources">Dates are drawn from Ukrhydroenergo station histories, linked in each station card. <a href="https://uhe.gov.ua/diyalnist/hidroenerhetyka/k-kaskad-hidroelektrostantsiy" target="_blank" rel="noreferrer">Ukrhydroenergo identifies six main Dnipro stations</a>. Markers persist after first operation; construction and full-power dates are distinct. This 1927–1975 view is historical: <a href="https://uhe.gov.ua/media_tsentr/novyny/vony-zruynuvaly-stantsiyu-ale-ne-zruynuyut-pamyat-pro-yiyi-roky-roboty-slavetni" target="_blank" rel="noreferrer">Kakhovka HPP and part of its dam were destroyed in 2023</a>.</p></section>'''
        html.append(history_html.rsplit('</section>',1)[0])
        html.append(history_location_tables(rows))
        html.append('</section>')
        html.append('<script id="history-dams" type="application/json">'+history_data+'</script>')
    html.append(f'''</main><script id="label-colors" type="application/json">{json.dumps(COLORS)}</script><script>{JS}</script></body></html>''')
    return '\n'.join(html)
if __name__=='__main__':
    out=ROOT/'outputs/landscape';rows=json.loads((out/'predictions.json').read_text())
    (out/'index.html').write_text(page(rows,'Landscape frames'))
    flagged=[r for r in rows if r['review_reasons']]
    (out/'uncertain/index.html').write_text(page(flagged,'Uncertain landscape frames',True))
    print(f'Rendered {len(rows)} landscape frames and {len(flagged)} uncertain frames.')
