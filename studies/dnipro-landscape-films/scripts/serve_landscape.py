"""Local-only gallery and annotation API. Run: python3 scripts/serve_landscape.py"""
import argparse,json,re,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,unquote
from landscape_store import ReviewStore,ConflictError
ROOT=Path(__file__).resolve().parents[1]/'outputs/landscape'

def make_server(root=ROOT,port=8765):
    root=Path(root).resolve();store=ReviewStore(root);store.rebuild();lock=threading.Lock()
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(root),**kwargs)
        def end_headers(self):
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
        def allowed_host(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        def reply(self,status,data):
            encoded=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(encoded)));self.end_headers();self.wfile.write(encoded)
        def serve_clip(self,target):
            # Browsers need byte ranges to seek within locally served MP4 clips.
            with target.open('rb') as file:
                size=target.stat().st_size;start=0;end=size-1
                requested=self.headers.get('Range')
                if requested:
                    match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
                    if match and any(match.groups()):
                        first,last=match.groups()
                        if first:start=int(first);end=min(int(last),end) if last else end
                        else:start=max(0,size-int(last))
                    if not match or not any(match.groups()) or start>end or start>=size:
                        self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
                self.send_response(206 if requested else 200)
                self.send_header('Content-Type','video/mp4');self.send_header('Accept-Ranges','bytes')
                self.send_header('Content-Length',str(end-start+1))
                if requested:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.end_headers();file.seek(start);remaining=end-start+1
                try:
                    while remaining:
                        chunk=file.read(min(512*1024,remaining))
                        if not chunk:break
                        self.wfile.write(chunk);remaining-=len(chunk)
                except (BrokenPipeError,ConnectionResetError):pass
        def do_GET(self):
            if not self.allowed_host():return self.reply(403,{'error':'Local host required.'})
            path=urlsplit(self.path).path
            if path=='/api/state':
                with lock:self.reply(200,store.state())
                return
            target=(root/unquote(path).lstrip('/')).resolve()
            if not target.is_relative_to(root):return self.reply(403,{'error':'Path not allowed.'})
            if target.name=='manual_annotations.json':return self.reply(403,{'error':'Use the review API.'})
            if target.suffix=='.mp4' and target.is_relative_to(root/'geolocation/clips') and target.is_file():return self.serve_clip(target)
            return super().do_GET()
        def list_directory(self,path):self.send_error(404);return None
        def do_POST(self):
            if not self.allowed_host():return self.reply(403,{'error':'Local host required.'})
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://{self.headers.get("Host")}':return self.reply(403,{'error':'Same-origin request required.'})
            if self.headers.get('X-Landscape-Editor')!='1' or self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(403,{'error':'Use the gallery Save button.'})
            if self.path!='/api/labels':return self.reply(404,{'error':'Unknown endpoint.'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=100000:raise ValueError('Invalid request size.')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict):raise ValueError('Expected an object.')
                with lock:result=store.save(data.get('revision'),data.get('changes'))
                return self.reply(200,result)
            except ConflictError as e:return self.reply(409,{'error':str(e)})
            except (ValueError,TypeError) as e:return self.reply(400,{'error':str(e)})
            except Exception:
                return self.reply(500,{'error':'Could not finish saving. Your draft is retained. Reload to check stored labels before retrying.'})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    server=make_server(port=args.port)
    print(f'Gallery and editor: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
