import streamlit as st
import plotly.express as px
import gspread
from data_processing import load_and_process_data

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="재고 대시보드", layout="wide")

# --- 2. 보안: 비밀번호 로그인 시스템 ---
# st.session_state를 사용해 한 번 로그인하면 새로고침해도 유지되게 만듭니다.
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 회사 재고관리 시스템")
    st.write("접근 권한이 필요합니다.")
    # 임시 비밀번호는 '1234'로 설정했습니다.
    pwd = st.text_input("비밀번호를 입력하세요:", type="password")
    if st.button("로그인"):
        if pwd == "1234": 
            st.session_state.authenticated = True
            st.rerun() # 로그인 성공 시 화면 새로고침
        else:
            st.error("비밀번호가 일치하지 않습니다.")
    st.stop() # 로그인이 안 되면 여기서 코드를 멈추고 아래 대시보드는 안 보여줍니다.

# --- 3. 데이터 불러오기 (캐싱) ---
# @st.cache_data를 쓰면 구글 시트를 매번 안 읽고 10분(600초)에 한 번만 읽어옵니다. (속도 폭발적 향상)
@st.cache_data(ttl=600)
def fetch_data():
    gc = gspread.service_account(filename='credentials.json')
    sheet_name = '미니롤 재고 관리(응답)'
    return load_and_process_data(gc, sheet_name)

# 화면 상단 제목
st.title("📦 미니롤 재고 및 판매량 대시보드")

# 데이터 불러오는 동안 빙글빙글 도는 로딩창 표시
with st.spinner("최신 데이터를 구글 시트에서 불러오고 가공하는 중입니다..."):
    current, snapshot, sales = fetch_data()

# --- 4. 사이드바 (분류 필터링) ---
# 왼쪽 바에 대분류를 선택할 수 있는 드롭다운 메뉴를 만듭니다.
st.sidebar.header("🔍 검색 필터")
categories = ["전체"] + list(current['대분류'].unique())
selected_category = st.sidebar.selectbox("대분류 선택", categories)

# --- 4. 사이드바 (분류 필터링) --- 수정 부분
if selected_category != "전체":
    current = current[current['대분류'] == selected_category]
    
    # [수정 전] snapshot = snapshot[snapshot['SKU'].str.contains(selected_category, na=False)]
    # [수정 후] regex=False 옵션을 추가하여 괄호를 '글자 그대로' 인식하게 만듭니다.
    snapshot = snapshot[snapshot['SKU'].str.contains(selected_category, na=False, regex=False)]
    sales = sales[sales['SKU'].str.contains(selected_category, na=False, regex=False)]

# 새로고침 버튼 (10분 캐싱 무시하고 즉시 데이터 가져오기)
if st.sidebar.button("🔄 최신 데이터 즉시 동기화"):
    fetch_data.clear()
    st.rerun()

# --- 5. 그래프 그리기 ---

# [그래프 1] 현재 재고 현황 (누적 막대 그래프)
st.subheader("📊 1. 현재 재고 현황 (종류/사이즈별)")
# 요구사항: 같은 종류는 하나의 막대, 사이즈별로 색깔 다르게 -> barmode='stack'으로 해결
fig1 = px.bar(
    current, 
    x='최종 종류', 
    y='현재재고', 
    color='사이즈', 
    title=f"현재 재고 ({selected_category})",
    barmode='stack', 
    text_auto=True # 막대 안에 숫자 표시
)
st.plotly_chart(fig1, use_container_width=True)

st.divider() # 화면 구분선

# [그래프 2] 시간에 따른 재고 변화 추이 (이월 적용)
st.subheader("📈 2. 재고 변화 추이 (일별)")
# 요구사항: 시간에 따른 재고 변화 -> 꺾은선 그래프(line)로 해결
fig2 = px.line(
    snapshot,
    x='날짜',
    y='현재재고',
    color='SKU',
    markers=True, # 꺾이는 지점에 점 찍기
    title=f"재고 추이 ({selected_category})"
)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# [그래프 3] 시간에 따른 판매량 변화
st.subheader("📉 3. 일일 판매량 변화")
# 판매량은 특정 날짜에만 튀어오르는 성질이 있으므로 막대(bar) 그래프가 가장 직관적입니다.
fig3 = px.bar(
    sales,
    x='날짜',
    y='판매량',
    color='SKU',
    title=f"판매량 추이 ({selected_category})",
    text_auto=True
)
# 날짜 축의 빈 공간을 유지하여 판매가 없는 날은 자연스럽게 0으로(빈칸으로) 보이게 설정합니다.
fig3.update_layout(xaxis=dict(type='date')) 
st.plotly_chart(fig3, use_container_width=True)