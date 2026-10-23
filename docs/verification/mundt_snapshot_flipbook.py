"""Display five existing thesis snapshots; no interpolation or synthetic motion."""
from pathlib import Path
import json,hashlib,argparse
from pypdf import PdfReader
from PIL import Image,ImageDraw,ImageFont
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pdf',type=Path,default=Path('Mundt2023.pdf'))
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args();pdf=args.pdf;out=args.out
if out.exists():raise FileExistsError(out)
out.mkdir(parents=True)
page=PdfReader(pdf).pages[41];assert len(page.images)==1
source=page.images[0].image.convert('RGB');assert source.size==(1419,334)
source.save(out/'mundt_fig2_3_original.png')
font='/System/Library/Fonts/Supplemental/Arial.ttf'
f=ImageFont.truetype(font,20);small=ImageFont.truetype(font,16);big=ImageFont.truetype(font,27)
# Boundaries separating the five photographs in the original embedded image.
bounds=[0,284,569,853,1136,1419];times=[0,46,133,225,750000];ims=[]
for k,t in enumerate(times):
 im=Image.new('RGB',(760,535),'white');d=ImageDraw.Draw(im)
 d.text((380,15),'UW / MUNDT: PUBLISHED IGNITION SNAPSHOTS',font=f,fill='black',anchor='mt')
 d.text((380,44),'Five stills from Figure 2.3; this is NOT continuous video.',font=small,fill='black',anchor='mt')
 label=f't = {t} microseconds' if k<4 else 't = 0.75 seconds  [large time jump]'
 d.text((380,76),label,font=big,fill='#9a3b00' if k==4 else 'black',anchor='mt')
 crop=source.crop((bounds[k],0,bounds[k+1],334))
 im.paste(crop,((760-crop.width)//2,118))
 d.text((380,468),'Original photographs; no interpolation, rotation or contrast adjustment.',font=small,fill='black',anchor='mt')
 d.text((380,496),'Equal display holds. Physical time intervals are NOT equal.',font=small,fill='black',anchor='mt')
 ims.append(im);im.save(out/f'mundt_snapshot_{k}.png')
durations=[1700]*4+[3000]
ims[0].save(out/'mundt_published_snapshots.gif',save_all=True,append_images=ims[1:],duration=durations,disposal=2,optimize=False)
with Image.open(out/'mundt_published_snapshots.gif') as im:assert im.n_frames==5 and 'loop' not in im.info
(out/'mundt_snapshot_manifest.json').write_text(json.dumps(dict(
 source_pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),printed_page=26,pdf_page=42,figure='2.3',
 description='Five published photographs extracted from the user-provided thesis, not original continuous video.',
 image_name=page.images[0].name,image_size=list(source.size),crop_boundaries_px=bounds,
 physical_times_us=times,display_durations_ms=durations,
 qualification='Equal holds for readability; gap from225us to0.75s is explicit. No interpolated frames.'),indent=2)+'\n')
print('Created labeled five-snapshot flipbook from the original embedded thesis figure.')
