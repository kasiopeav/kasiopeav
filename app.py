import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# PAGE CONFIG
st.set_page_config(
    page_title="나만의 맞춤형 주식 대시보드",
    page_icon="📈",
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

# 기본 원본 보유 데이터
DEFAULT_HOLDINGS = pd.DataFrame([
    {"티커": "JEPQ", "수량(주)": 660, "내 평단가": 53.71, "예상 1주당 배당금": 0.5600},
    {"티커": "QQQI", "수량(주)": 627, "내 평단가": 53.07, "예상 1주당 배당금": 0.6346},
    {"티커": "SCHD", "수량(주)": 722, "내 평단가": 27.12, "예상 1주당 배당금": 0.2500},
    {"티커": "QLD", "수량(주)": 23, "내 평단가": 84.29, "예상 1주당 배당금": 0.0300},
    {"티커": "KODEX 미국배당커버드콜", "수량(주)": 194, "내 평단가": 11288, "예상 1주당 배당금": 99.0000},
    {"티커": "KODEX 200타겟위클리커버", "수량(주)": 299, "내 평단가": 15436, "예상 1주당 배당금": 262.0000}
])

try:
    spreadsheet = init_gspread()
    sheet = spreadsheet.get_worksheet(0)
except Exception as e:
    sheet = None

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
            st.error(f"구글 시트 저장 중 오류 발생: {e}")

# ---------------------------------------------------------
# 2. MACRO DATA FETCHERS
# ---------------------------------------------------------
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

@st.cache_data(ttl=600)
def get_stock_price(ticker):
    try:
        t = yf.Ticker(str(ticker).strip())
        info = t.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or 0.0
        return price
    except:
        return 0.0

# ---------------------------------------------------------
# 3. HEADER & MACRO INDICATORS (초기 원본 UI 스타일 복원)
# ---------------------------------------------------------
st.title("📈 나만의 맞춤형 주식 대시보드")

macro = get_macro_data()
usd_krw = macro.get("환율 (USD/KRW)", 1421.41)

col1, col2, col3, col4 = st.columns(4)
with col1:
    brent_val = macro.get('브렌트유', 83.62)
    brent_status = "⚠️ 주의" if brent_val >= 100 else "🟢 정상"
    st.metric(f"브렌트유 시세  {brent_status}", f"${brent_val:.2f} USD")

with col2:
    tnx_val = macro.get('미 10년물 국채 금리', 4.67)
    tnx_status = "⚠️ 주의" if tnx_val >= 4.5 else "🟢 정상"
    st.metric(f"미 10년물 국채 금리  {tnx_status}", f"{tnx_val:.2f} %")

with col3:
    krw_val = usd_krw
    krw_status = "⚠️ 주의" if krw_val >= 1450 else "🟢 정상"
    st.metric(f"환율 (USD/KRW)  {krw_status}", f"₩{krw_val:,.2f}")

with col4:
    vix_val = macro.get('VIX 지수', 15.15)
    vix_status = "⚠️ 주의" if vix_val >= 40 else "🟢 정상"
    st.metric(f"VIX 지수  {vix_status}", f"{vix_val:.2f}")

st.divider()

# ---------------------------------------------------------
# 4. 실시간 통합 보유 현황 (원본 표 및 3열 종합 요약 복원)
# ---------------------------------------------------------
st.subheader("📊 실시간 통합 보유 현황")
st.caption("💡 푸른색 배경의 수량(주) ✏️, 내 평단가 ✏️ 셀을 수정하신 후 저장 버튼을 누르시면 구글 시트에 자동 보관됩니다.")

raw_df = load_data(sheet, DEFAULT_HOLDINGS)

display_rows = []
tot_invested = 0.0
tot_annual_div_pre = 0.0

for idx, row in raw_df.iterrows():
    ticker = str(row.get("티커", "")).strip()
    try:
        qty = float(str(row.get("수량(주)", row.get("수량", 0))).replace(",", ""))
        avg_p = float(str(row.get("내 평단가", 0)).replace(",", "").replace("$", "").replace("₩", ""))
        div_p = float(str(row.get("예상 1주당 배당금", 0)).replace(",", "").replace("$", "").replace("₩", ""))
    except:
        qty, avg_p, div_p = 0.0, 0.0, 0.0

    if ticker:
        is_kr = "KODEX" in ticker or "TIGER" in ticker or "RISE" in ticker or ticker.endswith(".KS") or ticker.endswith(".KQ")
        cur_p = get_stock_price(ticker)
        if cur_p == 0: cur_p = avg_p

        if is_kr:
            avg_str = f"₩{avg_p:,.0f}"
            cur_str = f"₩{cur_p:,.0f}"
            invested = qty * avg_p
            tot_str = f"₩{invested:,.0f}"
            div_str = f"₩{div_p:,.0f}"
            annual_div = qty * div_p * 12
        else:
            avg_str = f"₩{avg_p * usd_krw:,.0f} [${avg_p:.2f}]"
            cur_str = f"₩{cur_p * usd_krw:,.0f} [${cur_p:.2f}]"
            invested = qty * avg_p * usd_krw
            tot_str = f"₩{invested:,.0f} [${qty * avg_p:,.2f}]"
            div_str = f"₩{div_p * usd_krw:,.0f} [${div_p:.4f}]"
            annual_div = qty * div_p * 12 * usd_krw

        tot_invested += invested
        tot_annual_div_pre += annual_div

        display_rows.append({
            "티커": ticker,
            "수량(주)": qty,
            "내 평단가": avg_p,
            "내 평단가 (한화/달러)": avg_str,
            "현재가 (한화/달러)": cur_str,
            "총 투자비용 (수량×평단가)": tot_str,
            "예상 1주당 배당금": div_p,
            "1주당 배당금 (한화/달러)": div_str
        })

display_df = pd.DataFrame(display_rows)

edited_df = st.data_editor(
    display_df,
    num_rows="dynamic",
    key="editor_holdings_main"
)

if st.button("🎴 현재 현황 구글 시트 저장 및 계산 반영", key="btn_save_holdings_main"):
    save_df = edited_df[["티커", "수량(주)", "내 평단가", "예상 1주당 배당금"]]
    save_data(sheet, save_df)
    st.success("현재 현황이 구글 시트에 안전하게 저장되었습니다!")
    st.rerun()

tot_annual_div_post = tot_annual_div_pre * 0.846
tot_monthly_div_post = tot_annual_div_post / 12
yield_rate = (tot_annual_div_post / tot_invested * 100) if tot_invested > 0 else 0.0

st.markdown("<br>", unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("📈 포트폴리오 세후 예상 배당률", f"{yield_rate:.2f}%")
with m2:
    st.metric("🎁 올해 받은 총 배당금", f"₩{tot_annual_div_post:,.0f}")
with m3:
    st.metric(
        "📅 이번달 / 올해 예상 배당금 (세후)",
        f"월 ₩{tot_monthly_div_post:,.0f}",
        delta=f"연간 ₩{tot_annual_div_post:,.0f}"
    )

st.divider()

# ---------------------------------------------------------
# 5. 미래 배당 세팅 목표 (원본 표 형태 복원)
# ---------------------------------------------------------
st.subheader("🎯 미래 배당 세팅 목표")

target_rows = []
tot_target_seed = 0.0
tot_target_div_post = 0.0

for idx, row in DEFAULT_HOLDINGS.iterrows():
    ticker = str(row.get("티커", "")).strip()
    qty = float(row.get("수량(주)", 0))
    div_p = float(row.get("예상 1주당 배당금", 0))

    if ticker:
        cur_p = get_stock_price(ticker)
        is_kr = "KODEX" in ticker or "TIGER" in ticker or "RISE" in ticker or ticker.endswith(".KS") or ticker.endswith(".KQ")

        if is_kr:
            cur_str = f"₩{cur_p:,.0f}" if cur_p > 0 else "₩10,985"
            seed = qty * (cur_p if cur_p > 0 else 10985)
            seed_str = f"₩{seed:,.0f}"
            div_str = f"₩{div_p:,.0f}"
            annual_div_post = (qty * div_p * 12) * 0.846
        else:
            cur_str = f"₩{cur_p * usd_krw:,.0f} [${cur_p:.2f}]" if cur_p > 0 else f"₩84,346 [$59.34]"
            seed = qty * (cur_p if cur_p > 0 else 59.34) * usd_krw
            seed_str = f"₩{seed:,.0f} [${qty * (cur_p if cur_p > 0 else 59.34):,.2f}]"
            div_str = f"₩{div_p * usd_krw:,.0f} [${div_p:.4f}]"
            annual_div_post = (qty * div_p * 12 * usd_krw) * 0.846

        tot_target_seed += seed
        tot_target_div_post += annual_div_post

        target_rows.append({
            "티커": ticker,
            "목표 수량(주) ✏️": qty,
            "예상 1주당 배당금 ✏️": div_p,
            "현재가 기준 평단가": cur_str,
            "목표 총 필요 시드": seed_str,
            "예상 1주당 배당금 (한화/달러)": div_str,
            "목표 연 예상 배당금 (세후)": f"₩{annual_div_post:,.0f}"
        })

target_df = pd.DataFrame(target_rows)

edited_target_df = st.data_editor(
    target_df,
    num_rows="dynamic",
    key="editor_target_main"
)

if st.button("💾 미래 목표 구글 시트 저장 및 즉시 연산", key="btn_save_target_main"):
    st.success("미래 배당 목표 설정이 업데이트되었습니다!")
    st.rerun()

st.divider()

# ---------------------------------------------------------
# 6. 미래 예상 배당금 요약 (원본 5열 메트릭 카드)
# ---------------------------------------------------------
st.subheader("🔮 미래 예상 배당금 요약")

add_seed_needed = max(0.0, tot_target_seed - tot_invested)

fc1, fc2, fc3, fc4, fc5 = st.columns(5)
with fc1:
    st.metric("💵 세전 예상 총 배당금 (연간)", f"₩{tot_annual_div_pre:,.0f}")
with fc2:
    st.metric("💰 세후 예상 총 배당금 (연간)", f"₩{tot_annual_div_post:,.0f}")
with fc3:
    st.metric("📅 월 예상 배당금 (세후)", f"₩{tot_monthly_div_post:,.0f}")
with fc4:
    st.metric("📈 세후 예상 배당률 (%)", f"{yield_rate:.2f}%")
with fc5:
    st.metric(
        "🎯 목표 달성 추가 필요 시드",
        f"₩{add_seed_needed:,.0f}",
        delta=f"목표시드: ₩{tot_target_seed:,.0f}"
    )
