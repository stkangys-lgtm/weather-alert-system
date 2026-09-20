from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "weather-safety-workflow-onepage.pdf"
FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

GREEN = HexColor("#009A44")
DEEP = HexColor("#003B2D")
MINT = HexColor("#E8F6EF")
INK = HexColor("#14251F")
MUTED = HexColor("#66756F")
LINE = HexColor("#C9D8D1")
AMBER = HexColor("#F5A623")
PALE_AMBER = HexColor("#FFF4DE")
PALE = HexColor("#F5F8F7")
WHITE = HexColor("#FFFFFF")


def box(c, x, y, w, h, title, lines, fill=MINT, accent=GREEN, number=None):
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, 8, fill=1, stroke=0)
    c.setFillColor(accent)
    c.roundRect(x, y + h - 5, w, 5, 3, fill=1, stroke=0)
    if number is not None:
        c.setFillColor(accent)
        c.circle(x + 17, y + h - 23, 10, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Korean", 8)
        c.drawCentredString(x + 17, y + h - 26, str(number))
        title_x = x + 33
    else:
        title_x = x + 13
    c.setFillColor(INK)
    c.setFont("Korean", 9.3)
    c.drawString(title_x, y + h - 27, title)
    c.setFillColor(MUTED)
    c.setFont("Korean", 7.1)
    cursor = y + h - 44
    for line in lines:
        c.drawString(x + 13, cursor, line)
        cursor -= 11


def arrow(c, x1, y1, x2, y2, color=GREEN):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.8)
    c.line(x1, y1, x2 - 6, y2)
    c.line(x2 - 6, y2, x2 - 11, y2 + 4)
    c.line(x2 - 6, y2, x2 - 11, y2 - 4)


def pill(c, x, y, text, fill, fg=WHITE, width=72):
    c.setFillColor(fill)
    c.roundRect(x, y, width, 17, 8, fill=1, stroke=0)
    c.setFillColor(fg)
    c.setFont("Korean", 6.8)
    c.drawCentredString(x + width / 2, y + 5.2, text)


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("Korean", FONT_PATH))
    width, height = landscape(A4)
    c = canvas.Canvas(str(OUTPUT), pagesize=(width, height))
    c.setTitle("전사 건설현장 기상안전 자동관제 - 현재 시스템 워크플로우")

    c.setFillColor(DEEP)
    c.rect(0, height - 72, width, 72, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Korean", 20)
    c.drawString(32, height - 36, "전사 건설현장 기상안전 자동관제")
    c.setFont("Korean", 8.5)
    c.setFillColor(HexColor("#BFE8D3"))
    c.drawString(33, height - 54, "현재 시스템 워크플로우 · 기상청 공공데이터 기반 · 현장 센서 미사용 · 모바일/웹 제공")
    pill(c, width - 128, height - 49, "2026.09  구현 현황", GREEN, width=96)

    c.setFillColor(INK)
    c.setFont("Korean", 10)
    c.drawString(32, height - 101, "자동 수집 · 판단 · 변화 감지")

    y = height - 225
    bw, bh, gap = 132, 104, 18
    xs = [32 + i * (bw + gap) for i in range(5)]
    box(c, xs[0], y, bw, bh, "예약 실행", ["매시 :47 주 실행", ":17 지연·누락 보완", "45분 이내 자료면 생략"], number=1)
    box(c, xs[1], y, bw, bh, "기상 데이터 수집", ["초단기 실황", "단기예보 · 중기예보", "21개 현장 위치 매핑"], number=2)
    box(c, xs[2], y, bw, bh, "위험 분석", ["강풍 · 강수 · 폭염", "향후 특이기상 추출", "데이터 실패 별도 표시"], number=3)
    box(c, xs[3], y, bw, bh, "상태 비교", ["이전 실행과 비교", "발생·상승·하락·해제", "같은 상태 중복 억제"], number=4)
    box(c, xs[4], y, bw, bh, "결과 생성", ["지도·현장 목록", "Google Sheets 기록", "전파 문안·상태 저장"], number=5)
    for i in range(4):
        arrow(c, xs[i] + bw + 3, y + bh / 2, xs[i + 1] - 3, y + bh / 2)

    branch_y = y - 39
    center_x = xs[4] + bw / 2
    c.setStrokeColor(LINE)
    c.setLineWidth(1.4)
    c.line(center_x, y, center_x, branch_y)
    c.line(139, branch_y, 703, branch_y)
    for px in (139, 421, 703):
        c.line(px, branch_y, px, branch_y - 16)

    out_y, out_h = 185, 89
    box(c, 32, out_y, 214, out_h, "A. 관제 화면", ["지도 중심 메인 · 현장별 현재 상태", "선택 시 상세·예보 · 검색/위험 필터", "모바일 및 데스크톱 반응형"], fill=PALE)
    box(c, 314, out_y, 214, out_h, "B. 기록·감사", ["실황/예보 Google Sheets 적재", "상태·최근 변화 JSON 보존", "Sheets 장애와 화면 생성을 분리"], fill=PALE)
    box(c, 596, out_y, 214, out_h, "C. 알림 전달", ["문안 생성 → 대기열 → 중복 방지", "실패 재시도 · 6시간 후 자동 만료", "Webhook/알림톡 연결은 현재 대기"], fill=PALE_AMBER, accent=AMBER)

    c.setFillColor(DEEP)
    c.roundRect(32, 28, width - 64, 86, 10, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Korean", 9.5)
    c.drawString(48, 92, "다음 진행 게이트")
    steps = [
        ("01", "법적 기준 재정립", "현행 법령·정부기관 근거표"),
        ("02", "기존 문자 수집", "개인정보 제거 예문"),
        ("03", "문체 규칙화", "표현·길이·조치 순서"),
        ("04", "사용자 컨펌", "샘플 승인 전 적용 금지"),
        ("05", "자동작성·실발송", "템플릿 승인 후 연결"),
    ]
    sx = 48
    for idx, (num, title, detail) in enumerate(steps):
        c.setFillColor(GREEN if idx < 1 else HexColor("#315F50"))
        c.circle(sx + 8, 61, 8, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Korean", 6.5)
        c.drawCentredString(sx + 8, 58.7, num)
        c.setFont("Korean", 7.7)
        c.drawString(sx + 21, 66, title)
        c.setFillColor(HexColor("#BFD4CC"))
        c.setFont("Korean", 6.5)
        c.drawString(sx + 21, 50, detail)
        if idx < 4:
            arrow(c, sx + 122, 61, sx + 139, 61, color=HexColor("#71B895"))
        sx += 150

    c.setFillColor(MUTED)
    c.setFont("Korean", 6.3)
    c.drawRightString(width - 32, 16, "주의: 현재 위험단계는 참고 판정이며, 다음 단계에서 법적 기준·공식 특보·선제 알림을 분리하여 재설계")
    c.showPage()
    c.save()
    print(OUTPUT)


if __name__ == "__main__":
    build()
