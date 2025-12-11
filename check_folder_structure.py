#!/usr/bin/env python3
"""
output 폴더의 각 Minor 폴더 구조 확인 스크립트
- 각 폴더에 이미지가 2장씩 있는지 확인
- 폴더명 순서가 연속적인지 확인 (빠진 번호 체크)
"""
import os
from pathlib import Path
from collections import defaultdict

OUTPUT_DIR = Path("output")
image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}

def check_folder_structure():
    """
    [단계 3] output 폴더의 구조를 확인합니다.
    
    확인 항목:
    1. 폴더명 순서가 연속적인지 확인 (빠진 번호 체크)
    2. 각 Minor 폴더에 이미지가 2장씩 있는지 확인
    3. 전체 통계 및 분포 확인
    """
    print("="*70)
    print("단계 3: Output 폴더 구조 확인")
    print("="*70)
    
    # 각 폴더별 파일 개수 수집
    folder_counts = {}
    folders_with_wrong_count = []
    
    # Minor 폴더들 찾기 및 번호 추출
    minor_folders = []
    for f in OUTPUT_DIR.iterdir():
        if f.is_dir() and f.name.startswith('Minor_'):
            try:
                # Minor_XXXX 형식에서 숫자 추출
                minor_num = int(f.name.replace('Minor_', ''))
                minor_folders.append((minor_num, f))
            except ValueError:
                # 숫자가 아닌 경우 (예: Minor_Unknown 등)
                print(f"⚠️  숫자가 아닌 폴더명: {f.name}")
                continue
    
    # 번호순으로 정렬
    minor_folders.sort(key=lambda x: x[0])
    
    print(f"\n📁 총 {len(minor_folders)}개 Minor 폴더 확인 중...\n")
    
    # 각 폴더의 이미지 개수 확인
    for minor_num, folder in minor_folders:
        # 이미지 파일 개수 세기
        image_files = [f for f in folder.iterdir() 
                      if f.is_file() and f.suffix in image_extensions]
        count = len(image_files)
        folder_counts[minor_num] = count
        
        if count != 2:
            folders_with_wrong_count.append((folder.name, count))
    
    # 폴더 번호 순서 확인
    if minor_folders:
        min_num = minor_folders[0][0]
        max_num = minor_folders[-1][0]
        existing_nums = set([num for num, _ in minor_folders])
        
        # 빠진 번호 찾기
        missing_nums = []
        for num in range(min_num, max_num + 1):
            if num not in existing_nums:
                missing_nums.append(num)
    else:
        min_num = max_num = 0
        existing_nums = set()
        missing_nums = []
    
    # 결과 출력
    print(f"\n📊 폴더 순서 확인:")
    print(f"  최소 번호: Minor_{min_num:04d}")
    print(f"  최대 번호: Minor_{max_num:04d}")
    print(f"  총 폴더 수: {len(minor_folders)}개")
    print(f"  예상 폴더 수: {max_num - min_num + 1}개")
    
    if missing_nums:
        print(f"  ❌ 빠진 번호: {len(missing_nums)}개")
        print(f"\n⚠️  빠진 Minor 번호들:")
        # 연속된 구간으로 그룹화
        if missing_nums:
            ranges = []
            start = missing_nums[0]
            end = missing_nums[0]
            
            for num in missing_nums[1:]:
                if num == end + 1:
                    end = num
                else:
                    if start == end:
                        ranges.append(f"Minor_{start:04d}")
                    else:
                        ranges.append(f"Minor_{start:04d} ~ Minor_{end:04d}")
                    start = num
                    end = num
            
            if start == end:
                ranges.append(f"Minor_{start:04d}")
            else:
                ranges.append(f"Minor_{start:04d} ~ Minor_{end:04d}")
            
            for i, range_str in enumerate(ranges[:50]):  # 처음 50개만 표시
                print(f"    {range_str}")
            if len(ranges) > 50:
                print(f"    ... 외 {len(ranges) - 50}개")
    else:
        print(f"  ✅ 모든 번호가 연속적으로 존재합니다!")
    
    # 이미지 개수 확인 결과
    total_folders = len(folder_counts)
    correct_folders = total_folders - len(folders_with_wrong_count)
    
    print(f"\n📊 이미지 개수 확인:")
    print(f"  ✅ 정상 (2장): {correct_folders}개 폴더")
    print(f"  ❌ 이상 (2장 아님): {len(folders_with_wrong_count)}개 폴더")
    
    if folders_with_wrong_count:
        print(f"\n⚠️  이미지 개수가 2장이 아닌 폴더들:")
        # 개수별로 그룹화
        count_groups = defaultdict(list)
        for folder_name, count in folders_with_wrong_count:
            count_groups[count].append(folder_name)
        
        for count in sorted(count_groups.keys()):
            folders = count_groups[count]
            print(f"\n  {count}장인 폴더 ({len(folders)}개):")
            for folder_name in sorted(folders)[:20]:  # 처음 20개만 표시
                print(f"    - {folder_name}")
            if len(folders) > 20:
                print(f"    ... 외 {len(folders) - 20}개")
    else:
        print(f"\n✅ 모든 폴더가 정상적으로 2장씩 있습니다!")
    
    # 통계
    count_distribution = defaultdict(int)
    for count in folder_counts.values():
        count_distribution[count] += 1
    
    print(f"\n📈 파일 개수 분포:")
    for count in sorted(count_distribution.keys()):
        folder_num = count_distribution[count]
        print(f"  {count}장: {folder_num}개 폴더")
    
    # 요약
    print(f"\n" + "="*70)
    print("단계 3: 구조 확인 완료")
    print("="*70)
    print(f"  폴더 순서: {'✅ 정상' if not missing_nums else f'❌ {len(missing_nums)}개 빠짐'}")
    print(f"  이미지 개수: {'✅ 모두 2장' if not folders_with_wrong_count else f'❌ {len(folders_with_wrong_count)}개 폴더 이상'}")
    print("="*70)
    if not missing_nums and not folders_with_wrong_count:
        print("\n✅ 모든 폴더가 정상입니다!")
        print("다음 단계: create_pdf.py 실행하여 PDF 생성")
    else:
        print("\n⚠️  일부 문제가 발견되었습니다. 확인이 필요합니다.")
    print("="*70)

if __name__ == "__main__":
    check_folder_structure()

