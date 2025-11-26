#!/usr/bin/env python3
"""
샘플 이미지에서 OCR을 수행하여 Minor 값 패턴을 파악하는 스크립트
"""
import os
import re
from pathlib import Path

try:
    import easyocr
    USE_EASYOCR = True
    print("Using EasyOCR...")
    reader = easyocr.Reader(['ko', 'en'], gpu=False)
except ImportError:
    try:
        from PIL import Image
        import pytesseract
        USE_EASYOCR = False
        print("Using pytesseract...")
    except ImportError:
        print("Error: Need to install either easyocr or pytesseract")
        print("Install: pip3 install easyocr")
        print("Or: pip3 install pillow pytesseract && brew install tesseract")
        exit(1)

SOURCE_DIR = Path("source")

def extract_text_easyocr(image_path):
    """EasyOCR을 사용하여 텍스트 추출"""
    results = reader.readtext(str(image_path))
    return ' '.join([result[1] for result in results])

def extract_text_tesseract(image_path):
    """pytesseract를 사용하여 텍스트 추출"""
    img = Image.open(image_path)
    return pytesseract.image_to_string(img, lang='kor+eng')

def analyze_image(image_path):
    """이미지에서 텍스트를 추출하고 Minor 관련 정보를 찾습니다"""
    print(f"\n{'='*60}")
    print(f"파일: {image_path.name}")
    print(f"{'='*60}")
    
    try:
        if USE_EASYOCR:
            text = extract_text_easyocr(image_path)
        else:
            text = extract_text_tesseract(image_path)
        
        print(f"\n추출된 텍스트:\n{text}\n")
        
        # Minor 관련 패턴 찾기
        patterns = [
            (r'Minor\s*[:：]?\s*(\S+)', 'Minor: 값'),
            (r'minor\s*[:：]?\s*(\S+)', 'minor: 값'),
            (r'Minor\s+(\d+)', 'Minor 숫자'),
            (r'minor\s+(\d+)', 'minor 숫자'),
            (r'Minor\s+([A-Za-z0-9]+)', 'Minor 영숫자'),
        ]
        
        found = False
        for pattern, desc in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                print(f"✓ {desc} 패턴 발견: {matches}")
                found = True
        
        if not found:
            # 숫자만 찾기
            numbers = re.findall(r'\d+', text)
            if numbers:
                print(f"⚠ Minor 패턴을 찾지 못했지만 숫자 발견: {numbers[:5]}...")
        
    except Exception as e:
        print(f"❌ 오류: {e}")

def main():
    """샘플 이미지 몇 개를 분석합니다"""
    image_files = sorted([f for f in SOURCE_DIR.iterdir() 
                         if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
    
    if not image_files:
        print("이미지 파일을 찾을 수 없습니다.")
        return
    
    # 처음 5개 이미지 분석
    print(f"총 {len(image_files)}개 이미지 중 처음 5개를 분석합니다...\n")
    
    for img_path in image_files[:5]:
        analyze_image(img_path)
    
    print(f"\n{'='*60}")
    print("분석 완료!")
    print("위 결과를 보고 Minor 값의 패턴을 확인한 후")
    print("organize_by_minor.py 스크립트를 실행하세요.")

if __name__ == "__main__":
    main()

