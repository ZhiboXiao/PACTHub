"""Image-space annotations after all numerical processing."""
from PIL import ImageDraw,ImageFont
def scale_bar(im,pixels_per_mm,length_mm=5,font_fraction=.043):
    im=im.convert('RGB').copy();d=ImageDraw.Draw(im)
    size=max(16,round(im.width*font_fraction));font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
    pad=max(12,round(im.width*.045));n=length_mm*pixels_per_mm
    if n>im.width*.4: length_mm/=2;n/=2
    x=im.width-pad-n;y=im.height-pad;label=f'{length_mm:g} mm'
    box=d.textbbox((0,0),label,font=font);tw=box[2]-box[0]
    d.rounded_rectangle((min(x,x+(n-tw)/2)-9,y-size-15,max(im.width-pad,x+(n+tw)/2)+9,y+7),radius=5,fill=(0,0,0))
    d.text((x+(n-tw)/2,y-size-12),label,font=font,fill='white')
    d.line((x,y,im.width-pad,y),fill='white',width=max(3,round(im.width*.006)))
    return im,dict(length_mm=length_mm,length_pixels=n,pixels_per_mm=pixels_per_mm,position='lower right; image-space annotation')
