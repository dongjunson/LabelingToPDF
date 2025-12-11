#!/usr/bin/env python3
"""
Unknown 폴더의 이미지들을 재검사하여 Minor 값을 다시 확인하는 검수 프로그램

- output/Unknown 폴더의 이미지들을 다시 OCR로 분석
- Minor 값을 찾으면 해당 Minor 폴더로 이동
- 여전히 찾지 못한 파일은 Unknown 폴더에 유지
"""
import os
import re
import shutil
import time
from pathlib import Path
from datetime import datetime

try:
    import easyocr
    import cv2
    import numpy as np
    from PIL import Image as PILImage
    USE_EASYOCR = True
    USE_IMAGE_PREPROCESSING = True
    print("EasyOCR과 이미지 전처리를 사용합니다...")
    reader = easyocr.Reader(['ko', 'en'], gpu=False)
except ImportError as e:
    if 'easyocr' in str(e):
        print("Error: easyocr이 설치되지 않았습니다.")
        print("설치: pip3 install easyocr")
        exit(1)
    elif 'cv2' in str(e):
        print("Warning: opencv-python이 설치되지 않았습니다. 이미지 전처리 기능이 제한됩니다.")
        print("설치: pip3 install opencv-python")
        USE_IMAGE_PREPROCESSING = False
    else:
        USE_IMAGE_PREPROCESSING = False

SOURCE_DIR = Path("source")
OUTPUT_DIR = Path("output")
UNKNOWN_DIR = OUTPUT_DIR / "Unknown"

def extract_minor_from_filename(filename):
    """
    파일명에서 우측 날짜를 제거하고 나머지에서 Minor 값을 추출합니다.
    
    처리 방식:
    1. 확장자 제거
    2. 우측에서 날짜 패턴 제거 (9자리 또는 8자리)
    3. 나머지에서 "설치" 다음의 숫자를 Minor로 추출
    
    예:
    - 장호원비콘설치10251104130.jpg -> 날짜(251104130) 제거 -> "장호원비콘설치10" -> Minor: 10
    - 장호원비콘설치1251104120.jpg -> 날짜(251104120) 제거 -> "장호원비콘설치1" -> Minor: 1
    - 장호원비콘설치49251104077.jpg -> 날짜(251104077) 제거 -> "장호원비콘설치49" -> Minor: 49
    - 장호원비콘설치6251104125.jpg -> 날짜(251104125) 제거 -> "장호원비콘설치6" -> Minor: 6
    
    날짜 패턴:
    - 9자리: 25로 시작하는 9자리 숫자 (예: 251104130)
    - 8자리: 8자리 숫자 (예: 51104130)
    """
    # 확장자 제거
    name_without_ext = re.sub(r'\.(jpg|jpeg|png|JPG|JPEG|PNG)$', '', filename)
    
    # 우선순위 1: 우측에서 9자리 날짜 패턴 제거 (25로 시작하는 9자리)
    # 예: 251104130, 251104077, 251104125
    match = re.search(r'^(.+?)(25\d{7})$', name_without_ext)
    if match:
        prefix = match.group(1)  # 날짜 제거 후 나머지
        # "설치" 다음의 숫자 추출
        install_match = re.search(r'설치(\d+)', prefix)
        if install_match:
            return install_match.group(1)
        # "설치"가 없으면 마지막 숫자 추출
        numbers = re.findall(r'\d+', prefix)
        if numbers:
            return numbers[-1]
    
    # 우선순위 2: 우측에서 8자리 날짜 패턴 제거
    # 예: 51104130, 1104120
    match = re.search(r'^(.+?)(\d{8})$', name_without_ext)
    if match:
        prefix = match.group(1)
        date = match.group(2)
        # 날짜가 25로 시작하지 않는 경우만 (25로 시작하면 9자리 패턴에서 처리됨)
        if not date.startswith('25'):
            # "설치" 다음의 숫자 추출
            install_match = re.search(r'설치(\d+)', prefix)
            if install_match:
                return install_match.group(1)
            # "설치"가 없으면 마지막 숫자 추출
            numbers = re.findall(r'\d+', prefix)
            if numbers:
                return numbers[-1]
    
    # 우선순위 3: 우측에서 6자리 이상 숫자 패턴 제거 (날짜로 추정)
    # 예: 251104, 51104130
    match = re.search(r'^(.+?)(\d{6,})$', name_without_ext)
    if match:
        prefix = match.group(1)
        # "설치" 다음의 숫자 추출
        install_match = re.search(r'설치(\d+)', prefix)
        if install_match:
            return install_match.group(1)
        # "설치"가 없으면 마지막 숫자 추출
        numbers = re.findall(r'\d+', prefix)
        if numbers:
            return numbers[-1]
    
    return None

def preprocess_image(image_path):
    """
    OCR 정확도를 높이기 위한 이미지 전처리
    좌측 하단은 이미 흰색 박스에 검은색 텍스트가 있으므로 전처리 불필요
    원본 이미지를 그대로 사용하여 텍스트 손실 방지
    """
    # 좌측 하단이 이미 흰색 박스에 검은색 텍스트가 있으므로
    # 전처리 없이 원본 이미지를 그대로 사용
    # 전처리를 하면 오히려 텍스트가 손실될 수 있음
    return str(image_path)

def normalize_four_digit_minor(value_str):
    """
    Minor 옆에 있는 4자리 숫자를 그대로 문자형으로 정규화합니다.
    예: "0019" -> "0019" (그대로 사용)
    예: "OO19" -> "0019" (O를 0으로 변환)
    예: "0001" -> "0001"
    
    개선: 더 많은 OCR 오류 패턴 처리
    """
    if not value_str:
        return None
    
    # 일반적인 OCR 오류 패턴 수정
    # O, o -> 0
    value_str = value_str.replace('O', '0').replace('o', '0')
    # I, l, | -> 1 (문맥에 따라 다를 수 있음)
    # S -> 5
    # Z -> 2
    # 하지만 너무 공격적으로 바꾸면 오히려 문제가 될 수 있으므로 신중하게
    
    # 숫자만 추출
    numbers = re.findall(r'\d+', value_str)
    if numbers:
        num_str = numbers[0]
        # 4자리로 패딩하여 반환 (그대로 사용)
        if len(num_str) >= 4:
            # 4자리 이상이면 앞 4자리만 사용
            return num_str[:4].zfill(4)
        else:
            # 4자리 미만이면 앞에 0을 붙여서 4자리로 만듦
            return num_str.zfill(4)
    
    return None

def extract_minor_value(image_path):
    """
    이미지에서 Minor 값을 추출합니다. (개선된 OCR 정밀도)
    
    우선순위:
    1. 최우선: 파일명에서 '설치' 옆 숫자 추출 (가장 정확함)
       예: 장호원비콘설치44251104067.jpg -> "44" -> "0044"
       단, 파일명에서 추출한 값이 5자리 이상이면 파일명 규칙이 이상한 것으로 간주하여 OCR로 처리
    2. OCR 우선순위 (파일명 추출 실패 시):
       2-1. '비콘' 옆에 숫자 4자리
       2-2. '설치' 옆에 숫자 4자리
       2-3. 'Minor' 영문 옆에 숫자 4자리
    
    OCR 개선 사항:
    - 이미지 전처리 (대비 향상, 노이즈 제거, 이진화)
    - 신뢰도 기반 필터링
    - 여러 OCR 파라미터 시도
    - 텍스트 위치 정보 활용
    
    OCR 오류 처리: "0000"은 유효하지 않은 값으로 간주
    """
    try:
        # 1. 최우선: 파일명에서 '설치' 옆 숫자 확인 (가장 정확함)
        filename_minor = extract_minor_from_filename(image_path.name)
        if filename_minor:
            # 파일명에서 추출한 Minor 값이 5자리 이상이면 파일명 규칙 에러로 간주
            # 이 경우 OCR로 처리해야 함
            if len(filename_minor) >= 5:
                # 5자리 이상이면 파일명 규칙 에러 - OCR로 처리
                # print(f"  ⚠ 파일명 규칙 에러: {filename_minor} (5자리 이상) -> OCR로 처리")
                pass  # 아래 OCR 코드로 진행
            else:
                # 4자리 이하는 정상적인 Minor 값으로 간주
                return f"{int(filename_minor):04d}"
        
        # 파일명에서 추출 실패하거나 5자리 이상인 경우 OCR 수행
        # 이미지 크기 먼저 가져오기 (좌측 하단 영역 계산용)
        try:
            img = PILImage.open(image_path)
            img_width, img_height = img.size
        except:
            img_width, img_height = 0, 0
        
        # 이미지 전처리 적용
        processed_image_path = preprocess_image(image_path)
        
        # OCR 수행 (최적화된 파라미터 사용 - 더 많은 텍스트 감지)
        # detail=1: 바운딩 박스와 신뢰도 정보 포함
        # text_threshold: 텍스트 감지 임계값 (낮을수록 더 많은 텍스트 감지)
        # contrast_ths: 대비 임계값
        # 좌측 하단 텍스트 인식률 향상을 위해 파라미터를 더 낮춤
        results = reader.readtext(
            processed_image_path,
            detail=1,
            paragraph=False,
            text_threshold=0.4,  # 더 낮춰서 더 많은 텍스트 감지 (특히 숫자, 한글)
            contrast_ths=0.03,   # 대비가 낮은 텍스트도 감지 (더 낮게)
            adjust_contrast=0.2, # 대비 자동 조정 (더 강하게)
            width_ths=0.3,      # 텍스트 너비 임계값 (더 낮게)
            height_ths=0.3,     # 텍스트 높이 임계값 (더 낮게)
        )
        
        # 전처리된 임시 파일 삭제
        if USE_IMAGE_PREPROCESSING and processed_image_path != str(image_path):
            try:
                temp_path = Path(processed_image_path)
                if temp_path.exists():
                    temp_path.unlink()
            except:
                pass
        
        # 신뢰도 기반으로 텍스트 필터링 및 정렬
        # 신뢰도가 높은 텍스트를 우선 사용 (임계값을 낮춰서 더 많은 텍스트 포함)
        filtered_results = []
        for result in results:
            if len(result) >= 3:  # (bbox, text, confidence) 형식
                confidence = result[2]
                if confidence >= 0.15:  # 신뢰도 15% 이상 사용 (더 낮게 설정하여 한글, 숫자도 포함)
                    filtered_results.append(result)
        
        # 좌측 하단 흰색 영역 정의 (우선순위 최고)
        # 이미지의 하단 40%, 좌측 60% - 흰색 박스 영역에 집중 (더 넓게)
        if img_width > 0 and img_height > 0 and filtered_results:
            # 좌측 하단 영역을 더 넓게 정의 (흰색 박스 영역)
            bottom_threshold = img_height * 0.6  # 하단 40% (y 좌표가 큰 값이 하단, 더 넓게)
            left_threshold = img_width * 0.6  # 좌측 60% (흰색 박스가 좌측 하단에 위치, 더 넓게)
            
            # 좌측 하단 영역의 텍스트 추출 (최우선)
            bottom_left_texts = []
            for result in filtered_results:
                if len(result) >= 2:
                    bbox = result[0]
                    text = result[1]
                    if bbox and len(bbox) >= 4:
                        # 바운딩 박스의 하단 점 계산
                        # 이미지 좌표계: (0,0)이 좌측 상단, y가 아래로 증가
                        min_x = min([p[0] for p in bbox if len(p) >= 2])
                        max_x = max([p[0] for p in bbox if len(p) >= 2])
                        max_y_point = max([p[1] for p in bbox if len(p) >= 2])
                        min_y_point = min([p[1] for p in bbox if len(p) >= 2])
                        # 바운딩 박스의 중심점도 계산 (더 정확한 위치 판단)
                        center_x = (min_x + max_x) / 2
                        center_y = (min_y_point + max_y_point) / 2
                        
                        # 좌측 하단 영역에 있는지 확인 (하단 30%, 좌측 50%)
                        # 흰색 박스는 좌측 하단에 위치하므로 이 영역에 집중
                        is_bottom_left = (max_y_point >= bottom_threshold and 
                                         center_y >= bottom_threshold and
                                         (center_x <= left_threshold or min_x <= left_threshold))
                        
                        if is_bottom_left:
                            # 좌측 하단 영역에 있는 텍스트만 추출
                            bottom_left_texts.append((result, max_y_point, min_x))  # (result, y, x) - 정렬용
            
            # 좌측 하단 영역의 텍스트를 y 좌표(하단 우선), x 좌표(좌측 우선) 순으로 정렬
            bottom_left_texts.sort(key=lambda x: (-x[1], x[2]))  # y는 내림차순(하단 우선), x는 오름차순(좌측 우선)
            
            # 좌측 하단 텍스트를 공백으로 합치기 (흰색 박스 내 텍스트들이 함께 인식되도록)
            bottom_left_text_parts = []
            for item in bottom_left_texts:
                text = item[0][1]
                bottom_left_text_parts.append(text)
            bottom_left_text = ' '.join(bottom_left_text_parts)
            
            # 좌측 하단 영역에서 "비콘" 텍스트와 숫자를 찾아서 조합 (최우선)
            beacon_texts = []
            number_texts = []
            for item in bottom_left_texts:
                text = item[0][1]
                bbox = item[0][0]
                # "비콘" 패턴 찾기
                if re.search(r'비[콘콕콘]', text, re.IGNORECASE):
                    beacon_texts.append((item, text, bbox))
                # 3자리 또는 4자리 숫자 패턴 찾기
                if re.search(r'[0-9OoIl|]{3,4}', text):
                    number_texts.append((item, text, bbox))
        else:
            bottom_left_text = ""
            beacon_texts = []
            number_texts = []
        
        # ===== 우선순위 1: 좌측 하단 흰색 영역에서 '비콘' 옆에 숫자 패턴 =====
        # 좌측 하단 흰색 영역에 집중하여 "비콘" 옆 숫자 인식 (최우선)
        
        # 먼저 좌측 하단 영역에서 "비콘"과 숫자가 분리되어 인식된 경우 처리 (최우선)
        if img_width > 0 and img_height > 0 and beacon_texts and number_texts:
            # "비콘" 텍스트와 숫자 텍스트가 근접한 경우 조합
            for beacon_item, beacon_text, beacon_bbox in beacon_texts:
                if beacon_bbox and len(beacon_bbox) >= 4:
                    beacon_center_x = sum([p[0] for p in beacon_bbox if len(p) >= 2]) / len([p for p in beacon_bbox if len(p) >= 2])
                    beacon_center_y = sum([p[1] for p in beacon_bbox if len(p) >= 2]) / len([p for p in beacon_bbox if len(p) >= 2])
                    
                    for num_item, num_text, num_bbox in number_texts:
                        if num_bbox and len(num_bbox) >= 4:
                            num_center_x = sum([p[0] for p in num_bbox if len(p) >= 2]) / len([p for p in num_bbox if len(p) >= 2])
                            num_center_y = sum([p[1] for p in num_bbox if len(p) >= 2]) / len([p for p in num_bbox if len(p) >= 2])
                            
                            # 거리 계산 (픽셀 단위)
                            distance = ((beacon_center_x - num_center_x)**2 + (beacon_center_y - num_center_y)**2)**0.5
                            # 이미지 크기의 20% 이내면 근접한 것으로 간주
                            max_distance = min(img_width, img_height) * 0.2
                            
                            if distance <= max_distance:
                                # "비콘"과 숫자를 조합하여 패턴 매칭 시도
                                combined_text = f"{beacon_text} {num_text}"
                                # 간단한 패턴으로 먼저 확인
                                simple_match = re.search(r'비[콘콕콘]\s+([0-9OoIl|]{4})', combined_text, re.IGNORECASE)
                                if simple_match:
                                    value_str = simple_match.group(1)
                                    result = normalize_four_digit_minor(value_str)
                                    if result and result != "0000":
                                        return result
        
        beacon_patterns_four_digit = [
            # 정확한 '비콘' 패턴 (직접 인접) - 최우선
            # 3자리 또는 4자리 숫자 모두 처리 (3자리는 4자리로 패딩)
            # 한글 '비콘' 인식 실패를 대비해 더 유연한 패턴 추가
            r'비콘\s+([0-9OoIl|]{3,4})',  # 비콘 307 또는 비콘 0307 (가장 일반적인 형식)
            r'비콘\s*[:：]?\s*([0-9OoIl|]{3,4})',  # 비콘: 307 또는 비콘: 0307
            r'비콘\s*[:\s]*([0-9OoIl|]{3,4})',  # 비콘: 307 또는 비콘 307 (더 유연한 공백 처리)
            r'비콘([0-9OoIl|]{3,4})',  # 비콘307 또는 비콘0307 (공백 없음)
            r'([0-9OoIl|]{3,4})\s*비콘',  # 307 비콘 또는 0307 비콘 (순서 반대)
            # '비콘' 앞에 단어가 있는 경우 (예: "공종 비콘 307" 또는 "공종 비콘 0307") - 중요!
            r'\S+\s+비콘\s+([0-9OoIl|]{3,4})',  # 공종 비콘 307 또는 공종 비콘 0307
            r'\S+\s+비콘\s*[:：]?\s*([0-9OoIl|]{3,4})',  # 공종 비콘: 307 또는 공종 비콘: 0307
            r'\S+\s+비콘\s*[:\s]*([0-9OoIl|]{3,4})',  # 공종 비콘: 307 (더 유연한 공백 처리)
            # '비콘'과 숫자 사이에 다른 단어가 있는 경우 (예: "비콘 공종 307")
            r'비콘\s+\S+\s+([0-9OoIl|]{3,4})',  # 비콘 공종 307 또는 비콘 공종 0307
            # OCR 오류 패턴 (비콕 등) - 한글 인식 실패 대비
            r'비[콘콕]\s+([0-9OoIl|]{3,4})',  # 비콘 307 또는 비콕 307
            r'비[콘콕]\s*[:：]?\s*([0-9OoIl|]{3,4})',  # 비콘: 307 또는 비콕: 307
            r'비[콘콕]\s*[:\s]*([0-9OoIl|]{3,4})',  # 비콘: 307 (더 유연한 공백 처리)
            r'비[콘콕]([0-9OoIl|]{3,4})',  # 비콘307 또는 비콕307
            r'([0-9OoIl|]{3,4})\s*비[콘콕]',  # 307 비콘 또는 307 비콕
            r'\S+\s+비[콘콕]\s+([0-9OoIl|]{3,4})',  # 공종 비콘 307 (OCR 오류 포함)
            r'비[콘콕]\s+\S+\s+([0-9OoIl|]{3,4})',  # 비콘 공종 307 (OCR 오류 포함)
            # 더 유연한 패턴 (한 글자 오류 허용, 한글 인식 실패 대비)
            r'비[콘콕콘]\s+([0-9OoIl|]{3,4})',  # 비콘 307 (다양한 변형)
            r'비[콘콕콘]\s*[:：]?\s*([0-9OoIl|]{3,4})',  # 비콘: 307
            r'비[콘콕콘]\s*[:\s]*([0-9OoIl|]{3,4})',  # 비콘: 307 (더 유연한 공백 처리)
            r'비[콘콕콘]([0-9OoIl|]{3,4})',  # 비콘307
            r'\S+\s+비[콘콕콘]\s+([0-9OoIl|]{3,4})',  # 공종 비콘 307 (유연한 변형)
            r'비[콘콕콘]\s+\S+\s+([0-9OoIl|]{3,4})',  # 비콘 공종 307 (유연한 변형)
            # 한글 '비'만 인식된 경우 (콘 인식 실패)
            r'비\s+([0-9OoIl|]{3,4})',  # 비 307
            r'비\s*[:：]?\s*([0-9OoIl|]{3,4})',  # 비: 307
            r'\S+\s+비\s+([0-9OoIl|]{3,4})',  # 공종 비 307
            # 한글 '콘'만 인식된 경우 (비 인식 실패)
            r'콘\s+([0-9OoIl|]{3,4})',  # 콘 307
            r'콘\s*[:：]?\s*([0-9OoIl|]{3,4})',  # 콘: 307
            r'\S+\s+콘\s+([0-9OoIl|]{3,4})',  # 공종 콘 307
        ]
        
        # 좌측 하단 흰색 영역에서 먼저 검색 (최우선순위)
        if bottom_left_text:
            # 우선순위 1: 좌측 하단에서 숫자만 직접 찾기 (한글 '비콘' 인식 실패 대비)
            # 좌측 하단 영역에 3-4자리 숫자가 있고, "공종", "위치", "일자" 같은 키워드가 있으면
            # 그 근처의 숫자를 Minor로 사용 (흰색 박스 영역)
            # "공종" 다음에 나오는 숫자를 우선적으로 찾기
            gongjong_match = re.search(r'공종', bottom_left_text)
            if gongjong_match:
                # "공종" 다음에 나오는 3-4자리 숫자 찾기
                after_gongjong = bottom_left_text[gongjong_match.end():]
                number_match = re.search(r'([0-9OoIl|]{3,4})', after_gongjong)
                if number_match:
                    value_str = number_match.group(1)
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
            
            # "공종"이 없으면 좌측 하단의 첫 번째 3-4자리 숫자 사용 (백업)
            all_numbers = re.findall(r'([0-9OoIl|]{3,4})', bottom_left_text)
            if all_numbers:
                # 4자리 숫자를 우선, 없으면 3자리 숫자 사용
                four_digit_numbers = [n for n in all_numbers if len(re.sub(r'[^0-9]', '', n)) >= 4]
                if four_digit_numbers:
                    value_str = four_digit_numbers[0]
                else:
                    value_str = all_numbers[0]
                result = normalize_four_digit_minor(value_str)
                if result and result != "0000":
                    return result
            
            # 우선순위 2: 좌측 하단 흰색 영역에서 "비콘" 패턴 검색
            for pattern in beacon_patterns_four_digit:
                matches = re.findall(pattern, bottom_left_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
            
            # 우선순위 3: 좌측 하단 영역에서 "비콘"과 숫자가 분리되어 있는 경우 직접 찾기
            # 한글 '비콘'의 다양한 변형 패턴 시도
            beacon_patterns_variants = [
                r'비[콘콕콘]',  # 비콘, 비콕, 비콘
                r'[비빕]\s*[콘콕]',  # 비 콘, 빕 콕 등
                r'[비빕][콘콕]',  # 비콘, 빕콕 등
            ]
            
            for beacon_pattern in beacon_patterns_variants:
                beacon_match = re.search(beacon_pattern, bottom_left_text, re.IGNORECASE)
                if beacon_match:
                    # "비콘" 다음에 나오는 3자리 또는 4자리 숫자 찾기
                    after_beacon = bottom_left_text[beacon_match.end():]
                    number_match = re.search(r'([0-9OoIl|]{3,4})', after_beacon)
                    if number_match:
                        value_str = number_match.group(1)
                        result = normalize_four_digit_minor(value_str)
                        if result and result != "0000":
                            return result
                    
                    # "비콘" 앞에 있는 3자리 또는 4자리 숫자 찾기 (순서 반대)
                    before_beacon = bottom_left_text[:beacon_match.start()]
                    number_match = re.search(r'([0-9OoIl|]{3,4})\s*$', before_beacon)
                    if number_match:
                        value_str = number_match.group(1)
                        result = normalize_four_digit_minor(value_str)
                        if result and result != "0000":
                            return result
        
        # 좌측 하단 텍스트가 없는 경우 전체 이미지에서 검색 (백업)
        if not bottom_left_text:
            # 전체 텍스트 준비
            full_text = ' '.join([result[1] for result in filtered_results])
            
            # 전체 텍스트에서 "공종" 다음 숫자 검색
            gongjong_match = re.search(r'공종', full_text)
            if gongjong_match:
                after_gongjong = full_text[gongjong_match.end():]
                number_match = re.search(r'([0-9OoIl|]{3,4})', after_gongjong)
                if number_match:
                    value_str = number_match.group(1)
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
            
            # 전체 텍스트에서 "비콘" 패턴 검색
            for pattern in beacon_patterns_four_digit:
                matches = re.findall(pattern, full_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
            
            # 전체 텍스트에서 flexible 패턴 검색
            for pattern in beacon_patterns_flexible:
                matches = re.findall(pattern, full_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        # 비콘 패턴 (4자리 미만도 시도 - 4자리로 패딩)
        beacon_patterns_flexible = [
            # 정확한 '비콘' 패턴 (직접 인접) - 최우선
            r'비콘\s+([0-9OoIl|]+)',  # 비콘 001 (가장 일반적인 형식)
            r'비콘\s*[:：]?\s*([0-9OoIl|]+)',  # 비콘: 001
            r'비콘([0-9OoIl|]+)',  # 비콘001
            # '비콘' 앞에 단어가 있는 경우 (예: "공종 비콘 0281") - 중요!
            r'\S+\s+비콘\s+([0-9OoIl|]+)',  # 공종 비콘 0281 또는 XXX 비콘 0281
            r'\S+\s+비콘\s*[:：]?\s*([0-9OoIl|]+)',  # 공종 비콘: 0281
            # '비콘'과 숫자 사이에 다른 단어가 있는 경우 (예: "비콘 공종 0293")
            r'비콘\s+\S+\s+([0-9OoIl|]+)',  # 비콘 공종 0293 또는 비콘 XXX 0293
            # OCR 오류 패턴
            r'비[콘콕]\s+([0-9OoIl|]+)',  # 비콘 001 또는 비콕 001
            r'비[콘콕]\s*[:：]?\s*([0-9OoIl|]+)',  # 비콘: 001 또는 비콕: 001
            r'비[콘콕]([0-9OoIl|]+)',  # 비콘001 또는 비콕001
            r'\S+\s+비[콘콕]\s+([0-9OoIl|]+)',  # 공종 비콘 0281 (OCR 오류 포함)
            r'비[콘콕]\s+\S+\s+([0-9OoIl|]+)',  # 비콘 공종 0293 (OCR 오류 포함)
            # 더 유연한 패턴
            r'비[콘콕콘]\s+([0-9OoIl|]+)',  # 비콘 001 (다양한 변형)
            r'비[콘콕콘]\s*[:：]?\s*([0-9OoIl|]+)',  # 비콘: 001
            r'비[콘콕콘]([0-9OoIl|]+)',  # 비콘001
            r'\S+\s+비[콘콕콘]\s+([0-9OoIl|]+)',  # 공종 비콘 0281 (유연한 변형)
            r'비[콘콕콘]\s+\S+\s+([0-9OoIl|]+)',  # 비콘 공종 0293 (유연한 변형)
        ]
        
        # 좌측 하단 흰색 영역에서 flexible 패턴 검색 (최우선순위)
        if bottom_left_text:
            for pattern in beacon_patterns_flexible:
                matches = re.findall(pattern, bottom_left_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        # ===== 우선순위 2: 좌측 하단에서 '설치' 옆에 숫자 패턴 =====
        if bottom_left_text:
            install_patterns = [
                r'설치\s*[:：]?\s*([0-9OoIl|]{3,4})',  # 설치: 307 또는 설치: 0307
                r'설치\s+([0-9OoIl|]{3,4})',  # 설치 307
                r'설치([0-9OoIl|]{3,4})',  # 설치307
                r'([0-9OoIl|]{3,4})\s*설치',  # 307 설치
            ]
            
            for pattern in install_patterns:
                matches = re.findall(pattern, bottom_left_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        # ===== 우선순위 3: 좌측 하단에서 'Minor' 영문 옆에 숫자 패턴 =====
        if bottom_left_text:
            minor_patterns = [
                r'(?:Minor|Mnor|Inor|minor|mnor|inor)\s*[:：]?\s*([0-9OoIl|]{3,4})',  # Minor: 307
                r'(?:Minor|Mnor|Inor|minor|mnor|inor)\s+([0-9OoIl|]{3,4})',  # Minor 307
                r'(?:Minor|Mnor|Inor|minor|mnor|inor)([0-9OoIl|]{3,4})',  # Minor307
            ]
            
            for pattern in minor_patterns:
                matches = re.findall(pattern, bottom_left_text, re.IGNORECASE)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        return None
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        return None

def print_progress_bar(current, total, bar_length=40):
    """프로그레스 바 출력"""
    percent = float(current) / total if total > 0 else 0
    hashes = '#' * int(round(percent * bar_length))
    spaces = ' ' * (bar_length - len(hashes))
    return f"[{hashes}{spaces}] {int(round(percent * 100))}%"

def format_time(seconds):
    """시간을 읽기 쉬운 형식으로 변환"""
    if seconds < 60:
        return f"{int(seconds)}초"
    elif seconds < 3600:
        return f"{int(seconds // 60)}분 {int(seconds % 60)}초"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}시간 {minutes}분"

def count_image_files(directory):
    """디렉토리의 이미지 파일 개수를 세는 함수"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    if not directory.exists():
        return 0
    return len([f for f in directory.rglob('*') 
                if f.is_file() and f.suffix in image_extensions])

def verify_file_location(file_path, current_minor_value):
    """
    파일이 올바른 위치에 있는지 확인하고, 파일명 규칙을 재검증합니다.
    파일명에서 추출한 Minor 값과 현재 위치가 일치하는지 확인.
    
    주의: 파일명에서 추출한 Minor 값이 5자리 이상이면 파일명 규칙 에러로 간주하여
    OCR로 처리해야 하므로 None을 반환합니다.
    """
    # 파일명에서 Minor 값 추출
    filename_minor = extract_minor_from_filename(file_path.name)
    if filename_minor:
        # 파일명에서 추출한 Minor 값이 5자리 이상이면 파일명 규칙 에러로 간주
        # 이 경우 OCR로 처리해야 하므로 None 반환
        if len(filename_minor) >= 5:
            return None  # OCR로 처리해야 함
        
        # 4자리 이하는 정상적인 Minor 값으로 간주
        expected_minor = f"{int(filename_minor):04d}"
        # 현재 위치와 일치하는지 확인
        if current_minor_value != expected_minor:
            return expected_minor  # 올바른 Minor 값 반환
    return None  # 위치가 올바르거나 파일명에서 추출 불가

def recheck_unknown_files():
    """
    [단계 2] Unknown 폴더의 이미지들을 OCR로 처리합니다.
    
    처리 순서:
    1. source와 output 파일 수 비교 (데이터 무결성 확인)
    2. output 폴더 전체 스캔하여 파일명 규칙 재검증 (Unknown 폴더 제외)
       - 파일명에서 5자리 이상 추출된 경우 Unknown으로 이동
       - 잘못된 위치에 있는 파일을 올바른 위치로 이동
    3. Unknown 폴더의 파일들 OCR 재검사
       - OCR로 Minor 값 추출 시도
       - 성공 시 Minor_XXXX 폴더로 이동
       - 실패 시 Unknown 폴더에 그대로 유지
    """
    # 시작 시간 기록 (가장 먼저 초기화)
    start_time = time.time()
    
    print("="*70)
    print("단계 2: Unknown 폴더 OCR 처리")
    print("="*70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. source와 output 파일 수 비교
    image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    
    source_count = count_image_files(SOURCE_DIR)
    output_count = count_image_files(OUTPUT_DIR)
    
    print("📊 파일 수 비교:")
    print(f"  source 폴더: {source_count}개 파일")
    print(f"  output 폴더: {output_count}개 파일")
    
    if source_count == 0:
        print("⚠ 경고: source 폴더에 파일이 없습니다.")
    
    if output_count == 0:
        print("⚠ 경고: output 폴더에 파일이 없습니다.")
        return
    
    if source_count != output_count:
        diff = abs(source_count - output_count)
        print(f"❌ 오류: 파일 수가 일치하지 않습니다. (차이: {diff}개)")
        print(f"  완료율: {output_count/source_count*100:.1f}%")
        print(f"  ⚠️  파일이 손실되었을 수 있습니다. 확인이 필요합니다.")
        # 파일 수가 다르면 계속 진행하되 경고 강화
    else:
        print(f"✅ 파일 수 일치: {source_count}개 (100%)")
    
    print()
    
    # 2. output 폴더 전체 스캔하여 파일명 규칙 재검증 (Unknown 폴더 제외)
    # Unknown 폴더의 파일들은 이미 파일명 규칙에 어긋난 파일들이므로 재검증하지 않음
    print("="*70)
    print("파일명 규칙 재검증 시작 (Unknown 폴더 제외)")
    print("="*70)
    
    all_output_files = []
    for folder in OUTPUT_DIR.iterdir():
        if folder.is_dir() and folder.name != 'Unknown':  # Unknown 폴더 제외
            for file_path in folder.iterdir():
                if file_path.is_file() and file_path.suffix in image_extensions:
                    # 현재 폴더명에서 Minor 값 추출
                    folder_name = folder.name
                    if folder_name.startswith('Minor_'):
                        current_minor = folder_name.replace('Minor_', '')
                    else:
                        current_minor = None
                    
                    all_output_files.append((file_path, current_minor))
    
    print(f"📁 총 {len(all_output_files)}개 파일을 검증합니다... (Unknown 폴더 제외)\n")
    
    moved_by_filename = 0
    moved_to_correct = []
    
    for file_path, current_minor in all_output_files:
        # 파일명 규칙 재검증
        correct_minor = verify_file_location(file_path, current_minor)
        
        # 파일명에서 직접 추출하여 5자리 이상인지 확인
        filename_minor = extract_minor_from_filename(file_path.name)
        if filename_minor and len(filename_minor) >= 5:
            # 파일명에서 추출한 Minor 값이 5자리 이상이면 파일명 규칙 에러
            # Unknown 폴더로 이동하여 OCR로 처리
            unknown_folder = OUTPUT_DIR / "Unknown"
            unknown_folder.mkdir(exist_ok=True)
            target_path = unknown_folder / file_path.name
            
            # 중복 파일 처리
            if target_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                counter = 1
                while target_path.exists():
                    new_name = f"{base_name}_dup{counter}{extension}"
                    target_path = unknown_folder / new_name
                    counter += 1
            
            # 파일 이동 전 파일 존재 확인
            if not file_path.exists():
                print(f"\n⚠ 경고: 파일이 존재하지 않습니다: {file_path.name}")
                continue
            
            shutil.move(str(file_path), str(target_path))
            
            # 파일 이동 후 확인
            if not target_path.exists():
                print(f"\n❌ 오류: 파일 이동 실패: {file_path.name} → {target_path}")
                continue
            
            moved_by_filename += 1
            moved_to_correct.append((file_path.name, current_minor, 'Unknown'))
        
        elif correct_minor:
            # 올바른 폴더로 이동
            target_folder = OUTPUT_DIR / f"Minor_{correct_minor}"
            target_folder.mkdir(exist_ok=True)
            target_path = target_folder / file_path.name
            
            # 중복 파일 처리
            if target_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                counter = 1
                while target_path.exists():
                    new_name = f"{base_name}_dup{counter}{extension}"
                    target_path = target_folder / new_name
                    counter += 1
            
            # 파일 이동 전 파일 존재 확인
            if not file_path.exists():
                print(f"\n⚠ 경고: 파일이 존재하지 않습니다: {file_path.name}")
                continue
            
            shutil.move(str(file_path), str(target_path))
            
            # 파일 이동 후 확인
            if not target_path.exists():
                print(f"\n❌ 오류: 파일 이동 실패: {file_path.name} → {target_path}")
                continue
            
            moved_by_filename += 1
            moved_to_correct.append((file_path.name, current_minor, correct_minor))
    
    if moved_by_filename > 0:
        print(f"\n✅ 파일명 규칙에 따라 {moved_by_filename}개 파일 이동:")
        for fname, old_minor, new_minor in moved_to_correct[:10]:
            print(f"  {fname}: Minor_{old_minor} → Minor_{new_minor}")
        if len(moved_to_correct) > 10:
            print(f"  ... 외 {len(moved_to_correct) - 10}개")
        
        # 파일 이동 후 파일 수 재검증
        output_count_after = count_image_files(OUTPUT_DIR)
        print(f"\n📊 파일 이동 후 파일 수 검증:")
        print(f"  source 폴더: {source_count}개")
        print(f"  output 폴더: {output_count_after}개")
        if source_count != output_count_after:
            diff_after = abs(source_count - output_count_after)
            print(f"  ❌ 오류: 파일 이동 후 파일 수가 일치하지 않습니다! (차이: {diff_after}개)")
            print(f"  ⚠️  파일이 손실되었을 수 있습니다. 확인이 필요합니다.")
        else:
            print(f"  ✅ 파일 이동 후 파일 수 일치: {source_count}개")
    else:
        print("✅ 모든 파일이 올바른 위치에 있습니다.")
    
    print()
    
    # 3. Unknown 폴더의 파일들 OCR 재검사
    # Unknown 폴더의 파일들은 이미 파일명 규칙에 어긋난 파일들이므로
    # 파일명 규칙 재검증 없이 바로 OCR로 처리
    print("="*70)
    print("Unknown 폴더 OCR 재검사 시작")
    print("="*70)
    print("ℹ️  Unknown 폴더의 파일들은 파일명 규칙에 어긋난 파일들입니다.")
    print("    파일명 규칙 재검증 없이 바로 OCR로 처리합니다.\n")
    
    if not UNKNOWN_DIR.exists():
        print("✅ Unknown 폴더가 존재하지 않습니다.")
        return
    
    unknown_files = sorted([f for f in UNKNOWN_DIR.iterdir() 
                           if f.is_file() and f.suffix in image_extensions])
    
    if not unknown_files:
        print("✅ Unknown 폴더에 재검사할 이미지가 없습니다.")
        return
    
    total_unknown_files = len(unknown_files)
    print(f"📁 총 {total_unknown_files}개 파일을 OCR로 처리합니다...\n")
    
    moved_by_ocr = 0
    still_unknown = []
    minor_counts = {}
    ocr_start_time = time.time()
    
    # 통계 출력을 위한 변수
    stats_update_interval = 3  # 3개 파일마다 통계 업데이트
    
    for idx, file_path in enumerate(unknown_files, 1):
        file_start_time = time.time()
        
        # 진행률 표시
        progress_bar = print_progress_bar(idx, total_unknown_files)
        elapsed_time = time.time() - ocr_start_time
        avg_time_per_file = elapsed_time / idx if idx > 0 else 0
        remaining_files = total_unknown_files - idx
        estimated_remaining_time = avg_time_per_file * remaining_files
        
        # 통계 정보 출력
        if idx % stats_update_interval == 0 or idx == total_unknown_files:
            print(f"\r{progress_bar} [{idx}/{total_unknown_files}] "
                  f"재검사 중: {file_path.name[:50]:<50} "
                  f"| 경과: {format_time(elapsed_time)} "
                  f"| 예상 남은 시간: {format_time(estimated_remaining_time)}", end="")
        
        # Minor 값 추출
        minor_value = extract_minor_value(file_path)
        
        if minor_value:
            # Minor 값을 확실히 4자리로 보장
            try:
                minor_num = int(minor_value)
                minor_value = f"{minor_num:04d}"  # 4자리로 패딩
            except (ValueError, TypeError):
                print(f"\n⚠ 경고: Minor 값이 숫자가 아닙니다: {minor_value}")
                still_unknown.append(file_path.name)
                continue
            
            # Minor 값으로 폴더 생성 (4자리 형식: Minor_0001)
            target_folder = OUTPUT_DIR / f"Minor_{minor_value}"
            target_folder.mkdir(exist_ok=True)
            
            # 파일 이동 (복사 후 원본 삭제)
            target_path = target_folder / file_path.name
            
            # 같은 이름의 파일이 이미 존재하는지 확인
            if target_path.exists():
                # 파일명에 번호 추가
                base_name = file_path.stem
                extension = file_path.suffix
                counter = 1
                while target_path.exists():
                    new_name = f"{base_name}_dup{counter}{extension}"
                    target_path = target_folder / new_name
                    counter += 1
            
            # 파일 이동 전 파일 존재 확인
            if not file_path.exists():
                print(f"\n⚠ 경고: 파일이 존재하지 않습니다: {file_path.name}")
                still_unknown.append(file_path.name)
                continue
            
            shutil.move(str(file_path), str(target_path))
            
            # 파일 이동 후 확인
            if not target_path.exists():
                print(f"\n❌ 오류: 파일 이동 실패: {file_path.name} → {target_path}")
                still_unknown.append(file_path.name)
                continue
            
            # 통계
            if minor_value not in minor_counts:
                minor_counts[minor_value] = 0
            minor_counts[minor_value] += 1
            
            moved_by_ocr += 1
            
            # 상세 정보 출력
            if idx % stats_update_interval == 0 or idx == total_unknown_files:
                file_time = time.time() - file_start_time
                print(f"\r{progress_bar} [{idx}/{total_unknown_files}] "
                      f"✓ {file_path.name[:40]:<40} → Minor_{minor_value:<15} "
                      f"({file_time:.1f}초)", end="" if idx < total_unknown_files else "\n")
        else:
            # 여전히 Minor 값을 찾지 못한 경우
            still_unknown.append(file_path.name)
            
            if idx % stats_update_interval == 0 or idx == total_unknown_files:
                file_time = time.time() - file_start_time
                print(f"\r{progress_bar} [{idx}/{total_unknown_files}] "
                      f"⚠ {file_path.name[:40]:<40} → Unknown (유지) "
                      f"({file_time:.1f}초)", end="" if idx < total_unknown_files else "\n")
    
    # OCR 재검사 결과 출력
    ocr_total_time = time.time() - ocr_start_time
    print("\n" + "="*70)
    print("Unknown 폴더 재검사 완료")
    print("="*70)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"OCR 재검사 소요 시간: {format_time(ocr_total_time)}")
    if moved_by_ocr > 0:
        print(f"평균 OCR 처리 속도: {ocr_total_time/moved_by_ocr:.2f}초/파일")
    
    # 최종 결과 출력
    total_time = time.time() - start_time
    print("\n" + "="*70)
    print("단계 2: Unknown 폴더 OCR 처리 완료")
    print("="*70)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {format_time(total_time)}")
    
    print(f"\n📊 처리 결과:")
    print(f"  ✓ 파일명 규칙 재검증 이동: {moved_by_filename}개 파일")
    print(f"  ✓ OCR로 인식 성공: {moved_by_ocr}개 파일 → Minor_XXXX 폴더")
    print(f"  ⚠ OCR 인식 실패: {len(still_unknown)}개 파일 → Unknown 폴더 유지")
    
    if minor_counts:
        print(f"\n📁 OCR로 이동된 파일 분류 ({len(minor_counts)}개 폴더):")
        for minor_value in sorted(minor_counts.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            folder_name = f"Minor_{minor_value}"
            print(f"  {folder_name}: {minor_counts[minor_value]}개 파일")
    
    if still_unknown:
        print(f"\n⚠ 여전히 Minor 값을 찾지 못한 파일들 ({len(still_unknown)}개):")
        for fname in still_unknown[:10]:  # 처음 10개만 표시
            print(f"  - {fname}")
        if len(still_unknown) > 10:
            print(f"  ... 외 {len(still_unknown) - 10}개")
    
    # 최종 파일 수 검증 (강화)
    final_output_count = count_image_files(OUTPUT_DIR)
    print(f"\n" + "="*70)
    print("최종 파일 수 검증")
    print("="*70)
    print(f"  source 폴더: {source_count}개")
    print(f"  output 폴더: {final_output_count}개")
    if source_count == final_output_count:
        print(f"  ✅ 파일 수 일치: {source_count}개 (100%)")
    else:
        diff_final = abs(source_count - final_output_count)
        print(f"  ❌ 오류: 파일 수가 일치하지 않습니다! (차이: {diff_final}개)")
        print(f"  완료율: {final_output_count/source_count*100:.1f}%")
        print(f"  ⚠️  파일이 손실되었을 수 있습니다. 확인이 필요합니다.")
    
    print("\n" + "="*70)
    print("다음 단계: check_folder_structure.py 실행하여 결과 확인")
    print("="*70)

if __name__ == "__main__":
    recheck_unknown_files()

