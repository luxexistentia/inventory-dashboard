import streamlit as st
import plotly.express as px
import gspread
from data_processing import load_and_process_data

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="재고 대시보드", layout="wide")

# --- 2. 보안: 금고에서 비밀번호 가져오기 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 회사 재고관리 시스템")
    st.write("접근 권한이 필요합니다.")
    pwd = st.text_input("비밀번호를 입력하세요:", type="password")
    
    if st.button("로그인"):
        # st.secrets 금고에서 방금 설정한 비밀번호를 꺼내와서 확인합니다.
        if pwd == st.secrets["app_password"]: 
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 일치하지 않습니다.")
    st.stop()

# --- 3. 데이터 불러오기 (캐싱) ---
@st.cache_data(ttl=600)
def fetch_data():
    # 파일 대신 st.secrets 금고에서 구글 접속 키를 꺼내와서 딕셔너리로 만듭니다.
    credentials_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(credentials_dict)
    
    sheet_name = '미니롤 재고 관리(응답)'
    return load_and_process_data(gc, sheet_name)

st.title("📦 미니롤 재고 및 판매량 대시보드")

with st.spinner("최신 데이터를 구글 시트에서 불러오고 가공하는 중입니다..."):
    current, snapshot, sales = fetch_data()

# --- 4. 사이드바 (분류 필터링) ---
st.sidebar.header("🔍 검색 필터")
categories = ["전체"] + list(current['대분류'].unique())
selected_category = st.sidebar.selectbox("대분류 선택", categories)

if selected_category != "전체":
    current = current[current['대분류'] == selected_category]
    # regex=False 옵션 추가 완료 (괄호 인식 문제 해결)
    snapshot = snapshot[snapshot['SKU'].str.contains(selected_category, na=False, regex=False)]
    sales = sales[sales['SKU'].str.contains(selected_category, na=False, regex=False)]

if st.sidebar.button("🔄 최신 데이터 즉시 동기화"):
    fetch_data.clear()
    st.rerun()

# --- 5. 그래프 그리기 ---

# 뷰어 옵션: 사용자가 일별/주별/월별을 선택할 수 있는 버튼 추가
st.divider()
time_unit = st.radio("🗓️ 시간 단위 선택 (추이 그래프 및 표 적용):", ["일별", "주별", "월별"], horizontal=True)

# ---------------------------------------------------------
# [데이터 재가공] 선택한 단위에 맞춰 데이터 묶기
# ---------------------------------------------------------
if time_unit == "일별":
    snap_display = snapshot.copy()
    sales_display = sales.copy()
elif time_unit == "주별":
    # W-MON (월요일 시작 주간): 재고는 해당 주의 마지막 값, 판매량은 합산
    snap_display = snapshot.groupby([pd.Grouper(key='날짜', freq='W-MON'), 'SKU'])['현재재고'].last().reset_index()
    sales_display = sales.groupby([pd.Grouper(key='날짜', freq='W-MON'), 'SKU'])['판매량'].sum().reset_index()
elif time_unit == "월별":
    # M (월말 기준): 재고는 해당 월의 마지막 값, 판매량은 합산
    snap_display = snapshot.groupby([pd.Grouper(key='날짜', freq='M'), 'SKU'])['현재재고'].last().reset_index()
    sales_display = sales.groupby([pd.Grouper(key='날짜', freq='M'), 'SKU'])['판매량'].sum().reset_index()


# ---------------------------------------------------------
# 1. 현재 재고 현황 (그래프 + 표)
# ---------------------------------------------------------
st.subheader("📊 1. 현재 재고 현황 (종류/사이즈별)")
current['표시이름'] = current['대분류'] + " - " + current['최종 종류']

col1, col2 = st.columns([6, 4]) # 화면을 6:4 비율로 분할

with col1:
    fig1 = px.bar(
        current, x='표시이름', y='현재재고', color='사이즈', 
        title=f"현재 재고 그래프 ({selected_category})", barmode='stack', text_auto=True
    )
    fig1.update_layout(xaxis_tickangle=-45) 
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.write(f"**[현재 재고 상세 표 - {selected_category}]**")
    # 표에 띄울 때 보기 편하도록 필요한 열만 추려냅니다.
    current_table = current[['대분류', '최종 종류', '사이즈', '현재재고']].sort_values(by=['대분류', '최종 종류'])
    st.dataframe(current_table, use_container_width=True, hide_index=True)


st.divider()

# ---------------------------------------------------------
# 2. 재고 변화 추이 (그래프)
# ---------------------------------------------------------
st.subheader(f"📈 2. 재고 변화 추이 ({time_unit})")
fig2 = px.line(
    snap_display, x='날짜', y='현재재고', color='SKU', 
    markers=True, title=f"재고 추이 ({selected_category} - {time_unit})"
)
st.plotly_chart(fig2, use_container_width=True)


st.divider()

# ---------------------------------------------------------
# 3. 판매량 변화 (그래프 + 표)
# ---------------------------------------------------------
st.subheader(f"📉 3. 판매량 변화 ({time_unit})")

col3, col4 = st.columns([6, 4]) # 화면 분할

with col3:
    fig3 = px.bar(
        sales_display, x='날짜', y='판매량', color='SKU', 
        title=f"판매량 그래프 ({selected_category} - {time_unit})", text_auto=True
    )
    fig3.update_layout(xaxis=dict(type='date')) 
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.write(f"**[판매량 상세 표 - {time_unit}]**")
    sales_table = sales_display.copy()
    sales_table['날짜'] = sales_table['날짜'].dt.strftime('%Y-%m-%d') # 날짜 형식 깔끔하게 변경
    sales_table = sales_table.sort_values(by=['날짜', 'SKU'], ascending=[False, True])
    st.dataframe(sales_table, use_container_width=True, hide_index=True)