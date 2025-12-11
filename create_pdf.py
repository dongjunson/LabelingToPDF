#!/usr/bin/env python3
"""
output 폴더의 Minor별 이미지들을 PDF로 변환하는 스크립트 (Refactored)

각 Minor 폴더의 이미지들을 Beacon 번호로 변환하여 PDF 생성
- 각 Beacon별로 사진들을 배열하여 출력
- PDFLayoutManager 클래스를 통해 레이아웃 및 페이지 관리
"""
import os
import re
import time
import shutil
import urllib.request
import zipfile
import math
from pathlib import Path
from datetime import datetime
from io import BytesIO
from PIL import Image

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import black, white
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

# ============================================================================
# 상수 및 설정
# ============================================================================

OUTPUT_DIR = Path("output")
PDF_OUTPUT_DIR = Path("pdf_output")
LOGO_PATH = Path("logo.png")
FONTS_DIR = Path("fonts")

# PDF 제목 설정
FACILITY_NAME = "안양 박달 하수도 사업소"
PDF_TITLE_TEMPLATE = f"{FACILITY_NAME} 설치된 Beacon"

# 폰트 설정
PRETENDARD_REGULAR = "Pretendard-Regular"
PRETENDARD_BOLD = "Pretendard-Bold"
PRETENDARD_FONT_REGULAR_PATH = FONTS_DIR / "Pretendard-Regular.ttf"
PRETENDARD_FONT_BOLD_PATH = FONTS_DIR / "Pretendard-Bold.ttf"

# PDF 기본 치수
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 20 * mm
HEADER_HEIGHT = 25 * mm
FOOTER_HEIGHT = 15 * mm
FOOTER_BOTTOM_MARGIN = 15 * mm

# 헤더 위치
HEADER_TEXT_Y = PAGE_HEIGHT - MARGIN - 5 * mm
HEADER_LINE_Y = HEADER_TEXT_Y - 3 * mm
CONTENT_START_Y = HEADER_LINE_Y - 8 * mm

# 본문 영역
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)
CONTENT_HEIGHT = CONTENT_START_Y - FOOTER_HEIGHT - FOOTER_BOTTOM_MARGIN


# ============================================================================
# 유틸리티 함수
# ============================================================================

def setup_pretendard_font():
    """Pretendard 폰트를 다운로드하고 reportlab에 등록"""
    FONTS_DIR.mkdir(exist_ok=True)
    
    if PRETENDARD_FONT_REGULAR_PATH.exists() and PRETENDARD_FONT_BOLD_PATH.exists():
        try:
            pdfmetrics.registerFont(TTFont(PRETENDARD_REGULAR, str(PRETENDARD_FONT_REGULAR_PATH)))
            pdfmetrics.registerFont(TTFont(PRETENDARD_BOLD, str(PRETENDARD_FONT_BOLD_PATH)))
            print("✓ Pretendard 폰트 로드 완료")
            return True
        except Exception as e:
            print(f"⚠ 폰트 등록 오류: {e}")
    
    try:
        print("Pretendard 폰트 다운로드 중...")
        font_zip_url = "https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip"
        zip_path = FONTS_DIR / "Pretendard.zip"
        
        urllib.request.urlretrieve(font_zip_url, zip_path)
        
        extract_dir = FONTS_DIR / "extract_temp"
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        ttf_files = list(extract_dir.rglob("*.ttf"))
        regular_found = False
        bold_found = False
        
        # 정확한 파일명으로 찾기
        for ttf_file in ttf_files:
            name_lower = ttf_file.name.lower()
            if ttf_file.name == "Pretendard-Regular.ttf" or name_lower == "pretendard-regular.ttf":
                shutil.copy2(ttf_file, PRETENDARD_FONT_REGULAR_PATH)
                regular_found = True
            elif ttf_file.name == "Pretendard-Bold.ttf" or name_lower == "pretendard-bold.ttf":
                shutil.copy2(ttf_file, PRETENDARD_FONT_BOLD_PATH)
                bold_found = True
                
        # 부분 매칭으로 찾기
        if not regular_found:
            for ttf_file in ttf_files:
                if "regular" in ttf_file.name.lower() and "pretendard" in ttf_file.name.lower():
                    shutil.copy2(ttf_file, PRETENDARD_FONT_REGULAR_PATH)
                    break
        if not bold_found:
            for ttf_file in ttf_files:
                if "bold" in ttf_file.name.lower() and "pretendard" in ttf_file.name.lower():
                    shutil.copy2(ttf_file, PRETENDARD_FONT_BOLD_PATH)
                    break
        
        if extract_dir.exists(): shutil.rmtree(extract_dir)
        if zip_path.exists(): zip_path.unlink()
        
        if PRETENDARD_FONT_REGULAR_PATH.exists():
            pdfmetrics.registerFont(TTFont(PRETENDARD_REGULAR, str(PRETENDARD_FONT_REGULAR_PATH)))
        if PRETENDARD_FONT_BOLD_PATH.exists():
            pdfmetrics.registerFont(TTFont(PRETENDARD_BOLD, str(PRETENDARD_FONT_BOLD_PATH)))
            
        print("✓ Pretendard 폰트 다운로드 및 등록 완료")
        return True
    except Exception as e:
        print(f"⚠ Pretendard 폰트 다운로드 실패: {e}")
        return False

def get_beacon_number(minor_folder_name):
    """Minor 폴더명에서 Beacon 번호 추출"""
    match = re.search(r'Minor_(\d+)', minor_folder_name)
    if match:
        return int(match[1])
    return None

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

def resize_image_for_pdf(image_path, target_width_pt, target_height_pt):
    """이미지를 PDF에 맞게 리사이즈"""
    try:
        img = Image.open(image_path)
        img = convert_to_rgb(img)
        
        orig_width, orig_height = img.size
        
        # 300 DPI 기준 픽셀 계산
        target_width_px = int(target_width_pt * 300 / 72)
        target_height_px = int(target_height_pt * 300 / 72)
        
        ratio = min(target_width_px / orig_width, target_height_px / orig_height)
        new_width = int(orig_width * ratio)
        new_height = int(orig_height * ratio)
        
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        actual_width_pt = new_width * 72 / 300
        actual_height_pt = new_height * 72 / 300
        
        return resized, actual_width_pt, actual_height_pt
    except Exception as e:
        print(f"  ⚠ 이미지 처리 오류 ({image_path.name}): {e}")
        return None, 0, 0

def get_layout_settings(high_density=False):
    """레이아웃 모드에 따른 설정값 반환"""
    if high_density:
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


# ============================================================================
# PDF Layout Manager Class
# ============================================================================

class PDFLayoutManager:
    def __init__(self, canvas_obj, layout_settings):
        self.c = canvas_obj
        self.layout = layout_settings
        
        # 설정값 언패킹
        self.BEACON_MARGIN = layout_settings['BEACON_MARGIN']
        self.IMAGE_MARGIN = layout_settings['IMAGE_MARGIN']
        self.BEACON_COLUMN_MARGIN = layout_settings['BEACON_COLUMN_MARGIN']
        self.BEACON_BOX_WIDTH = layout_settings['BEACON_BOX_WIDTH']
        self.BEACON_TITLE_HEIGHT = layout_settings['BEACON_TITLE_HEIGHT']
        self.BOX_PADDING = layout_settings['BOX_PADDING']
        self.MAX_IMAGE_HEIGHT = layout_settings['MAX_IMAGE_HEIGHT']
        self.MAX_COLUMN_SLOTS = layout_settings['MAX_COLUMN_SLOTS_PER_PAGE']
        self.MIN_Y_MARGIN = layout_settings['MIN_Y_MARGIN']
        
        # 상태 변수
        self.page_number = 1
        self.col_y_positions = [CONTENT_START_Y, CONTENT_START_Y] # [Left Y, Right Y]
        self.current_col = 0 # 0: Left, 1: Right
        self.row_heights = [] # 현재 행의 박스 높이들
        self.column_slots_used = 0 # 현재 페이지에서 사용된 슬롯 수
        self.left_beacon_data = None # 왼쪽 열 비콘 데이터 (재그리기용)
        self.left_beacon_box_info = None # 왼쪽 열 비콘 박스 정보 (위치 등)
        
        # 통계
        self.success_count = 0
        
        # 첫 페이지 시작
        self._start_new_page(first_page=True)

    def _start_new_page(self, first_page=False):
        """새 페이지 시작 및 헤더/푸터/워터마크 출력"""
        if not first_page:
            self.c.showPage()
            self.page_number += 1
            
        self._draw_header()
        self._draw_watermark()
        self._draw_footer()
        
        # 상태 초기화
        self.col_y_positions = [CONTENT_START_Y, CONTENT_START_Y]
        self.current_col = 0
        self.row_heights = []
        self.column_slots_used = 0
        self.left_beacon_data = None
        self.left_beacon_box_info = None

    def _draw_header(self):
        """헤더 그리기"""
        c = self.c
        try:
            c.setFont(PRETENDARD_BOLD, 14)
            font_name = PRETENDARD_BOLD
        except:
            c.setFont("Helvetica-Bold", 14)
            font_name = "Helvetica-Bold"
            
        c.setFillColor(black)
        c.drawString(MARGIN, HEADER_TEXT_Y, FACILITY_NAME)
        
        # JRIndustry
        jr_text = "JRIndustry"
        try:
            c.setFont(PRETENDARD_BOLD, 11)
        except:
            c.setFont("Helvetica-Bold", 11)
            
        text_width = c.stringWidth(jr_text, c._fontname, 11)
        c.drawString(PAGE_WIDTH - MARGIN - text_width, HEADER_TEXT_Y, jr_text)
        
        # Line
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.line(MARGIN, HEADER_LINE_Y, PAGE_WIDTH - MARGIN, HEADER_LINE_Y)

    def _draw_footer(self):
        """푸터 그리기"""
        c = self.c
        footer_y = FOOTER_BOTTOM_MARGIN
        
        # Page Number
        try:
            c.setFont(PRETENDARD_REGULAR, 8)
        except:
            c.setFont("Helvetica", 8)
        c.setFillColor(black)
        c.drawString(MARGIN, footer_y, f"Page {self.page_number}")
        
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

    def _draw_watermark(self):
        """워터마크 그리기"""
        if not LOGO_PATH.exists(): return
        
        c = self.c
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

    def _calculate_box_height(self, num_images, fixed_height=None):
        """비콘 박스의 높이 계산"""
        available_width = self.BEACON_BOX_WIDTH - (self.BOX_PADDING * 2)
        available_height = CONTENT_HEIGHT - self.BEACON_TITLE_HEIGHT - self.BOX_PADDING * 2
        
        # 이미지 레이아웃 결정
        if num_images == 4: # Full width
             # Full width logic handled separately usually, but here for height calc
             # If full width, width is larger
             available_width = CONTENT_WIDTH - (self.BOX_PADDING * 2)
             image_layout = (4, 1)
        elif num_images == 0: image_layout = (0, 0)
        elif num_images <= 3: image_layout = (num_images, 1)
        else: image_layout = (2, (num_images + 1) // 2)
        
        cols, rows = image_layout
        
        if num_images == 0:
            image_area_height = 15 * mm
        else:
            image_area_height = min(available_height, self.MAX_IMAGE_HEIGHT)
            
        if fixed_height is not None:
            return fixed_height
            
        return self.BEACON_TITLE_HEIGHT + image_area_height + (self.BOX_PADDING * 2)

    def _draw_beacon_box_content(self, beacon_number, image_files, box_x, box_y_top, box_width, fixed_height=None):
        """실제 비콘 박스 그리기 로직"""
        c = self.c
        num_images = len(image_files)
        
        # 레이아웃 계산
        available_width = box_width - (self.BOX_PADDING * 2)
        available_height = CONTENT_HEIGHT - self.BEACON_TITLE_HEIGHT - self.BOX_PADDING * 2
        
        if num_images == 0:
            image_layout = (0, 0)
            image_area_height = 15 * mm
        elif num_images <= 3:
            image_layout = (num_images, 1)
            image_area_height = min(available_height, self.MAX_IMAGE_HEIGHT)
        elif num_images == 4:
            image_layout = (4, 1)
            image_area_height = min(available_height, self.MAX_IMAGE_HEIGHT)
        else:
            image_layout = (2, (num_images + 1) // 2)
            image_area_height = min(available_height, self.MAX_IMAGE_HEIGHT)
            
        # 고정 높이가 있으면 재조정
        if fixed_height is not None:
            box_height = fixed_height
            image_area_height = box_height - self.BEACON_TITLE_HEIGHT - (self.BOX_PADDING * 2)
        else:
            box_height = self.BEACON_TITLE_HEIGHT + image_area_height + (self.BOX_PADDING * 2)
            
        box_y_bottom = box_y_top - box_height
        
        # 배경 및 테두리
        bg_color = HexColor('#F5F5F5') if USE_HEXCOLOR else white
        border_color = HexColor('#E0E0E0') if USE_HEXCOLOR else black
        
        c.setFillColor(bg_color)
        c.setStrokeColor(bg_color)
        
        # Rounded Rect simulation
        r = 1.5 * mm
        c.circle(box_x + r, box_y_top - r, r, fill=1, stroke=0)
        c.circle(box_x + box_width - r, box_y_top - r, r, fill=1, stroke=0)
        c.circle(box_x + r, box_y_bottom + r, r, fill=1, stroke=0)
        c.circle(box_x + box_width - r, box_y_bottom + r, r, fill=1, stroke=0)
        c.rect(box_x, box_y_bottom + r, box_width, box_height - 2*r, fill=1, stroke=0)
        c.rect(box_x + r, box_y_bottom, box_width - 2*r, box_height, fill=1, stroke=0)
        
        c.setStrokeColor(border_color)
        c.setLineWidth(0.8)
        c.rect(box_x, box_y_bottom, box_width, box_height, fill=0, stroke=1)
        
        # Title
        try:
            c.setFont(PRETENDARD_BOLD, 7)
        except:
            c.setFont("Helvetica-Bold", 7)
        c.setFillColor(black)
        c.drawString(box_x + self.BOX_PADDING, box_y_top - self.BOX_PADDING - 2*mm, f"Beacon {beacon_number}")
        
        # Images
        if num_images > 0:
            cols, rows = image_layout
            img_cell_w = (available_width - (self.IMAGE_MARGIN * (cols - 1))) / cols if cols > 0 else available_width
            img_cell_h = (image_area_height - (self.IMAGE_MARGIN * (rows - 1))) / rows if rows > 1 else image_area_height
            
            img_start_y = box_y_top - self.BEACON_TITLE_HEIGHT - self.BOX_PADDING
            
            for i, img_path in enumerate(image_files):
                r_idx = i // cols
                c_idx = i % cols
                
                resized, w, h = resize_image_for_pdf(img_path, img_cell_w, img_cell_h)
                
                if resized:
                    ix = box_x + self.BOX_PADDING + c_idx * (img_cell_w + self.IMAGE_MARGIN) + (img_cell_w - w)/2
                    iy = img_start_y - (r_idx + 1) * img_cell_h - r_idx * self.IMAGE_MARGIN + (img_cell_h - h)/2
                    
                    buffer = BytesIO()
                    resized.save(buffer, format='JPEG', quality=98)
                    buffer.seek(0)
                    c.drawImage(ImageReader(buffer), ix, iy, width=w, height=h)
        else:
            # No Image Text
            try: c.setFont(PRETENDARD_REGULAR, 10)
            except: c.setFont("Helvetica", 10)
            c.drawCentredString(box_x + box_width/2, box_y_top - box_height/2, "이미지 없음")
            
        return box_height

    def add_beacon(self, beacon_info):
        """비콘 하나를 레이아웃에 배치"""
        beacon_number = beacon_info['number']
        image_files = beacon_info['images']
        num_images = len(image_files)
        is_full_width = (num_images == 4)
        
        # 1. 공간 확인 및 페이지 넘김 결정
        
        # 4개 이미지(Full Width)인 경우
        if is_full_width:
            # 왼쪽 열에 대기중인 비콘이 있으면 먼저 처리 완료해야 함
            if self.current_col == 1:
                self.current_col = 0
                self.row_heights = []
                self.column_slots_used += 1
                # Y 위치 조정 (왼쪽 비콘 높이만큼)
                left_h = self.left_beacon_box_info['height']
                self.col_y_positions[0] -= (left_h + self.BEACON_MARGIN)
                self.col_y_positions[1] = min(self.col_y_positions[0], self.col_y_positions[1])
                self.left_beacon_data = None
            
            # 새 페이지 필요 여부 체크
            est_height = self._calculate_box_height(num_images)
            next_y = min(self.col_y_positions) - est_height - self.BEACON_MARGIN
            min_y = FOOTER_HEIGHT + FOOTER_BOTTOM_MARGIN + self.MIN_Y_MARGIN
            
            if next_y < min_y or self.column_slots_used + 2 > self.MAX_COLUMN_SLOTS:
                self._start_new_page()
                
            # 그리기
            box_y = min(self.col_y_positions)
            height = self._draw_beacon_box_content(
                beacon_number, image_files, 
                MARGIN, box_y, CONTENT_WIDTH
            )
            
            # 상태 업데이트
            self.col_y_positions[0] = box_y - height - self.BEACON_MARGIN
            self.col_y_positions[1] = self.col_y_positions[0]
            self.column_slots_used += 2
            self.success_count += 1
            print(f"  Beacon {beacon_number}: Full Width 배치 완료")
            
        # 일반 비콘 (Half Width)
        else:
            # 현재 열 위치 계산
            box_y = self.col_y_positions[self.current_col]
            min_y = FOOTER_HEIGHT + FOOTER_BOTTOM_MARGIN + self.MIN_Y_MARGIN
            
            # 페이지 넘김 체크
            # 왼쪽 열일 때만 체크 (오른쪽은 왼쪽과 같은 행이므로 공간이 있다고 가정하되, 너무 좁으면 넘김)
            if self.current_col == 0:
                if box_y < min_y or self.column_slots_used + 2 > self.MAX_COLUMN_SLOTS:
                    self._start_new_page()
                    box_y = self.col_y_positions[0]
            else:
                # 오른쪽 열인데 공간 부족하면? -> 왼쪽만 그리고 다음 페이지로
                # (이전 로직 유지: 오른쪽 공간 부족시 왼쪽만 카운트하고 페이지 넘김)
                if box_y < min_y or self.column_slots_used + 2 > self.MAX_COLUMN_SLOTS:
                    # 왼쪽 비콘은 이미 그려짐. 페이지 넘기고 초기화
                    self._start_new_page()
                    box_y = self.col_y_positions[0]
                    # 왼쪽 비콘 데이터는 날아감 (이미 전 페이지에 그려짐)
                    self.left_beacon_data = None 
            
            # 그리기
            box_x = MARGIN + self.current_col * (self.BEACON_BOX_WIDTH + self.BEACON_COLUMN_MARGIN)
            height = self._draw_beacon_box_content(
                beacon_number, image_files,
                box_x, box_y, self.BEACON_BOX_WIDTH
            )
            
            if self.current_col == 0:
                # 왼쪽 열: 대기
                self.row_heights = [height]
                self.left_beacon_data = beacon_info
                self.left_beacon_box_info = {'x': box_x, 'y': box_y, 'height': height}
                self.current_col = 1
                print(f"  Beacon {beacon_number}: 왼쪽 배치 (오른쪽 대기 중)")
            else:
                # 오른쪽 열: 높이 맞추기 및 확정
                self.row_heights.append(height)
                max_h = max(self.row_heights)
                
                # 높이가 다르면 다시 그리기
                if self.left_beacon_data and max_h > self.left_beacon_box_info['height']:
                    # 왼쪽 다시 그리기
                    self._draw_beacon_box_content(
                        self.left_beacon_data['number'], self.left_beacon_data['images'],
                        self.left_beacon_box_info['x'], self.left_beacon_box_info['y'],
                        self.BEACON_BOX_WIDTH, fixed_height=max_h
                    )
                if max_h > height:
                    # 오른쪽 다시 그리기
                    self._draw_beacon_box_content(
                        beacon_number, image_files,
                        box_x, box_y, self.BEACON_BOX_WIDTH, fixed_height=max_h
                    )
                
                # 상태 업데이트
                next_y = min(self.col_y_positions) - max_h - self.BEACON_MARGIN
                self.col_y_positions[0] = next_y
                self.col_y_positions[1] = next_y
                self.column_slots_used += 2
                self.success_count += 2 # 왼쪽 + 오른쪽
                self.current_col = 0
                self.row_heights = []
                self.left_beacon_data = None
                print(f"  Beacon {beacon_number}: 오른쪽 배치 완료 (행 높이: {int(max_h/mm)}mm)")

    def finish(self):
        """마지막 남은 비콘 처리 및 저장"""
        if self.current_col == 1 and self.left_beacon_data:
            # 왼쪽 비콘만 있고 오른쪽이 없는 상태로 종료됨
            self.success_count += 1
            print(f"  Beacon {self.left_beacon_data['number']}: 마지막 왼쪽 배치 완료")
            
        self.c.save()
        return self.success_count, self.page_number


# ============================================================================
# 메인 로직
# ============================================================================

def collect_beacon_data():
    """Minor 폴더에서 비콘 데이터 수집"""
    minor_folders = sorted([f for f in OUTPUT_DIR.iterdir() if f.is_dir() and f.name.startswith('Minor_')])
    
    if not minor_folders:
        print("❌ Minor 폴더를 찾을 수 없습니다.")
        return []
        
    beacon_data = []
    image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    
    for folder in minor_folders:
        b_num = get_beacon_number(folder.name)
        if b_num is None: continue
        
        images = [f for f in folder.iterdir() if f.is_file() and f.suffix in image_extensions]
        
        # 정렬 로직
        def sort_key(p):
            n = p.name
            is_eng_num = all(ord(c) < 128 for c in n.replace('.', '').replace('_', '').replace('-', ''))
            return (0 if is_eng_num else 1, n)
            
        images.sort(key=sort_key)
        
        if images:
            beacon_data.append({'number': b_num, 'images': images})
            
    return beacon_data

def create_all_pdfs():
    """
    [단계 4] output 폴더의 Minor별 이미지들을 PDF로 변환합니다.
    """
    print("="*70)
    print("단계 4: PDF 생성")
    print("="*70)
    
    # 사용자 입력
    print("📊 레이아웃 모드 선택:")
    print("  1. 일반 모드 (페이지당 ~8개)")
    print("  2. 고밀도 모드 (페이지당 ~16개)")
    
    try:
        choice = input("\n선택 (1/2, 기본 1): ").strip()
        high_density = (choice == '2')
    except:
        high_density = False
        
    layout_settings = get_layout_settings(high_density)
    
    # 폰트 설정
    setup_pretendard_font()
    
    # 데이터 수집
    beacon_data = collect_beacon_data()
    if not beacon_data:
        print("데이터가 없습니다.")
        return

    print(f"\n📁 총 {len(beacon_data)}개 Beacon 처리 시작...\n")
    
    # PDF 생성 준비
    PDF_OUTPUT_DIR.mkdir(exist_ok=True)
    pdf_filename = f"{FACILITY_NAME.replace(' ', '_')}_Beacon_설치현황.pdf"
    pdf_path = PDF_OUTPUT_DIR / pdf_filename
    
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    manager = PDFLayoutManager(c, layout_settings)
    
    start_time = time.time()
    
    # 비콘 추가
    for info in beacon_data:
        manager.add_beacon(info)
        
    # 완료
    success_count, total_pages = manager.finish()
    
    elapsed = time.time() - start_time
    print("\n" + "="*70)
    print("단계 4: PDF 생성 완료")
    print("="*70)
    print(f"  처리된 Beacon 수: {success_count}개")
    print(f"  총 페이지 수: {total_pages}페이지")
    print(f"  파일 위치: {pdf_path.absolute()}")
    print(f"  소요 시간: {elapsed:.1f}초")
    print("="*70)
    print("\n✅ 모든 단계가 완료되었습니다!")
    print("="*70)

if __name__ == "__main__":
    create_all_pdfs()
