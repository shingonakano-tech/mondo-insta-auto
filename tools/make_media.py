"""ストーリー画像・フィード画像を作る道具。
使い方:
  python tools/make_media.py feed  stock/270.jpg media/20270104_feed.jpg
  python tools/make_media.py story stock/270.jpg media/20270104_story.jpg "出雲の味" "割子そば" "出雲名物を、\\n有楽町で。"
"""
import sys, os
from PIL import Image, ImageOps, ImageDraw, ImageFont
W, H = 1080, 1920
BG=(20,18,16); GOLD=(196,164,106); WHITE=(240,236,228); GREY=(170,164,154)
def font(bold, size):
    for p in (["/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"] if bold else ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc","/usr/share/fonts/opentype/noto/NotoSerifCJK-Light.ttc"]) + ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc","/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
        if os.path.exists(p): return ImageFont.truetype(p, size, index=0)
    raise SystemExit("日本語フォントがありません: apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra")
def ct(d,y,t,f,fill,sp=18):
    b=d.multiline_textbbox((0,0),t,font=f,spacing=sp,align="center")
    d.multiline_text(((W-(b[2]-b[0]))/2-b[0],y),t,font=f,fill=fill,spacing=sp,align="center"); return y+(b[3]-b[1])
def feed(src,out):
    ImageOps.fit(ImageOps.exif_transpose(Image.open(src)).convert("RGB"),(1080,1350),Image.LANCZOS).save(out,"JPEG",quality=90)
def story(src,out,label,title,catch):
    catch=catch.replace("\\n","\n"); title=title.replace("\\n","\n")
    im=ImageOps.fit(ImageOps.exif_transpose(Image.open(src)).convert("RGB"),(960,960),Image.LANCZOS)
    c=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(c)
    ct(d,120,"しまね料理とさばしゃぶの店",font(False,30),GREY); ct(d,162,"主水 有楽町店",font(True,44),WHITE)
    d.rectangle([54,254,1025,1225],outline=GOLD,width=2); c.paste(im,(60,260))
    y=ct(d,1275,f"― {label} ―",font(False,36),GOLD)+30
    y=ct(d,y,title,font(True,70 if len(title)<=9 else 56),WHITE,12)+40
    y=ct(d,y,catch,font(False,38),WHITE,20)
    if y>1700: raise SystemExit(f"文字が下に出すぎ（y={y}）。キャッチを短くしてください")
    c.save(out,"JPEG",quality=88)
if __name__=="__main__":
    k=sys.argv[1]
    feed(*sys.argv[2:4]) if k=="feed" else story(*sys.argv[2:7])
    print("OK", sys.argv[3])
