"""Join the five theory chapters and measured-mouse chapter without re-encoding.

Rebuild q-theory.mp4 and q-mouse.mp4 with their numerical source scripts, then
run this assembler. Bilingual captions are displayed outside the image.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess

root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser()
ap.add_argument('--qa-dir', type=Path, required=True)
args=ap.parse_args(); args.qa_dir.mkdir(parents=True, exist_ok=True)
media=root/'assets/media'
sources=[media/'q-theory.mp4', media/'q-mouse.mp4']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'stream=codec_name,width,height,r_frame_rate,nb_frames','-show_entries',
        'format=duration','-of','json',str(path)],text=True))
specs=[probe(p) for p in sources]
for p in specs:
    s=p['streams'][0]
    assert (s['codec_name'],s['width'],s['height'],s['r_frame_rate'])==('h264',1280,720,'24/1')
assert [float(p['format']['duration']) for p in specs]==[35.,16.]
concat=args.qa_dir/'q_concat.txt'
concat.write_text(''.join("file '"+p.as_posix()+"'\n" for p in sources),encoding='utf-8')
output=media/'q-calculation.mp4'
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0',
                '-i',str(concat),'-c','copy','-movflags','+faststart',str(output)],check=True)
joined=probe(output)
assert float(joined['format']['duration'])==51
assert int(joined['streams'][0]['nb_frames'])==1224
poster=root/'assets/images/showcase/q-film-thumbnail.webp'
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(output),
                '-frames:v','1','-c:v','libwebp','-quality','94',str(poster)],check=True)

def seconds(value):
    h,m,s=value.split(':');return int(h)*3600+int(m)*60+float(s)
def stamp(value):
    return f'{int(value)//3600:02d}:{int(value)//60%60:02d}:{value%60:06.3f}'
cues=[]
for lang in ['en','zh']:
    blocks=(media/f'q-theory.{lang}.vtt').read_text(encoding='utf-8').strip().split('\n\n')[1:]
    for index,block in enumerate(blocks):
        timing,*lines=block.splitlines();a,b=timing.split(' --> ')
        if lang=='en':cues.append(dict(start=seconds(a),end=seconds(b),text={}))
        cues[index]['text'][lang]=' '.join(lines)
mouse=json.loads((root/'data/q-mouse-calculation.json').read_text(encoding='utf-8'));score=mouse['score']
cues.extend([
    dict(start=35,end=41,text=dict(zh='小鼠实例：从 GT 提取局部背景与正对比度。',en='Measured mouse: extract the local background and positive contrast from GT.')),
    dict(start=41,end=44,text=dict(zh='使用 GT 确定的弱、强结构区域，评价待评估图像。',en='Evaluate the test image on the weak and strong support defined by GT.')),
    dict(start=44,end=48,text=dict(zh='在三维体中累计两组的共有对比度，得到结构重叠分数。',en='Accumulate shared contrast in both groups throughout the 3D volume to obtain the overlap scores.')),
    dict(start=48,end=51,text=dict(zh=f'小鼠实例结果：Dweak = {score["D_weak"]:.4f}，Dstrong = {score["D_strong"]:.4f}，Q = {score["Q"]:.2f}。',en=f'Measured mouse result: Dweak = {score["D_weak"]:.4f}, Dstrong = {score["D_strong"]:.4f}, Q = {score["Q"]:.2f}.'))
])
chapters=[dict(start=t,end=(7*(i+1) if i<5 else 51),key=k) for i,(t,k) in enumerate(zip([0,7,14,21,28,35],['q.pair','q.contrast','q.support','q.overlap','q.complement','q.measured']))]
record=dict(movie='assets/media/q-calculation.mp4',movie_sha256=sha(output),
            poster=poster.relative_to(root).as_posix(),poster_sha256=sha(poster),poster_frame_index=0,duration_seconds=51,
            fps=24,frame_count=1224,frame_size=[1280,720],assembly='Lossless H.264 stream concatenation; no image re-encoding',
            sources=[dict(file=p.relative_to(root).as_posix(),sha256=sha(p),duration_seconds=float(s['format']['duration'])) for p,s in zip(sources,specs)],
            chapters=chapters,captions=cues,caption_presentation='Dedicated text band below the video; no subtitle overlay',
            numerical_records=['data/q-calculation.json','data/q-mouse-calculation.json'])
(root/'data/q-video.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for lang in ['en','zh']:
    text='WEBVTT\n\n'+''.join(f'{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"][lang]}\n\n' for c in cues)
    (media/f'q-calculation.{lang}.vtt').write_text(text,encoding='utf-8')
print(f'Q_COMPLETE: {joined["format"]["duration"]} seconds / 6 chapters / 1224 frames')
