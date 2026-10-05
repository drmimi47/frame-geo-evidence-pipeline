"""Produce B0 landscape deliverables using project_config.json and frozen visual screening."""
import csv,json,shutil,hashlib
from pathlib import Path
from html import escape
import numpy as np
import torch
from PIL import Image
from transformers import SegformerImageProcessor,SegformerForSemanticSegmentation
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/landscape'
config=json.loads((ROOT/'project_config.json').read_text())
assert config['selected_model']=='nvidia/segformer-b0-finetuned-ade-512-512'
decisions=json.loads((OUT/'screening/decisions.json').read_text());selected=[r for r in decisions if r['include']]
for name in ['frames','overlays','masks','records','uncertain/frames','uncertain/overlays']:(OUT/name).mkdir(parents=True,exist_ok=True)
annotations=json.loads((ROOT/'outputs/review_uncertain/annotations.json').read_text())
annotations.update(json.loads((ROOT/'outputs/validation/annotations.json').read_text()))
manual=OUT/'manual_annotations.json'
if manual.exists():annotations.update(json.loads(manual.read_text())['annotations'])
def normalize(labels):
 mapping={'grass':'plants','plant':'plants','tree':'trees','land':'terrain','mountain':'terrain','mountains':'terrain','sky':'unknown'}
 return sorted({mapping.get(x,x) for x in labels})
colors={'trees':(25,145,65),'plants':(150,220,45),'field':(225,190,45),'water':(30,145,240),'terrain':(160,105,65),'built surfaces':(175,175,185)}
names=list(colors)
lookup=np.zeros(150,dtype=np.uint8);palette=np.array([(0,0,0)]+list(colors.values()),dtype=np.uint8)
torch.set_num_threads(4)
processor=SegformerImageProcessor.from_pretrained(ROOT/config['local_model_directory'],local_files_only=True)
model=SegformerForSemanticSegmentation.from_pretrained(ROOT/config['local_model_directory'],local_files_only=True).eval()
for i,name in enumerate(names,1):
 for key,label in model.config.id2label.items():
  if label.strip() in config['categories'][name]:lookup[key]=i
fingerprint=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
results=[]
for i,r in enumerate(selected,1):
 name=r['filename'];stem=Path(name).stem;source=ROOT/r['source'];cache=OUT/'records'/f'{stem}.json'
 if cache.exists():
  data=json.loads(cache.read_text());assert data['config_fingerprint']==fingerprint,'Configuration changed: use a new output directory.'
 else:
  original=Image.open(source).convert('RGB')
  with torch.inference_mode():
   logits=model(**processor(images=original,return_tensors='pt')).logits
   logits=torch.nn.functional.interpolate(logits,size=(512,512),mode='bilinear',align_corners=False)
   top=logits.softmax(dim=1).topk(2,dim=1)
   raw=top.indices[0,0].numpy().astype(np.uint8);score=top.values[0,0].numpy();margin=(top.values[0,0]-top.values[0,1]).numpy()
  grouped=lookup[raw];possible=(grouped>=1)&(grouped<=5)
  uncertain=float((score[possible]<config['pixel_score_cutoff']).mean()) if possible.any() else 0
  ambiguous=float((margin[possible]<.15).mean()) if possible.any() else 0
  possible_fraction=float(possible.mean());low=float((score<config['pixel_score_cutoff']).mean())
  grouped[score<config['pixel_score_cutoff']]=0
  coverage={name:float((grouped==j).mean()*100) for j,name in enumerate(names,1)}
  tags=[name for name,value in coverage.items() if value>=config['minimum_image_tag_coverage_percent']] or ['unknown']
  mask=Image.fromarray(grouped).resize(original.size,Image.Resampling.NEAREST);mask.save(OUT/'masks'/f'{stem}.png')
  mapped=np.asarray(mask);pixels=np.array(original);active=mapped>0
  pixels[active]=(pixels[active]*.5+palette[mapped[active]]*.5).astype(np.uint8)
  Image.fromarray(pixels).save(OUT/'overlays'/name,quality=90)
  data={'filename':name,'video':name.split('_')[0]+'.mp4','requested_seek_seconds':float(stem.split('_seek_')[1][:-1]),'model_labels':tags,'config_fingerprint':fingerprint,'internal_pixel_coverage_percent':coverage,'low_score_fraction':low,'possible_landscape_fraction':possible_fraction,'uncertain_landscape_fraction':uncertain,'ambiguous_landscape_fraction':ambiguous}
  cache.write_text(json.dumps(data,indent=2))
 shutil.copy2(source,OUT/'frames'/name)
 data['landscape_id']=f'L{i:03d}'
 a=annotations.get(name)
 if a and a.get('labels'):
  data['human_labels']=normalize(a['labels']);data['labels']=data['human_labels'];data['labels_source']='user';data['previous_review_id']=a.get('validation_id',a.get('review_id',''))
 else:
  data['human_labels']=[];data['labels']=data['model_labels'];data['labels_source']='model';data['previous_review_id']=''
 reasons=[]
 if data['possible_landscape_fraction']>=.05 and data['uncertain_landscape_fraction']>=.25:reasons.append('Low model scores in possible landscape regions')
 if data['possible_landscape_fraction']>=.05 and data['ambiguous_landscape_fraction']>=.2:reasons.append('Competing pixel labels')
 if data['low_score_fraction']>=.45:reasons.append('Many low-score pixels')
 if any(.3<=data['internal_pixel_coverage_percent'][key]<2 for key in ['trees','plants','water']):reasons.append('Small region near image-tag threshold')
 if r['quality_review']:reasons.append('Blur, darkness, dust, smoke, or transition warrants visual review')
 if data['human_labels'] and set(data['human_labels'])!=set(data['model_labels']):reasons.append('Existing human labels disagree with model; image labels already corrected, mask uncorrected')
 if data['model_labels']==['unknown']:reasons.append('No target category confidently tagged')
 data['review_reasons']=reasons
 if reasons:
  shutil.copy2(source,OUT/'uncertain/frames'/name);shutil.copy2(OUT/'overlays'/name,OUT/'uncertain/overlays'/name)
 results.append(data)
 if i%10==0:print(f'{i}/{len(selected)} landscape frames processed',flush=True)
from render_landscape_gallery import page
flagged=[r for r in results if r['review_reasons']]
(OUT/'index.html').write_text(page(results,'Landscape frames — B0'))
(OUT/'uncertain/index.html').write_text(page(flagged,'Uncertain landscape results',True))
(OUT/'predictions.json').write_text(json.dumps(results,indent=2))
fields=['landscape_id','video','requested_seek_seconds','filename','labels','labels_source','model_labels','human_labels','previous_review_id','review_reasons']
for path,rows in [(OUT/'labels.csv',results),(OUT/'uncertain/review.csv',flagged)]:
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({key:'; '.join(r[key]) if isinstance(r[key],list) else r[key] for key in fields})
with (OUT/'screening/screening.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['screen_id','filename','include','screening_reason','quality_review']);w.writeheader()
 for r in decisions:w.writerow({key:r[key] for key in w.fieldnames})
(OUT/'configuration.json').write_text(json.dumps(config,indent=2))
(OUT/'mask_legend.json').write_text(json.dumps({0:{'name':'unknown','color':[0,0,0]},**{i:{'name':name,'color':colors[name]} for i,name in enumerate(names,1)}},indent=2))
summary={'screened_frames':len(decisions),'selected_frames':len(results),'excluded_frames':len(decisions)-len(results),'by_video':{v:sum(r['video']==v for r in results) for v in config['analysis_videos']},'uncertain_frames':len(flagged),'uncertain_with_existing_human_labels':sum(bool(r['human_labels']) for r in flagged),'frames_with_saved_human_labels':sum(bool(r['human_labels']) for r in results),'model':config['selected_model'],'taxonomy':config['taxonomy'],'scope':'30-second samples only; visual screening, image labels and model overlays. Pixel boundaries unverified. No full-video overlay export or area trend claims.'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
