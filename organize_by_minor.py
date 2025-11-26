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
    2. 차순위: OCR에서 Minor 옆에 숫자 4자리를 그대로 문자형으로 사용
       예: "0019" -> "0019" (그대로 사용)
    3. 3순위: OCR에서 '설치' 텍스트 옆에 숫자 추출
    
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
            return f"{int(filename_minor):04d}"
        
        # 파일명에서 추출 실패시 OCR 수행
        # 이미지 전처리 적용
        processed_image_path = preprocess_image(image_path)
        
        # OCR 수행 (최적화된 파라미터 사용)
        # detail=1: 바운딩 박스와 신뢰도 정보 포함
        # text_threshold: 텍스트 감지 임계값 (높을수록 정확하지만 놓칠 수 있음)
        # contrast_ths: 대비 임계값
        results = reader.readtext(
            processed_image_path,
            detail=1,
            paragraph=False,
            text_threshold=0.6,  # 기본값 0.7보다 낮춰서 더 많은 텍스트 감지
            contrast_ths=0.1,   # 대비가 낮은 텍스트도 감지
            adjust_contrast=0.5, # 대비 자동 조정
            width_ths=0.5,      # 텍스트 너비 임계값
            height_ths=0.5,     # 텍스트 높이 임계값
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
        # 신뢰도가 높은 텍스트를 우선 사용
        filtered_results = []
        for result in results:
            if len(result) >= 3:  # (bbox, text, confidence) 형식
                confidence = result[2]
                if confidence >= 0.3:  # 신뢰도 30% 이상만 사용
                    filtered_results.append(result)
        
        # 신뢰도 순으로 정렬 (높은 것부터)
        filtered_results.sort(key=lambda x: x[2] if len(x) >= 3 else 0, reverse=True)
        
        # 모든 텍스트를 하나의 문자열로 합치기 (신뢰도 높은 순서)
        full_text = ' '.join([result[1] for result in filtered_results])
        
        # 신뢰도가 높은 텍스트만 별도로 추출 (Minor 패턴 우선 검색)
        high_confidence_text = ' '.join([result[1] for result in filtered_results if len(result) >= 3 and result[2] >= 0.5])
        
        # 2. 차순위: Minor 관련 패턴 찾기 (4자리 숫자를 그대로 사용)
        # 우선 신뢰도가 높은 텍스트에서 검색
        search_texts = [high_confidence_text] if high_confidence_text else [full_text]
        search_texts.append(full_text)  # 전체 텍스트도 검색
        
        # 정확히 4자리 숫자 패턴 (더 많은 변형 패턴 추가)
        patterns_four_digit = [
            r'(?:Minor|Mnor|Inor|Mior|Mmor|M1nor|M|nor|minor|mnor|inor|mior|mmor|m1nor)\s*[:：]?\s*([0-9OoIl|]{4})',  # Minor: 0019 (4자리, OCR 오류 패턴 포함)
            r'(?:Minor|Mnor|Inor|minor|mnor|inor)\s+([0-9OoIl|]{4})',  # Minor 0019
            r'(?:Minor|Mnor|Inor|minor|mnor|inor)([0-9OoIl|]{4})',  # Minor0019 (공백 없음)
            r'([0-9OoIl|]{4})\s*(?:Minor|Mnor|Inor)',  # 0019 Minor (순서 반대)
        ]
        
        for search_text in search_texts:
            for pattern in patterns_four_digit:
                matches = re.findall(pattern, search_text, re.IGNORECASE)
                if matches:
                    # 첫 번째 매치 사용
                    value_str = matches[0]
                    # 4자리 숫자를 그대로 문자형으로 정규화 (O를 0으로 변환만)
                    result = normalize_four_digit_minor(value_str)
                    # "0000"은 유효하지 않은 값으로 간주 (OCR 오류)
                    if result and result != "0000":
                        return result
        
        # 4자리가 아닌 경우도 시도 (3자리, 2자리 등) - 4자리로 패딩
        patterns_flexible = [
            r'(?:Minor|Mnor|Inor|Mior|Mmor|M1nor|minor|mnor|inor|mior|mmor|m1nor)\s*[:：]?\s*([0-9OoIl|]+)',  # Minor: 001 또는 Mnor OO01
            r'(?:Minor|Mnor|Inor|minor|mnor|inor)\s+([0-9OoIl|]+)',  # Minor 001
            r'(?:Minor|Mnor|Inor|minor|mnor|inor)([0-9OoIl|]+)',  # Minor001 (공백 없음)
        ]
        
        for search_text in search_texts:
            for pattern in patterns_flexible:
                matches = re.findall(pattern, search_text, re.IGNORECASE)
                if matches:
                    value_str = matches[0]
                    # 4자리로 정규화 (O를 0으로 변환하고 4자리로 패딩)
                    result = normalize_four_digit_minor(value_str)
                    # "0000"은 유효하지 않은 값으로 간주 (OCR 오류)
                    if result and result != "0000":
                        return result
        
        # 3. 3순위: OCR에서 '설치' 옆의 1~3자리 숫자 찾기 (개선된 패턴)
        install_patterns = [
            r'설치\s*(\d{1,3})(?=25\d{4,})',  # 설치10251104 또는 설치1251104 (날짜 패턴, 개선됨)
            r'설치\s*(\d{1,3})(?=\d{6})',    # 설치 + 숫자 + 6자리 이상
            r'설치\s*[:：]?\s*(\d{1,3})',    # 설치: 10 또는 설치: 1 또는 설치: 100
            r'설치\s*[:：]?\s*([0-9OoIl|]{1,4})',  # 설치: OO19 (OCR 오류 포함)
        ]
        
        for search_text in search_texts:
            for pattern in install_patterns:
                matches = re.findall(pattern, search_text)
                if matches:
                    # 숫자를 4자리로 변환
                    digit_str = matches[0]
                    # OCR 오류 패턴 처리
                    digit_str = digit_str.replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1').replace('|', '1')
                    # 숫자만 추출
                    numbers = re.findall(r'\d+', digit_str)
                    if numbers:
                        try:
                            digit = int(numbers[0])
                            return f"{digit:04d}"
                        except ValueError:
                            continue
        
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
    source 폴더의 이미지들을 Minor 값에 따라 output 폴더로 재구조화합니다.
    모니터링 기능 포함: 진행률, 처리 속도, 예상 시간 표시
    """
    print("="*70)
    print("단계 1: 이미지 분류 시작")
    print("="*70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 시작 시간 기록 (가장 먼저 초기화)
    start_time = time.time()
    
    # output 폴더 생성
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # source 폴더의 모든 이미지 파일 처리
    image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    image_files = sorted([f for f in SOURCE_DIR.iterdir() 
                         if f.suffix in image_extensions])
    
    if not image_files:
        print("❌ 이미지 파일을 찾을 수 없습니다.")
        return
    
    total_files = len(image_files)
    print(f"📁 총 {total_files}개 이미지 파일을 처리합니다...\n")
    
    processed = 0
    failed = []
    minor_counts = {}
    last_update_time = start_time
    
    # 통계 출력을 위한 변수
    stats_update_interval = 5  # 5개 파일마다 통계 업데이트
    
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
                  f"처리 중: {file_path.name[:50]:<50} "
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
                # 숫자가 아닌 경우 그대로 사용하되, 경고 출력
                print(f"\n⚠ 경고: Minor 값이 숫자가 아닙니다: {minor_value}")
            
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
        else:
            # Minor 값을 찾을 수 없는 경우
            unknown_folder = OUTPUT_DIR / "Unknown"
            unknown_folder.mkdir(exist_ok=True)
            target_path = unknown_folder / file_path.name
            shutil.copy2(file_path, target_path)
            failed.append(file_path.name)
        
        # 상세 정보 출력 (매 N개마다)
        if idx % stats_update_interval == 0 or idx == total_files:
            file_time = time.time() - file_start_time
            status = "✓" if minor_value else "⚠"
            minor_info = f"Minor_{minor_value}" if minor_value else "Unknown"
            print(f"\r{progress_bar} [{idx}/{total_files}] "
                  f"{status} {file_path.name[:40]:<40} → {minor_info:<15} "
                  f"({file_time:.1f}초)", end="" if idx < total_files else "\n")
    
    # 최종 결과 출력
    total_time = time.time() - start_time
    print("\n" + "="*70)
    print("단계 1: 이미지 분류 완료")
    print("="*70)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {format_time(total_time)}")
    print(f"평균 처리 속도: {total_time/total_files:.2f}초/파일")
    print(f"\n📊 처리 결과:")
    print(f"  ✓ 성공: {processed}개 파일")
    print(f"  ⚠ 실패: {len(failed)}개 파일")
    
    if minor_counts:
        print(f"\n📁 Minor 값별 분류 ({len(minor_counts)}개 폴더):")
        # 4자리 숫자 형식으로 정렬
        for minor_value in sorted(minor_counts.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            folder_name = f"Minor_{minor_value}"
            print(f"  {folder_name}: {minor_counts[minor_value]}개 파일")
    
    if failed:
        print(f"\n⚠ Minor 값을 찾지 못한 파일들 ({len(failed)}개):")
        for fname in failed[:10]:  # 처음 10개만 표시
            print(f"  - {fname}")
        if len(failed) > 10:
            print(f"  ... 외 {len(failed) - 10}개")
    
    print("\n" + "="*70)
    print("다음 단계: output 폴더의 분류된 이미지들을 PDF로 변환")
    print("="*70)

if __name__ == "__main__":
    organize_files()

