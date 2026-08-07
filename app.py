import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. 페이지 기본 설정
st.set_page_config(page_title="나만의 맞춤형 주식 대시보드", layout="wide")

# 2. 구글 시트 연동 함수
@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def load_sheet_data(sheet_name):
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(st.secrets["spreadsheet"]["sheet_id"])
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"'{sheet_name}' 시트를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(), None

def save_sheet_data(worksheet, df):
    try:
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        # 저장 즉시 캐시를 비워 모바일/PC에 바로 반영
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")
        return False

# ----- 메인 화면 구성 -----
st.title("💖 재국♡광희 재테크 계획")

# 지수 요약 정보
st.markdown("##### 🗓 오늘은 2026년 08월 07일 금요일입니다.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("브렌트유 시세 🟢 정상", "$83.17 USD")
with col2:
    st.metric("미 10년물 국채 금리 ⚠️ 주의", "4.67 %")
with col3:
    st.metric("환율 (USD/KRW) 🟢 정상", "₩1,418.50")
with col4:
    st.metric("VIX 지수 🟢 정상", "15.15")

st.divider()

# 탭 메뉴
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 실시간 현황 (재국)", 
    "📊 실시간 현황 (광희)", 
    "🎯 미래 배당 목표 (재국)", 
    "🎯 미래 배당 목표 (광희)"
])

# [탭 1] 실시간 현황 (재국)
with tab1:
    st.markdown("### 📊 실시간 통합 보유 현황 (재국)")
    df1, ws1 = load_sheet_data("현재(재국)")
    if not df1.empty:
        edited_df1 = st.data_editor(df1, key="editor1", num_rows="dynamic", use_container_width=True)
        if st.button("💾 현재 현황 구글 시트 저장 및 계산 반영 (재국)", key="btn1"):
            if save_sheet_data(ws1, edited_df1):
                st.success("구글 시트 [현재(재국)]에 성공적으로 저장되었습니다!")
                st.rerun()

# [탭 2] 실시간 현황 (광희)
with tab2:
    st.markdown("### 📊 실시간 통합 보유 현황 (광희)")
    df2, ws2 = load_sheet_data("현재(광희)")
    if not df2.empty:
        edited_df2 = st.data_editor(df2, key="editor2", num_rows="dynamic", use_container_width=True)
        if st.button("💾 현재 현황 구글 시트 저장 및 계산 반영 (광희)", key="btn2"):
            if save_sheet_data(ws2, edited_df2):
                st.success("구글 시트 [현재(광희)]에 성공적으로 저장되었습니다!")
                st.rerun()

# [탭 3] 미래 배당 목표 (재국)
with tab3:
    st.markdown("### 🎯 미래 배당 세팅 목표 (재국)")
    df3, ws3 = load_sheet_data("미래(재국)")
    if not df3.empty:
        edited_df3 = st.data_editor(df3, key="editor3", num_rows="dynamic", use_container_width=True)
        if st.button("💾 미래 목표 저장 및 즉시 연산 (재국)", key="btn3"):
            if save_sheet_data(ws3, edited_df3):
                st.success("구글 시트 [미래(재국)]에 성공적으로 저장되었습니다!")
                st.rerun()

# [탭 4] 미래 배당 목표 (광희)
with tab4:
    st.markdown("### 🎯 미래 배당 세팅 목표 (광희)")
    df4, ws4 = load_sheet_data("미래(광희)")
    if not df4.empty:
        edited_df4 = st.data_editor(df4, key="editor4", num_rows="dynamic", use_container_width=True)
        if st.button("💾 미래 목표 저장 및 즉시 연산 (광희)", key="btn4"):
            if save_sheet_data(ws4, edited_df4):
                st.success("구글 시트 [미래(광희)]에 성공적으로 저장되었습니다!")
                st.rerun()
