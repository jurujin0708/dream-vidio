"""
꿈 영상 생성기 — Streamlit 웹 앱
==================================
실행: streamlit run app.py
"""

import os, sys, re, json, io, tempfile, time
from pathlib import Path

import streamlit as st

# ── 페이지 설정 (반드시 첫 번째 st 호출) ──────────────────────────────────────
st.set_page_config(
    page_title="나의 꿈 영상 만들기",
    page_icon="🌟",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS 커스텀 ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

/* 전체 배경 */
.stApp {
    background: linear-gradient(135deg, #0a0a1a 0%, #0d1b3e 50%, #1a0d2e 100%);
    min-height: 100vh;
}

/* 헤더 */
.hero {
    text-align: center;
    padding: 2.5rem 0 1.5rem;
}
.hero h1 {
    font-size: 2.6rem;
    font-weight: 700;
    background: linear-gradient(90deg, #e2b96f, #fff, #b39ddb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.4rem;
}
.hero p {
    color: #8899bb;
    font-size: 1rem;
}

/* 카드 */
.card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1.2rem;
}
.card-title {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #e2b96f;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

/* 스텝 뱃지 */
.step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px; height: 26px;
    border-radius: 50%;
    background: #e2b96f22;
    border: 1px solid #e2b96f66;
    color: #e2b96f;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 8px;
}

/* 입력 필드 */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #e2b96f !important;
    box-shadow: 0 0 0 2px rgba(226,185,111,0.2) !important;
}
label { color: #aabbcc !important; font-size: 0.88rem !important; }

/* 파일 업로더 */
.stFileUploader {
    background: rgba(255,255,255,0.04) !important;
    border: 1.5px dashed rgba(226,185,111,0.4) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}

/* 버튼 */
.stButton > button {
    width: 100%;
    padding: 0.85rem 2rem;
    border-radius: 12px;
    background: linear-gradient(135deg, #e2b96f, #c8943a);
    border: none;
    color: #1a0d00;
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 0.03em;
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Noto Sans KR', sans-serif;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(226,185,111,0.35);
}
.stButton > button:active { transform: translateY(0); }

/* 진행 상태 */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #e2b96f, #b39ddb) !important;
    border-radius: 999px !important;
}

/* 성공/경고 메시지 */
.stSuccess { background: rgba(100,255,200,0.08) !important; border-color: rgba(100,255,200,0.3) !important; }
.stWarning { background: rgba(255,200,100,0.08) !important; border-color: rgba(255,200,100,0.3) !important; }

/* 사진 미리보기 */
.photo-preview {
    border-radius: 12px;
    overflow: hidden;
    border: 2px solid rgba(226,185,111,0.3);
    margin-top: 0.5rem;
}

/* 장면 카드 */
.scene-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.scene-time {
    font-size: 0.75rem;
    color: #e2b96f;
    font-weight: 600;
    margin-bottom: 0.3rem;
    letter-spacing: 0.05em;
}
.scene-text { color: #dde4f0; font-size: 0.9rem; line-height: 1.6; }

/* 다운로드 버튼 */
.stDownloadButton > button {
    background: linear-gradient(135deg, #4fc3f7, #1976d2) !important;
    color: white !important;
    font-size: 1rem;
    padding: 0.85rem !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
}

/* 구분선 */
hr { border-color: rgba(255,255,255,0.08) !important; }

/* 스크롤바 */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #334; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── 패키지 확인 ───────────────────────────────────────────────────────────────
missing = []
try:
    import anthropic
except ImportError:
    missing.append("anthropic")
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import numpy as np
except ImportError:
    missing.append("pillow numpy")
try:
    import cv2
except ImportError:
    missing.append("opencv-python")
try:
    from moviepy.editor import ImageClip, concatenate_videoclips
    from moviepy.video.fx.all import fadein, fadeout
except ImportError:
    missing.append("moviepy")

if missing:
    st.error(f"필요한 패키지를 설치해주세요:\n\n```\npip install {' '.join(missing)}\n```")
    st.stop()

# ── 유틸 (dream_video_generator_v2 인라인) ────────────────────────────────────
KOREAN_FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]
JOB_THEMES = {
    "의사":       {"bg": "#0a2342", "accent": "#4fc3f7", "icon": "＋"},
    "과학자":     {"bg": "#0d1b2a", "accent": "#64ffda", "icon": "⚛"},
    "우주비행사": {"bg": "#050d1a", "accent": "#b39ddb", "icon": "★"},
    "선생님":     {"bg": "#1a237e", "accent": "#ffd54f", "icon": "✎"},
    "운동선수":   {"bg": "#1b2631", "accent": "#f44336", "icon": "▶"},
    "요리사":     {"bg": "#3e2723", "accent": "#ffcc02", "icon": "◈"},
    "음악가":     {"bg": "#1a0533", "accent": "#e040fb", "icon": "♪"},
    "화가":       {"bg": "#1a0000", "accent": "#ff6e40", "icon": "◉"},
    "프로그래머": {"bg": "#0d1117", "accent": "#58a6ff", "icon": "#"},
    "건축가":     {"bg": "#1c2833", "accent": "#48c9b0", "icon": "▣"},
    "default":    {"bg": "#1a1a2e", "accent": "#e2b96f", "icon": "✦"},
}
W, H = 1280, 720

def find_font():
    for p in KOREAN_FONTS:
        if Path(p).exists(): return p
    return None

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def load_font(path, size):
    if path:
        try: return ImageFont.truetype(path, size)
        except Exception: pass
    try: return ImageFont.truetype("arial.ttf", size)
    except Exception: return ImageFont.load_default()

def wrap_korean(text, max_chars=20):
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= max_chars:
            lines.append(cur.strip()); cur = ""
    if cur.strip(): lines.append(cur.strip())
    return lines or [text]

def prepare_photo(pil_img: Image.Image, target_size=(300, 380)) -> Image.Image:
    img = pil_img.convert("RGBA")
    iw, ih = img.size
    arr = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    clf = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = clf.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
    if len(faces):
        fx, fy, fw, fh = max(faces, key=lambda f: f[2]*f[3])
        cx, cy = fx+fw//2, fy+fh//2
        ch = int(fh*3.5); cw = int(ch*0.75)
        x1=max(0,cx-cw//2); y1=max(0,fy-int(fh*0.6))
        x2=min(iw,x1+cw);   y2=min(ih,y1+ch)
        img = img.crop((x1,y1,x2,y2))
    else:
        cw = min(iw, ih*3//4)
        img = img.crop((iw//2-cw//2, 0, iw//2+cw//2, ih))
    img = img.resize(target_size, Image.LANCZOS)
    tw, th = target_size
    mask = Image.new("L",(tw,th),0)
    d=ImageDraw.Draw(mask)
    d.ellipse([6,6,tw-6,th-6],fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(3))
    out = Image.new("RGBA",(tw,th),(0,0,0,0))
    out.paste(img,(0,0),mask)
    return out

def draw_bg(draw, bg_rgb, acc_rgb):
    draw.rectangle([0,0,W,H], fill=bg_rgb)
    for i in range(40):
        a=int(60*(i/40))
        c=tuple(min(255,bg_rgb[j]+a) for j in range(3))
        draw.rectangle([0,H-i*6,W,H], fill=c)
    ax,ay=W*3//4,H//3
    for r,a in [(260,12),(180,20),(100,35)]:
        c=tuple(int(acc_rgb[j]*a//255) for j in range(3))
        draw.ellipse([ax-r,ay-r,ax+r,ay+r], outline=c+(a,), width=1)

def paste_photo_with_glow(img, photo, px, py, acc_rgb):
    pw,ph=photo.size
    glow=Image.new("RGBA",(W,H),(0,0,0,0))
    gd=ImageDraw.Draw(glow)
    cx,cy=px+pw//2,py+ph//2
    for r in range(pw//2+70,pw//2,-5):
        a=int(60*(1-(r-pw//2)/70))
        gd.ellipse([cx-r,cy-r,cx+r,cy+r], fill=acc_rgb+(a,))
    img=Image.alpha_composite(img.convert("RGBA"),glow)
    img.paste(photo,(px,py),photo)
    return img

def make_title_frame(story, student, photo, font_path, theme):
    img=Image.new("RGBA",(W,H),hex2rgb(theme["bg"])+(255,))
    draw=ImageDraw.Draw(img)
    bg=hex2rgb(theme["bg"]); acc=hex2rgb(theme["accent"])
    draw_bg(draw,bg,acc)
    pw,ph=photo.size
    px,py=100,(H-ph)//2-30
    img=paste_photo_with_glow(img,photo,px,py,acc)
    d2=ImageDraw.Draw(img)
    tx=480
    d2.text((tx,170),"나의 꿈 이야기",font=load_font(font_path,18),fill=acc+(180,))
    d2.text((tx,210),story["title"],font=load_font(font_path,58),fill=(255,255,255))
    d2.text((tx,285),story["tagline"],font=load_font(font_path,26),fill=acc+(220,))
    d2.line([(tx,335),(tx+380,335)],fill=acc+(60,),width=1)
    d2.text((tx,350),f"{student['name']}의 이야기",font=load_font(font_path,34),fill=(200,200,220))
    d2.text((tx,400),f"꿈: {student['dream_job']}",font=load_font(font_path,18),fill=(140,140,180))
    return img.convert("RGB")

def make_scene_frame(scene, idx, total, student, photo, font_path, theme):
    img=Image.new("RGBA",(W,H),hex2rgb(theme["bg"])+(255,))
    draw=ImageDraw.Draw(img)
    bg=hex2rgb(theme["bg"]); acc=hex2rgb(theme["accent"])
    draw_bg(draw,bg,acc)
    scale=0.75+0.05*idx
    pw2,ph2=int(photo.size[0]*scale),int(photo.size[1]*scale)
    p2=photo.resize((pw2,ph2),Image.LANCZOS)
    px=W-pw2-80; py=(H-ph2)//2
    img=paste_photo_with_glow(img,p2,px,py,acc)
    d2=ImageDraw.Draw(img)
    lx=70
    tl=scene.get("time_label","")
    tbb=d2.textbbox((0,0),tl,font=load_font(font_path,16))
    tw_=tbb[2]-tbb[0]+24
    d2.rounded_rectangle([lx,70,lx+tw_,98],radius=12,fill=acc+(25,),outline=acc+(70,))
    d2.text((lx+12,74),tl,font=load_font(font_path,16),fill=acc)
    lines=wrap_korean(scene.get("narration",""),18)
    y=140
    for ln in lines:
        d2.text((lx,y),ln,font=load_font(font_path,38),fill=(255,255,255)); y+=52
    for vl in wrap_korean(scene.get("visual_desc",""),30):
        d2.text((lx,y+18),vl,font=load_font(font_path,20),fill=(150,150,190)); y+=30
    bw,gap=56,10
    tot_w=total*bw+(total-1)*gap
    bx=(W-tot_w)//2; by=H-38
    for i in range(total):
        c=acc if i<idx else (50,50,80)
        d2.rounded_rectangle([bx+i*(bw+gap),by,bx+i*(bw+gap)+bw,by+5],radius=3,fill=c)
    return img.convert("RGB")

def make_ending_frame(student, photo, font_path, theme):
    img=Image.new("RGBA",(W,H),hex2rgb(theme["bg"])+(255,))
    draw=ImageDraw.Draw(img)
    bg=hex2rgb(theme["bg"]); acc=hex2rgb(theme["accent"])
    draw_bg(draw,bg,acc)
    scale=1.35
    pw2,ph2=int(photo.size[0]*scale),int(photo.size[1]*scale)
    p2=photo.resize((pw2,ph2),Image.LANCZOS)
    img=paste_photo_with_glow(img,p2,W//2-pw2//2,H//2-ph2//2-20,acc)
    d2=ImageDraw.Draw(img)
    for txt,y,sz,col in [
        (f"{student['name']}, 너의 꿈은", 36, 44, (255,255,255)),
        ("이미 시작됐어.", 88, 44, acc),
        (f"미래의 {student['dream_job']}가 오늘을 응원하고 있어.", H-108, 27, (180,180,220)),
        ("네 꿈을 믿어.", H-66, 20, acc+(180,)),
    ]:
        bb=d2.textbbox((0,0),txt,font=load_font(font_path,sz))
        d2.text(((W-(bb[2]-bb[0]))//2,y),txt,font=load_font(font_path,sz),fill=col)
    return img.convert("RGB")

def generate_story(student, api_key) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    hobby_line = f"좋아하는 것: {student['hobby']}" if student.get("hobby") else ""
    prompt = f"""
중학생 {student['name']}의 꿈을 이룬 미래를 5장면으로 만들어주세요.
직업: {student['dream_job']} / 하고싶은 일: {student['dream_detail']} / {hobby_line}

반드시 JSON만 응답. 다른 텍스트 없이.
{{"title":"15자이내","tagline":"25자이내","scenes":[
  {{"scene_number":1,"time_label":"현재 · 중학교 2학년","narration":"40자이내","visual_desc":"30자이내"}},
  {{"scene_number":2,"time_label":"5년 후 · 고등학교 졸업","narration":"40자이내","visual_desc":"30자이내"}},
  {{"scene_number":3,"time_label":"10년 후 · 꿈을 향해","narration":"40자이내","visual_desc":"30자이내"}},
  {{"scene_number":4,"time_label":"15년 후 · {student['dream_job']}이 되다","narration":"40자이내","visual_desc":"30자이내"}},
  {{"scene_number":5,"time_label":"오늘 · 다시 현재로","narration":"40자이내","visual_desc":"30자이내"}}
]}}"""
    msg = client.messages.create(
        model="claude-opus-4-5", max_tokens=1200,
        messages=[{"role":"user","content":prompt}]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```json\s*","",raw); raw = re.sub(r"\s*```$","",raw)
    return json.loads(raw)

def build_video_bytes(frames: list, font_path) -> bytes:
    """PIL 프레임 리스트 → mp4 bytes"""
    with tempfile.TemporaryDirectory() as td:
        clips = []
        for i, frm in enumerate(frames):
            p = Path(td)/f"f{i:03d}.jpg"
            frm.save(str(p), quality=92)
            clip = ImageClip(str(p), duration=6.0)
            clip = fadein(clip, 0.6)
            clip = fadeout(clip, 0.6)
            clips.append(clip)
        out = Path(td)/"out.mp4"
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(str(out), fps=24, codec="libx264",
                              audio=False, logger=None)
        return out.read_bytes()

# ── UI ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>✨ 나의 꿈 영상 만들기</h1>
  <p>사진과 꿈을 입력하면 미래의 내 모습을 담은 영상이 만들어져요</p>
</div>
""", unsafe_allow_html=True)

# ── API 키 입력 ───────────────────────────────────────────────────────────────
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    with st.expander("🔑 Anthropic API 키 설정", expanded=True):
        api_key = st.text_input(
            "API 키",
            type="password",
            placeholder="sk-ant-...",
            help="https://console.anthropic.com 에서 발급받으세요"
        )

if not api_key:
    st.info("위에서 Anthropic API 키를 입력해주세요.")
    st.stop()

# ── STEP 1: 사진 업로드 ───────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title"><span class="step-badge">1</span>사진 업로드</div>', unsafe_allow_html=True)

uploaded = st.file_uploader(
    "얼굴이 잘 보이는 사진을 올려주세요 (정면, 밝은 조명 권장)",
    type=["jpg","jpeg","png"],
    label_visibility="collapsed"
)

if uploaded:
    col1, col2 = st.columns([1, 2])
    with col1:
        orig = Image.open(uploaded)
        st.image(orig, caption="원본 사진", use_container_width=True)
    with col2:
        with st.spinner("얼굴 탐지 중..."):
            try:
                processed = prepare_photo(orig)
                st.image(processed, caption="처리된 사진 (영상에 사용될 모습)", use_container_width=True)
                st.success("✅ 얼굴을 찾았어요!")
            except Exception as e:
                st.warning(f"얼굴 자동 탐지에 실패했지만 계속 진행할 수 있어요. ({e})")
                processed = prepare_photo(orig)

st.markdown('</div>', unsafe_allow_html=True)

# ── STEP 2: 학생 정보 ────────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title"><span class="step-badge">2</span>나의 꿈 입력</div>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)
with col_a:
    name = st.text_input("이름", placeholder="김민준", max_chars=10)
with col_b:
    dream_job = st.text_input("미래 직업", placeholder="우주비행사, 의사, 프로그래머 …", max_chars=15)

dream_detail = st.text_area(
    "그 직업에서 어떤 일을 하고 싶나요?",
    placeholder="예: 화성에 처음 발을 딛는 우주비행사가 되고 싶어요. 인류의 새로운 도전을 이끌고 싶습니다.",
    max_chars=100,
    height=90,
)
hobby = st.text_input("현재 좋아하는 것 (선택)", placeholder="수학, 그림 그리기, 음악 …", max_chars=20)

st.markdown('</div>', unsafe_allow_html=True)

# ── STEP 3: 생성 버튼 ────────────────────────────────────────────────────────
ready = uploaded and name and dream_job and dream_detail

if not ready:
    missing_items = []
    if not uploaded: missing_items.append("사진")
    if not name: missing_items.append("이름")
    if not dream_job: missing_items.append("미래 직업")
    if not dream_detail: missing_items.append("하고 싶은 일")
    if missing_items:
        st.caption(f"아직 입력이 필요해요: {', '.join(missing_items)}")

generate_btn = st.button("🎬  나의 꿈 영상 만들기", disabled=not ready)

# ── 생성 프로세스 ─────────────────────────────────────────────────────────────
if generate_btn and ready:
    student = {"name": name, "dream_job": dream_job,
               "dream_detail": dream_detail, "hobby": hobby}
    font_path = find_font()
    theme = next((v for k,v in JOB_THEMES.items() if k in dream_job), JOB_THEMES["default"])

    progress = st.progress(0)
    status   = st.empty()

    try:
        # 1. 스토리 생성
        status.markdown("🤖 **AI가 미래 스토리를 쓰고 있어요...**")
        story = generate_story(student, api_key)
        progress.progress(25)

        # 스토리 미리보기
        with st.expander("📖 생성된 스토리 보기", expanded=True):
            st.markdown(f"### {story['title']}")
            st.caption(story['tagline'])
            st.divider()
            for sc in story["scenes"]:
                st.markdown(f'<div class="scene-card"><div class="scene-time">{sc["time_label"]}</div><div class="scene-text">{sc["narration"]}</div></div>', unsafe_allow_html=True)

        # 2. 이미지 처리
        status.markdown("🖼️ **학생 사진 처리 중...**")
        photo = prepare_photo(Image.open(uploaded))
        progress.progress(40)

        # 3. 프레임 생성
        status.markdown("🎨 **장면 이미지를 그리고 있어요...**")
        frames = []
        frames.append(make_title_frame(story, student, photo, font_path, theme))
        progress.progress(50)

        scenes = story["scenes"]
        for i, sc in enumerate(scenes, 1):
            frames.append(make_scene_frame(sc, i, len(scenes), student, photo, font_path, theme))
            progress.progress(50 + i * 7)
            status.markdown(f"🎨 **장면 {i}/5 그리는 중...**")

        frames.append(make_ending_frame(student, photo, font_path, theme))
        progress.progress(88)

        # 4. 영상 합성
        status.markdown("🎬 **영상을 합성하고 있어요...**")
        video_bytes = build_video_bytes(frames, font_path)
        progress.progress(100)

        status.empty()
        progress.empty()

        # 결과
        st.balloons()
        st.success(f"🎉 {name}의 꿈 영상이 완성됐어요!")

        st.video(video_bytes)

        safe = re.sub(r"[^\w가-힣]","_", name)
        st.download_button(
            label="⬇️  영상 다운로드 (.mp4)",
            data=video_bytes,
            file_name=f"dream_{safe}.mp4",
            mime="video/mp4",
            use_container_width=True,
        )

    except json.JSONDecodeError:
        st.error("AI 응답 파싱에 실패했어요. 다시 시도해주세요.")
    except anthropic.AuthenticationError:
        st.error("API 키가 올바르지 않아요. 다시 확인해주세요.")
    except Exception as e:
        st.error(f"오류가 발생했어요: {e}")
        st.exception(e)
