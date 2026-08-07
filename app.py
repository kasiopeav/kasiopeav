import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. 페이지 기본 설정
st.set_page_config(page_title="나만의 맞춤형 주식 대시보드", layout="wide")

# 2. 구글 시트 연동 함수 (캐시 적용)
@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    # private_key 줄바꿈 처리
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
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
        # 헤더와 데이터 함께 업데이트
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        # 저장 후 데이터 캐시를 완전히 비워 즉시 반영되도록 함
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")
        return False

# ----- 앱 메인 화면 -----
st.title("📈 나만의 맞춤형 주식 대시보드")

# 탭 구성 (직관적인 한글 명칭 반영)
tab1, tab2, tab3, tab4 = st.tabs(["실시간 현황 (재국)", "실시간 현황 (광희)", "미래 목표 (재국)", "미래 목표 (광희)"])

# ----- [탭 1] 현재(재국) -----
with tab1:
    st.subheader("📊 실시간 통합 보유 현황 (재국)")
    df_current_jg, ws_current_jg = load_sheet_data("현재(재국)")
    
    if not df_current_jg.empty:
        edited_df1 = st.data_editor(df_current_jg, key="editor_current_jg", num_rows="dynamic")
        if st.button("💾 현재 현황 저장 및 반영 (재국)", key="btn1"):
            if save_sheet_data(ws_current_jg, edited_df1):
                st.success("구글 시트 [현재(재국)]에 성공적으로 저장되었습니다!")
                st.rerun()

# ----- [탭 2] 현재(광희) -----
with tab2:
    st.subheader("📊 실시간 통합 보유 현황 (광희)")
    df_current_gh, ws_current_gh = load_sheet_data("현재(광희)")
    
    if not df_current_gh.empty:
        edited_df2 = st.data_editor(df_current_gh, key="editor_current_gh", num_rows="dynamic")
        if st.button("💾 현재 현황 저장 및 반영 (광희)", key="btn2"):
            if save_sheet_data(ws_current_gh, edited_df2):
                st.success("구글 시트 [현재(광희)]에 성공적으로 저장되었습니다!")
                st.rerun()

# ----- [탭 3] 미래(재국) -----
with tab3:
    st.subheader("🎯 미래 배당 세팅 목표 (재국)")
    df_future_jg, ws_future_jg = load_sheet_data("미래(재국)")
    
    if not df_future_jg.empty:
        edited_df3 = st.data_editor(df_future_jg, key="editor_future_jg", num_rows="dynamic")
        if st.button("💾 미래 목표 저장 및 즉시 연산 (재국)", key="btn3"):
            if save_sheet_data(ws_future_jg, edited_df3):
                st.success("구글 시트 [미래(재국)]에 성공적으로 저장되었습니다!")
                st.rerun()

# ----- [탭 4] 미래(광희) -----
with tab4:
    st.subheader("🎯 미래 배당 세팅 목표 (광희)")
    df_future_gh, ws_future_gh = load_sheet_data("미래(광희)")
    
    if not df_future_gh.empty:
        edited_df4 = st.data_editor(df_future_gh, key="editor_future_gh", num_rows="dynamic")
        if st.button("💾 미래 목표 저장 및 즉시 연산 (광희)", key="btn4"):
            if save_sheet_data(ws_future_gh, edited_df4):
                st.success("구글 시트 [미래(광희)]에 성공적으로 저장되었습니다!")
                st.rerun()
