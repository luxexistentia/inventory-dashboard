import gspread

# 1. 아까 다운받은 JSON 출입증을 들고 구글에 로그인 시도
try:
    gc = gspread.service_account(filename='credentials.json')
    print("✅ 구글 클라우드 로그인 성공!")
    
    # 2. 공유받은 구글 시트 파일 열기
    # (주의: 파일 이름이 실제와 100% 똑같아야 합니다)
    sheet_name = '미니롤 재고 관리(응답)' 
    doc = gc.open(sheet_name)
    
    # 3. 첫 번째 워크시트(탭) 선택 및 첫 번째 줄(헤더) 가져오기
    worksheet = doc.sheet1
    headers = worksheet.row_values(1)
    
    print(f"✅ [{sheet_name}] 파일 연결 성공!")
    print("가져온 열 이름(첫 줄):", headers)

except Exception as e:
    print("❌ 에러가 발생했습니다:", e)