#!/usr/bin/env python3
"""
output 폴더의 Minor별 이미지들을 PDF로 변환하는 스크립트

각 Minor 폴더의 이미지들을 Beacon 번호로 변환하여 PDF 생성
- 각 Beacon별로 사진들을 배열하여 출력
"""
import os
import re
from pathlib import Path
from datetime import datetime
from PIL import Image
import time

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import mm, inch
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import black, white, grey
    try:
        from reportlab.lib.colors import HexColor
        USE_HEXCOLOR = True
    except ImportError:
        USE_HEXCOLOR = False
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    USE_REPORTLAB = True
except ImportError:
    print("Error: reportlab이 설치되지 않았습니다.")
    print("설치: pip3 install reportlab pillow")
    exit(1)

OUTPUT_DIR = Path("output")
PDF_OUTPUT_DIR = Path("pdf_output")
LOGO_PATH = Path("logo.png")
FONTS_DIR = Path("fonts")

# PDF 제목 설정 (여기서 변경 가능)
FACILITY_NAME = "이천 단월 하수도 사업소"  # 시설명 설정
PDF_TITLE_TEMPLATE = f"{FACILITY_NAME} 설치된 Beacon"  # PDF 제목 템플릿

# Pretendard 폰트 설정
PRETENDARD_REGULAR = "Pretendard-Regular"
PRETENDARD_BOLD = "Pretendard-Bold"
PRETENDARD_FONT_REGULAR_PATH = FONTS_DIR / "Pretendard-Regular.ttf"
PRETENDARD_FONT_BOLD_PATH = FONTS_DIR / "Pretendard-Bold.ttf"

def setup_pretendard_font():
    """
    Pretendard 폰트를 다운로드하고 reportlab에 등록
    """
    import urllib.request
    import zipfile
    import shutil
    
    # 폰트 디렉토리 생성
    FONTS_DIR.mkdir(exist_ok=True)
    
    # 폰트 파일이 이미 있으면 사용
    if PRETENDARD_FONT_REGULAR_PATH.exists() and PRETENDARD_FONT_BOLD_PATH.exists():
        try:
            pdfmetrics.registerFont(TTFont(PRETENDARD_REGULAR, str(PRETENDARD_FONT_REGULAR_PATH)))
            pdfmetrics.registerFont(TTFont(PRETENDARD_BOLD, str(PRETENDARD_FONT_BOLD_PATH)))
            print("✓ Pretendard 폰트 로드 완료")
            return True
        except Exception as e:
            print(f"⚠ 폰트 등록 오류: {e}")
    
    # 폰트 다운로드 시도
    try:
        print("Pretendard 폰트 다운로드 중...")
        font_zip_url = "https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip"
        zip_path = FONTS_DIR / "Pretendard.zip"
        
        urllib.request.urlretrieve(font_zip_url, zip_path)
        
        # ZIP 파일 압축 해제
        extract_dir = FONTS_DIR / "extract_temp"
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # TTF 파일 찾기 (압축 해제된 폴더 구조에 따라 다를 수 있음)
        ttf_files = list(extract_dir.rglob("*.ttf"))
        
        # Regular와 Bold 찾기
        regular_found = False
        bold_found = False
        
        # 정확한 파일명으로 먼저 찾기
        for ttf_file in ttf_files:
            filename_lower = ttf_file.name.lower()
            # Regular 찾기 (정확한 매칭 우선)
            if ttf_file.name == "Pretendard-Regular.ttf" or (filename_lower == "pretendard-regular.ttf"):
                shutil.copy2(ttf_file, PRETENDARD_FONT_REGULAR_PATH)
                regular_found = True
            # Bold 찾기
            elif ttf_file.name == "Pretendard-Bold.ttf" or (filename_lower == "pretendard-bold.ttf"):
                shutil.copy2(ttf_file, PRETENDARD_FONT_BOLD_PATH)
                bold_found = True
        
        # 정확한 매칭이 없으면 부분 매칭으로 찾기
        if not regular_found:
            for ttf_file in ttf_files:
                filename_lower = ttf_file.name.lower()
                if "regular" in filename_lower and "pretendard" in filename_lower:
                    shutil.copy2(ttf_file, PRETENDARD_FONT_REGULAR_PATH)
                    regular_found = True
                    break
        
        if not bold_found:
            for ttf_file in ttf_files:
                filename_lower = ttf_file.name.lower()
                if "bold" in filename_lower and "pretendard" in filename_lower:
                    shutil.copy2(ttf_file, PRETENDARD_FONT_BOLD_PATH)
                    bold_found = True
                    break
        
        # 임시 폴더 삭제
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        
        # ZIP 파일 삭제
        if zip_path.exists():
            zip_path.unlink()
        
        # 폰트 등록
        if PRETENDARD_FONT_REGULAR_PATH.exists():
            pdfmetrics.registerFont(TTFont(PRETENDARD_REGULAR, str(PRETENDARD_FONT_REGULAR_PATH)))
        if PRETENDARD_FONT_BOLD_PATH.exists():
            pdfmetrics.registerFont(TTFont(PRETENDARD_BOLD, str(PRETENDARD_FONT_BOLD_PATH)))
        
        print("✓ Pretendard 폰트 다운로드 및 등록 완료")
        return True
        
    except Exception as e:
        print(f"⚠ Pretendard 폰트 다운로드 실패: {e}")
        print("  기본 폰트(Helvetica)를 사용합니다.")
        return False

# PDF 기본 설정
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 20 * mm
HEADER_HEIGHT = 25 * mm
FOOTER_HEIGHT = 15 * mm
FOOTER_BOTTOM_MARGIN = 15 * mm

# 헤더 위치
HEADER_TEXT_Y = PAGE_HEIGHT - MARGIN - 5 * mm
HEADER_LINE_Y = HEADER_TEXT_Y - 3 * mm
CONTENT_START_Y = HEADER_LINE_Y - 8 * mm

# 본문 영역 계산
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)
CONTENT_HEIGHT = CONTENT_START_Y - FOOTER_HEIGHT - FOOTER_BOTTOM_MARGIN

# 레이아웃 모드별 설정
def get_layout_settings(high_density=False):
    """
    레이아웃 모드에 따른 설정값 반환
    
    Args:
        high_density: True면 고밀도 모드 (페이지당 ~16개), False면 일반 모드 (페이지당 ~8개)
    
    Returns:
        dict: 레이아웃 설정값
    """
    if high_density:
        # 고밀도 모드: 간격과 크기를 줄여서 더 많이 배치
        return {
            'BEACON_MARGIN': 3 * mm,
            'IMAGE_MARGIN': 2 * mm,
            'BEACON_COLUMN_MARGIN': 5 * mm,
            'BEACON_BOX_WIDTH': (CONTENT_WIDTH - 5 * mm) / 2,
            'BEACON_TITLE_HEIGHT': 3 * mm,
            'BOX_PADDING': 1.5 * mm,
            'MAX_IMAGE_HEIGHT': 25 * mm,
            'MAX_COLUMN_SLOTS_PER_PAGE': 20,
            'MIN_Y_MARGIN': 6 * mm
        }
    else:
        # 일반 모드: 기존 설정 유지
        return {
            'BEACON_MARGIN': 6 * mm,
            'IMAGE_MARGIN': 4 * mm,
            'BEACON_COLUMN_MARGIN': 8 * mm,
            'BEACON_BOX_WIDTH': (CONTENT_WIDTH - 8 * mm) / 2,
            'BEACON_TITLE_HEIGHT': 4 * mm,
            'BOX_PADDING': 2 * mm,
            'MAX_IMAGE_HEIGHT': 45 * mm,
            'MAX_COLUMN_SLOTS_PER_PAGE': 10,
            'MIN_Y_MARGIN': 8 * mm
        }

# 기본 설정값 (일반 모드)
LAYOUT = get_layout_settings(high_density=False)
BEACON_MARGIN = LAYOUT['BEACON_MARGIN']
IMAGE_MARGIN = LAYOUT['IMAGE_MARGIN']
BEACON_COLUMN_MARGIN = LAYOUT['BEACON_COLUMN_MARGIN']
BEACON_BOX_WIDTH = LAYOUT['BEACON_BOX_WIDTH']
BEACON_TITLE_HEIGHT = LAYOUT['BEACON_TITLE_HEIGHT']
BOX_PADDING = LAYOUT['BOX_PADDING']
MAX_IMAGE_HEIGHT = LAYOUT['MAX_IMAGE_HEIGHT']

def get_beacon_number(minor_folder_name):
    """
    Minor 폴더명에서 Beacon 번호 추출
    예: Minor_0019 -> 19
    """
    match = re.search(r'Minor_(\d+)', minor_folder_name)
    if match:
        return int(match[1])
    return None

def convert_to_rgb(img):
    """
    이미지를 RGB 모드로 안전하게 변환
    """
    if img.mode == 'RGB':
        return img
    elif img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        return background
    elif img.mode == 'P':
        return img.convert('RGB')
    elif img.mode == 'L':
        return img.convert('RGB')
    elif img.mode == 'CMYK':
        return img.convert('RGB')
    else:
        try:
            return img.convert('RGB')
        except:
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            return background

def resize_image_for_pdf(image_path, target_width_pt, target_height_pt):
    """
    이미지를 PDF에 맞게 리사이즈 (비율 유지, 고해상도 유지)
    """
    try:
        img = Image.open(image_path)
        img = convert_to_rgb(img)
        
        orig_width = img.width
        orig_height = img.height
        
        # 300 DPI 기준으로 변환
        target_width_px = int(target_width_pt * 300 / 72)
        target_height_px = int(target_height_pt * 300 / 72)
        
        # 비율 계산
        width_ratio = target_width_px / orig_width
        height_ratio = target_height_px / orig_height
        ratio = min(width_ratio, height_ratio)
        
        # 새 크기 계산
        new_width = int(orig_width * ratio)
        new_height = int(orig_height * ratio)
        
        # 고품질 리사이즈
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 실제 포인트 크기 반환
        actual_width_pt = new_width * 72 / 300
        actual_height_pt = new_height * 72 / 300
        
        return resized, actual_width_pt, actual_height_pt
    except Exception as e:
        print(f"  ⚠ 이미지 처리 오류 ({image_path.name}): {e}")
        return None, 0, 0

def draw_header(canvas_obj):
    """
    페이지 상단 헤더에 사업소 이름과 JRIndustry 표시
    """
    header_text_y = HEADER_TEXT_Y
    
    # 사업소 이름 (좌측, Bold)
    try:
        canvas_obj.setFont(PRETENDARD_BOLD, 14)
        font_name_bold = PRETENDARD_BOLD
    except:
        canvas_obj.setFont("Helvetica-Bold", 14)
        font_name_bold = "Helvetica-Bold"
    canvas_obj.setFillColor(black)
    canvas_obj.drawString(MARGIN, header_text_y, FACILITY_NAME)
    
    # JRIndustry 텍스트 (우측 상단)
    jr_text = "JRIndustry"
    try:
        canvas_obj.setFont(PRETENDARD_BOLD, 11)
        font_name = PRETENDARD_BOLD
    except:
        canvas_obj.setFont("Helvetica-Bold", 11)
        font_name = "Helvetica-Bold"
    
    from reportlab.pdfbase.pdfmetrics import stringWidth
    text_width = stringWidth(jr_text, font_name, 11)
    canvas_obj.drawString(PAGE_WIDTH - MARGIN - text_width, header_text_y, jr_text)
    
    # 구분선
    canvas_obj.setStrokeColor(black)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(MARGIN, HEADER_LINE_Y, PAGE_WIDTH - MARGIN, HEADER_LINE_Y)

def draw_watermark(canvas_obj):
    """
    페이지 전체에 로고 워터마크를 사선 패턴으로 배치
    """
    if not LOGO_PATH.exists():
        return
    
    try:
        from PIL import Image as PILImage
        import math
        
        # 로고 이미지 로드
        logo_img = PILImage.open(LOGO_PATH)
        
        # 로고를 회색조로 변환
        logo_img = logo_img.convert('L')  # 흑백 변환
        logo_img = logo_img.convert('RGB')  # RGB로 다시 변환 (PDF용)
        
        # 워터마크 크기 설정 (더 작게)
        watermark_width = 35 * mm
        watermark_height = watermark_width * logo_img.height / logo_img.width
        
        # 사선 패턴 설정 (더 조밀하게)
        rotation_angle = 45  # 45도 회전
        spacing_x = 55 * mm  # 가로 간격 (더 조밀하게)
        spacing_y = 35 * mm   # 세로 간격 (더 조밀하게)
        
        # 45도 회전된 워터마크의 대각선 길이 계산
        # 회전된 직사각형의 바운딩 박스 크기
        diagonal = math.sqrt(watermark_width**2 + watermark_height**2)
        # 회전 중심에서 가장자리까지의 거리 (대각선의 절반)
        half_diagonal = diagonal / 2
        
        # 상태 저장
        canvas_obj.saveState()
        
        # 불투명도 설정 (0.1 = 10% 불투명, 매우 연하게)
        canvas_obj.setFillAlpha(0.08)
        canvas_obj.setStrokeAlpha(0.08)
        
        # 페이지 경계에서 자연스럽게 잘리도록 워터마크 배치
        # 회전된 워터마크가 페이지 경계에서 자연스럽게 잘리도록 시작 위치 조정
        # 회전 중심이 페이지 내부에 있으면, 회전된 워터마크의 일부는 페이지 밖으로 나감
        # 왼쪽 경계(x=0)에서 워터마크가 자연스럽게 잘리도록:
        # 회전 중심이 half_diagonal 이상 떨어져 있어야 회전된 워터마크의 왼쪽 끝이 페이지 밖으로 나감
        # x는 워터마크의 왼쪽 상단 모서리, 회전 중심은 x + width/2
        # 회전된 워터마크의 왼쪽 끝 = 회전 중심 - half_diagonal
        # 페이지 경계에서 자연스럽게 잘리려면: 회전 중심 - half_diagonal < 0
        # 즉: (x + width/2) - half_diagonal < 0
        # x < half_diagonal - width/2
        # 하지만 너무 왼쪽에서 시작하면 안 보이므로, 약간의 여유를 둠
        start_x = half_diagonal - watermark_width / 2 - spacing_x  # 왼쪽 경계에서 자연스럽게 잘리도록
        start_y = -100 * mm
        # 오른쪽 경계에서도 자연스럽게 잘리도록
        # 회전 중심이 PAGE_WIDTH - half_diagonal 이하에 있어야 회전된 워터마크의 오른쪽 끝이 페이지 밖으로 나감
        # x + width/2 <= PAGE_WIDTH - half_diagonal
        # x <= PAGE_WIDTH - half_diagonal - width/2
        end_x = PAGE_WIDTH - half_diagonal + watermark_width / 2 + spacing_x  # 오른쪽 경계에서 자연스럽게 잘리도록
        end_y = PAGE_HEIGHT + 100 * mm
        
        # 임시 이미지 버퍼 생성
        from io import BytesIO
        
        y = start_y
        row_idx = 0
        while y < end_y:
            # 사선 효과를 위해 행마다 x 시작점을 교차 조정 (지그재그 패턴)
            if row_idx % 2 == 0:
                x = start_x
            else:
                x = start_x + (spacing_x / 2)
            
            while x < end_x:
                # 각 워터마크 위치에서 회전하여 그리기
                canvas_obj.saveState()
                
                # 회전 중심을 워터마크 중앙으로
                center_x = x + watermark_width / 2
                center_y = y + watermark_height / 2
                
                # 이동 -> 회전 -> 이미지 그리기
                canvas_obj.translate(center_x, center_y)
                canvas_obj.rotate(rotation_angle)
                
                # 이미지를 버퍼에 저장
                img_buffer = BytesIO()
                logo_img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                # 회전된 상태에서 이미지 그리기 (중앙 기준)
                canvas_obj.drawImage(
                    ImageReader(img_buffer),
                    -watermark_width / 2,
                    -watermark_height / 2,
                    width=watermark_width,
                    height=watermark_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
                
                canvas_obj.restoreState()
                x += spacing_x
            
            y += spacing_y
            row_idx += 1
        
        # 상태 복원
        canvas_obj.restoreState()
        
    except Exception as e:
        print(f"  ⚠ 워터마크 처리 오류: {e}")


def draw_footer(canvas_obj, page_number):
    """
    페이지 하단 푸터: 좌측에 페이지 번호, 우측에 로고
    """
    footer_y = FOOTER_BOTTOM_MARGIN  # 푸터를 더 아래로 (3mm 제거)
    
    # 페이지 번호 표시 (좌측 하단)
    try:
        canvas_obj.setFont(PRETENDARD_REGULAR, 8)
    except:
        canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(black)
    page_text = f"Page {page_number}"
    canvas_obj.drawString(MARGIN, footer_y, page_text)
    
    # 로고 이미지 표시 (우측 하단)
    if LOGO_PATH.exists():
        try:
            logo_img = Image.open(LOGO_PATH)
            logo_max_width = 35 * mm
            logo_max_height = FOOTER_HEIGHT - 5 * mm
            
            width_ratio = logo_max_width / logo_img.width
            height_ratio = logo_max_height / logo_img.height
            ratio = min(width_ratio, height_ratio, 1.0)
            
            logo_width_pt = logo_img.width * ratio * 0.75
            logo_height_pt = logo_img.height * ratio * 0.75
            
            logo_x = PAGE_WIDTH - MARGIN - logo_width_pt
            logo_y = footer_y
            
            from io import BytesIO
            logo_buffer = BytesIO()
            logo_img = convert_to_rgb(logo_img)
            resized_logo = logo_img.resize((int(logo_img.width * ratio), int(logo_img.height * ratio)), Image.Resampling.LANCZOS)
            resized_logo.save(logo_buffer, format='JPEG', quality=95)
            logo_buffer.seek(0)
            
            canvas_obj.drawImage(ImageReader(logo_buffer), logo_x, logo_y, 
                               width=logo_width_pt, height=logo_height_pt, preserveAspectRatio=True)
        except Exception as e:
            print(f"  ⚠ 로고 이미지 처리 오류: {e}")

def draw_beacon_box(canvas_obj, beacon_number, image_files, box_x, box_y_top, box_width, is_full_width=False, fixed_height=None):
    """
    비콘 박스 그리기 (단순화된 버전)
    
    Args:
        canvas_obj: PDF 캔버스 객체
        beacon_number: Beacon 번호
        image_files: 이미지 파일 리스트
        box_x: 박스 시작 X 위치
        box_y_top: 박스 상단 Y 위치 (reportlab 좌표계: 큰 값이 위쪽)
        box_width: 박스 너비
        is_full_width: 전체 너비 사용 여부 (4개 이미지일 때 True)
        fixed_height: 고정 높이 (같은 행의 박스 높이 통일용, None이면 자동 계산)
    
    Returns:
        box_height: 박스 높이
    """
    num_images = len(image_files)
    
    # 색상 정의
    if USE_HEXCOLOR:
        light_grey = HexColor('#E0E0E0')
    else:
        from reportlab.lib.colors import Color
        light_grey = Color(0.88, 0.88, 0.88)
    
    # 이미지 영역 크기 계산
    available_width = box_width - (BOX_PADDING * 2)
    available_height = CONTENT_HEIGHT - BEACON_TITLE_HEIGHT - BOX_PADDING * 2
    
    # 이미지 배치 결정
    if num_images == 0:
        # 이미지 없음
        image_layout = []
        image_area_height = 15 * mm
    elif num_images == 1:
        # 1개: 가로로 배치
        image_layout = [(1, 1)]  # (열 수, 행 수)
        image_area_height = min(available_height, MAX_IMAGE_HEIGHT)
    elif num_images == 2:
        # 2개: 가로로 배치
        image_layout = [(2, 1)]
        image_area_height = min(available_height, MAX_IMAGE_HEIGHT)
    elif num_images == 3:
        # 3개: 가로로 배치 (크기 줄어듦)
        image_layout = [(3, 1)]
        image_area_height = min(available_height, MAX_IMAGE_HEIGHT)
    elif num_images == 4:
        # 4개: 가로로 한 줄 4개 배치 (전체 너비 사용)
        image_layout = [(4, 1)]
        image_area_height = min(available_height, MAX_IMAGE_HEIGHT)
    else:
        # 5개 이상: 2열로 배치
        rows = (num_images + 1) // 2
        image_layout = [(2, rows)]
        image_area_height = min(available_height, MAX_IMAGE_HEIGHT)
    
    # 이미지 크기 계산
    images_per_row = image_layout[0][0]
    num_rows = image_layout[0][1]
    
    if images_per_row > 0:
        image_cell_width = (available_width - (IMAGE_MARGIN * (images_per_row - 1))) / images_per_row
        if num_rows > 1:
            image_cell_height = (image_area_height - (IMAGE_MARGIN * (num_rows - 1))) / num_rows
        else:
            image_cell_height = image_area_height
    else:
        image_cell_width = available_width
        image_cell_height = image_area_height
    
    # 박스 높이 계산
    if fixed_height is not None:
        # 고정 높이 사용 (같은 행의 박스 높이 통일)
        box_height = fixed_height
        image_area_height = box_height - BEACON_TITLE_HEIGHT - (BOX_PADDING * 2)
        # 이미지 크기 재계산
        if images_per_row > 0:
            image_cell_width = (available_width - (IMAGE_MARGIN * (images_per_row - 1))) / images_per_row
            if num_rows > 1:
                image_cell_height = (image_area_height - (IMAGE_MARGIN * (num_rows - 1))) / num_rows
            else:
                image_cell_height = image_area_height
        else:
            image_cell_width = available_width
            image_cell_height = image_area_height
    else:
        box_height = BEACON_TITLE_HEIGHT + image_area_height + (BOX_PADDING * 2)
    
    # 박스 하단 Y 위치 계산 (reportlab: y는 하단 좌표)
    box_y_bottom = box_y_top - box_height
    
    # 배경색 정의 (아주 옅은 회색)
    if USE_HEXCOLOR:
        bg_grey = HexColor('#F5F5F5')  # 아주 옅은 회색
    else:
        from reportlab.lib.colors import Color
        bg_grey = Color(0.96, 0.96, 0.96)  # #F5F5F5 = RGB(245, 245, 245) / 255
    
    # border-radius 효과를 위한 작은 값
    corner_radius = 1.5 * mm  # 아주 작은 둥근 모서리
    
    # 박스 배경 그리기 (배경색 채우기)
    canvas_obj.setFillColor(bg_grey)
    canvas_obj.setStrokeColor(bg_grey)
    
    # border-radius 효과를 위해 모서리에 작은 원을 그려서 둥근 효과 구현
    # 상단 좌측 모서리
    canvas_obj.circle(box_x + corner_radius, box_y_top - corner_radius, corner_radius, fill=1, stroke=0)
    # 상단 우측 모서리
    canvas_obj.circle(box_x + box_width - corner_radius, box_y_top - corner_radius, corner_radius, fill=1, stroke=0)
    # 하단 좌측 모서리
    canvas_obj.circle(box_x + corner_radius, box_y_bottom + corner_radius, corner_radius, fill=1, stroke=0)
    # 하단 우측 모서리
    canvas_obj.circle(box_x + box_width - corner_radius, box_y_bottom + corner_radius, corner_radius, fill=1, stroke=0)
    
    # 중앙 사각형 배경 (모서리 원 사이의 공간 채우기)
    canvas_obj.rect(box_x, box_y_bottom + corner_radius, box_width, box_height - (corner_radius * 2), fill=1, stroke=0)
    canvas_obj.rect(box_x + corner_radius, box_y_bottom, box_width - (corner_radius * 2), box_height, fill=1, stroke=0)
    
    # 박스 테두리 그리기 (rect의 y는 하단 좌표)
    canvas_obj.setStrokeColor(light_grey)
    canvas_obj.setLineWidth(0.8)
    canvas_obj.rect(box_x, box_y_bottom, box_width, box_height, fill=0, stroke=1)
    
    # 비콘 제목 (박스 상단 내부, 간격 축소)
    beacon_title = f"Beacon {beacon_number}"
    # Pretendard 폰트 사용 (크기 축소: 9 -> 7)
    try:
        canvas_obj.setFont(PRETENDARD_BOLD, 7)
        font_name = PRETENDARD_BOLD
    except:
        # Pretendard 폰트가 없으면 기본 폰트 사용
        canvas_obj.setFont("Helvetica-Bold", 7)
        font_name = "Helvetica-Bold"
    canvas_obj.setFillColor(black)
    title_y = box_y_top - BOX_PADDING - 2 * mm  # 간격 축소 (3 -> 2)
    canvas_obj.drawString(box_x + BOX_PADDING, title_y, beacon_title)
    
    # 이미지 영역 시작 위치 (타이틀 아래, 간격 축소)
    image_area_top_y = title_y - 2 * mm  # 타이틀 아래 간격
    
    # 이미지 그리기
    if num_images == 0:
        # 이미지 없음 메시지
        try:
            canvas_obj.setFont(PRETENDARD_REGULAR, 10)
        except:
            canvas_obj.setFont("Helvetica", 10)
        canvas_obj.setFillColor(black)
        text_x = box_x + box_width / 2
        text_y = image_area_top_y - image_area_height / 2
        canvas_obj.drawCentredString(text_x, text_y, "이미지 없음")
    else:
        for idx, image_path in enumerate(image_files):
            row = idx // images_per_row
            col = idx % images_per_row
            
            # 이미지 리사이즈
            resized_img, img_width_pt, img_height_pt = resize_image_for_pdf(
                image_path, image_cell_width, image_cell_height
            )
            
            if resized_img is None:
                # 이미지 로드 실패
                try:
                    canvas_obj.setFont(PRETENDARD_REGULAR, 8)
                except:
                    canvas_obj.setFont("Helvetica", 8)
                canvas_obj.setFillColor(black)
                error_x = box_x + BOX_PADDING + col * (image_cell_width + IMAGE_MARGIN) + image_cell_width / 2
                row_start_y = image_area_top_y - row * (image_cell_height + IMAGE_MARGIN) - image_cell_height
                error_y = row_start_y + image_cell_height / 2
                canvas_obj.drawCentredString(error_x, error_y, f"이미지\n로드 실패")
                continue
            
            # 이미지 위치 계산 (reportlab: y는 하단 좌표)
            img_x = box_x + BOX_PADDING + col * (image_cell_width + IMAGE_MARGIN) + (image_cell_width - img_width_pt) / 2
            # 각 행의 하단 Y 위치 계산
            row_bottom_y = image_area_top_y - row * (image_cell_height + IMAGE_MARGIN) - image_cell_height
            img_y = row_bottom_y + (image_cell_height - img_height_pt) / 2
            
            # 이미지 그리기
            from io import BytesIO
            img_buffer = BytesIO()
            if resized_img.mode != 'RGB':
                resized_img = convert_to_rgb(resized_img)
            try:
                resized_img.save(img_buffer, format='JPEG', quality=98, optimize=True)
                img_buffer.seek(0)
                canvas_obj.drawImage(ImageReader(img_buffer), img_x, img_y, 
                           width=img_width_pt, height=img_height_pt, preserveAspectRatio=True)
            except Exception as e:
                # 이미지 저장 실패
                try:
                    canvas_obj.setFont(PRETENDARD_REGULAR, 8)
                except:
                    canvas_obj.setFont("Helvetica", 8)
                canvas_obj.setFillColor(black)
                error_x = box_x + BOX_PADDING + col * (image_cell_width + IMAGE_MARGIN) + image_cell_width / 2
                error_y = row_bottom_y + image_cell_height / 2
                canvas_obj.drawCentredString(error_x, error_y, f"이미지\n처리 오류")
    
    return box_height

def calculate_total_pages(beacon_data):
    """
    비콘 데이터를 기반으로 총 페이지 수를 계산 (실제로 그리지 않고 계산만)
    """
    current_page = 1
    current_col = 0
    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
    row_heights = []
    column_slots_used = 0
    MAX_COLUMN_SLOTS_PER_PAGE = LAYOUT['MAX_COLUMN_SLOTS_PER_PAGE']
    MIN_Y_MARGIN = LAYOUT['MIN_Y_MARGIN']
    
    for idx, beacon_info in enumerate(beacon_data, 1):
        num_images = len(beacon_info['images'])
        is_full_width = (num_images == 4)
        
        # 4개 이미지 비콘이 오기 전에 왼쪽 열에 비콘이 남아있는지 확인
        if is_full_width and current_col == 1 and len(row_heights) > 0:
            column_slots_used += 1
            left_box_height = row_heights[0]
            column_y_positions[0] = column_y_positions[0] - left_box_height - BEACON_MARGIN
            column_y_positions[1] = min(column_y_positions[0], column_y_positions[1])
            row_heights = []
            current_col = 0
        
        if is_full_width:
            # 전체 너비 사용: 2열 공간 차지
            if column_slots_used + 2 > MAX_COLUMN_SLOTS_PER_PAGE:
                current_page += 1
                column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                current_col = 0
                row_heights = []
                column_slots_used = 0
            
            # 박스 높이 추정 (실제 계산과 유사하게)
            box_height = MAX_IMAGE_HEIGHT + BEACON_TITLE_HEIGHT + BOX_PADDING * 2 + 2 * mm
            next_y_top = min(column_y_positions) - box_height - BEACON_MARGIN
            min_y_position = FOOTER_HEIGHT + FOOTER_BOTTOM_MARGIN + MIN_Y_MARGIN
            
            if next_y_top < min_y_position:
                current_page += 1
                column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                current_col = 0
                row_heights = []
                column_slots_used = 0
            elif column_slots_used >= MAX_COLUMN_SLOTS_PER_PAGE:
                current_page += 1
                column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                current_col = 0
                row_heights = []
                column_slots_used = 0
            
            column_slots_used += 2
            column_y_positions[0] = next_y_top
            column_y_positions[1] = next_y_top
            current_col = 0
            row_heights = []
        else:
            # 일반 비콘 박스 (2열 레이아웃)
            box_y_top = column_y_positions[current_col]
            min_y_position = FOOTER_HEIGHT + FOOTER_BOTTOM_MARGIN + MIN_Y_MARGIN
            
            if current_col == 0:
                if box_y_top < min_y_position:
                    current_page += 1
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    column_slots_used = 0
                    box_y_top = column_y_positions[current_col]
                elif column_slots_used + 2 > MAX_COLUMN_SLOTS_PER_PAGE:
                    current_page += 1
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    column_slots_used = 0
                    box_y_top = column_y_positions[current_col]
            
            # 박스 높이 추정
            box_height = MAX_IMAGE_HEIGHT + BEACON_TITLE_HEIGHT + BOX_PADDING * 2 + 2 * mm
            
            if current_col == 0:
                row_heights = [box_height]
                current_col = 1
            else:
                row_heights.append(box_height)
                max_row_height = max(row_heights)
                box_height = max_row_height
                box_y_top = min(column_y_positions[0], column_y_positions[1])
                column_slots_used += 2
            
            next_y_top = box_y_top - box_height - BEACON_MARGIN
            min_y_position = FOOTER_HEIGHT + FOOTER_BOTTOM_MARGIN + MIN_Y_MARGIN
            
            if next_y_top < min_y_position:
                if current_col == 1:
                    current_page += 1
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    column_slots_used = 0
                else:
                    column_slots_used += 1
                    current_page += 1
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    column_slots_used = 0
            elif column_slots_used >= MAX_COLUMN_SLOTS_PER_PAGE:
                if current_col == 1:
                    current_page += 1
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    column_slots_used = 0
                else:
                    column_slots_used += 1
                    current_page += 1
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    column_slots_used = 0
            else:
                if current_col == 1:
                    column_y_positions[0] = next_y_top
                    column_y_positions[1] = next_y_top
                    current_col = 0
                    row_heights = []
                else:
                    current_col = 1
    
    # 루프가 끝날 때 왼쪽 열에 비콘이 남아있는지 확인
    if len(row_heights) > 0 and current_col == 1:
        column_slots_used += 1
    
    return current_page

def create_all_pdfs():
    """
    모든 Minor 폴더의 이미지들을 하나의 PDF로 통합 생성
    """
    global BEACON_MARGIN, IMAGE_MARGIN, BEACON_COLUMN_MARGIN, BEACON_BOX_WIDTH
    global BEACON_TITLE_HEIGHT, BOX_PADDING, MAX_IMAGE_HEIGHT, LAYOUT
    
    print("="*70)
    print("PDF 생성 시작 (통합 PDF)")
    print("="*70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 레이아웃 모드 선택
    print("📊 레이아웃 모드를 선택하세요:")
    print("  1. 일반 모드 (페이지당 약 8개 비콘, 큰 이미지)")
    print("  2. 고밀도 모드 (페이지당 약 16개 비콘, 작은 이미지)")
    
    while True:
        try:
            choice = input("\n선택 (1 또는 2, 기본값 1): ").strip()
            if choice == '' or choice == '1':
                high_density = False
                mode_name = "일반 모드"
                break
            elif choice == '2':
                high_density = True
                mode_name = "고밀도 모드"
                break
            else:
                print("❌ 1 또는 2를 입력해주세요.")
        except EOFError:
            # 파이프 입력 등에서 기본값 사용
            high_density = False
            mode_name = "일반 모드"
            break
    
    # 선택한 모드에 따라 레이아웃 설정 업데이트
    LAYOUT = get_layout_settings(high_density=high_density)
    BEACON_MARGIN = LAYOUT['BEACON_MARGIN']
    IMAGE_MARGIN = LAYOUT['IMAGE_MARGIN']
    BEACON_COLUMN_MARGIN = LAYOUT['BEACON_COLUMN_MARGIN']
    BEACON_BOX_WIDTH = LAYOUT['BEACON_BOX_WIDTH']
    BEACON_TITLE_HEIGHT = LAYOUT['BEACON_TITLE_HEIGHT']
    BOX_PADDING = LAYOUT['BOX_PADDING']
    MAX_IMAGE_HEIGHT = LAYOUT['MAX_IMAGE_HEIGHT']
    
    print(f"\n✓ {mode_name} 선택됨")
    print(f"  - 비콘 간 간격: {int(BEACON_MARGIN / mm)}mm")
    print(f"  - 최대 이미지 높이: {int(MAX_IMAGE_HEIGHT / mm)}mm")
    print(f"  - 페이지당 최대 슬롯: {LAYOUT['MAX_COLUMN_SLOTS_PER_PAGE']}")
    print()
    
    # Pretendard 폰트 설정
    setup_pretendard_font()
    print()
    
    start_time = time.time()
    
    # 출력 폴더 생성
    PDF_OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Minor 폴더 목록 가져오기
    minor_folders = sorted([
        f for f in OUTPUT_DIR.iterdir() 
        if f.is_dir() and f.name.startswith('Minor_')
    ])
    
    if not minor_folders:
        print("❌ Minor 폴더를 찾을 수 없습니다.")
        return
    
    print(f"📁 총 {len(minor_folders)}개 Beacon을 하나의 PDF로 통합합니다...\n")
    
    # 통합 PDF 파일명 생성
    pdf_filename = f"{FACILITY_NAME.replace(' ', '_')}_Beacon_설치현황.pdf"
    pdf_path = PDF_OUTPUT_DIR / pdf_filename
    
    # PDF 생성
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    
    success_count = 0
    failed_count = 0
    total_images = 0
    
    # Beacon 데이터 수집
    beacon_data = []
    for idx, minor_folder in enumerate(minor_folders, 1):
        beacon_number = get_beacon_number(minor_folder.name)
        if beacon_number is None:
            print(f"  ⚠ [{idx}/{len(minor_folders)}] {minor_folder.name}: Beacon 번호 추출 실패")
            failed_count += 1
            continue
        
        # 이미지 파일 목록 가져오기
        image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        all_image_files = [
            f for f in minor_folder.iterdir() 
            if f.is_file() and f.suffix in image_extensions
        ]
        
        # 정렬: 영어/숫자 파일 먼저, 한글 파일 나중에
        def sort_key(file_path):
            filename = file_path.name
            is_english_numeric = all(ord(c) < 128 for c in filename.replace('.', '').replace('_', '').replace('-', ''))
            return (0 if is_english_numeric else 1, filename)
        
        image_files = sorted(all_image_files, key=sort_key)
        
        if not image_files:
            print(f"  ⚠ Beacon {beacon_number}: 이미지 파일이 없습니다.")
            failed_count += 1
            continue
        
        beacon_data.append({
            'number': beacon_number,
            'images': image_files
        })
        total_images += len(image_files)
    
    # 페이지당 비콘 배치
    current_page = 1
    max_page = 1  # 실제 생성된 최대 페이지 번호
    current_y = CONTENT_START_Y  # 현재 Y 위치 (상단부터 시작)
    current_col = 0  # 현재 열 (0: 왼쪽, 1: 오른쪽)
    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]  # 각 열의 현재 Y 위치
    row_heights = []  # 같은 행의 박스 높이 저장 (왼쪽, 오른쪽)
    beacons_on_page = 0  # 현재 페이지의 비콘 수
    column_slots_used = 0  # 사용된 열 공간
    MAX_COLUMN_SLOTS_PER_PAGE = LAYOUT['MAX_COLUMN_SLOTS_PER_PAGE']
    MIN_Y_MARGIN = LAYOUT['MIN_Y_MARGIN']
    last_beacon_counted = False  # 마지막 비콘이 이미 카운트되었는지 추적
    left_beacon_idx = None  # 왼쪽 열 비콘의 beacon_data 인덱스
    
    # 첫 번째 페이지 헤더와 푸터 그리기 (올바른 페이지 수 사용)
    draw_header(c)
    draw_watermark(c)
    draw_footer(c, current_page)
    
    for idx, beacon_info in enumerate(beacon_data, 1):
        beacon_number = beacon_info['number']
        image_files = beacon_info['images']
        num_images = len(image_files)
        
        # 디버깅: 현재 상태 출력
        # print(f"[DEBUG] Beacon {beacon_number}: idx={idx}/{len(beacon_data)}, current_col={current_col}, row_heights={len(row_heights)}, beacons_on_page={beacons_on_page}, column_slots_used={column_slots_used}")
        
        # 4개 이미지는 전체 너비 사용
        is_full_width = (num_images == 4)
        
        # 4개 이미지 비콘이 오기 전에 왼쪽 열에 비콘이 남아있는지 확인
        # current_col == 1이고 row_heights가 있으면 왼쪽 열에 비콘이 있는 상태
        if is_full_width and current_col == 1 and len(row_heights) > 0:
            # 왼쪽 열에 비콘이 있는 상태에서 4개 이미지 비콘이 오면
            # 왼쪽 열 비콘을 카운트하고 행 완료 처리
            beacons_on_page += 1
            column_slots_used += 1
            success_count += 1  # 누락된 카운트 추가
            # 왼쪽 열 비콘의 높이로 위치 업데이트
            left_box_height = row_heights[0]
            column_y_positions[0] = column_y_positions[0] - left_box_height - BEACON_MARGIN
            column_y_positions[1] = min(column_y_positions[0], column_y_positions[1])
            row_heights = []
            current_col = 0
            # 왼쪽 열 비콘 번호 출력 (left_beacon_idx가 None이 아닌 경우에만)
            if left_beacon_idx is not None and left_beacon_idx < len(beacon_data):
                print(f"  [왼쪽 열 비콘 카운트 완료] Beacon {beacon_data[left_beacon_idx]['number']}")
            else:
                print(f"  [왼쪽 열 비콘 카운트 완료] (인덱스 정보 없음)")
            left_beacon_idx = None  # 카운트 후 초기화
        
        if is_full_width:
            # 전체 너비 사용: 2열 공간 차지
            box_x = MARGIN
            box_width = CONTENT_WIDTH
            box_y_top = min(column_y_positions)  # 두 열 중 더 위쪽 위치 사용
            
            # 박스 높이 추정 (실제 그리기 전에 공간 확인용)
            estimated_box_height = MAX_IMAGE_HEIGHT + BEACON_TITLE_HEIGHT + BOX_PADDING * 2
            next_y_estimate = box_y_top - estimated_box_height - BEACON_MARGIN
            min_y_position = FOOTER_HEIGHT + FOOTER_BOTTOM_MARGIN + MIN_Y_MARGIN
            
            # Y 위치 또는 열 공간이 부족한지 확인
            need_new_page = False
            if next_y_estimate < min_y_position:
                # Y 위치가 부족하면 페이지 넘김
                need_new_page = True
            elif column_slots_used + 2 > MAX_COLUMN_SLOTS_PER_PAGE:
                # 열 공간이 부족하면 페이지 넘김
                need_new_page = True
            
            if need_new_page:
                current_page += 1
                max_page = max(max_page, current_page)
                c.showPage()
                draw_header(c)
                draw_watermark(c)
                draw_footer(c, current_page)
                column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                current_col = 0
                row_heights = []
                beacons_on_page = 0
                column_slots_used = 0
                left_beacon_idx = None
                # 새 페이지에서 다시 위치 계산
                box_x = MARGIN
                box_width = CONTENT_WIDTH
                box_y_top = min(column_y_positions)
            
            # 박스 그리기
            print(f"  [{idx}/{len(beacon_data)}] Beacon {beacon_number}: {num_images}개 이미지 (전체 너비)...", end="")
            box_height = draw_beacon_box(c, beacon_number, image_files, box_x, box_y_top, box_width, is_full_width=True)
            beacons_on_page += 1  # 비콘 수 증가
            column_slots_used += 2  # 2열 공간 사용
            
            # 다음 위치로 이동 (전체 너비 사용 후에는 두 열 모두 업데이트)
            next_y_top = box_y_top - box_height - BEACON_MARGIN
            column_y_positions[0] = next_y_top
            column_y_positions[1] = next_y_top
            current_col = 0  # 다음은 왼쪽 열부터 시작
            row_heights = []  # 행 높이 초기화
            
            print(f" ✓ 완료")
            success_count += 1
        else:
            # 일반 비콘 박스 (2열 레이아웃)
            # Y 위치를 먼저 확인: Y 위치에 여유가 있으면 열 공간 체크를 하지 않음
            box_y_top = column_y_positions[current_col]
            min_y_position = FOOTER_HEIGHT + FOOTER_BOTTOM_MARGIN + MIN_Y_MARGIN
            
            # 페이지당 열 공간 확인
            if current_col == 0:
                # 왼쪽 열: Y 위치에 여유가 있는지 먼저 확인
                if box_y_top < min_y_position:
                    # Y 위치가 부족하면 페이지 넘김
                    current_page += 1
                    max_page = max(max_page, current_page)
                    c.showPage()
                    draw_header(c)
                    draw_watermark(c)
                    draw_footer(c, current_page)
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    beacons_on_page = 0
                    column_slots_used = 0
                    left_beacon_idx = None
                    box_y_top = column_y_positions[current_col]  # 새 페이지의 Y 위치
                # Y 위치가 충분하면 열 공간 체크
                elif column_slots_used + 2 > MAX_COLUMN_SLOTS_PER_PAGE:
                    # 열 공간이 부족하면 페이지 넘김
                    current_page += 1
                    max_page = max(max_page, current_page)
                    c.showPage()
                    draw_header(c)
                    draw_watermark(c)
                    draw_footer(c, current_page)
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    beacons_on_page = 0
                    column_slots_used = 0
                    left_beacon_idx = None
                    box_y_top = column_y_positions[current_col]  # 새 페이지의 Y 위치
            else:
                # 오른쪽 열: 왼쪽 비콘이 이미 그려진 상태에서 페이지 공간 확인
                # Y 위치나 열 공간이 부족하면 왼쪽 비콘만 카운트하고 페이지 넘김
                if box_y_top < min_y_position or column_slots_used + 2 > MAX_COLUMN_SLOTS_PER_PAGE:
                    # 왼쪽 비콘만 카운트
                    beacons_on_page += 1
                    column_slots_used += 1
                    success_count += 1
                    print(f" ✓ 완료 (왼쪽 열만, 페이지 넘김 - 오른쪽 공간 부족)")
                    # 페이지 넘김
                    current_page += 1
                    max_page = max(max_page, current_page)
                    c.showPage()
                    draw_header(c)
                    draw_watermark(c)
                    draw_footer(c, current_page)
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0  # 현재 비콘을 새 페이지 왼쪽에 그림
                    row_heights = []
                    beacons_on_page = 0
                    column_slots_used = 0
                    left_beacon_idx = None
                    box_y_top = column_y_positions[current_col]
            
            box_x = MARGIN + current_col * (BEACON_BOX_WIDTH + BEACON_COLUMN_MARGIN)
            box_width = BEACON_BOX_WIDTH
            
            # 높이 계산 및 박스 그리기
            if current_col == 0:
                # 왼쪽 열: 높이 계산하고 저장
                print(f"  [{idx}/{len(beacon_data)}] Beacon {beacon_number}: {num_images}개 이미지 (왼쪽, 페이지 {current_page}, Y={int(column_y_positions[0])})...", end="")
                box_height = draw_beacon_box(c, beacon_number, image_files, box_x, box_y_top, box_width, is_full_width=False)
                row_heights = [box_height]  # 왼쪽 높이 저장
                left_beacon_idx = idx - 1  # 왼쪽 비콘의 beacon_data 인덱스 저장 (enumerate는 1부터)
                # 박스 상단 위치 저장 (다음 위치 계산용)
                actual_box_y_top = column_y_positions[0]
                box_y_top = actual_box_y_top  # 박스 상단 위치
                # 왼쪽 열은 아직 카운트하지 않음 (오른쪽 열과 함께 한 행으로 카운트)
                # 단, 마지막 비콘이면 왼쪽 열만으로도 카운트
                if idx == len(beacon_data):
                    # 마지막 비콘이면 왼쪽 열만으로도 카운트
                    beacons_on_page += 1
                    column_slots_used += 1
                    success_count += 1
                    last_beacon_counted = True  # 마지막 비콘 카운트 완료 표시
                    print(f" ✓ 완료 (마지막)")
                    continue
                else:
                    # 마지막이 아니면 오른쪽 대기 중
                    print(f" [그려짐] 대기 중 (오른쪽 열 기다림)")
            else:
                # 오른쪽 열: 높이 계산하고 왼쪽과 비교
                print(f"  [{idx}/{len(beacon_data)}] Beacon {beacon_number}: {num_images}개 이미지 (오른쪽, 페이지 {current_page}, Y={int(column_y_positions[1])})...", end="")
                temp_height = draw_beacon_box(c, beacon_number, image_files, box_x, box_y_top, box_width, is_full_width=False)
                row_heights.append(temp_height)  # 오른쪽 높이 추가
                
                # 같은 행의 최대 높이 계산
                max_row_height = max(row_heights)
                
                # 왼쪽 비콘 정보 확인
                if left_beacon_idx is None or left_beacon_idx >= len(beacon_data):
                    print(f" ⚠ 오류: 왼쪽 비콘 인덱스 오류 (left_beacon_idx={left_beacon_idx})")
                    continue
                
                left_beacon_info = beacon_data[left_beacon_idx]
                
                # 두 박스를 같은 높이로 다시 그리기
                # 왼쪽 박스 다시 그키
                left_box_x = MARGIN
                left_box_y_top = column_y_positions[0]
                draw_beacon_box(c, left_beacon_info['number'], left_beacon_info['images'], 
                               left_box_x, left_box_y_top, BEACON_BOX_WIDTH, is_full_width=False, 
                               fixed_height=max_row_height)
                
                # 오른쪽 박스 다시 그리기
                right_box_x = MARGIN + BEACON_BOX_WIDTH + BEACON_COLUMN_MARGIN
                right_box_y_top = column_y_positions[1]
                draw_beacon_box(c, beacon_number, image_files, 
                               right_box_x, right_box_y_top, BEACON_BOX_WIDTH, is_full_width=False, 
                               fixed_height=max_row_height)
                
                # 박스 높이는 최대 높이 사용
                box_height = max_row_height
                box_y_top = min(column_y_positions[0], column_y_positions[1])  # 두 열 중 더 위쪽
                beacons_on_page += 2  # 한 행 완료 시 2개 비콘 카운트
                column_slots_used += 2  # 한 행 완료 시 2열 공간 사용
                success_count += 2  # 누락된 카운트 추가 (왼쪽 + 오른쪽)
            
            # 다음 위치로 이동 (박스 상단에서 높이와 마진을 뺀 위치)
            # 오른쪽 비콘을 그린 경우에만 페이지 넘김 체크
            if current_col == 1:
                # 오른쪽 비콘을 그렸으므로 한 행 완료
                next_y_top = box_y_top - box_height - BEACON_MARGIN
                
                # 페이지 넘김 확인 (푸터 영역 고려, 더 여유있게)
                min_y_position = FOOTER_HEIGHT + FOOTER_BOTTOM_MARGIN + MIN_Y_MARGIN
                # Y 위치를 먼저 체크
                if next_y_top < min_y_position:
                    # Y 위치가 부족하면 페이지 넘김
                    current_page += 1
                    max_page = max(max_page, current_page)
                    c.showPage()
                    draw_header(c)
                    draw_watermark(c)
                    draw_footer(c, current_page)
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    beacons_on_page = 0
                    column_slots_used = 0
                    left_beacon_idx = None
                # Y 위치가 충분하면 열 공간 체크
                elif column_slots_used >= MAX_COLUMN_SLOTS_PER_PAGE:
                    # 열 공간이 부족하면 페이지 넘김
                    current_page += 1
                    max_page = max(max_page, current_page)
                    c.showPage()
                    draw_header(c)
                    draw_watermark(c)
                    draw_footer(c, current_page)
                    column_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
                    current_col = 0
                    row_heights = []
                    beacons_on_page = 0
                    column_slots_used = 0
                    left_beacon_idx = None
                else:
                    # Y 위치와 열 공간 모두 충분: 계속 배치 가능
                    # 오른쪽 열 처리 완료: 두 열 모두 업데이트
                    column_y_positions[0] = next_y_top
                    column_y_positions[1] = next_y_top
                    current_col = 0  # 다음 행은 왼쪽부터
                    row_heights = []  # 행 높이 초기화
                    print(f" ✓ 완료")
                    # success_count는 이미 beacons_on_page += 2 시점에 추가됨
            else:
                # 왼쪽 열만 처리: 오른쪽 열로 이동 (페이지 넘김 체크 안 함)
                current_col = 1
    
    # 루프가 끝날 때 왼쪽 열에 비콘이 남아있는지 확인하고 카운트
    # current_col == 1: 왼쪽 열에 비콘을 그린 후 오른쪽 열로 이동했지만 다음 비콘이 없음
    # current_col == 0 and len(row_heights) > 0: 왼쪽 열에 비콘을 그렸지만 아직 카운트되지 않음
    if len(row_heights) > 0 and not last_beacon_counted:
        # 왼쪽 열에 비콘이 남아있고, 마지막 비콘이 이미 카운트되지 않은 경우만 카운트
        if current_col == 1:
            # 왼쪽 열에 비콘을 그린 후 오른쪽 열로 이동했지만 다음 비콘이 없음
            beacons_on_page += 1
            column_slots_used += 1
            print(f" ✓ 완료 (왼쪽 열만, 루프 종료)")
            success_count += 1
        elif current_col == 0:
            # 왼쪽 열에 비콘을 그렸지만 아직 카운트되지 않음 (페이지 넘김 등으로 인해)
            # 마지막 비콘이 왼쪽 열에만 있는 경우는 이미 처리되었으므로, 이 경우는 페이지 넘김 등으로 인한 것
            beacons_on_page += 1
            column_slots_used += 1
            print(f" ✓ 완료 (왼쪽 열만, 루프 종료 - current_col=0)")
            success_count += 1
    
    # PDF 저장
    c.save()
    
    # 최종 결과 출력
    total_time = time.time() - start_time
    print("\n" + "="*70)
    print("PDF 생성 완료")
    print("="*70)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {int(total_time // 60)}분 {int(total_time % 60)}초")
    print(f"\n📊 처리 결과:")
    print(f"  ✓ 성공: {success_count}개 Beacon")
    print(f"  ✗ 실패: {failed_count}개 Beacon")
    print(f"  📷 총 이미지: {total_images}개")
    print(f"  📄 총 페이지: {max_page}페이지")
    print(f"\n📁 출력 파일: {pdf_path.absolute()}")
    if LOGO_PATH.exists():
        print(f"  ✓ 로고 이미지 포함됨")
    else:
        print(f"  ⚠ 로고 이미지 없음 (logo.png 파일이 필요합니다)")
    print("="*70)

if __name__ == "__main__":
    create_all_pdfs()
