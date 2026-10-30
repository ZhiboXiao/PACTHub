"""Local static preview with HTTP byte ranges for seekable video chapters."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import argparse,os,re,functools
class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining=None
        path=Path(self.translate_path(self.path))
        header=self.headers.get('Range')
        if not header or not path.is_file():return super().send_head()
        size=path.stat().st_size
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',header.strip())
        if not match:return super().send_head()
        a,b=match.groups()
        if not a and not b:return super().send_head()
        if a:start=int(a);end=min(int(b) if b else size-1,size-1)
        else:start=max(0,size-int(b));end=size-1
        if start>end or start>=size:
            self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return None
        stream=path.open('rb');stream.seek(start);self.remaining=end-start+1
        self.send_response(206);self.send_header('Content-type',self.guess_type(str(path)))
        self.send_header('Accept-Ranges','bytes');self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length',str(self.remaining));self.send_header('Last-Modified',self.date_time_string(path.stat().st_mtime));self.end_headers()
        return stream
    def end_headers(self):
        if getattr(self,'remaining',None) is None:self.send_header('Accept-Ranges','bytes')
        super().end_headers()
    def copyfile(self,source,outputfile):
        if self.remaining is None:return super().copyfile(source,outputfile)
        while self.remaining>0:
            block=source.read(min(65536,self.remaining))
            if not block:break
            outputfile.write(block);self.remaining-=len(block)
ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765);args=ap.parse_args()
directory=Path(__file__).resolve().parents[1]
print(f'PACTHub preview http://127.0.0.1:{args.port}',flush=True)
ThreadingHTTPServer(('127.0.0.1',args.port),functools.partial(Handler,directory=str(directory))).serve_forever()
