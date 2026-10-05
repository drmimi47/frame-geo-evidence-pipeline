"""Durable human annotations with rebuildable gallery/CSV projections."""
import csv,hashlib,io,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from render_landscape_gallery import COLORS,page

class ConflictError(ValueError):pass

def atomic_write(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

class ReviewStore:
    def __init__(self,root):self.root=Path(root)
    def document(self):
        path=self.root/'manual_annotations.json'
        return json.loads(path.read_text()) if path.exists() else {'version':1,'annotations':{},'history':[]}
    def rows(self):
        rows=json.loads((self.root/'predictions.json').read_text())
        for row in rows:
            a=self.document()['annotations'].get(row['filename'])
            if a:
                row.update(human_labels=a['labels'],labels=a['labels'],labels_source='user')
            if row['human_labels']:
                row['review_reasons']=[r for r in row['review_reasons'] if not r.startswith('Existing human labels disagree')]
                if set(row['human_labels'])!=set(row['model_labels']):row['review_reasons'].append('Existing human labels disagree with model; image labels already corrected, mask uncorrected')
        return rows
    def state(self):
        rows=self.rows()
        revision=hashlib.sha256(json.dumps({'annotations':self.document(),'human':[(r['filename'],r['human_labels']) for r in rows]},sort_keys=True).encode()).hexdigest()
        return {'revision':revision,'rows':rows}
    def save(self,revision,changes):
        state=self.state()
        if revision!=state['revision']:raise ConflictError('Labels changed in another window. Reload before saving; your draft is still visible.')
        if not isinstance(changes,list) or not 1<=len(changes)<=len(state['rows']):raise ValueError('Supply between 1 and 102 frame changes.')
        known={r['filename']:r for r in state['rows']};seen=set();clean=[]
        for change in changes:
            if not isinstance(change,dict):raise ValueError('Invalid change.')
            name=change.get('filename');labels=change.get('labels')
            if not isinstance(name,str) or name not in known or name in seen:raise ValueError('Unknown or repeated frame.')
            if not isinstance(labels,list) or not labels or any(not isinstance(x,str) or x not in COLORS for x in labels):raise ValueError('Choose at least one valid label; use unknown when appropriate.')
            seen.add(name);clean.append((name,[x for x in COLORS if x in labels]))
        doc=self.document();now=datetime.now(timezone.utc).isoformat()
        for name,labels in clean:
            doc['history'].append({'filename':name,'before':known[name]['human_labels'],'after':labels,'saved_at':now})
            doc['annotations'][name]={'labels':labels,'source':'user_web_editor','status':'reviewed','updated_at':now,'scope':'Image labels only; model masks unchanged'}
        atomic_write(self.root/'manual_annotations.json',json.dumps(doc,indent=2)+'\n')
        self.rebuild()
        return self.state()
    def rebuild(self):
        rows=self.rows();flagged=[r for r in rows if r['review_reasons']]
        fields=['landscape_id','video','requested_seek_seconds','filename','labels','labels_source','model_labels','human_labels','previous_review_id','review_reasons']
        def csv_text(items):
            f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            for r in items:w.writerow({k:'; '.join(r[k]) if isinstance(r[k],list) else r[k] for k in fields})
            return f.getvalue()
        outputs={'predictions.json':json.dumps(rows,indent=2)+'\n','labels.csv':csv_text(rows),'index.html':page(rows,'Landscape frames'),'uncertain/review.csv':csv_text(flagged),'uncertain/index.html':page(flagged,'Uncertain landscape frames',True)}
        # Use shared originals on the uncertain page so newly flagged frames work immediately.
        outputs['uncertain/index.html']=outputs['uncertain/index.html'].replace('href="frames/','href="../frames/').replace('src="frames/','src="../frames/').replace('href="overlays/','href="../overlays/').replace('src="overlays/','src="../overlays/')
        summary_path=self.root/'summary.json'
        if summary_path.exists():
            summary=json.loads(summary_path.read_text());summary.update(uncertain_frames=len(flagged),uncertain_with_existing_human_labels=sum(bool(r['human_labels']) for r in flagged),frames_with_saved_human_labels=sum(bool(r['human_labels']) for r in rows))
            outputs['summary.json']=json.dumps(summary,indent=2)+'\n'
        for name,text in outputs.items():atomic_write(self.root/name,text)
