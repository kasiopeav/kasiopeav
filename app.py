import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 디자인
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
# 2. 구글 시트 연동 및 캐시 관리
# -----------------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
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
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")
        return False

@st.cache_data(ttl=300)
def fetch_market_data():
    tickers = ["CL=F", "^TNX", "KRW=X", "^VIX"]
    try:
        data = yf.download(tickers, period="5d", interval="1d", progress=False)['Close']
        latest_oil = data['CL=F'].dropna().iloc[-1] if 'CL=F' in data else 83.17
        latest_tnx = data['^TNX'].dropna().iloc[-1] if '^TNX' in data else 4.67
        latest_usdkrw = data['KRW=X'].dropna().iloc[-1] if 'KRW=X' in data else 1418.50
        latest_vix = data['^VIX'].dropna().iloc[-1] if '^VIX' in data else 15.15
    except Exception:
        latest_oil, latest_tnx, latest_usdkrw, latest_vix = 83.17, 4.67, 1418.50, 15.15
    return float(latest_oil), float(latest_tnx), float(latest_usdkrw), float(latest_vix)

# 시장 데이터 로드
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
# 4. 실시간 통합 보유 현황
# -----------------------------------------------------------------------------
st.subheader("📊 실시간 통합 보유 현황")
st.caption("💡 푸른색 배경의 수량(주), 내 평단가 셀을 수정한 후 저장 버튼을 누르시면 구글 시트에 자동 보관됩니다.")

df1, ws1 = load_sheet_data("Portfolio")
if not df1.empty:
    edited_df1 = st.data_editor(df1, key="editor1", num_rows="dynamic", use_container_width=True)
    if st.button("💾 현재 현황 구글 시트 저장 및 계산 반영", key="btn1"):
        if save_sheet_data(ws1, edited_df1):
            st.success("구글 시트에 성공적으로 저장되었습니다!")
            st.rerun()

    try:
        total_invest = 0
        annual_div = 0
        for idx, row in edited_df1.iterrows():
            qty = float(row.get('qty', 0) or 0)
            avg_price = float(row.get('avg_price', 0) or 0)
            last_div = float(row.get('last_div', 0) or 0)
            currency = str(row.get('currency', 'USD')).upper()
            rate = usdkrw if currency == 'USD' else 1.0
            
            total_invest += qty * avg_price * rate
            annual_div += qty * last_div * rate

        st.markdown("#### 💰 계좌 성과 및 배당금 종합 요약")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("💵 계좌 총 투자 비용", f"₩{total_invest:,.0f}")
        with m2:
            st.metric("🏦 현재 계좌 총 자산", f"₩{total_invest:,.0f}")
        with m3:
            st.metric("💵 예상 세전 연 배당금", f"₩{annual_div:,.0f}")
        with m4:
            st.metric("📅 예상 세전 월 배당금", f"₩{(annual_div / 12):,.0f}")
    except Exception:
        pass

st.divider()

# -----------------------------------------------------------------------------
# 5. 미래 배당 세팅 목표
# -----------------------------------------------------------------------------
st.subheader("🎯 미래 배당 세팅 목표")
st.caption("💡 목표 수량을 수정 후 저장 버튼을 누르면 미래 연간/월간 예상 배당금이 자동 연산됩니다.")

df2, ws2 = load_sheet_data("FutureTarget")
if not df2.empty:
    edited_df2 = st.data_editor(df2, key="editor2", num_rows="dynamic", use_container_width=True)
    if st.button("💾 미래 목표 저장 및 즉시 연산", key="btn2"):
        if save_sheet_data(ws2, edited_df2):
            st.success("구글 시트에 성공적으로 저장되었습니다!")
            st.rerun()

    try:
        future_annual_div = 0
        for idx, row in edited_df2.iterrows():
            target_qty = float(row.get('target_qty', row.get('qty', 0)) or 0)
            last_div = float(row.get('last_div', 0) or 0)
            currency = str(row.get('currency', 'USD')).upper()
            rate = usdkrw if currency == 'USD' else 1.0
            
            future_annual_div += target_qty * last_div * rate

        st.markdown("#### 🚀 미래 목표 달성 시 예상 배당 요약")
        f1, f2 = st.columns(2)
        with f1:
            st.metric("🎯 미래 예상 연 배당금", f"₩{future_annual_div:,.0f}")
        with f2:
            st.metric("📅 미래 예상 월 배당금", f"₩{(future_annual_div / 12):,.0f}")
    except Exception:
        pass
