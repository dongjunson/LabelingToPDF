#!/usr/bin/env python3
"""
전체 워크플로우 통합 실행 스크립트

4단계 순차 실행:
1. organize_by_minor.py - 파일명 규칙으로 이미지 분류
2. recheck_unknown.py - Unknown 폴더 OCR 처리
3. check_folder_structure.py - 결과 확인
4. create_pdf.py - PDF 생성
"""
import sys
import subprocess
from pathlib import Path

def run_step(step_num, script_name, description):
    """각 단계를 실행하고 결과를 확인"""
    print("\n" + "="*70)
    print(f"단계 {step_num} 시작: {description}")
    print("="*70)
    
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"❌ 오류: {script_name} 파일을 찾을 수 없습니다.")
        return False
    
    try:
        # Python 스크립트 실행
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path(__file__).parent,
            check=False
        )
        
        if result.returncode == 0:
            print(f"\n✅ 단계 {step_num} 완료: {description}")
            return True
        else:
            print(f"\n❌ 단계 {step_num} 실패: {description} (종료 코드: {result.returncode})")
            return False
    except Exception as e:
        print(f"\n❌ 단계 {step_num} 실행 중 오류 발생: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("="*70)
    print("전체 워크플로우 실행")
    print("="*70)
    print("\n4단계 순차 실행:")
    print("  1. 파일명 규칙으로 이미지 분류")
    print("  2. Unknown 폴더 OCR 처리")
    print("  3. 결과 확인 (폴더 구조 및 파일 개수)")
    print("  4. PDF 생성")
    print("\n각 단계는 이전 단계가 성공적으로 완료되어야 진행됩니다.")
    
    # 사용자 확인
    try:
        response = input("\n계속하시겠습니까? (y/n, 기본: y): ").strip().lower()
        if response and response != 'y':
            print("실행이 취소되었습니다.")
            return
    except KeyboardInterrupt:
        print("\n실행이 취소되었습니다.")
        return
    
    # 단계별 실행
    steps = [
        (1, "organize_by_minor.py", "파일명 규칙으로 이미지 분류"),
        (2, "recheck_unknown.py", "Unknown 폴더 OCR 처리"),
        (3, "check_folder_structure.py", "결과 확인"),
        (4, "create_pdf.py", "PDF 생성"),
    ]
    
    for step_num, script_name, description in steps:
        success = run_step(step_num, script_name, description)
        
        if not success:
            print("\n" + "="*70)
            print(f"❌ 단계 {step_num}에서 실패했습니다.")
            print("="*70)
            print("\n다음 옵션:")
            print("  1. 수동으로 문제를 해결한 후 다시 실행")
            print("  2. 실패한 단계부터 다시 시작")
            print("  3. 종료")
            
            try:
                choice = input("\n선택 (1/2/3, 기본: 3): ").strip()
                if choice == '2':
                    # 실패한 단계부터 다시 시작
                    continue
                elif choice == '1':
                    print("\n문제를 해결한 후 다시 실행하세요.")
                else:
                    print("\n실행이 중단되었습니다.")
                return
            except KeyboardInterrupt:
                print("\n실행이 중단되었습니다.")
                return
        
        # 단계 간 사용자 확인 (선택적)
        if step_num < len(steps):
            try:
                response = input(f"\n단계 {step_num} 완료. 다음 단계로 진행하시겠습니까? (y/n, 기본: y): ").strip().lower()
                if response and response != 'y':
                    print(f"\n단계 {step_num}까지만 실행되었습니다.")
                    return
            except KeyboardInterrupt:
                print(f"\n단계 {step_num}까지만 실행되었습니다.")
                return
    
    # 모든 단계 완료
    print("\n" + "="*70)
    print("✅ 모든 단계가 성공적으로 완료되었습니다!")
    print("="*70)
    print("\n생성된 파일:")
    pdf_output_dir = Path("pdf_output")
    if pdf_output_dir.exists():
        pdf_files = list(pdf_output_dir.glob("*.pdf"))
        for pdf_file in pdf_files:
            print(f"  - {pdf_file.absolute()}")
    print("\n" + "="*70)

if __name__ == "__main__":
    main()

