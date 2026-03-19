#!/usr/bin/env python3
"""
꿈 영상 생성기 v2 — 학생 사진 합성 버전
=========================================
학생 사진을 받아 미래 직업 배경과 합성하고,
Claude AI 스토리를 자막으로 붙여 .mp4 영상을 생성합니다.

설치:
    pip install anthropic pillow moviepy opencv-python

실행:
    python dream_video_generator_v2.py
"""

import os, sys, re, json, math, textwrap, tempfile, urllib.request
from pathlib import Path

# ── 패키지 확인 ──────────────────────────────────────────────────────────────
def require(pkg, install):
    try:
        return __import__(pkg)
    except ImportError:
        print(f"❌ 패키지 없음: pip install {install}")
        sys.exit(1)

anthropic_mod = require("anthropic", "anthropic")
PIL_mod       = require("PIL", "pillow")
cv2           = require("cv2", "opencv-python")

import anthropic
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import ImageClip, concatenate_videoclips
from moviepy.video.fx.all import fadein, fadeout

# ── 설정 ────────────────────────────────────────────────────────────────────
W, H          = 1280, 720
SCENE_SECS    = 6.0
OUTPUT_DIR    = Path("./dream_videos")
HAAR_CASCADE  = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

# 직업별 테마 색상 & 아이콘 이름 (이모지 대신 텍스트)
JOB_THEMES = {
    "의사":       {"bg": "#0a2342", "accent": "#4fc3f7", "icon": "＋", "label": "Dr."},
    "과학자":     {"bg": "#0d1b2a", "accent": "#64ffda", "icon": "⚛", "label": "Dr."},
    "우주비행사": {"bg": "#050d1a", "accent": "#b39ddb", "icon": "★", "label": ""},
    "선생님":     {"bg": "#1a237e", "accent": "#ffd54f", "icon": "✎", "label": ""},
    "운동선수":   {"bg": "#1b2631", "accent": "#f44336", "icon": "▶", "label": ""},
    "요리사":     {"bg": "#3e2723", "accent": "#ffcc02", "icon": "◈", "label": "Chef"},
    "음악가":     {"bg": "#1a0533", "accent": "#e040fb", "icon": "♪", "label": ""},
    "화가":       {"bg": "#1a0000", "accent": "#ff6e40", "icon": "◉", "label": ""},
    "프로그래머": {"bg": "#0d1117", "accent": "#58a6ff", "icon": "#", "label": "dev."},
    "건축가":     {"bg": "#1c2833", "accent": "#48c9b0", "icon": "▣", "label": "Arch."},
    "default":    {"bg": "#1a1a2e", "accent": "#e2b96f", "icon": "✦", "label": ""},
}

KOREAN_FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]

# ── 유틸 ────────────────────────────────────────────────────────────────────
def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def find_font():
    for p in KOREAN_FONTS:
        if Path(p).exists():
            return p
    return None

def load_font(path, size):
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def wrap_korean(text, max_chars=20):
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= max_chars and ch in " ,.，。":
            lines.append(cur.strip()); cur = ""
    if cur.strip():
        lines.append(cur.strip())
    return lines or [text]

# ── 얼굴 탐지 & 사진 처리 ────────────────────────────────────────────────────
def detect_face_region(img_pil: Image.Image):
    """OpenCV로 얼굴 위치 탐지 → (x,y,w,h) or None"""
    gray = cv2.cvtColor(
        cv2.cvtColor(img_pil.convert("RGB").__array__()
                     if hasattr(img_pil, '__array__')
                     else __import__('numpy').array(img_pil.convert("RGB")),
                     cv2.COLOR_RGB2GRAY),
        cv2.COLOR_GRAY2GRAY
    )
    clf = cv2.CascadeClassifier(HAAR_CASCADE)
    faces = clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        return None
    # 가장 큰 얼굴
    return max(faces, key=lambda f: f[2] * f[3])

def prepare_student_photo(photo_path: str, target_size=(300, 380)) -> Image.Image:
    """
    사진 로드 → 얼굴 중심으로 크롭 → 리사이즈 → 원형 마스크 적용
    """
    img = Image.open(photo_path).convert("RGBA")
    iw, ih = img.size

    face = detect_face_region(img)
    if face is not None:
        fx, fy, fw, fh = face
        # 얼굴 중심을 기준으로 상반신 포함 영역 크롭
        cx, cy = fx + fw // 2, fy + fh // 2
        crop_h = int(fh * 3.5)
        crop_w = int(crop_h * 0.75)
        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, fy - int(fh * 0.6))
        x2 = min(iw, x1 + crop_w)
        y2 = min(ih, y1 + crop_h)
        img = img.crop((x1, y1, x2, y2))
    else:
        # 얼굴 미탐지 시 중앙 상단 크롭
        cx = iw // 2
        crop_w = min(iw, ih * 3 // 4)
        x1 = max(0, cx - crop_w // 2)
        img = img.crop((x1, 0, x1 + crop_w, ih))

    img = img.resize(target_size, Image.LANCZOS)
    tw, th = target_size

    # 타원형 마스크
    mask = Image.new("L", (tw, th), 0)
    d = ImageDraw.Draw(mask)
    margin = 6
    d.ellipse([margin, margin, tw - margin, th - margin], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(3))

    result = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)
    return result

# ── 배경 그리기 ───────────────────────────────────────────────────────────────
def draw_background(draw: ImageDraw.Draw, bg_rgb, accent_rgb, style="default"):
    """배경 + 기하학적 장식"""
    draw.rectangle([0, 0, W, H], fill=bg_rgb)

    # 어두운 그라데이션 레이어 (루프로 시뮬레이션)
    for i in range(40):
        alpha = int(60 * (i / 40))
        c = tuple(min(255, bg_rgb[j] + alpha) for j in range(3))
        draw.rectangle([0, H - i * 6, W, H], fill=c)

    # 빛나는 원 장식
    ax, ay = W * 3 // 4, H // 3
    for r, a in [(260, 12), (180, 20), (100, 35)]:
        c = tuple(int(accent_rgb[j] * a / 255) for j in range(3))
        draw.ellipse([ax - r, ay - r, ax + r, ay + r], outline=c + (a,), width=1)

    # 수평선
    for y_off, opacity in [(H - 4, 60), (H - 2, 40)]:
        c = tuple(int(accent_rgb[j] * opacity // 255) for j in range(3))
        draw.line([(0, y_off), (W, y_off)], fill=c, width=1)

# ── 장면별 이미지 생성 ────────────────────────────────────────────────────────
def create_title_frame(story, student, photo: Image.Image, font_path, theme) -> Image.Image:
    img   = Image.new("RGBA", (W, H), hex2rgb(theme["bg"]) + (255,))
    draw  = ImageDraw.Draw(img)
    bg    = hex2rgb(theme["bg"])
    acc   = hex2rgb(theme["accent"])
    draw_background(draw, bg, acc)

    # 사진 배치 (좌측)
    pw, ph = photo.size
    px, py = 120, (H - ph) // 2 - 30
    # 글로우 효과 (배경에 원 그리기)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    for r in range(pw // 2 + 60, pw // 2, -4):
        a = int(80 * (1 - (r - pw // 2) / 60))
        gd.ellipse([px + pw // 2 - r, py + ph // 2 - r,
                    px + pw // 2 + r, py + ph // 2 + r],
                   fill=acc + (a,))
    img = Image.alpha_composite(img, glow)
    img.paste(photo, (px, py), photo)

    # 오른쪽 텍스트
    tx = 520
    fn_sm  = load_font(font_path, 18)
    fn_mid = load_font(font_path, 36)
    fn_big = load_font(font_path, 62)
    fn_tag = load_font(font_path, 26)

    draw2 = ImageDraw.Draw(img)
    draw2.text((tx, 180), "나의 꿈 이야기", font=fn_sm, fill=acc + (180,))
    draw2.text((tx, 215), story["title"], font=fn_big, fill=(255, 255, 255))
    draw2.text((tx, 300), story["tagline"], font=fn_tag, fill=acc + (220,))

    # 구분선
    draw2.line([(tx, 345), (tx + 380, 345)], fill=acc + (80,), width=1)
    draw2.text((tx, 360), f"{student['name']}의 이야기", font=fn_mid, fill=(200, 200, 220))
    draw2.text((tx, 410), f"꿈: {student['dream_job']}", font=fn_sm, fill=(160, 160, 200))

    # 아이콘
    fn_icon = load_font(font_path, 72)
    draw2.text((W - 110, H - 110), theme["icon"], font=fn_icon, fill=acc + (40,))

    return img.convert("RGB")


def create_scene_frame(scene, scene_idx, total, student, photo: Image.Image,
                       font_path, theme) -> Image.Image:
    img  = Image.new("RGBA", (W, H), hex2rgb(theme["bg"]) + (255,))
    draw = ImageDraw.Draw(img)
    bg   = hex2rgb(theme["bg"])
    acc  = hex2rgb(theme["accent"])
    draw_background(draw, bg, acc)

    # ── 사진 (우측) ──
    pw, ph = photo.size
    # 장면에 따라 사진 크기 변화 (점점 커짐)
    scale = 0.75 + 0.05 * scene_idx
    new_w = int(pw * scale)
    new_h = int(ph * scale)
    photo_resized = photo.resize((new_w, new_h), Image.LANCZOS)

    px = W - new_w - 80
    py = (H - new_h) // 2

    # 사진 글로우
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    cx, cy = px + new_w // 2, py + new_h // 2
    for r in range(new_w // 2 + 70, new_w // 2, -5):
        a = int(60 * (1 - (r - new_w // 2) / 70))
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=acc + (a,))
    img = Image.alpha_composite(img, glow)
    img.paste(photo_resized, (px, py), photo_resized)

    # ── 텍스트 (좌측) ──
    draw2   = ImageDraw.Draw(img)
    fn_time = load_font(font_path, 16)
    fn_nar  = load_font(font_path, 38)
    fn_sm   = load_font(font_path, 20)

    lx = 70

    # 시간 레이블 박스
    time_label = scene.get("time_label", "")
    tbb = draw2.textbbox((0, 0), time_label, font=fn_time)
    tw_ = tbb[2] - tbb[0] + 24
    draw2.rounded_rectangle([lx, 70, lx + tw_, 100], radius=12,
                             fill=acc + (30,), outline=acc + (80,))
    draw2.text((lx + 12, 75), time_label, font=fn_time, fill=acc)

    # 나레이션 (줄 나누기)
    narration = scene.get("narration", "")
    lines     = wrap_korean(narration, 18)
    y_nar     = 140
    for line in lines:
        draw2.text((lx, y_nar), line, font=fn_nar, fill=(255, 255, 255))
        y_nar += 52

    # 시각 설명 (작은 글씨)
    visual = scene.get("visual_desc", "")
    vis_lines = wrap_korean(visual, 28)
    y_vis = y_nar + 24
    for vl in vis_lines:
        draw2.text((lx, y_vis), vl, font=fn_sm, fill=(160, 160, 200))
        y_vis += 32

    # ── 하단 진행 바 ──
    bar_w, bar_h, gap = 56, 5, 10
    total_w = total * bar_w + (total - 1) * gap
    bx = (W - total_w) // 2
    by = H - 38
    for i in range(total):
        color = acc if i < scene_idx else (60, 60, 90)
        draw2.rounded_rectangle([bx + i * (bar_w + gap), by,
                                   bx + i * (bar_w + gap) + bar_w, by + bar_h],
                                  radius=3, fill=color)

    return img.convert("RGB")


def create_ending_frame(student, photo: Image.Image, font_path, theme) -> Image.Image:
    img  = Image.new("RGBA", (W, H), hex2rgb(theme["bg"]) + (255,))
    draw = ImageDraw.Draw(img)
    bg   = hex2rgb(theme["bg"])
    acc  = hex2rgb(theme["accent"])
    draw_background(draw, bg, acc)

    # 사진 크게 중앙 배치
    pw, ph = photo.size
    scale  = 1.4
    new_w, new_h = int(pw * scale), int(ph * scale)
    photo_big = photo.resize((new_w, new_h), Image.LANCZOS)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    cx, cy = W // 2, H // 2 - 30
    for r in range(new_w // 2 + 100, new_w // 2, -6):
        a = int(70 * (1 - (r - new_w // 2) / 100))
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=acc + (a,))
    img = Image.alpha_composite(img, glow)
    img.paste(photo_big, (cx - new_w // 2, cy - new_h // 2), photo_big)

    draw2   = ImageDraw.Draw(img)
    fn_big  = load_font(font_path, 46)
    fn_mid  = load_font(font_path, 28)
    fn_sm   = load_font(font_path, 20)

    # 상단 메시지
    msg1 = f"{student['name']}, 너의 꿈은"
    bb   = draw2.textbbox((0, 0), msg1, font=fn_big)
    draw2.text(((W - (bb[2] - bb[0])) // 2, 38), msg1,
               font=fn_big, fill=(255, 255, 255))

    msg2 = "이미 시작됐어."
    bb2  = draw2.textbbox((0, 0), msg2, font=fn_big)
    draw2.text(((W - (bb2[2] - bb2[0])) // 2, 92), msg2,
               font=fn_big, fill=acc)

    # 하단 메시지
    msg3 = f"미래의 {student['dream_job']}가 오늘을 응원하고 있어."
    bb3  = draw2.textbbox((0, 0), msg3, font=fn_mid)
    draw2.text(((W - (bb3[2] - bb3[0])) // 2, H - 110), msg3,
               font=fn_mid, fill=(200, 200, 230))

    msg4 = "네 꿈을 믿어."
    bb4  = draw2.textbbox((0, 0), msg4, font=fn_sm)
    draw2.text(((W - (bb4[2] - bb4[0])) // 2, H - 68), msg4,
               font=fn_sm, fill=acc + (180,))

    return img.convert("RGB")

# ── Claude 스토리 생성 ───────────────────────────────────────────────────────
def generate_story(student: dict, client) -> dict:
    print("\n  🤖 AI가 미래 스토리를 쓰고 있어요...")
    hobby_line = f"좋아하는 것: {student['hobby']}" if student.get("hobby") else ""
    prompt = f"""
중학생 {student['name']}의 꿈을 이룬 미래를 5장면으로 만들어주세요.
- 꿈의 직업: {student['dream_job']}
- 하고싶은 일: {student['dream_detail']}
- {hobby_line}

반드시 아래 JSON만 응답. 다른 텍스트 없이.

{{
  "title": "영상 제목 15자 이내",
  "tagline": "감동 문구 25자 이내",
  "scenes": [
    {{"scene_number":1,"time_label":"현재 · 중학교 2학년","narration":"나레이션 2문장 40자이내","visual_desc":"장면묘사 30자이내","bg_color":"#16213e"}},
    {{"scene_number":2,"time_label":"5년 후 · 고등학교 졸업","narration":"나레이션 2문장 40자이내","visual_desc":"장면묘사 30자이내","bg_color":"#0f3460"}},
    {{"scene_number":3,"time_label":"10년 후 · 꿈을 향해","narration":"나레이션 2문장 40자이내","visual_desc":"장면묘사 30자이내","bg_color":"#533483"}},
    {{"scene_number":4,"time_label":"15년 후 · {student['dream_job']}이 되다","narration":"나레이션 2문장 40자이내","visual_desc":"장면묘사 30자이내","bg_color":"#e94560"}},
    {{"scene_number":5,"time_label":"오늘 · 다시 현재로","narration":"나레이션 2문장 40자이내","visual_desc":"장면묘사 30자이내","bg_color":"#1a1a2e"}}
  ]
}}"""
    msg = client.messages.create(
        model="claude-opus-4-5", max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    story = json.loads(raw)
    print(f"  ✅ 스토리: '{story['title']}'")
    return story

# ── 입력 수집 ────────────────────────────────────────────────────────────────
def collect_input() -> dict:
    print("\n" + "="*52)
    print("  ✨  나의 꿈 영상 만들기  (사진 합성 버전)")
    print("="*52 + "\n")

    name = input("이름: ").strip() or "학생"
    dream_job = input("미래 직업: ").strip() or "과학자"
    dream_detail = input("그 직업에서 하고 싶은 일: ").strip() or "세상을 바꾸고 싶어요"
    hobby = input("좋아하는 것 (선택): ").strip()

    # 사진 경로
    while True:
        photo_path = input("\n사진 파일 경로 (jpg/png): ").strip().strip("'\"")
        if not photo_path:
            print("  ⚠️  사진 경로를 입력해주세요.")
            continue
        if not Path(photo_path).exists():
            print(f"  ❌ 파일이 없어요: {photo_path}")
            continue
        break

    return {"name": name, "dream_job": dream_job,
            "dream_detail": dream_detail, "hobby": hobby,
            "photo_path": photo_path}

# ── 영상 합성 ────────────────────────────────────────────────────────────────
def build_video(frames: list, output_path: Path):
    print("\n  🎬 영상 조합 중...")
    clips = []
    for i, frame_pil in enumerate(frames):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            frame_pil.save(f.name, quality=95)
            clip = ImageClip(f.name, duration=SCENE_SECS)
            clip = fadein(clip, 0.7)
            clip = fadeout(clip, 0.7)
            clips.append(clip)
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(str(output_path), fps=24, codec="libx264",
                          audio=False, logger=None)

# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  환경변수 설정 필요: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    font_path = find_font()
    print(f"{'✅ 폰트:' if font_path else '⚠️  한글 폰트 없음 —'} {font_path or '기본 폰트 사용'}")

    student = collect_input()

    # 사진 처리
    print("\n  🖼️  사진 처리 중 (얼굴 탐지)...")
    photo = prepare_student_photo(student["photo_path"])
    print("  ✅ 사진 준비 완료")

    # 직업 테마 선택
    theme = next(
        (v for k, v in JOB_THEMES.items() if k in student["dream_job"]),
        JOB_THEMES["default"]
    )

    # AI 스토리
    client = anthropic.Anthropic(api_key=api_key)
    story  = generate_story(student, client)

    # 프레임 생성
    print("\n  🎨 장면 이미지 그리는 중...")
    frames = []

    frames.append(create_title_frame(story, student, photo, font_path, theme))
    print("  ✅ 타이틀")

    scenes = story["scenes"]
    for i, scene in enumerate(scenes, 1):
        frames.append(create_scene_frame(scene, i, len(scenes),
                                          student, photo, font_path, theme))
        print(f"  ✅ 장면 {i}: {scene['time_label']}")

    frames.append(create_ending_frame(student, photo, font_path, theme))
    print("  ✅ 엔딩")

    # 영상 저장
    safe  = re.sub(r"[^\w가-힣]", "_", student["name"])
    out   = OUTPUT_DIR / f"dream_{safe}.mp4"
    build_video(frames, out)

    print(f"\n{'='*52}")
    print(f"  🎉  완성!  →  {out.resolve()}")
    print(f"{'='*52}\n")

if __name__ == "__main__":
    main()
