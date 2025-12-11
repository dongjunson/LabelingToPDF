#!/usr/bin/env python3
"""
파일명 규칙 가이드를 PDF로 생성하는 스크립트
"""
import math
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image

FONTS_DIR = Path("fonts")
LOGO_PATH = Path("logo.png")
PRETENDARD_REGULAR = "Pretendard-Regular"
PRETENDARD_BOLD = "Pretendard-Bold"
PRETENDARD_FONT_REGULAR_PATH = FONTS_DIR / "Pretendard-Regular.ttf"
PRETENDARD_FONT_BOLD_PATH = FONTS_DIR / "Pretendard-Bold.ttf"

# PDF 기본 치수
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 20 * mm
FOOTER_HEIGHT = 15 * mm
FOOTER_BOTTOM_MARGIN = 15 * mm

def setup_fonts():
    """Pretendard 폰트 설정"""
    try:
        if PRETENDARD_FONT_REGULAR_PATH.exists():
            pdfmetrics.registerFont(TTFont(PRETENDARD_REGULAR, str(PRETENDARD_FONT_REGULAR_PATH), subfontIndex=0))
        if PRETENDARD_FONT_BOLD_PATH.exists():
            pdfmetrics.registerFont(TTFont(PRETENDARD_BOLD, str(PRETENDARD_FONT_BOLD_PATH), subfontIndex=0))
        return True
    except Exception as e:
        print(f"⚠ 폰트 등록 오류: {e}")
        return False

def convert_to_rgb(img):
    """이미지를 RGB 모드로 변환"""
    if img.mode == 'RGB':
        return img
    try:
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            return background
        else:
            return img.convert('RGB')
    except:
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img)
        return background

def draw_watermark(canvas_obj, doc):
    """워터마크 그리기"""
    if not LOGO_PATH.exists():
        return
    
    c = canvas_obj
    try:
        logo_img = Image.open(LOGO_PATH).convert('L').convert('RGB')
        watermark_width = 35 * mm
        watermark_height = watermark_width * logo_img.height / logo_img.width
        
        rotation = 45
        spacing_x = 55 * mm
        spacing_y = 35 * mm
        
        c.saveState()
        c.setFillAlpha(0.08)
        c.setStrokeAlpha(0.08)
        
        diagonal = math.sqrt(watermark_width**2 + watermark_height**2)
        half_diag = diagonal / 2
        
        start_x = half_diag - watermark_width/2 - spacing_x
        end_x = PAGE_WIDTH + spacing_x
        start_y = -100 * mm
        end_y = PAGE_HEIGHT + 100 * mm
        
        buffer = BytesIO()
        logo_img.save(buffer, format='PNG')
        buffer.seek(0)
        img_reader = ImageReader(buffer)
        
        y = start_y
        row = 0
        while y < end_y:
            x = start_x if row % 2 == 0 else start_x + (spacing_x / 2)
            while x < end_x:
                c.saveState()
                c.translate(x + watermark_width/2, y + watermark_height/2)
                c.rotate(rotation)
                c.drawImage(img_reader, -watermark_width/2, -watermark_height/2, 
                          width=watermark_width, height=watermark_height, mask='auto')
                c.restoreState()
                x += spacing_x
            y += spacing_y
            row += 1
            
        c.restoreState()
    except Exception as e:
        print(f"  ⚠ 워터마크 오류: {e}")

def draw_footer(canvas_obj, doc, page_num):
    """푸터 그리기 (로고 포함)"""
    c = canvas_obj
    footer_y = FOOTER_BOTTOM_MARGIN
    
    # Page Number
    fonts_available = PRETENDARD_FONT_REGULAR_PATH.exists()
    try:
        if fonts_available:
            c.setFont(PRETENDARD_REGULAR, 8)
        else:
            c.setFont("Helvetica", 8)
    except:
        c.setFont("Helvetica", 8)
    c.setFillColor(black)
    c.drawString(MARGIN, footer_y, f"Page {page_num}")
    
    # Logo
    if LOGO_PATH.exists():
        try:
            logo_img = Image.open(LOGO_PATH)
            logo_max_width = 35 * mm
            logo_max_height = FOOTER_HEIGHT - 5 * mm
            
            ratio = min(logo_max_width / logo_img.width, logo_max_height / logo_img.height, 1.0)
            logo_width = logo_img.width * ratio * 0.75
            logo_height = logo_img.height * ratio * 0.75
            
            logo_x = PAGE_WIDTH - MARGIN - logo_width
            
            buffer = BytesIO()
            logo_img = convert_to_rgb(logo_img)
            logo_img.resize((int(logo_img.width * ratio), int(logo_img.height * ratio)), Image.Resampling.LANCZOS).save(buffer, format='JPEG', quality=95)
            buffer.seek(0)
            
            c.drawImage(ImageReader(buffer), logo_x, footer_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
        except Exception as e:
            print(f"  ⚠ 로고 오류: {e}")

def create_filename_guide_pdf():
    """파일명 규칙 가이드 PDF 생성"""
    output_path = Path("파일명_규칙_가이드.pdf")
    print(f"📄 PDF 생성 시작: {output_path.absolute()}")
    
    try:
        # PDF 문서 생성
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # 스타일 설정
        styles = getSampleStyleSheet()
        fonts_available = setup_fonts()
        
        # 한글 폰트가 있으면 사용, 없으면 기본 폰트
        if fonts_available:
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=PRETENDARD_BOLD,
                fontSize=20,
                textColor=black,
                spaceAfter=12,
                alignment=TA_CENTER
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName=PRETENDARD_BOLD,
                fontSize=14,
                textColor=black,
                spaceAfter=8,
                spaceBefore=12
            )
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontName=PRETENDARD_REGULAR,
                fontSize=10,
                textColor=black,
                spaceAfter=6,
                leading=14
            )
            code_style = ParagraphStyle(
                'CustomCode',
                parent=styles['Normal'],
                fontName=PRETENDARD_REGULAR,
                fontSize=9,
                textColor=black,
                backColor=HexColor('#F5F5F5'),
                leftIndent=10,
                rightIndent=10,
                spaceAfter=6,
                leading=12
            )
            example_style = ParagraphStyle(
                'CustomExample',
                parent=styles['Normal'],
                fontName=PRETENDARD_REGULAR,
                fontSize=9,
                textColor=black,
                leftIndent=5,
                spaceAfter=4,
                leading=13
            )
        else:
            title_style = styles['Heading1']
            heading_style = styles['Heading2']
            body_style = styles['Normal']
            code_style = ParagraphStyle(
                'CustomCode',
                parent=styles['Normal'],
                fontSize=9,
                textColor=black,
                backColor=HexColor('#F5F5F5'),
                leftIndent=10,
                rightIndent=10,
                spaceAfter=6
            )
            example_style = ParagraphStyle(
                'CustomExample',
                parent=styles['Normal'],
                fontSize=9,
                textColor=black,
                leftIndent=5,
                spaceAfter=4
            )
        
        # 내용 구성
        story = []
        
        # 제목
        story.append(Paragraph("파일명 규칙 가이드", title_style))
        story.append(Spacer(1, 10*mm))
    
    # 기본 규칙
        story.append(Paragraph("기본 규칙", heading_style))
        story.append(Paragraph(
        "파일명 형식은 다음 두 가지를 지원합니다:",
        body_style
        ))
        story.append(Spacer(1, 3*mm))
    
        story.append(Paragraph("<b>형식 1: \"설치\" 포함 형식 (권장)</b>", body_style))
        story.append(Paragraph(
        "[텍스트]설치[Minor번호][날짜].jpg",
        code_style
        ))
        story.append(Spacer(1, 2*mm))
    
        story.append(Paragraph("<b>형식 2: \"설치\" 없이 \"비콘\" 다음 숫자 형식</b>", body_style))
        story.append(Paragraph(
        "비콘[Minor번호][날짜].jpg",
        code_style
        ))
        story.append(Spacer(1, 5*mm))
    
    # 상세 설명
        story.append(Paragraph("상세 설명", heading_style))
    
        story.append(Paragraph("<b>1. 필수 요소</b>", body_style))
        story.append(Spacer(1, 2*mm))
    
        story.append(Paragraph("<b>형식 1 (설치 포함):</b>", body_style))
        story.append(Paragraph(
        "- \"설치\" 텍스트: Minor 번호 앞에 \"설치\"가 있어야 합니다<br/>"
        "- Minor 번호: \"설치\" 바로 다음에 오는 숫자 (1~4자리 권장)<br/>"
        "- 날짜: 파일명 끝에 날짜 숫자 (6자리 이상)",
        body_style
        ))
        story.append(Spacer(1, 3*mm))
    
        story.append(Paragraph("<b>형식 2 (비콘 직접):</b>", body_style))
        story.append(Paragraph(
        "- \"비콘\" 텍스트: Minor 번호 앞에 \"비콘\"이 있어야 합니다<br/>"
        "- Minor 번호: \"비콘\" 바로 다음에 오는 숫자 (1~4자리 권장, 앞에 0 포함 가능)<br/>"
        "- 날짜: 파일명 끝에 날짜 숫자 (6자리 이상)",
        body_style
        ))
        story.append(Spacer(1, 5*mm))
    
    # 파일명 예시
        story.append(Paragraph("파일명 예시", heading_style))
    
        story.append(Paragraph("<b>형식 1 예시 (설치 포함):</b>", body_style))
        examples1 = [
            "장호원비콘설치10251104130.jpg -> Minor 번호: 10",
            "장호원비콘설치1251104120.jpg -> Minor 번호: 1",
            "장호원비콘설치49251104077.jpg -> Minor 번호: 49",
            "설치100251104130.jpg -> Minor 번호: 100"
        ]
        for ex in examples1:
            story.append(Paragraph(ex, example_style))
        story.append(Spacer(1, 3*mm))
    
        story.append(Paragraph("<b>형식 2 예시 (비콘 직접):</b>", body_style))
        examples2 = [
            "비콘0001251127000.jpg -> Minor 번호: 0001 (1로 처리됨)",
            "비콘10251104130.jpg -> Minor 번호: 10",
            "비콘250251104130.jpg -> Minor 번호: 250"
        ]
        for ex in examples2:
            story.append(Paragraph(ex, example_style))
        story.append(Spacer(1, 3*mm))
        
        story.append(Paragraph("<b>잘못된 예시:</b>", body_style))
        wrong_examples = [
            "1764849216211.jpg -> \"설치\" 또는 \"비콘\"이 없어서 인식 불가",
            "장호원비콘설치12345251104130.jpg -> Minor 번호가 5자리 이상 -> 오류 처리됨",
            "비콘12345251104130.jpg -> Minor 번호가 5자리 이상 -> 오류 처리됨",
            "비콘10.jpg -> 날짜가 없어서 인식 불가"
        ]
        for ex in wrong_examples:
            story.append(Paragraph(ex, example_style))
        story.append(Spacer(1, 5*mm))
    
    # 권장 파일명 형식
        story.append(Paragraph("권장 파일명 형식", heading_style))
    
        story.append(Paragraph("<b>형식 1 (권장):</b>", body_style))
        story.append(Paragraph(
        "[장소명]비콘설치[Minor번호][날짜].jpg",
        code_style
        ))
        story.append(Paragraph("예시:", body_style))
        story.append(Paragraph("- 장호원비콘설치10251104130.jpg", example_style))
        story.append(Paragraph("- 안양비콘설치250251104130.jpg", example_style))
        story.append(Spacer(1, 3*mm))
    
        story.append(Paragraph("<b>형식 2:</b>", body_style))
        story.append(Paragraph(
        "비콘[Minor번호][날짜].jpg",
        code_style
        ))
        story.append(Paragraph("예시:", body_style))
        story.append(Paragraph("- 비콘0001251127000.jpg", example_style))
        story.append(Paragraph("- 비콘10251104130.jpg", example_style))
        story.append(Paragraph("- 비콘250251104130.jpg", example_style))
        story.append(Spacer(1, 5*mm))
    
        # 주의사항
        story.append(Paragraph("주의사항", heading_style))
        notes = [
            "<b>1. Minor 번호는 1~4자리 권장</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;- 5자리 이상이면 오류 처리되어 Unknown 폴더로 이동합니다<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;- 형식 2에서 비콘0001처럼 앞에 0이 있어도 정상 처리됩니다",
            "<b>2. \"설치\" 또는 \"비콘\" 텍스트 필수</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;- 둘 중 하나는 반드시 포함되어야 합니다",
            "<b>3. 날짜는 파일명 끝에 위치</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;- 6자리 이상 숫자를 날짜로 인식합니다<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;- 예: 251104130 (9자리), 51104130 (8자리), 251104 (6자리)",
            "<b>4. 확장자</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;- 지원: .jpg, .jpeg, .png (대소문자 구분 없음)"
        ]
        for note in notes:
            story.append(Paragraph(note, body_style))
        story.append(Spacer(1, 2*mm))
        story.append(Spacer(1, 3*mm))
    
    # 빠른 체크리스트
        story.append(Paragraph("빠른 체크리스트", heading_style))
        checklist = [
            "[ ] \"설치\" 또는 \"비콘\" 텍스트가 포함되어 있나요?",
            "[ ] \"설치\"/\"비콘\" 바로 다음에 Minor 번호(1~4자리)가 있나요?",
            "[ ] 파일명 끝에 날짜 숫자(6자리 이상)가 있나요?",
            "[ ] 확장자가 .jpg, .jpeg, .png 중 하나인가요?"
        ]
        for item in checklist:
            story.append(Paragraph(item, body_style))
        story.append(Spacer(1, 5*mm))
    
    # 예시 템플릿
        story.append(Paragraph("예시 템플릿", heading_style))
    
        story.append(Paragraph("<b>형식 1 (권장):</b>", body_style))
        story.append(Paragraph(
        "[장소명]비콘설치[번호][날짜].jpg",
        code_style
        ))
        story.append(Paragraph("예시:", body_style))
        story.append(Paragraph("- 장호원비콘설치10251104130.jpg", example_style))
        story.append(Paragraph("- 안양비콘설치250251104130.jpg", example_style))
        story.append(Spacer(1, 3*mm))
    
        story.append(Paragraph("<b>형식 2:</b>", body_style))
        story.append(Paragraph(
        "비콘[번호][날짜].jpg",
        code_style
        ))
        story.append(Paragraph("예시:", body_style))
        story.append(Paragraph("- 비콘0001251127000.jpg", example_style))
        story.append(Paragraph("- 비콘10251104130.jpg", example_style))
        story.append(Paragraph("- 비콘250251104130.jpg", example_style))
        
        # PDF 생성 (워터마크 및 푸터 포함)
        def on_first_page(canvas_obj, doc):
            """첫 페이지 헤더/푸터"""
            try:
                draw_watermark(canvas_obj, doc)
            except Exception as e:
                print(f"  ⚠ 첫 페이지 워터마크 오류 (무시): {e}")
            try:
                draw_footer(canvas_obj, doc, 1)
            except Exception as e:
                print(f"  ⚠ 첫 페이지 푸터 오류 (무시): {e}")
        
        def on_later_pages(canvas_obj, doc):
            """나머지 페이지 헤더/푸터"""
            try:
                draw_watermark(canvas_obj, doc)
            except Exception as e:
                print(f"  ⚠ 페이지 워터마크 오류 (무시): {e}")
            try:
                draw_footer(canvas_obj, doc, canvas_obj.getPageNumber())
            except Exception as e:
                print(f"  ⚠ 페이지 푸터 오류 (무시): {e}")
        
        print("📝 PDF 내용 작성 중...")
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"✅ PDF 생성 완료!")
            print(f"   파일 위치: {output_path.absolute()}")
            print(f"   파일 크기: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        else:
            print(f"❌ 오류: PDF 파일이 생성되지 않았습니다.")
            return None
        return output_path
    except Exception as e:
        print(f"❌ PDF 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    create_filename_guide_pdf()

