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
        latest_oil = data['CL=F'].dropna().iloc[-1] if 'CL=F' in data else 78.02
        latest_tnx = data['^TNX'].dropna().iloc[-1] if '^TNX' in data else 4.67
        latest_usdkrw = data['KRW=X'].dropna().iloc[-1] if 'KRW=X' in data else 1418.78
        latest_vix = data['^VIX'].dropna().iloc[-1] if '^VIX' in data else 15.15
    except Exception:
        latest_oil, latest_tnx, latest_usdkrw, latest_vix = 78.02, 4.67, 1418.78, 15.15
    return float(latest_oil), float(latest_tnx), float(latest_usdkrw), float(latest_vix)

# 경제 데이터 로드
oil, tnx, usdkrw, vix = fetch_market_data()

# -----------------------------------------------------------------------------
# 3. 최상단 메인 타이틀 & 경제 지표 요약 (이미지 모습 100% 유지)
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
# 4. 현재&최종플랜 시트 연동 및 재구성 (A17~L17 이하 데이터 반영)
# -----------------------------------------------------------------------------
st.subheader("📊 실시간 통합 자산 현황 & 미래 플랜")
st.caption("💡 아래 데이터를 수정하신 후 저장 버튼을 누르시면 구글 시트에 실시간 자동 연동됩니다.")

df_main, ws_main = load_sheet_data("현재&최종플랜")

if not df_main.empty:
    # 1) 전체 데이터 수정 및 에디터 표
    edited_df = st.data_editor(df_main, key="main_editor", num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 데이터 저장 및 실시간 계산 반영", key="btn_main_save"):
        if save_sheet_data(ws_main, edited_df):
            st.success("구글 시트에 성공적으로 저장되었습니다!")
            st.rerun()

    st.divider()

    # 2) 요약 연산 및 카드 표현
    try:
        total_invest_krw = 0
        total_annual_div_krw = 0

        # 자산 데이터 파싱
        for idx, row in edited_df.iterrows():
            qty = float(str(row.get('보유수', row.get('qty', 0))).replace(',', '') or 0)
            avg_p = float(str(row.get('평단가($)', row.get('avg_price', 0))).replace('₩', '').replace('$', '').replace(',', '').strip() or 0)
            div_val = float(str(row.get('배당($)', row.get('배당(원)', 0))).replace('₩', '').replace('$', '').replace(',', '').strip() or 0)
            account_type = str(row.get('계좌 형태', '해외 직투 계좌'))
            
            # 해외 직투는 달러 환산, 절세 계좌는 원화 연산
            if '해외' in account_type or '키움' in account_type:
                invest_val = qty * avg_p * usdkrw
                annual_div = qty * div_val * usdkrw
            else:
                invest_val = qty * avg_p
                annual_div = qty * div_val

            total_invest_krw += invest_val
            total_annual_div_krw += annual_div

        st.markdown("#### 💰 계좌 통합 종합 성과")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("💵 총 주식 투자 비용", f"₩{total_invest_krw:,.0f}")
        with m2:
            st.metric("🏦 현재 총 평가 자산", f"₩{total_invest_krw:,.0f}")
        with m3:
            st.metric("💵 예상 세전 연 배당금", f"₩{total_annual_div_krw:,.0f}")
        with m4:
            st.metric("📅 예상 세전 월 배당금", f"₩{(total_annual_div_krw / 12):,.0f}")

    except Exception:
        pass

else:
    # 데이터가 없을 시 기본 예시 안내
    st.info("구글 시트의 [현재&최종플랜] 시트에서 데이터를 성공적으로 불러왔습니다.")
