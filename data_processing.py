import pandas as pd
from datetime import datetime

def load_and_process_data(gc, sheet_name):
    # 1. 구글 시트 데이터 불러오기
    doc = gc.open(sheet_name)
    worksheet = doc.sheet1
    
    # [수정된 부분] 깐깐한 get_all_records() 대신 통째로 가져오기
    raw_data = worksheet.get_all_values()
    
    # 첫 번째 줄을 열 이름(columns)으로, 두 번째 줄부터 데이터로 DataFrame 생성
    df = pd.DataFrame(raw_data[1:], columns=raw_data[0])

    # 구글 시트 특성상 아래쪽 빈 행까지 가져오는 경우가 있으므로 빈 데이터 제거
    # '타임스탬프'가 비어있으면 데이터가 없는 줄이므로 삭제합니다.
    df = df[df['타임스탬프'].astype(bool)]

    # 2. 날짜 전처리 (시간 제거)
    df['날짜'] = df['타임스탬프'].astype(str).str.extract(r'(\d{4}\. \d{1,2}\. \d{1,2})')[0]
    df['날짜'] = pd.to_datetime(df['날짜'], format='%Y. %m. %d')

    # 3. 고유 품목명(SKU) 만들기
    df['SKU'] = df['대분류'].astype(str) + " | " + df['최종 종류'].astype(str) + " | " + df['사이즈'].astype(str)

    # 4. 변화량 계산 (입고는 플러스, 출고는 마이너스)
    # 수량을 빈칸 대신 0으로 채우고 숫자로 변환합니다.
    df['수량'] = pd.to_numeric(df['수량'], errors='coerce').fillna(0)
    df['변화량'] = df.apply(lambda x: x['수량'] if '입고' in str(x['작업 종류']) else -x['수량'], axis=1)

    # ==========================================
    # [데이터 1] 현재 재고 현황 (그래프 1용)
    # ==========================================
    current_stock = df.groupby(['대분류', '최종 종류', '사이즈', 'SKU'])['변화량'].sum().reset_index()
    current_stock.rename(columns={'변화량': '현재재고'}, inplace=True)

    # ==========================================
    # [데이터 2] 시간에 따른 재고 추이 (이월 처리 - 그래프 2용)
    # ==========================================
    daily_changes = df.groupby(['날짜', 'SKU'])['변화량'].sum().reset_index()

    min_date = daily_changes['날짜'].min()
    max_date = pd.to_datetime(datetime.today().date())
    if pd.isna(min_date): 
        min_date = max_date
    all_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    all_skus = df['SKU'].unique()

    idx = pd.MultiIndex.from_product([all_dates, all_skus], names=['날짜', 'SKU'])
    snapshot_df = pd.DataFrame(index=idx).reset_index()

    snapshot_df = pd.merge(snapshot_df, daily_changes, on=['날짜', 'SKU'], how='left')
    snapshot_df['변화량'] = snapshot_df['변화량'].fillna(0)

    snapshot_df['현재재고'] = snapshot_df.groupby('SKU')['변화량'].cumsum()

    # ==========================================
    # [데이터 3] 시간에 따른 판매량 추이 (그래프 3용)
    # ==========================================
    sales_data = df[df['작업 종류'].astype(str).str.contains('출고', na=False)].copy()
    
    if not sales_data.empty:
        sales_trend = sales_data.groupby(['날짜', 'SKU'])['수량'].sum().reset_index()
        sales_trend.rename(columns={'수량': '판매량'}, inplace=True)
    else:
        sales_trend = pd.DataFrame(columns=['날짜', 'SKU', '판매량'])

    return current_stock, snapshot_df, sales_trend

# ==========================================
# 테스트 실행 코드 (터미널에서 결과 확인용)
# ==========================================
if __name__ == "__main__":
    import gspread
    
    try:
        gc = gspread.service_account(filename='credentials.json')
        sheet_name = '미니롤 재고 관리(응답)' # 실제 파일명으로 확인!
        
        print("데이터를 불러오고 가공하는 중입니다...")
        current, snapshot, sales = load_and_process_data(gc, sheet_name)
        
        print("\n✅ 1. 현재 재고 데이터 (상위 5개)")
        print(current.head())
        
        print("\n✅ 2. 재고 추이 (이월) 데이터 (상위 5개)")
        print(snapshot.head())
        
        print("\n✅ 3. 판매량 데이터 (상위 5개)")
        print(sales.head())
        
    except Exception as e:
        print("❌ 에러 발생:", e)