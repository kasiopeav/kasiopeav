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

# 백업용 초기 원본 보유 데이터
DEFAULT_JAEGUK_HOLDINGS = pd.DataFrame([
    {"티커": "JEPQ", "수량(주)": 660, "내 평단가": 53.71, "예상 1주당 배당금": 0.5600},
    {"티커": "QQQI", "수량(주)": 627, "내 평단가": 53.07, "예상 1주당 배당금": 0.6346},
    {"티커": "SCHD", "수량(주)": 722, "내 평단가": 27.12, "예상 1주당 배당금": 0.2500},
    {"티커": "QLD", "수량(주)": 23, "내 평단가": 84.29, "예상 1주당 배당금": 0.0300},
    {"티커": "KODEX 미국배당커버드콜", "수량(주)": 194, "내 평단가": 11288, "예상 1주당 배당금": 99.0000},
    {"티커": "KODEX 200타겟위클리커버", "수량(주)": 299, "내 평단가": 15436, "예상 1주당 배당금": 262.0000}
])

DEFAULT_GWANGHEE_HOLDINGS = pd.DataFrame([
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
            st.error(f"구글 시트 저장 중 오류: {e}")

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
# 2. HEADER & MACRO INDICATORS
# ---------------------------------------------------------
st.title("💖 재국♡광희 인생 계획")

weekday_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
now = datetime.now()
today_str = f"📅 오늘은 {now.strftime('%Y년 %m월 %d일')} {weekday_kr[now.weekday()]}입니다."
st.markdown(f"#### {today_str}")
st.divider()

macro = get_macro_data()
usd_krw = macro.get("환율 (USD/KRW)", 1420.08)

col1, col2, col3, col4 = st.columns(4)
with col1:
    brent_val = macro.get('브렌트유', 83.20)
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
# 3. 실시간 통합 보유 현황 및 계좌 요약 (원본 UI 형태 복원)
# ---------------------------------------------------------
def render_holdings_and_summary(owner_name, sheet, default_df):
    st.subheader(f"📊 실시간 통합 보유 현황 ({owner_name})")
    st.caption("💡 푸른색 배경의 수량(주) ✏️, 내 평단가 ✏️ 셀을 수정하신 후 저장 버튼을 누르시면 구글 시트에 자동 보관됩니다.")
    
    raw_df = load_data(sheet, default_df)
    
    display_rows = []
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
            else:
                avg_str = f"₩{avg_p * usd_krw:,.0f} [${avg_p:.2f}]"
                cur_str = f"₩{cur_p * usd_krw:,.0f} [${cur_p:.2f}]"
                invested = qty * avg_p * usd_krw
                tot_str = f"₩{invested:,.0f} [${qty * avg_p:,.2f}]"
                div_str = f"₩{div_p * usd_krw:,.0f} [${div_p:.4f}]"

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
    
    # 수정 가능한 data_editor
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        key=f"editor_holdings_{owner_name}"
    )

    if st.button(f"🎴 현재 현황 구글 시트 저장 및 계산 반영 ({owner_name})", key=f"btn_save_holdings_{owner_name}"):
        save_df = edited_df[["티커", "수량(주)", "내 평단가", "예상 1주당 배당금"]]
        save_data(sheet, save_df)
        st.success(f"{owner_name} 님의 현황이 구글 시트에 안전하게 보관되었습니다!")
        st.rerun()

    # ⭐ 사용자가 입력창(edited_df)에서 편집한 즉시 반응하는 실시간 연산 로직
    tot_invested = 0.0
    tot_annual_div_pre = 0.0

    for idx, row in edited_df.iterrows():
        ticker = str(row.get("티커", "")).strip()
        try:
            qty = float(str(row.get("수량(주)", 0)).replace(",", ""))
            avg_p = float(str(row.get("내 평단가", 0)).replace(",", "").replace("$", "").replace("₩", ""))
            div_p = float(str(row.get("예상 1주당 배당금", 0)).replace(",", "").replace("$", "").replace("₩", ""))
        except:
            qty, avg_p, div_p = 0.0, 0.0, 0.0

        if ticker:
            is_kr = "KODEX" in ticker or "TIGER" in ticker or "RISE" in ticker or ticker.endswith(".KS") or ticker.endswith(".KQ")
            if is_kr:
                invested = qty * avg_p
                annual_div = qty * div_p * 12
            else:
                invested = qty * avg_p * usd_krw
                annual_div = qty * div_p * 12 * usd_krw

            tot_invested += invested
            tot_annual_div_pre += annual_div

    tot_annual_div_post = tot_annual_div_pre * 0.846
    tot_monthly_div_post = tot_annual_div_post / 12
    yield_rate = (tot_annual_div_post / tot_invested * 100) if tot_invested > 0 else 0.0

    # 원본 계좌 성과 메트릭 (3열 구조)
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

    return tot_invested, tot_annual_div_pre, tot_annual_div_post

# 재국 & 광희 섹션 각각 호출
invest_j, div_pre_j, div_post_j = render_holdings_and_summary("재국", sheet_jaeguk, DEFAULT_JAEGUK_HOLDINGS)
st.markdown("---")
invest_g, div_pre_g, div_post_g = render_holdings_and_summary("광희", sheet_gwanghee, DEFAULT_GWANGHEE_HOLDINGS)

st.divider()

# ---------------------------------------------------------
# 4. 미래 배당 세팅 목표 (원본 표 형식 및 실시간 연산 적용)
# ---------------------------------------------------------
def render_future_target_table(owner_name, sheet, default_df):
    st.subheader(f"🎯 미래 배당 세팅 목표 ({owner_name})")
    
    raw_df = load_data(sheet, default_df)
    target_rows = []

    for idx, row in raw_df.iterrows():
        ticker = str(row.get("티커", "")).strip()
        try:
            qty = float(str(row.get("목표 수량(주) ✏️", row.get("수량(주)", row.get("수량", 0)))).replace(",", ""))
            div_p = float(str(row.get("예상 1주당 배당금 ✏️", row.get("예상 1주당 배당금", 0))).replace(",", "").replace("$", "").replace("₩", ""))
        except:
            qty, div_p = 0.0, 0.0

        if ticker:
            cur_p = get_stock_price(ticker)
            is_kr = "KODEX" in ticker or "TIGER" in ticker or "RISE" in ticker or ticker.endswith(".KS") or ticker.endswith(".KQ")

            if is_kr:
                cur_str = f"₩{cur_p:,.0f}" if cur_p > 0 else "₩10,000"
                seed = qty * (cur_p if cur_p > 0 else 10000)
                seed_str = f"₩{seed:,.0f}"
                div_str = f"₩{div_p:,.0f}"
                annual_div_post = (qty * div_p * 12) * 0.846
            else:
                cur_str = f"₩{cur_p * usd_krw:,.0f} [${cur_p:.2f}]" if cur_p > 0 else f"₩84,346 [$59.34]"
                seed = qty * (cur_p if cur_p > 0 else 59.34) * usd_krw
                seed_str = f"₩{seed:,.0f} [${qty * (cur_p if cur_p > 0 else 59.34):,.2f}]"
                div_str = f"₩{div_p * usd_krw:,.0f} [${div_p:.4f}]"
                annual_div_post = (qty * div_p * 12 * usd_krw) * 0.846

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
        key=f"editor_target_{owner_name}"
    )

    if st.button(f"💾 미래 목표 구글 시트 저장 및 즉시 연산 ({owner_name})", key=f"btn_save_target_{owner_name}"):
        save_df = edited_target_df[["티커", "목표 수량(주) ✏️", "예상 1주당 배당금 ✏️"]]
        save_df.columns = ["티커", "수량(주)", "예상 1주당 배당금"]
        save_data(sheet, save_df)
        st.success(f"{owner_name} 님의 미래 배당 목표 설정이 성공적으로 업데이트되었습니다!")
        st.rerun()

    # ⭐ 미래 목표 연산 실시간 반영
    tot_target_seed = 0.0
    tot_target_div_post = 0.0

    for idx, row in edited_target_df.iterrows():
        ticker = str(row.get("티커", "")).strip()
        try:
            qty = float(str(row.get("목표 수량(주) ✏️", 0)).replace(",", ""))
            div_p = float(str(row.get("예상 1주당 배당금 ✏️", 0)).replace(",", "").replace("$", "").replace("₩", ""))
        except:
            qty, div_p = 0.0, 0.0

        if ticker:
            cur_p = get_stock_price(ticker)
            is_kr = "KODEX" in ticker or "TIGER" in ticker or "RISE" in ticker or ticker.endswith(".KS") or ticker.endswith(".KQ")

            if is_kr:
                seed = qty * (cur_p if cur_p > 0 else 10000)
                annual_div_post = (qty * div_p * 12) * 0.846
            else:
                seed = qty * (cur_p if cur_p > 0 else 59.34) * usd_krw
                annual_div_post = (qty * div_p * 12 * usd_krw) * 0.846

            tot_target_seed += seed
            tot_target_div_post += annual_div_post

    return tot_target_seed, tot_target_div_post

target_seed_j, target_div_j = render_future_target_table("재국", sheet_jaeguk, DEFAULT_JAEGUK_HOLDINGS)
st.markdown("<br>", unsafe_allow_html=True)
target_seed_g, target_div_g = render_future_target_table("광희", sheet_gwanghee, DEFAULT_GWANGHEE_HOLDINGS)

st.divider()

# ---------------------------------------------------------
# 5. 미래 예상 배당금 요약 (초기 5열 메트릭 복원 및 재국+광희 합산)
# ---------------------------------------------------------
st.subheader("🎯 미래 재국♡광희 예상 배당금 요약")

comb_invest = invest_j + invest_g
comb_div_pre = div_pre_j + div_pre_g
comb_div_post = div_post_j + div_post_g
comb_m_div_post = comb_div_post / 12
comb_yield = (comb_div_post / comb_invest * 100) if comb_invest > 0 else 0.0

total_target_seed = target_seed_j + target_seed_g
add_seed_needed = max(0.0, total_target_seed - comb_invest)

fc1, fc2, fc3, fc4, fc5 = st.columns(5)
with fc1:
    st.metric("💵 세전 예상 총 배당금 (연간)", f"₩{comb_div_pre:,.0f}")
with fc2:
    st.metric("💰 세후 예상 총 배당금 (연간)", f"₩{comb_div_post:,.0f}")
with fc3:
    st.metric("📅 월 예상 배당금 (세후)", f"₩{comb_m_div_post:,.0f}")
with fc4:
    st.metric("📈 세후 예상 배당률 (%)", f"{comb_yield:.2f}%")
with fc5:
    st.metric(
        "🎯 목표 달성 추가 필요 시드",
        f"₩{add_seed_needed:,.0f}",
        delta=f"목표시드: ₩{total_target_seed:,.0f}"
    )
