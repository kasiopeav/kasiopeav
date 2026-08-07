import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# PAGE CONFIG
st.set_page_config(
    page_title="재국♡광희 인생 계획",
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

try:
    spreadsheet = init_gspread()
    # 첫 번째 워크시트(인덱스 0)를 무조건 기본 데이터(재국)로 설정
    sheet_jaeguk = spreadsheet.get_worksheet(0)
    
    # '광희' 시트 검색, 없으면 생성
    try:
        sheet_gwanghee = spreadsheet.worksheet("광희")
    except gspread.exceptions.WorksheetNotFound:
        sheet_gwanghee = spreadsheet.add_worksheet(title="광희", rows="100", cols="20")
        headers = sheet_jaeguk.row_values(1)
        if headers:
            sheet_gwanghee.append_row(headers)
except Exception as e:
    st.error(f"구글 시트 연동 실패: {e}")
    st.stop()

# ---------------------------------------------------------
# 2. DATA LOAD & SAVE FUNCTIONS
# ---------------------------------------------------------
def load_data(sheet):
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        return pd.DataFrame()
    
    headers = [str(h).strip() for h in rows[0]]
    # 빈 열 이름 처리
    headers = [h if h != "" else f"Unnamed_{i}" for i, h in enumerate(headers)]
    
    df = pd.DataFrame(rows[1:], columns=headers)
    return df

def save_data(sheet, df):
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# ---------------------------------------------------------
# 3. YFINANCE DATA FETCHERS
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
def get_stock_info(ticker_symbol):
    try:
        t = yf.Ticker(str(ticker_symbol).strip())
        info = t.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0.0
        dividend_yield = info.get('dividendYield') or 0.0
        if dividend_yield > 1:
            dividend_yield = dividend_yield / 100
        return current_price, dividend_yield
    except:
        return 0.0, 0.0

# ---------------------------------------------------------
# 4. DASHBOARD HEADER & MACRO INDICATORS
# ---------------------------------------------------------
st.title("💖 재국♡광희 인생 계획")

weekday_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
now = datetime.now()
today_str = f"📅 오늘은 {now.strftime('%Y년 %m월 %d일')} {weekday_kr[now.weekday()]}입니다."
st.markdown(f"#### {today_str}")
st.divider()

macro = get_macro_data()
usd_krw = macro.get("환율 (USD/KRW)", 1350.0)

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
# 5. INTEGRATED HOLDINGS PROCESSOR
# ---------------------------------------------------------
def process_holdings_ui(owner_name, sheet):
    st.subheader(f"📊 실시간 통합 보유 현황 ({owner_name})")
    
    df = load_data(sheet)
    
    if df.empty:
        st.info(f"{owner_name} 님의 등록된 보유 주식이 없습니다.")
        return df, 0.0, 0.0

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        key=f"editor_{owner_name}"
    )

    if st.button(f"💾 {owner_name} 현황 구글 시트 저장 및 계산 반영", key=f"btn_{owner_name}"):
        save_data(sheet, edited_df)
        st.success(f"{owner_name} 님의 데이터가 구글 시트에 저장되었습니다!")
        st.rerun()

    total_invested = 0.0
    total_annual_div = 0.0

    # 컬럼 이름 유연하게 탐색 (티커, 수량, 내 평단가)
    ticker_col = next((col for col in edited_df.columns if "티커" in col or "Ticker" in col.lower()), None)
    qty_col = next((col for col in edited_df.columns if "수량" in col or "Qty" in col.lower()), None)
    price_col = next((col for col in edited_df.columns if "평단가" in col or "Price" in col.lower()), None)

    if ticker_col and qty_col and price_col:
        for idx, row in edited_df.iterrows():
            ticker = str(row.get(ticker_col, "")).strip()
            
            # 수량 및 평단가에서 숫자 이외 문자 제거 처리
            try:
                raw_qty = str(row.get(qty_col, "0")).replace(",", "").replace("$", "").replace("₩", "").strip()
                qty = float(raw_qty) if raw_qty else 0.0
            except:
                qty = 0.0

            try:
                raw_price = str(row.get(price_col, "0")).replace(",", "").replace("$", "").replace("₩", "").strip()
                avg_price = float(raw_price) if raw_price else 0.0
            except:
                avg_price = 0.0

            if ticker:
                cur_price, div_yield = get_stock_info(ticker)
                if not (ticker.endswith(".KS") or ticker.endswith(".KQ")):
                    invested = qty * avg_price * usd_krw
                    annual_div = (qty * cur_price * usd_krw) * div_yield
                else:
                    invested = qty * avg_price
                    annual_div = (qty * cur_price) * div_yield

                total_invested += invested
                total_annual_div += annual_div

    return edited_df, total_invested, total_annual_div

df_j, invest_j, div_j = process_holdings_ui("재국", sheet_jaeguk)
st.markdown("---")
df_g, invest_g, div_g = process_holdings_ui("광희", sheet_gwanghee)

st.divider()

# ---------------------------------------------------------
# 6. SUMMARY SECTION
# ---------------------------------------------------------
st.subheader("💰 계좌 성과 및 배당금 종합 요약")

tab_j, tab_g = st.tabs(["재국 계좌 요약", "광희 계좌 요약"])

def render_summary_tab(invest_val, div_val):
    c1, c2, c3 = st.columns(3)
    div_rate = (div_val / invest_val * 100) if invest_val > 0 else 0.0
    with c1:
        st.metric("총 투자 비용", f"₩{invest_val:,.0f}")
    with c2:
        st.metric("예상 연간 배당금", f"₩{div_val:,.0f}")
    with c3:
        st.metric("예상 배당률", f"{div_rate:.2f}%")

with tab_j:
    render_summary_tab(invest_j, div_j)

with tab_g:
    render_summary_tab(invest_g, div_g)

st.divider()

# ---------------------------------------------------------
# 7. FUTURE DIVIDEND TARGETS
# ---------------------------------------------------------
col_target_j, col_target_g = st.columns(2)

with col_target_j:
    st.subheader("🎯 미래 배당 세팅 목표 (재국)")
    target_j = st.number_input("재국 목표 월 배당금 (원화)", value=1000000, step=100000, key="target_j")
    current_m_j = div_j / 12
    progress_j = min(current_m_j / target_j, 1.0) if target_j > 0 else 0.0
    st.progress(progress_j)
    st.caption(f"현재 월 배당금: ₩{current_m_j:,.0f} / 목표: ₩{target_j:,.0f} ({progress_j*100:.1f}%)")

with col_target_g:
    st.subheader("🎯 미래 배당 세팅 목표 (광희)")
    target_g = st.number_input("광희 목표 월 배당금 (원화)", value=1000000, step=100000, key="target_g")
    current_m_g = div_g / 12
    progress_g = min(current_m_g / target_g, 1.0) if target_g > 0 else 0.0
    st.progress(progress_g)
    st.caption(f"현재 월 배당금: ₩{current_m_g:,.0f} / 목표: ₩{target_g:,.0f} ({progress_g*100:.1f}%)")

st.divider()

# ---------------------------------------------------------
# 8. COMBINED FUTURE DIVIDEND SUMMARY
# ---------------------------------------------------------
st.subheader("👩‍❤️‍👨 미래 재국♡광희 예상 배당금")

total_combined_invest = invest_j + invest_g
total_combined_annual_div = div_j + div_g
total_combined_monthly_div = total_combined_annual_div / 12

mc1, mc2, mc3 = st.columns(3)
with mc1:
    st.metric("합산 총 투자 비용", f"₩{total_combined_invest:,.0f}")
with mc2:
    st.metric("합산 예상 연간 배당금", f"₩{total_combined_annual_div:,.0f}")
with mc3:
    st.metric("합산 예상 월 평균 배당금", f"₩{total_combined_monthly_div:,.0f}")
