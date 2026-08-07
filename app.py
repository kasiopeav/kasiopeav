import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="재국♡광희 주식 대시보드 (ver2)", layout="wide")

TAX_RATE = 0.154  # 배당소득세율 (15.4%)

# ---------------------------------------------------------
# 0. 구글 시트 연동 설정
# ---------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )
        return gspread.authorize(credentials)
    except Exception:
        return None

gc = get_gspread_client()

# 기본 포트폴리오 (재국)
DEFAULT_PORTFOLIO_JG = [
    {"ticker": "JEPQ", "ticker_symbol": "JEPQ", "qty": 660, "avg_price": 53.71, "currency": "USD", "last_div": 0.56, "total_received_div": 3101187},
    {"ticker": "QQQI", "ticker_symbol": "QQQI", "qty": 627, "avg_price": 53.07, "currency": "USD", "last_div": 0.6346, "total_received_div": 680792},
    {"ticker": "SCHD", "ticker_symbol": "SCHD", "qty": 722, "avg_price": 27.12, "currency": "USD", "last_div": 0.25, "total_received_div": 253716},
    {"ticker": "QLD",  "ticker_symbol": "QLD",  "qty": 23,  "avg_price": 84.29, "currency": "USD", "last_div": 0.03, "total_received_div": 0},
    {"ticker": "KODEX 미국배당커버드콜 액티브", "ticker_symbol": "441680.KS", "qty": 194, "avg_price": 11288, "currency": "KRW", "last_div": 99, "total_received_div": 299148},
    {"ticker": "KODEX 200타겟위클리커버드콜", "ticker_symbol": "480460.KS", "qty": 299, "avg_price": 15436, "currency": "KRW", "last_div": 262, "total_received_div": 1517126}
]

# 기본 포트폴리오 (광희)
DEFAULT_PORTFOLIO_GH = [
    {"ticker": "QQQI", "ticker_symbol": "QQQI", "qty": 240, "avg_price": 53.11, "currency": "USD", "last_div": 0.6346, "total_received_div": 339613}
]

def load_sheet_data(worksheet_name, default_data):
    if gc is None:
        return default_data
    try:
        sh = gc.open_by_key(st.secrets["spreadsheet"]["sheet_id"])
        try:
            ws = sh.worksheet(worksheet_name)
        except Exception:
            ws = sh.add_worksheet(title=worksheet_name, rows=100, cols=20)
            ws.update([list(default_data[0].keys())] + [list(x.values()) for x in default_data])
        
        data = ws.get_all_records()
        if not data:
            return default_data
        return data
    except Exception:
        return default_data

def save_sheet_data(worksheet_name, data):
    if gc is None:
        return
    try:
        sh = gc.open_by_key(st.secrets["spreadsheet"]["sheet_id"])
        ws = sh.worksheet(worksheet_name)
        ws.clear()
        if data:
            headers = list(data[0].keys())
            rows = [headers] + [[row[h] for h in headers] for row in data]
            ws.update(rows)
            st.cache_data.clear()
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")

# Session State 초기화
if "portfolio_jg" not in st.session_state:
    st.session_state.portfolio_jg = load_sheet_data("Portfolio", DEFAULT_PORTFOLIO_JG)

if "portfolio_gh" not in st.session_state:
    st.session_state.portfolio_gh = load_sheet_data("Portfolio_GH", DEFAULT_PORTFOLIO_GH)

if "future_target_jg" not in st.session_state:
    st.session_state.future_target_jg = load_sheet_data("FutureTarget", DEFAULT_PORTFOLIO_JG)

if "future_target_gh" not in st.session_state:
    st.session_state.future_target_gh = load_sheet_data("FutureTarget_GH", DEFAULT_PORTFOLIO_GH)

# CSS 스타일 정의 (ver2 동일)
st.markdown("""
    <style>
    .macro-card { background-color: #f8f9fa; border-radius: 12px; padding: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e9ecef; text-align: center; }
    .macro-card-warning { background-color: #fff5f5; border-radius: 12px; padding: 16px; box-shadow: 0 4px 6px rgba(229, 62, 62, 0.1); border: 1px solid #feb2b2; text-align: center; }
    .macro-title { font-size: 14px; color: #495057; font-weight: 600; margin-bottom: 6px; }
    .macro-value { font-size: 24px; font-weight: 800; color: #1a202c; }
    .status-badge-ok { display: inline-block; background-color: #c6f6d5; color: #22543d; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 12px; }
    .status-badge-warn { display: inline-block; background-color: #fed7d7; color: #9b2c2c; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 12px; }
    div[data-testid="stDataEditor"] div[role="columnheader"] { background-color: #e2e8f0 !important; color: #0f172a !important; font-weight: 800 !important; font-size: 15px !important; border-bottom: 2px solid #94a3b8 !important; }
    div[data-testid="stDataEditor"] div[role="columnheader"]:nth-child(2), div[data-testid="stDataEditor"] div[role="columnheader"]:nth-child(3) { background-color: #dbeafe !important; color: #1e40af !important; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 거시지표 (ver2 동일)
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def get_macro_indicators():
    try:
        brent = yf.Ticker("BZ=F").fast_info['lastPrice']
        us10y = yf.Ticker("^TNX").fast_info['lastPrice']
        usd_krw = yf.Ticker("KRW=X").fast_info['lastPrice']
        vix = yf.Ticker("^VIX").fast_info['lastPrice']
        return brent, us10y, usd_krw, vix
    except Exception:
        return 100.0, 4.5, 1450.0, 20.0

brent, us10y, usd_krw, vix = get_macro_indicators()

st.title("💖 재국♡광희 맞춤형 주식 대시보드 (ver2)")
st.write("")

def render_macro_card(title, value, unit, is_warn):
    card_class = "macro-card-warning" if is_warn else "macro-card"
    badge_class = "status-badge-warn" if is_warn else "status-badge-ok"
    badge_text = "⚠️ 주의" if is_warn else "🟢 정상"
    st.markdown(f"""
        <div class="{card_class}">
            <div class="macro-title">{title} <span class="{badge_class}">{badge_text}</span></div>
            <div class="macro-value">{value} <span style="font-size: 14px; font-weight: 500;">{unit}</span></div>
        </div>
    """, unsafe_allow_html=True)

macro_col1, macro_col2, macro_col3, macro_col4 = st.columns(4)
with macro_col1: render_macro_card("브렌트유 시세", f"${brent:.2f}", "USD", brent >= 100)
with macro_col2: render_macro_card("미 10년물 국채 금리", f"{us10y:.2f}", "%", us10y >= 4.5)
with macro_col3: render_macro_card("환율 (USD/KRW)", f"₩{usd_krw:,.2f}", "", usd_krw >= 1450)
with macro_col4: render_macro_card("VIX 지수", f"{vix:.2f}", "", vix >= 40)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 공통 포트폴리오 랜더링 함수
# ---------------------------------------------------------
def render_portfolio_section(owner_name, portfolio_key, sheet_name):
    st.subheader(f"📊 실시간 통합 보유 현황 ({owner_name})")
    st.caption("💡 푸른색 배경의 **수량(주) ✏️**, **내 평단가 ✏️** 셀을 수정한 후 저장 버튼을 누르시면 구글 시트에 자동 보관됩니다.")

    df_data = []
    total_eval_krw, total_buy_krw, total_received_div_all_krw, monthly_est_div_krw = 0.0, 0.0, 0.0, 0.0

    for item in st.session_state[portfolio_key]:
        symbol = item.get("ticker_symbol", item["ticker"])
        qty, avg_p, curr, last_div, tot_div = item["qty"], item["avg_price"], item["currency"], item["last_div"], item["total_received_div"]
        total_received_div_all_krw += tot_div

        try:
            current_p = yf.Ticker(symbol).fast_info['lastPrice']
        except Exception:
            current_p = avg_p

        if curr == "USD":
            buy_val_krw = qty * avg_p * usd_krw
            eval_val_krw = qty * current_p * usd_krw
            avg_price_disp = f"₩{avg_p * usd_krw:,.0f} [${avg_p:,.2f}]"
            current_price_disp = f"₩{current_p * usd_krw:,.0f} [${current_p:,.2f}]"
            invest_cost_disp = f"₩{buy_val_krw:,.0f} [${qty * avg_p:,.2f}]"
            div_per_share_disp = f"₩{last_div * usd_krw:,.0f} [${last_div:.4f}]"
            monthly_div_item_krw = qty * last_div * usd_krw * (1 - TAX_RATE)
        else:
            buy_val_krw, eval_val_krw = qty * avg_p, qty * current_p
            avg_price_disp, current_price_disp = f"₩{avg_p:,.0f}", f"₩{current_p:,.0f}"
            invest_cost_disp, div_per_share_disp = f"₩{buy_val_krw:,.0f}", f"₩{last_div:,.0f}"
            monthly_div_item_krw = qty * last_div * (1 - TAX_RATE)

        return_rate = ((eval_val_krw - buy_val_krw) / buy_val_krw) * 100 if buy_val_krw > 0 else 0.0
        return_rate_disp = f"🔴 +{return_rate:.2f}%" if return_rate > 0 else (f"🔵 {return_rate:.2f}%" if return_rate < 0 else "⚪ 0.00%")

        total_buy_krw += buy_val_krw
        total_eval_krw += eval_val_krw
        monthly_est_div_krw += monthly_div_item_krw

        df_data.append({
            "티커": item["ticker"],
            "수량(주) ✏️": qty,
            "내 평단가 ✏️": avg_p,
            "내 평단가 (한화/달러)": avg_price_disp,
            "현재가 (한화/달러)": current_price_disp,
            "총 투자비용 (수량×평단가)": invest_cost_disp,
            "1주당 배당금 (한화/달러)": div_per_share_disp,
            "월 예상 배당금 (세후)": f"₩{monthly_div_item_krw:,.0f}",
            "현재 수익률": return_rate_disp
        })

    df_display = pd.DataFrame(df_data)

    edited_df = st.data_editor(
        df_display,
        disabled=["티커", "내 평단가 (한화/달러)", "현재가 (한화/달러)", "총 투자비용 (수량×평단가)", "1주당 배당금 (한화/달러)", "월 예상 배당금 (세후)", "현재 수익률"],
        column_config={
            "수량(주) ✏️": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
            "내 평단가 ✏️": st.column_config.NumberColumn(format="$%.2f")
        },
        use_container_width=True, hide_index=True, key=f"editor_current_{portfolio_key}"
    )

    if st.button(f"💾 현재 현황 구글 시트 저장 및 계산 반영 ({owner_name})", use_container_width=True, key=f"btn_save_curr_{portfolio_key}"):
        for idx, row in edited_df.iterrows():
            st.session_state[portfolio_key][idx]["qty"] = int(row["수량(주) ✏️"])
            st.session_state[portfolio_key][idx]["avg_price"] = float(row["내 평단가 ✏️"])
        
        save_sheet_data(sheet_name, st.session_state[portfolio_key])
        st.success(f"[{owner_name}] 구글 시트에 성공적으로 저장되었습니다!")
        st.rerun()

    # 종합 요약
    st.subheader(f"💰 계좌 성과 및 배당금 종합 요약 ({owner_name})")
    account_return_rate = ((total_eval_krw - total_buy_krw) / total_buy_krw) * 100 if total_buy_krw > 0 else 0.0
    yearly_est_div_krw = monthly_est_div_krw * 12
    current_total_account_val = total_eval_krw + total_received_div_all_krw
    portfolio_div_yield = (yearly_est_div_krw / total_eval_krw * 100) if total_eval_krw > 0 else 0.0

    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1: st.metric(label="💵 계좌 총 투자 비용 (총 매수원금)", value=f"₩{total_buy_krw:,.0f}")
    with row1_col2: st.metric(label="🏦 현재 계좌 총 자산", value=f"₩{current_total_account_val:,.0f}", delta=f"총 평가손익: ₩{total_eval_krw - total_buy_krw:+,.0f}")
    with row1_col3: st.metric(label="📊 순수 주식 수익률 (배당 제외)", value=f"{account_return_rate:+.2f}%")

    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1: st.metric(label="📈 포트폴리오 세후 예상 배당률", value=f"{portfolio_div_yield:.2f}%")
    with row2_col2: st.metric(label="🎁 올해 받은 총 배당금", value=f"₩{total_received_div_all_krw:,.0f}")
    with row2_col3: st.metric(label="📅 이번달 / 올해 예상 배당금 (세후)", value=f"월 ₩{monthly_est_div_krw:,.0f}", delta=f"연간 ₩{yearly_est_div_krw:,.0f}")

    return total_buy_krw

# ---------------------------------------------------------
# 공통 미래 목표 랜더링 함수
# ---------------------------------------------------------
def render_future_target_section(owner_name, target_key, current_total_buy, sheet_name):
    st.subheader(f"🎯 미래 배당 세팅 목표 ({owner_name})")
    future_df_data = []
    future_total_buy_krw, future_yearly_pre_tax_div_krw, future_yearly_post_tax_div_krw = 0.0, 0.0, 0.0

    for item in st.session_state[target_key]:
        symbol, qty, curr, last_div = item.get("ticker_symbol", item["ticker"]), item["qty"], item["currency"], item["last_div"]
        try: current_p = yf.Ticker(symbol).fast_info['lastPrice']
        except Exception: current_p = item["avg_price"]

        if curr == "USD":
            buy_val_krw = qty * current_p * usd_krw
            pre_tax_div_annual_krw = qty * (last_div * 12) * usd_krw
            post_tax_div_annual_krw = pre_tax_div_annual_krw * (1 - TAX_RATE)
            target_price_disp = f"₩{current_p * usd_krw:,.0f} [${current_p:,.2f}]"
            invest_cost_disp = f"₩{buy_val_krw:,.0f} [${qty * current_p:,.2f}]"
            div_per_share_disp = f"₩{last_div * usd_krw:,.0f} [${last_div:.4f}]"
        else:
            buy_val_krw = qty * current_p
            pre_tax_div_annual_krw = qty * (last_div * 12)
            post_tax_div_annual_krw = pre_tax_div_annual_krw * (1 - TAX_RATE)
            target_price_disp = f"₩{current_p:,.0f}"
            invest_cost_disp = f"₩{buy_val_krw:,.0f}"
            div_per_share_disp = f"₩{last_div:,.0f}"

        future_total_buy_krw += buy_val_krw
        future_yearly_pre_tax_div_krw += pre_tax_div_annual_krw
        future_yearly_post_tax_div_krw += post_tax_div_annual_krw

        future_df_data.append({
            "티커": item["ticker"],
            "목표 수량(주) ✏️": qty,
            "예상 1주당 배당금 ✏️": last_div,
            "현재가 기준 평단가": target_price_disp,
            "목표 총 필요 시드": invest_cost_disp,
            "예상 1주당 배당금 (한화/달러)": div_per_share_disp,
            "목표 연 예상 배당금 (세후)": f"₩{post_tax_div_annual_krw:,.0f}"
        })

    edited_future_df = st.data_editor(
        pd.DataFrame(future_df_data),
        disabled=["티커", "현재가 기준 평단가", "목표 총 필요 시드", "예상 1주당 배당금 (한화/달러)", "목표 연 예상 배당금 (세후)"],
        column_config={"목표 수량(주) ✏️": st.column_config.NumberColumn(min_value=0, step=1, format="%d"), "예상 1주당 배당금 ✏️": st.column_config.NumberColumn(format="$%.4f")},
        use_container_width=True, hide_index=True, key=f"editor_future_{target_key}"
    )

    if st.button(f"💾 미래 목표 구글 시트 저장 및 즉시 연산 ({owner_name})", use_container_width=True, key=f"btn_save_fut_{target_key}"):
        for idx, row in edited_future_df.iterrows():
            st.session_state[target_key][idx]["qty"] = int(row["목표 수량(주) ✏️"])
            st.session_state[target_key][idx]["last_div"] = float(row["예상 1주당 배당금 ✏️"])
        
        save_sheet_data(sheet_name, st.session_state[target_key])
        st.success(f"[{owner_name}] 미래 목표가 저장되었습니다!")
        st.rerun()

    st.markdown(f"#### 🔮 미래 예상 배당금 요약 ({owner_name})")
    future_monthly_post_tax_div_krw = future_yearly_post_tax_div_krw / 12
    future_div_yield = (future_yearly_post_tax_div_krw / future_total_buy_krw * 100) if future_total_buy_krw > 0 else 0.0
    needed_additional_seed = max(0.0, future_total_buy_krw - current_total_buy)

    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
    with f_col1: st.metric(label="💵 세전 예상 총 배당금 (연간)", value=f"₩{future_yearly_pre_tax_div_krw:,.0f}")
    with f_col2: st.metric(label="💰 세후 예상 총 배당금 (연간)", value=f"₩{future_yearly_post_tax_div_krw:,.0f}")
    with f_col3: st.metric(label="📅 월 예상 배당금 (세후)", value=f"₩{future_monthly_post_tax_div_krw:,.0f}")
    with f_col4: st.metric(label="📈 세후 예상 배당률 (%)", value=f"{future_div_yield:.2f}%")
    with f_col5: st.metric(label="🎯 목표 달성 추가 필요 시드", value=f"₩{needed_additional_seed:,.0f}", delta=f"목표시드: ₩{future_total_buy_krw:,.0f}")


# ---------------------------------------------------------
# 메인 세션 차례대로 배치 (스크롤)
# ---------------------------------------------------------

# 1. 재국 보유 현황 & 미래 목표
buy_jg = render_portfolio_section("재국", "portfolio_jg", "Portfolio")
st.markdown("---")
render_future_target_section("재국", "future_target_jg", buy_jg, "FutureTarget")

st.markdown("---")
st.markdown("---")

# 2. 광희 보유 현황 & 미래 목표
buy_gh = render_portfolio_section("광희", "portfolio_gh", "Portfolio_GH")
st.markdown("---")
render_future_target_section("광희", "future_target_gh", buy_gh, "FutureTarget_GH")

st.markdown("---")

# ---------------------------------------------------------
# 추가 매수 시뮬레이터 (ver2 동일)
# ---------------------------------------------------------
st.subheader("🧮 추가 매수 시뮬레이터")
all_items = st.session_state.portfolio_jg + st.session_state.portfolio_gh
ticker_options = list(dict.fromkeys([item["ticker"] for item in all_items]))

sim_col1, sim_col2, sim_col3 = st.columns(3)
with sim_col1: selected_ticker = st.selectbox("종목 선택", ticker_options)
with sim_col2: add_qty = st.number_input("추가 구매 수량(주)", min_value=1, value=10, step=1)

selected_item = next(item for item in all_items if item["ticker"] == selected_ticker)
symbol, curr, last_div = selected_item.get("ticker_symbol", selected_item["ticker"]), selected_item["currency"], selected_item["last_div"]

try: current_p = yf.Ticker(symbol).fast_info['lastPrice']
except Exception: current_p = selected_item["avg_price"]

if curr == "USD":
    required_cost_krw = add_qty * current_p * usd_krw
    add_monthly_div_krw = add_qty * last_div * usd_krw * (1 - TAX_RATE)
    price_str = f"₩{current_p * usd_krw:,.0f} [${current_p:,.2f}]"
else:
    required_cost_krw = add_qty * current_p
    add_monthly_div_krw = add_qty * last_div * (1 - TAX_RATE)
    price_str = f"₩{current_p:,.0f}"

with sim_col3: st.write(f"**현재가:** {price_str}")

st.info(f"""
💡 **{selected_ticker}** 종목을 **{add_qty}주** 매수할 때 예상 수치:
* **필요 금액:** **₩{required_cost_krw:,.0f}**
* **월 예상 배당금 증가 (세후):** +**₩{add_monthly_div_krw:,.0f}**
* **연 예상 배당금 증가 (세후):** +**₩{add_monthly_div_krw * 12:,.0f}**
""")
