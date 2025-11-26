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
    """
    # 파일명에서 Minor 값 추출
    filename_minor = extract_minor_from_filename(file_path.name)
    if filename_minor:
        expected_minor = f"{int(filename_minor):04d}"
        # 현재 위치와 일치하는지 확인
        if current_minor_value != expected_minor:
            return expected_minor  # 올바른 Minor 값 반환
    return None  # 위치가 올바르거나 파일명에서 추출 불가

def recheck_unknown_files():
    """
    output 폴더의 모든 파일을 재검사하여 파일명 규칙을 재검증합니다.
    1. source와 output 파일 수 비교
    2. output 폴더 전체 스캔하여 파일명 규칙 재검증
    3. Unknown 폴더의 파일들 OCR 재검사
    """
    # 시작 시간 기록 (가장 먼저 초기화)
    start_time = time.time()
    
    print("="*70)
    print("Output 폴더 재검증 시작")
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
        print(f"⚠ 경고: 파일 수가 일치하지 않습니다. (차이: {diff}개)")
        print(f"  완료율: {output_count/source_count*100:.1f}%")
    else:
        print(f"✅ 파일 수 일치: {source_count}개 (100%)")
    
    print()
    
    # 2. output 폴더 전체 스캔하여 파일명 규칙 재검증
    print("="*70)
    print("파일명 규칙 재검증 시작")
    print("="*70)
    
    all_output_files = []
    for folder in OUTPUT_DIR.iterdir():
        if folder.is_dir():
            for file_path in folder.iterdir():
                if file_path.is_file() and file_path.suffix in image_extensions:
                    # 현재 폴더명에서 Minor 값 추출
                    folder_name = folder.name
                    if folder_name.startswith('Minor_'):
                        current_minor = folder_name.replace('Minor_', '')
                    elif folder_name == 'Unknown':
                        current_minor = None
                    else:
                        current_minor = None
                    
                    all_output_files.append((file_path, current_minor))
    
    print(f"📁 총 {len(all_output_files)}개 파일을 검증합니다...\n")
    
    moved_by_filename = 0
    moved_to_correct = []
    
    for file_path, current_minor in all_output_files:
        # 파일명 규칙 재검증
        correct_minor = verify_file_location(file_path, current_minor)
        
        if correct_minor:
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
            
            shutil.move(str(file_path), str(target_path))
            moved_by_filename += 1
            moved_to_correct.append((file_path.name, current_minor, correct_minor))
    
    if moved_by_filename > 0:
        print(f"\n✅ 파일명 규칙에 따라 {moved_by_filename}개 파일 이동:")
        for fname, old_minor, new_minor in moved_to_correct[:10]:
            print(f"  {fname}: Minor_{old_minor} → Minor_{new_minor}")
        if len(moved_to_correct) > 10:
            print(f"  ... 외 {len(moved_to_correct) - 10}개")
    else:
        print("✅ 모든 파일이 올바른 위치에 있습니다.")
    
    print()
    
    # 3. Unknown 폴더의 파일들 OCR 재검사
    print("="*70)
    print("Unknown 폴더 OCR 재검사 시작")
    print("="*70)
    
    if not UNKNOWN_DIR.exists():
        print("✅ Unknown 폴더가 존재하지 않습니다.")
        return
    
    unknown_files = sorted([f for f in UNKNOWN_DIR.iterdir() 
                           if f.is_file() and f.suffix in image_extensions])
    
    if not unknown_files:
        print("✅ Unknown 폴더에 재검사할 이미지가 없습니다.")
        return
    
    total_unknown_files = len(unknown_files)
    print(f"📁 총 {total_unknown_files}개 파일을 OCR로 재검사합니다...\n")
    
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
            
            shutil.move(str(file_path), str(target_path))
            
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
    print("재검증 완료")
    print("="*70)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {format_time(total_time)}")
    
    print(f"\n📊 최종 결과:")
    print(f"  ✓ 파일명 규칙으로 이동: {moved_by_filename}개 파일")
    print(f"  ✓ OCR 재검사로 이동: {moved_by_ocr}개 파일")
    print(f"  ⚠ 여전히 Unknown: {len(still_unknown)}개 파일")
    
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
    
    # 최종 파일 수 확인
    final_output_count = count_image_files(OUTPUT_DIR)
    print(f"\n📊 최종 파일 수:")
    print(f"  source 폴더: {source_count}개")
    print(f"  output 폴더: {final_output_count}개")
    if source_count == final_output_count:
        print(f"  ✅ 완료율: 100%")
    else:
        print(f"  ⚠ 완료율: {final_output_count/source_count*100:.1f}%")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    recheck_unknown_files()

