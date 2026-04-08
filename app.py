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
st.subheader("📊 1. 현재 재고 현황 (종류/사이즈별)")

# 핵심 로직 추가: X축에 보여줄 이름을 [대분류 - 최종 종류] 형태로 새로 만듭니다.
current['표시이름'] = current['대분류'] + " - " + current['최종 종류']

fig1 = px.bar(
    current, 
    x='표시이름', # X축을 단순히 '최종 종류'가 아니라 새로 만든 '표시이름'으로 변경!
    y='현재재고', 
    color='사이즈', 
    title=f"현재 재고 ({selected_category})", 
    barmode='stack', 
    text_auto=True
)
# X축 글자가 길어지면 겹쳐 보일 수 있으므로 글자를 45도 기울여줍니다.
fig1.update_layout(xaxis_tickangle=-45) 
st.plotly_chart(fig1, use_container_width=True)

st.divider()

st.subheader("📈 2. 재고 변화 추이 (일별)")
fig2 = px.line(
    snapshot, x='날짜', y='현재재고', color='SKU', 
    markers=True, title=f"재고 추이 ({selected_category})"
)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

st.subheader("📉 3. 일일 판매량 변화")
fig3 = px.bar(
    sales, x='날짜', y='판매량', color='SKU', 
    title=f"판매량 추이 ({selected_category})", text_auto=True
)
fig3.update_layout(xaxis=dict(type='date')) 
st.plotly_chart(fig3, use_container_width=True)