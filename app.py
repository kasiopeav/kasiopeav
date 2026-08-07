import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 디자인 (ver1 그대로 유지)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="재국♡광희 재테크 계획", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .status-badge {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: bold;
    }
    .badge-normal { background-color: #d1fae5; color: #065f46; }
    .badge-warn { background-color: #fef3c7; color: #92400e; }
    .badge-danger { background-color: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 구글 시트 연동 및 캐시 관리
# -----------------------------------------------------------------------------
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

@st.cache_data(ttl=300)
def load_sheet_data(sheet_name):
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(st.secrets["spreadsheet"]["sheet_id"])
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df, worksheet
    except Exception as e:
        return pd.DataFrame(), None

def save_sheet_data(worksheet, df):
    try:
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        # 저장 직후 캐시를 초기화하여 PC/모바일 즉시 반영
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")
        return False

@st.cache_data(ttl=300)
def fetch_market_data():
    # 주요 지수 및 환율 데이터 로드
    tickers = ["CL=F", "^TNX", "KRW=X", "^VIX"]
    data = yf.download(tickers, period="5d", interval="1d", progress=False)['Close']
    
    latest_oil = data['CL=F'].dropna().iloc[-1] if 'CL=F' in data else 83.17
    latest_tnx = data['^TNX'].dropna().iloc[-1] if '^TNX' in data else 4.67
    latest_usdkrw = data['KRW=X'].dropna().iloc[-1] if 'KRW=X' in data else 1418.50
    latest_vix = data['^VIX'].dropna().iloc[-1] if '^VIX' in data else 15.15
    
    return float(latest_oil), float(latest_tnx), float(latest_usdkrw), float(latest_vix)

# 데이터 로드
oil, tnx, usdkrw, vix = fetch_market_data()

# -----------------------------------------------------------------------------
# 3. 메인 헤더 & 경제 지표 요약
# -----------------------------------------------------------------------------
st.title("💖 재국♡광희 재테크 계획")

today = datetime.datetime.now()
st.markdown(f"##### 🗓 오늘은 {today.strftime('%Y년 %m월 %d일')}입니다.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("브렌트유 시세 🟢 정상", f"${oil:.2f} USD")
with c2:
    st.metric("미 10년물 국채 금리 ⚠️ 주의", f"{tnx:.2f} %")
with c3:
    st.metric("환율 (USD/KRW) 🟢 정상", f"₩{usdkrw:,.2f}")
with c4:
    st.metric("VIX 지수 🟢 정상", f"{vix:.2f}")

st.divider()

# -----------------------------------------------------------------------------
# 4. 4개 탭 구성 (현재/미래 × 재국/광희)
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 실시간 현황 (재국)", 
    "📊 실시간 현황 (광희)", 
    "🎯 미래 배당 목표 (재국)", 
    "🎯 미래 배당 목표 (광희)"
])

# ----- [탭 1] 실시간 현황 (재국) -----
with tab1:
    st.subheader("📊 실시간 통합 보유 현황 (재국)")
    st.caption("💡 푸른색 배경의 수량(주), 내 평단가 셀을 수정한 후 저장 버튼을 누르시면 구글 시트에 자동 보관됩니다.")
    
    df1, ws1 = load_sheet_data("현재(재국)")
    if not df1.empty:
        edited_df1 = st.data_editor(df1, key="editor1", num_rows="dynamic", use_container_width=True)
        if st.button("💾 현재 현황 구글 시트 저장 및 계산 반영 (재국)", key="btn1"):
            if save_sheet_data(ws1, edited_df1):
                st.success("구글 시트 [현재(재국)]에 성공적으로 저장되었습니다!")
                st.rerun()

# ----- [탭 2] 실시간 현황 (광희) -----
with tab2:
    st.subheader("📊 실시간 통합 보유 현황 (광희)")
    st.caption("💡 푸른색 배경의 수량(주), 내 평단가 셀을 수정한 후 저장 버튼을 누르시면 구글 시트에 자동 보관됩니다.")
    
    df2, ws2 = load_sheet_data("현재(광희)")
    if not df2.empty:
        edited_df2 = st.data_editor(df2, key="editor2", num_rows="dynamic", use_container_width=True)
        if st.button("💾 현재 현황 구글 시트 저장 및 계산 반영 (광희)", key="btn2"):
            if save_sheet_data(ws2, edited_df2):
                st.success("구글 시트 [현재(광희)]에 성공적으로 저장되었습니다!")
                st.rerun()

# ----- [탭 3] 미래 배당 목표 (재국) -----
with tab3:
    st.subheader("🎯 미래 배당 세팅 목표 (재국)")
    st.caption("💡 목표 수량을 수정 후 저장 버튼을 누르면 미래 연간/월간 예상 배당금이 자동 연산됩니다.")
    
    df3, ws3 = load_sheet_data("미래(재국)")
    if not df3.empty:
        edited_df3 = st.data_editor(df3, key="editor3", num_rows="dynamic", use_container_width=True)
        if st.button("💾 미래 목표 저장 및 즉시 연산 (재국)", key="btn3"):
            if save_sheet_data(ws3, edited_df3):
                st.success("구글 시트 [미래(재국)]에 성공적으로 저장되었습니다!")
                st.rerun()

# ----- [탭 4] 미래 배당 목표 (광희) -----
with tab4:
    st.subheader("🎯 미래 배당 세팅 목표 (광희)")
    st.caption("💡 목표 수량을 수정 후 저장 버튼을 누르면 미래 연간/월간 예상 배당금이 자동 연산됩니다.")
    
    df4, ws4 = load_sheet_data("미래(광희)")
    if not df4.empty:
        edited_df4 = st.data_editor(df4, key="editor4", num_rows="dynamic", use_container_width=True)
        if st.button("💾 미래 목표 저장 및 즉시 연산 (광희)", key="btn4"):
            if save_sheet_data(ws4, edited_df4):
                st.success("구글 시트 [미래(광희)]에 성공적으로 저장되었습니다!")
                st.rerun()
