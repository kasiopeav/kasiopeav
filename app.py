import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# PAGE CONFIG
st.set_page_config(
    page_title="재국♡광희 인생 계획",
    page_icon="💖",
    layout="wide"
)

# ---------------------------------------------------------
# 1. GOOGLE SHEETS CONNECTOR
# ---------------------------------------------------------
@st.cache_resource
def init_gspread():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["spreadsheet"]["sheet_id"])
    return spreadsheet

DEFAULT_JAEGUK_DATA = pd.DataFrame([
    {"티커": "JEPQ", "수량(주)": 660, "내 평단가": 53.71, "예상 1주당 배당금": 0.5600},
    {"티커": "QQQI", "수량(주)": 627, "내 평단가": 53.07, "예상 1주당 배당금": 0.6346},
    {"티커": "SCHD", "수량(주)": 722, "내 평단가": 27.12, "예상 1주당 배당금": 0.2500},
    {"티커": "QLD", "수량(주)": 23, "내 평단가": 84.29, "예상 1주당 배당금": 0.0300},
    {"티커": "KODEX 미국배당커버드콜", "수량(주)": 194, "내 평단가": 11288, "예상 1주당 배당금": 99.0000},
    {"티커": "KODEX 200타겟위클리커버", "수량(주)": 299, "내 평단가": 15436, "예상 1주당 배당금": 262.0000}
])

DEFAULT_GWANGHEE_DATA = pd.DataFrame([
    {"티커": "QQQI", "수량(주)": 240, "내 평단가": 53.11, "예상 1주당 배당금": 0.6346}
])

try:
    spreadsheet = init_gspread()
    sheet_jaeguk = spreadsheet.get_worksheet(0)
    try:
        sheet_gwanghee = spreadsheet.worksheet("광희")
    except:
        sheet_gwanghee = None
except Exception as e:
    sheet_jaeguk = None
    sheet_gwanghee = None

def load_data(sheet, default_df):
    if sheet is None:
        return default_df.copy()
    try:
        rows = sheet.get_all_values()
        if not rows or len(rows) < 2:
            return default_df.copy()
        headers = [str(h).strip() for h in rows[0]]
        df = pd.DataFrame(rows[1:], columns=headers)
        if not any("티커" in c for c in df.columns):
            return default_df.copy()
        return df
    except:
        return default_df.copy()

def save_data(sheet, df):
    if sheet is not None:
        try:
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
        except Exception as e:
            st.error(f"저장 실패: {e}")

@st.cache_data(ttl=3600)
def get_macro_data():
    tickers = {
        "브렌트유": "BZ=F",
        "미 10년물 국채 금리": "^TNX",
        "환율 (USD/KRW)": "KRW=X",
        "VIX 지수": "^VIX"
    }
    macro_info = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) > 0:
                price = hist['Close'].iloc[-1]
                macro_info[name] = price
            else:
                macro_info[name] = 0.0
        except:
            macro_info[name] = 0.0
    return macro_info

# ---------------------------------------------------------
# DASHBOARD HEADER & MACRO INDICATORS
# ---------------------------------------------------------
st.title("💖 재국♡광희 인생 계획")

weekday_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
now = datetime.now()
today_str = f"📅 오늘은 {now.strftime('%Y년 %m월 %d일')} {weekday_kr[now.weekday()]}입니다."
st.markdown(f"#### {today_str}")
st.divider()

macro = get_macro_data()
usd_krw = macro.get("환율 (USD/KRW)", 1464.49)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("브렌트유 시세", f"${macro.get('브렌트유', 0):.2f} USD")
with col2:
    st.metric("미 10년물 국채 금리", f"{macro.get('미 10년물 국채 금리', 0):.2f} %")
with col3:
    st.metric("환율 (USD/KRW)", f"₩{usd_krw:,.2f}")
with col4:
    st.metric("VIX 지수", f"{macro.get('VIX 지수', 0):.2f}")

st.divider()

# ---------------------------------------------------------
# HOLDINGS & CALCULATIONS FUNCTION (초기 원본 방식 복원)
# ---------------------------------------------------------
def render_account_section(owner_name, sheet, default_df):
    st.subheader(f"📊 실시간 통합 보유 현황 ({owner_name})")
    st.caption("💡 푸른색 배경의 수량(주), 내 평단가 셀을 수정하신 후 저장 버튼을 누르시면 구글 시트에 자동 보관됩니다.")
    
    df = load_data(sheet, default_df)
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        key=f"editor_{owner_name}"
    )

    if st.button(f"💾 {owner_name} 현황 구글 시트 저장 및 계산 반영", key=f"btn_{owner_name}"):
        save_data(sheet, edited_df)
        st.success(f"{owner_name} 님의 데이터가 저장되었습니다!")
        st.rerun()

    # 계산 변수
    total_invested = 0.0
    total_annual_div_before = 0.0
    
    for idx, row in edited_df.iterrows():
        ticker = str(row.get("티커", "")).strip()
        try:
            qty = float(str(row.get("수량(주)", row.get("수량", 0))).replace(",", ""))
            avg_price = float(str(row.get("내 평단가", 0)).replace(",", "").replace("$", "").replace("₩", ""))
            div_per_share = float(str(row.get("예상 1주당 배당금", 0)).replace(",", "").replace("$", "").replace("₩", ""))
        except:
            qty, avg_price, div_per_share = 0.0, 0.0, 0.0

        if ticker:
            if "KODEX" in ticker or "TIGER" in ticker or "RISE" in ticker or ticker.endswith(".KS") or ticker.endswith(".KQ"):
                invested = qty * avg_price
                annual_div = qty * div_per_share * 12
            else:
                invested = qty * avg_price * usd_krw
                annual_div = qty * div_per_share * 12 * usd_krw

            total_invested += invested
            total_annual_div_before += annual_div

    total_annual_div_after = total_annual_div_before * 0.846  # 세후 15.4% 차감
    monthly_div_after = total_annual_div_after / 12
    yield_rate = (total_annual_div_after / total_invested * 100) if total_invested > 0 else 0.0

    # 초기 버전 스타일 3열 지표 메트릭
    st.markdown(f"#### 💰 {owner_name} 계좌 요약")
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.metric("📈 포트폴리오 세후 예상 배당률", f"{yield_rate:.2f}%")
    with mc2:
        st.metric("🎁 올해 받은 총 배당금", f"₩{total_annual_div_after:,.0f}")
    with mc3:
        st.metric("📅 이번달 / 올해 예상 배당금 (세후)", f"월 ₩{monthly_div_after:,.0f}", delta=f"연간 ₩{total_annual_div_after:,.0f}")

    return total_invested, total_annual_div_before, total_annual_div_after, monthly_div_after, yield_rate

# 재국 & 광희 섹션 출력
invest_j, div_pre_j, div_post_j, m_div_j, yield_j = render_account_section("재국", sheet_jaeguk, DEFAULT_JAEGUK_DATA)
st.markdown("---")
invest_g, div_pre_g, div_post_g, m_div_g, yield_g = render_account_section("광희", sheet_gwanghee, DEFAULT_GWANGHEE_DATA)

st.divider()

# ---------------------------------------------------------
# 미래 예상 배당금 요약 (초기 버전 스타일 5열 메트릭 카드 복원)
# ---------------------------------------------------------
st.subheader("🎯 미래 재국♡광희 예상 배당금 요약")

tot_invest = invest_j + invest_g
tot_div_pre = div_pre_j + div_pre_g
tot_div_post = div_post_j + div_post_g
tot_m_div = tot_div_post / 12
tot_yield = (tot_div_post / tot_invest * 100) if tot_invest > 0 else 0.0

fc1, fc2, fc3, fc4, fc5 = st.columns(5)
with fc1:
    st.metric("💵 세전 예상 총 배당금 (연간)", f"₩{tot_div_pre:,.0f}")
with fc2:
    st.metric("💰 세후 예상 총 배당금 (연간)", f"₩{tot_div_post:,.0f}")
with fc3:
    st.metric("📅 월 예상 배당금 (세후)", f"₩{tot_m_div:,.0f}")
with fc4:
    st.metric("📈 세후 예상 배당률 (%)", f"{tot_yield:.2f}%")
with fc5:
    st.metric("🎯 총 합산 투자 비용", f"₩{tot_invest:,.0f}")
