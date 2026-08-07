import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 스타일링 (상단 디자인 그대로 유지)
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
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 구글 시트 연동 및 데이터 처리 (첫 번째 시트 자동 연결)
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

@st.cache_data(ttl=60)
def load_raw_sheet_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(st.secrets["spreadsheet"]["sheet_id"])
        # 탭 이름 에러 방지를 위해 첫 번째 시트(sheet1)를 직접 지정하여 불러옴
        worksheet = sh.get_worksheet(0)
        raw_values = worksheet.get_all_values()
        return raw_values, worksheet
    except Exception as e:
        st.error(f"구글 시트를 불러오는 중 오류 발생: {e}")
        return [], None

def save_raw_sheet_data(worksheet, values):
    try:
        worksheet.clear()
        worksheet.update(values)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")
        return False

@st.cache_data(ttl=300)
def fetch_market_data():
    tickers = ["CL=F", "^TNX", "KRW=X", "^VIX"]
    try:
        data = yf.download(tickers, period="5d", interval="1d", progress=False)['Close']
        latest_oil = data['CL=F'].dropna().iloc[-1] if 'CL=F' in data else 78.04
        latest_tnx = data['^TNX'].dropna().iloc[-1] if '^TNX' in data else 4.67
        latest_usdkrw = data['KRW=X'].dropna().iloc[-1] if 'KRW=X' in data else 1418.38
        latest_vix = data['^VIX'].dropna().iloc[-1] if '^VIX' in data else 15.15
    except Exception:
        latest_oil, latest_tnx, latest_usdkrw, latest_vix = 78.04, 4.67, 1418.38, 15.15
    return float(latest_oil), float(latest_tnx), float(latest_usdkrw), float(latest_vix)

# 시장 지수 로드
oil, tnx, usdkrw, vix = fetch_market_data()

# -----------------------------------------------------------------------------
# 3. 최상단 타이틀 & 경제 지표 요약
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
# 4. 자산 현황 및 플랜 표 출력
# -----------------------------------------------------------------------------
st.subheader("📊 실시간 통합 자산 현황 & 미래 플랜")
st.caption("💡 아래 구글 시트 테이블 데이터를 직접 수정하신 후 저장 버튼을 누르시면 실시간 연동됩니다.")

raw_data, ws_main = load_raw_sheet_data()

if raw_data:
    # A17행(17번째 줄, 파이썬 인덱스 16)부터 데이터 추출
    start_row = 16 if len(raw_data) >= 17 else 0
    sub_data = raw_data[start_row:]
    
    if len(sub_data) > 1:
        headers = sub_data[0]
        rows = sub_data[1:]
        
        cleaned_headers = []
        for i, h in enumerate(headers):
            h_str = str(h).strip()
            if not h_str:
                h_str = f"열_{i+1}"
            cleaned_headers.append(h_str)

        df = pd.DataFrame(rows, columns=cleaned_headers)
        
        edited_df = st.data_editor(df, key="sheet_editor", num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 데이터 저장 및 실시간 계산 반영", key="btn_save_sheet"):
            updated_sub = [edited_df.columns.tolist()] + edited_df.values.tolist()
            full_updated = raw_data[:start_row] + updated_sub
            
            if save_raw_sheet_data(ws_main, full_updated):
                st.success("구글 시트에 성공적으로 업데이트되었습니다!")
                st.rerun()
    else:
        df_full = pd.DataFrame(raw_data)
        edited_df = st.data_editor(df_full, key="full_editor", num_rows="dynamic", use_container_width=True)
        if st.button("💾 전체 데이터 저장 및 반영", key="btn_save_full"):
            if save_raw_sheet_data(ws_main, edited_df.values.tolist()):
                st.success("저장 완료!"); st.rerun()
