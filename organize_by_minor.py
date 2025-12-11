#!/usr/bin/env python3
"""
이미지에서 Minor 값을 추출하여 output 폴더에 재구조화하는 스크립트

단계 1: 이미지 분류
- source 폴더의 이미지들을 OCR로 분석하여 Minor 값 추출
- Minor 값별로 output 폴더에 분류
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
    elif 'cv2' in str(e):
        print("Warning: opencv-python이 설치되지 않았습니다. 이미지 전처리 기능이 제한됩니다.")
        print("설치: pip3 install opencv-python")
        USE_IMAGE_PREPROCESSING = False
    else:
        USE_IMAGE_PREPROCESSING = False
    if not USE_EASYOCR:
        exit(1)

SOURCE_DIR = Path("source")
OUTPUT_DIR = Path("output")

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
    
    처리 내용:
    1. 그레이스케일 변환
    2. 대비 향상 (CLAHE)
    3. 노이즈 제거
    4. 이진화 (OTSU)
    5. 모폴로지 연산으로 텍스트 선명화
    """
    if not USE_IMAGE_PREPROCESSING:
        return str(image_path)
    
    try:
        # 이미지 읽기
        img = cv2.imread(str(image_path))
        if img is None:
            return str(image_path)
        
        # 그레이스케일 변환
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)로 대비 향상
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 가우시안 블러로 노이즈 제거
        denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        # OTSU 이진화
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 모폴로지 연산으로 텍스트 선명화 (작은 노이즈 제거)
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 임시 파일로 저장
        temp_path = image_path.parent / f"_temp_{image_path.name}"
        cv2.imwrite(str(temp_path), processed)
        
        return str(temp_path)
    except Exception as e:
        # 전처리 실패시 원본 이미지 사용
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
          예: "비콘 0019" -> "0019", "비콘: 0019" -> "0019"
       2-2. '설치' 옆에 숫자 4자리
          예: "설치 0019" -> "0019", "설치: 0019" -> "0019"
       2-3. 'Minor' 영문 옆에 숫자 4자리
          예: "Minor: 0019" -> "0019", "Minor 0019" -> "0019"
    
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
            # 파일명에서 추출한 Minor 값이 5자리 이상이면 파일명 규칙이 이상한 것으로 간주
            # 이 경우 OCR로 처리해야 함
            if len(filename_minor) >= 5:
                # 5자리 이상이면 None을 반환하여 OCR로 처리
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
        results = reader.readtext(
            processed_image_path,
            detail=1,
            paragraph=False,
            text_threshold=0.5,  # 더 낮춰서 더 많은 텍스트 감지 (특히 숫자)
            contrast_ths=0.05,   # 대비가 낮은 텍스트도 감지 (더 낮게)
            adjust_contrast=0.3, # 대비 자동 조정 (더 강하게)
            width_ths=0.4,      # 텍스트 너비 임계값 (더 낮게)
            height_ths=0.4,     # 텍스트 높이 임계값 (더 낮게)
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
                if confidence >= 0.2:  # 신뢰도 20% 이상 사용 (더 낮게 설정하여 숫자도 포함)
                    filtered_results.append(result)
        
        # 좌측 하단 영역 정의 (이미지의 하단 30%, 좌측 60% - 박스 영역에 맞게 더 넓게 조정)
        if img_width > 0 and img_height > 0 and filtered_results:
            bottom_threshold = img_height * 0.7  # 하단 30% (y 좌표가 큰 값이 하단)
            left_threshold = img_width * 0.6  # 좌측 60% (더 넓게)
            
            # 좌측 하단 영역의 텍스트 추출
            bottom_left_texts = []
            for result in filtered_results:
                if len(result) >= 2:
                    bbox = result[0]
                    text = result[1]
                    if bbox and len(bbox) >= 4:
                        # 바운딩 박스의 좌측 하단 점 계산
                        # 이미지 좌표계: (0,0)이 좌측 상단, y가 아래로 증가
                        min_x = min([p[0] for p in bbox if len(p) >= 2])
                        max_x = max([p[0] for p in bbox if len(p) >= 2])
                        max_y_point = max([p[1] for p in bbox if len(p) >= 2])
                        # 바운딩 박스의 중심점도 계산 (더 정확한 위치 판단)
                        center_x = (min_x + max_x) / 2
                        
                        # 좌측 하단 영역에 있는지 확인 (y가 큰 값이 하단, x가 작은 값이 좌측)
                        # 중심점이 좌측 영역에 있거나, 바운딩 박스가 좌측 영역과 겹치는 경우 포함
                        if max_y_point >= bottom_threshold and (center_x <= left_threshold or min_x <= left_threshold):
                            bottom_left_texts.append((result, max_y_point, min_x))  # (result, y, x) - 정렬용
            
            # 좌측 하단 영역의 텍스트를 y 좌표(하단 우선), x 좌표(좌측 우선) 순으로 정렬
            bottom_left_texts.sort(key=lambda x: (-x[1], x[2]))  # y는 내림차순(하단 우선), x는 오름차순(좌측 우선)
            # 텍스트를 공백으로 합치되, 좌측 하단 박스의 텍스트들이 함께 인식되도록
            # "비콘"과 숫자가 분리되어 인식될 경우를 대비해 더 가까운 텍스트들을 우선적으로 합침
            bottom_left_text_parts = []
            for item in bottom_left_texts:
                text = item[0][1]
                bottom_left_text_parts.append(text)
            bottom_left_text = ' '.join(bottom_left_text_parts)
            
            # 추가: "비콘" 텍스트와 4자리 숫자가 근접하게 있는 경우를 찾아서 직접 매칭
            # 좌측 하단 영역에서 "비콘"과 숫자를 찾아서 조합
            beacon_texts = []
            number_texts = []
            for item in bottom_left_texts:
                text = item[0][1]
                bbox = item[0][0]
                # "비콘" 패턴 찾기
                if re.search(r'비[콘콕콘]', text, re.IGNORECASE):
                    beacon_texts.append((item, text, bbox))
                # 4자리 숫자 패턴 찾기
                if re.search(r'[0-9OoIl|]{4}', text):
                    number_texts.append((item, text, bbox))
            
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
                                for pattern in beacon_patterns_four_digit:
                                    matches = re.findall(pattern, combined_text)
                                    if matches:
                                        value_str = matches[0]
                                        result = normalize_four_digit_minor(value_str)
                                        if result and result != "0000":
                                            return result
        else:
            bottom_left_text = ""
        
        # 신뢰도 순으로 정렬 (높은 것부터)
        filtered_results.sort(key=lambda x: x[2] if len(x) >= 3 else 0, reverse=True)
        
        # 모든 텍스트를 하나의 문자열로 합치기 (신뢰도 높은 순서)
        full_text = ' '.join([result[1] for result in filtered_results])
        
        # 신뢰도가 높은 텍스트만 별도로 추출
        high_confidence_text = ' '.join([result[1] for result in filtered_results if len(result) >= 3 and result[2] >= 0.5])
        
        # 검색할 텍스트 목록 (좌측 하단 영역 우선, 그 다음 신뢰도 높은 텍스트, 마지막 전체 텍스트)
        search_texts = []
        if bottom_left_text:
            search_texts.append(bottom_left_text)  # 좌측 하단 영역 우선
        if high_confidence_text:
            search_texts.append(high_confidence_text)
        search_texts.append(full_text)  # 전체 텍스트도 검색
        
        # ===== 우선순위 1: '비콘' 옆에 숫자 4자리 패턴 =====
        # 다양한 OCR 오류 패턴 고려 (비콘, 비콕, 비콘, 비콕 등)
        # "공종 비콘 0293" 같은 형식도 인식하도록 유연한 패턴 추가
        beacon_patterns_four_digit = [
            # 정확한 '비콘' 패턴 (직접 인접) - 최우선
            r'비콘\s+([0-9OoIl|]{4})',  # 비콘 0019 (가장 일반적인 형식)
            r'비콘\s*[:：]?\s*([0-9OoIl|]{4})',  # 비콘: 0019
            r'비콘\s*[:\s]*([0-9OoIl|]{4})',  # 비콘: 0019 또는 비콘 0019 (더 유연한 공백 처리)
            r'비콘([0-9OoIl|]{4})',  # 비콘0019 (공백 없음)
            r'([0-9OoIl|]{4})\s*비콘',  # 0019 비콘 (순서 반대)
            # '비콘' 앞에 단어가 있는 경우 (예: "공종 비콘 0281") - 중요!
            r'\S+\s+비콘\s+([0-9OoIl|]{4})',  # 공종 비콘 0281 또는 XXX 비콘 0281
            r'\S+\s+비콘\s*[:：]?\s*([0-9OoIl|]{4})',  # 공종 비콘: 0281
            r'\S+\s+비콘\s*[:\s]*([0-9OoIl|]{4})',  # 공종 비콘: 0281 (더 유연한 공백 처리)
            # '비콘'과 숫자 사이에 다른 단어가 있는 경우 (예: "비콘 공종 0293")
            r'비콘\s+\S+\s+([0-9OoIl|]{4})',  # 비콘 공종 0293 또는 비콘 XXX 0293
            # OCR 오류 패턴 (비콕 등)
            r'비[콘콕]\s+([0-9OoIl|]{4})',  # 비콘 0019 또는 비콕 0019
            r'비[콘콕]\s*[:：]?\s*([0-9OoIl|]{4})',  # 비콘: 0019 또는 비콕: 0019
            r'비[콘콕]\s*[:\s]*([0-9OoIl|]{4})',  # 비콘: 0019 (더 유연한 공백 처리)
            r'비[콘콕]([0-9OoIl|]{4})',  # 비콘0019 또는 비콕0019
            r'([0-9OoIl|]{4})\s*비[콘콕]',  # 0019 비콘 또는 0019 비콕
            r'\S+\s+비[콘콕]\s+([0-9OoIl|]{4})',  # 공종 비콘 0281 (OCR 오류 포함)
            r'비[콘콕]\s+\S+\s+([0-9OoIl|]{4})',  # 비콘 공종 0293 (OCR 오류 포함)
            # 더 유연한 패턴 (한 글자 오류 허용)
            r'비[콘콕콘]\s+([0-9OoIl|]{4})',  # 비콘 0019 (다양한 변형)
            r'비[콘콕콘]\s*[:：]?\s*([0-9OoIl|]{4})',  # 비콘: 0019
            r'비[콘콕콘]\s*[:\s]*([0-9OoIl|]{4})',  # 비콘: 0019 (더 유연한 공백 처리)
            r'비[콘콕콘]([0-9OoIl|]{4})',  # 비콘0019
            r'\S+\s+비[콘콕콘]\s+([0-9OoIl|]{4})',  # 공종 비콘 0281 (유연한 변형)
            r'비[콘콕콘]\s+\S+\s+([0-9OoIl|]{4})',  # 비콘 공종 0293 (유연한 변형)
        ]
        
        # 좌측 하단 영역에서 먼저 검색 (우선순위 최고)
        if bottom_left_text:
            # 좌측 하단 영역 텍스트를 디버깅용으로 출력 (선택적)
            # print(f"  [DEBUG] 좌측 하단 텍스트: {bottom_left_text[:100]}")
            
            # 4자리 숫자 패턴 우선 검색
            for pattern in beacon_patterns_four_digit:
                matches = re.findall(pattern, bottom_left_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
            
            # 좌측 하단 영역에서 "비콘"과 숫자가 분리되어 있는 경우 직접 찾기
            # "비콘" 텍스트와 4자리 숫자를 각각 찾아서 조합
            beacon_match = re.search(r'비[콘콕콘]', bottom_left_text, re.IGNORECASE)
            if beacon_match:
                # "비콘" 다음에 나오는 4자리 숫자 찾기
                after_beacon = bottom_left_text[beacon_match.end():]
                number_match = re.search(r'([0-9OoIl|]{4})', after_beacon)
                if number_match:
                    value_str = number_match.group(1)
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
                
                # "비콘" 앞에 있는 4자리 숫자 찾기 (순서 반대)
                before_beacon = bottom_left_text[:beacon_match.start()]
                number_match = re.search(r'([0-9OoIl|]{4})\s*$', before_beacon)
                if number_match:
                    value_str = number_match.group(1)
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        # 전체 텍스트에서도 검색
        for search_text in search_texts:
            if search_text == bottom_left_text:
                continue  # 이미 검색했으므로 스킵
            for pattern in beacon_patterns_four_digit:
                matches = re.findall(pattern, search_text)
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
        
        # 좌측 하단 영역에서 먼저 검색 (우선순위 최고)
        if bottom_left_text:
            for pattern in beacon_patterns_flexible:
                matches = re.findall(pattern, bottom_left_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        # 전체 텍스트에서도 검색
        for search_text in search_texts:
            if search_text == bottom_left_text:
                continue  # 이미 검색했으므로 스킵
            for pattern in beacon_patterns_flexible:
                matches = re.findall(pattern, search_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        # ===== 우선순위 2: '설치' 옆에 숫자 4자리 패턴 =====
        install_patterns_four_digit = [
            r'설치\s*[:：]?\s*([0-9OoIl|]{4})',  # 설치: 0019 (4자리)
            r'설치\s+([0-9OoIl|]{4})',  # 설치 0019
            r'설치([0-9OoIl|]{4})',  # 설치0019 (공백 없음)
            r'([0-9OoIl|]{4})\s*설치',  # 0019 설치 (순서 반대)
        ]
        
        for search_text in search_texts:
            for pattern in install_patterns_four_digit:
                matches = re.findall(pattern, search_text)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        # 설치 패턴 (4자리 미만도 시도 - 4자리로 패딩)
        install_patterns_flexible = [
            r'설치\s*(\d{1,3})(?=25\d{4,})',  # 설치10251104 (날짜 패턴)
            r'설치\s*(\d{1,3})(?=\d{6})',    # 설치 + 숫자 + 6자리 이상
            r'설치\s*[:：]?\s*(\d{1,4})',    # 설치: 10 또는 설치: 0019
            r'설치\s*[:：]?\s*([0-9OoIl|]{1,4})',  # 설치: OO19 (OCR 오류 포함)
            r'설치\s+([0-9OoIl|]+)',  # 설치 001
            r'설치([0-9OoIl|]+)',  # 설치001
        ]
        
        for search_text in search_texts:
            for pattern in install_patterns_flexible:
                matches = re.findall(pattern, search_text)
                if matches:
                    digit_str = matches[0]
                    result = normalize_four_digit_minor(digit_str)
                    if result and result != "0000":
                        return result
        
        # ===== 우선순위 3: 'Minor' 영문 옆에 숫자 4자리 패턴 =====
        minor_patterns_four_digit = [
            r'(?:Minor|Mnor|Inor|Mior|Mmor|M1nor|M|nor|minor|mnor|inor|mior|mmor|m1nor)\s*[:：]?\s*([0-9OoIl|]{4})',  # Minor: 0019 (4자리)
            r'(?:Minor|Mnor|Inor|minor|mnor|inor)\s+([0-9OoIl|]{4})',  # Minor 0019
            r'(?:Minor|Mnor|Inor|minor|mnor|inor)([0-9OoIl|]{4})',  # Minor0019 (공백 없음)
            r'([0-9OoIl|]{4})\s*(?:Minor|Mnor|Inor)',  # 0019 Minor (순서 반대)
        ]
        
        for search_text in search_texts:
            for pattern in minor_patterns_four_digit:
                matches = re.findall(pattern, search_text, re.IGNORECASE)
                if matches:
                    value_str = matches[0]
                    result = normalize_four_digit_minor(value_str)
                    if result and result != "0000":
                        return result
        
        # Minor 패턴 (4자리 미만도 시도 - 4자리로 패딩)
        minor_patterns_flexible = [
            r'(?:Minor|Mnor|Inor|Mior|Mmor|M1nor|minor|mnor|inor|mior|mmor|m1nor)\s*[:：]?\s*([0-9OoIl|]+)',  # Minor: 001
            r'(?:Minor|Mnor|Inor|minor|mnor|inor)\s+([0-9OoIl|]+)',  # Minor 001
            r'(?:Minor|Mnor|Inor|minor|mnor|inor)([0-9OoIl|]+)',  # Minor001 (공백 없음)
        ]
        
        for search_text in search_texts:
            for pattern in minor_patterns_flexible:
                matches = re.findall(pattern, search_text, re.IGNORECASE)
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
    percent = float(current) / total
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

def organize_files():
    """
    [단계 1] source 폴더의 이미지들을 파일명 규칙으로만 분류합니다.
    
    처리 순서:
    1. 파일명에서 Minor 값 추출 (OCR 없이, 빠른 처리)
    2. 파일명 추출 성공 → Minor_XXXX 폴더로 이동
    3. 파일명 추출 실패 또는 5자리 이상 → Unknown 폴더로 이동
    
    주의사항:
    - 이 단계에서는 OCR을 사용하지 않습니다 (단계 2에서 처리)
    - Unknown 폴더에 이미 있는 파일은 건너뜁니다
    """
    print("="*70)
    print("단계 1: 파일명 규칙으로 이미지 분류")
    print("="*70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 시작 시간 기록 (가장 먼저 초기화)
    start_time = time.time()
    
    # output 폴더 생성
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # source 폴더의 모든 이미지 파일 처리
    # Unknown 폴더에 이미 있는 파일은 건너뛰기 (무한 반복 방지)
    unknown_folder = OUTPUT_DIR / "Unknown"
    unknown_existing_files = set()
    if unknown_folder.exists():
        unknown_existing_files = {f.name for f in unknown_folder.iterdir() if f.is_file()}
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    image_files = sorted([f for f in SOURCE_DIR.iterdir() 
                         if f.suffix in image_extensions and f.name not in unknown_existing_files])
    
    if unknown_existing_files:
        print(f"ℹ️  Unknown 폴더에 이미 {len(unknown_existing_files)}개 파일이 있습니다. (건너뜀)")
    
    if not image_files:
        print("❌ 처리할 이미지 파일을 찾을 수 없습니다.")
        if unknown_existing_files:
            print("   (Unknown 폴더의 파일들은 별도로 OCR 처리가 필요합니다.)")
        return
    
    total_files = len(image_files)
    print(f"📁 총 {total_files}개 이미지 파일을 처리합니다...\n")
    
    processed = 0
    failed = []
    minor_counts = {}
    last_update_time = start_time
    
    # 통계 출력을 위한 변수
    stats_update_interval = 5  # 5개 파일마다 통계 업데이트
    
    # 파일명 규칙으로만 분류 (OCR 없이)
    print("📋 파일명 규칙으로 분류 중...")
    unknown_files = []
    
    for idx, file_path in enumerate(image_files, 1):
        file_start_time = time.time()
        
        # 진행률 표시
        progress_bar = print_progress_bar(idx, total_files)
        elapsed_time = time.time() - start_time
        avg_time_per_file = elapsed_time / idx if idx > 0 else 0
        remaining_files = total_files - idx
        estimated_remaining_time = avg_time_per_file * remaining_files
        
        # 통계 정보 출력 (매 N개마다 또는 마지막 파일일 때)
        if idx % stats_update_interval == 0 or idx == total_files:
            print(f"\r{progress_bar} [{idx}/{total_files}] "
                  f"파일명 분석 중: {file_path.name[:50]:<50} "
                  f"| 경과: {format_time(elapsed_time)} "
                  f"| 예상 남은 시간: {format_time(estimated_remaining_time)}", end="")
        
        # 파일명에서만 Minor 값 추출 (OCR 없이)
        filename_minor = extract_minor_from_filename(file_path.name)
        
        if filename_minor and len(filename_minor) < 5:
            # 파일명에서 추출 성공 (4자리 이하)
            try:
                minor_num = int(filename_minor)
                minor_value = f"{minor_num:04d}"
                
                # Minor 값으로 폴더 생성 (4자리 형식: Minor_0001)
                target_folder = OUTPUT_DIR / f"Minor_{minor_value}"
                target_folder.mkdir(exist_ok=True)
                
                # 파일 복사
                target_path = target_folder / file_path.name
                shutil.copy2(file_path, target_path)
                
                # 통계
                if minor_value not in minor_counts:
                    minor_counts[minor_value] = 0
                minor_counts[minor_value] += 1
                
                processed += 1
            except (ValueError, TypeError):
                # 숫자가 아닌 경우 Unknown으로
                unknown_files.append(file_path)
        else:
            # 파일명에서 추출 실패 또는 5자리 이상 -> Unknown으로
            unknown_files.append(file_path)
    
    print(f"\n✓ 파일명 분류 완료: {processed}개 성공, {len(unknown_files)}개 Unknown")
    
    # Unknown 파일들을 Unknown 폴더로 이동
    if unknown_files:
        print(f"\n📁 Unknown 폴더로 {len(unknown_files)}개 파일 이동 중...")
        unknown_folder = OUTPUT_DIR / "Unknown"
        unknown_folder.mkdir(exist_ok=True)
        
        for file_path in unknown_files:
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
            shutil.copy2(file_path, target_path)
        
        print(f"✓ Unknown 폴더로 이동 완료")
        print(f"  ℹ️  다음 단계(recheck_unknown.py)에서 OCR로 처리됩니다.")
    
    # 최종 결과 출력
    total_time = time.time() - start_time
    print("\n" + "="*70)
    print("단계 1: 파일명 규칙 분류 완료")
    print("="*70)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {format_time(total_time)}")
    if total_files > 0:
        print(f"평균 처리 속도: {total_time/total_files:.2f}초/파일")
    print(f"\n📊 처리 결과:")
    print(f"  ✓ 파일명 규칙 성공: {processed}개 파일 → Minor_XXXX 폴더")
    print(f"  ⚠ 파일명 규칙 실패: {len(unknown_files)}개 파일 → Unknown 폴더")
    
    if minor_counts:
        print(f"\n📁 Minor 값별 분류 ({len(minor_counts)}개 폴더):")
        # 4자리 숫자 형식으로 정렬
        for minor_value in sorted(minor_counts.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            folder_name = f"Minor_{minor_value}"
            print(f"  {folder_name}: {minor_counts[minor_value]}개 파일")
    
    if unknown_files:
        print(f"\n⚠ Unknown 폴더로 이동된 파일들 ({len(unknown_files)}개):")
        for fname in unknown_files[:10]:  # 처음 10개만 표시
            print(f"  - {fname.name}")
        if len(unknown_files) > 10:
            print(f"  ... 외 {len(unknown_files) - 10}개")
    
    print("\n" + "="*70)
    print("다음 단계: recheck_unknown.py 실행하여 Unknown 폴더 OCR 처리")
    print("="*70)

if __name__ == "__main__":
    organize_files()

