import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="재국♡광희 주식 대시보드 (ver6)", layout="wide")

TAX_RATE = 0.154  # 배당소득세율 (15.4%)

# 분기 배당 종목 정의
QUARTERLY_DIV_TICKERS = ["SCHD"]

KR_TICKER_MAP = {
    "KODEX 미국배당커버드콜 액티브": {"code": "441680", "default_div": 99.0, "default_price": 13110.0},
    "KODEX 미국 AI테크 TOP10 타겟커버드콜": {"code": "480410", "default_div": 149.0, "default_price": 12335.0},
    "KODEX 200타겟위클리커버드콜": {"code": "480460", "default_div": 252.0, "default_price": 18920.0},
    "KODEX 금융고배당TOP10타겟위클리커버트콜": {"code": "489240", "default_div": 162.0, "default_price": 12035.0},
    "RISE 미국테크100데일리고정커버드콜": {"code": "486250", "default_div": 271.0, "default_price": 10980.0},
    "TIGER 미국나스닥 100 타겟 데일리 커버드콜": {"code": "482730", "default_div": 127.0, "default_price": 10905.0},
    "KODEX 미국S&P500 데일리 커버드콜 OTM": {"code": "482720", "default_div": 119.0, "default_price": 9795.0}
}

# ---------------------------------------------------------
# 0. 구글 시트 연동 & 실시간 시세 조회
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

def fetch_realtime_price(ticker_name, ticker_symbol, currency):
    if currency == "KRW" or ticker_name in KR_TICKER_MAP:
        code = KR_TICKER_MAP.get(ticker_name, {}).get("code")
        if not code and ticker_symbol:
            code = str(ticker_symbol).replace(".KS", "").replace(".KQ", "").strip()
        if code:
            try:
                url = f"https://polling.finance.naver.com/api/realtime/market/stock/price?stocks={code}"
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get(url, headers=headers, timeout=3).json()
                datas = res.get("result", {}).get("areas", [{}])[0].get("datas", [])
                if datas:
                    price = datas[0].get("closePrice") or datas[0].get("now")
                    if price:
                        return float(price)
            except Exception:
                pass
        if ticker_name in KR_TICKER_MAP:
            return KR_TICKER_MAP[ticker_name]["default_price"]

    if ticker_symbol:
        try:
            p = float(yf.Ticker(ticker_symbol).fast_info['lastPrice'])
            if p > 0:
                return p
        except Exception:
            pass

    return None

DEFAULT_PORTFOLIO_JG = [
    {"ticker": "JEPQ", "ticker_symbol": "JEPQ", "qty": 660, "avg_price": 53.71, "current_price": 59.34, "currency": "USD", "last_div": 0.56},
    {"ticker": "QQQI", "ticker_symbol": "QQQI", "qty": 627, "avg_price": 53.07, "current_price": 54.75, "currency": "USD", "last_div": 0.6346},
    {"ticker": "SCHD", "ticker_symbol": "SCHD", "qty": 722, "avg_price": 27.12, "current_price": 33.70, "currency": "USD", "last_div": 0.25},
    {"ticker": "QLD",  "ticker_symbol": "QLD",  "qty": 23,  "avg_price": 84.29, "current_price": 90.13, "currency": "USD", "last_div": 0.03},
    {"ticker": "KODEX 미국배당커버드콜 액티브", "ticker_symbol": "441680.KS", "qty": 194, "avg_price": 11288, "current_price": 13110, "currency": "KRW", "last_div": 99},
    {"ticker": "KODEX 미국 AI테크 TOP10 타겟커버드콜", "ticker_symbol": "480410.KS", "qty": 149, "avg_price": 12224, "current_price": 12335, "currency": "KRW", "last_div": 149},
    {"ticker": "KODEX 200타겟위클리커버드콜", "ticker_symbol": "480460.KS", "qty": 344, "avg_price": 16687, "current_price": 18920, "currency": "KRW", "last_div": 262},
    {"ticker": "KODEX 금융고배당TOP10타겟위클리커버트콜", "ticker_symbol": "489240.KS", "qty": 215, "avg_price": 12272, "current_price": 12035, "currency": "KRW", "last_div": 162},
    {"ticker": "RISE 미국테크100데일리고정커버드콜", "ticker_symbol": "486250.KS", "qty": 250, "avg_price": 10919, "current_price": 10980, "currency": "KRW", "last_div": 271},
    {"ticker": "TIGER 미국나스닥 100 타겟 데일리 커버드콜", "ticker_symbol": "482730.KS", "qty": 53, "avg_price": 10443, "current_price": 10905, "currency": "KRW", "last_div": 127},
    {"ticker": "KODEX 미국S&P500 데일리 커버드콜 OTM", "ticker_symbol": "482720.KS", "qty": 26, "avg_price": 9744, "current_price": 9795, "currency": "KRW", "last_div": 119}
]

DEFAULT_PORTFOLIO_GH = [
    {"ticker": "QQQI", "ticker_symbol": "QQQI", "qty": 240, "avg_price": 53.11, "current_price": 54.75, "currency": "USD", "last_div": 0.6346}
]

DEFAULT_DIV_HISTORY_JG = []
DEFAULT_DIV_HISTORY_GH = []

def load_sheet_data(worksheet_name, default_data):
    if gc is None:
        return default_data
    try:
        sh = gc.open_by_key(st.secrets["spreadsheet"]["sheet_id"])
        try:
            ws = sh.worksheet(worksheet_name)
        except Exception:
            ws = sh.add_worksheet(title=worksheet_name, rows=200, cols=10)
            if default_data:
                ws.update([list(default_data[0].keys())] + [list(x.values()) for x in default_data])
            else:
                ws.update([["month", "account_type", "ticker", "amount_krw"]])
        
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
        else:
            ws.update([["month", "account_type", "ticker", "amount_krw"]])
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

if "div_history_jg" not in st.session_state:
    st.session_state.div_history_jg = load_sheet_data("Dividend_History", DEFAULT_DIV_HISTORY_JG)

if "div_history_gh" not in st.session_state:
    st.session_state.div_history_gh = load_sheet_data("Dividend_History_GH", DEFAULT_DIV_HISTORY_GH)

# CSS 스타일 정의 (가독성 시각 강화)
st.markdown("""
    <style>
    .macro-card { background-color: #f8f9fa; border-radius: 12px; padding: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e9ecef; text-align: center; }
    .macro-card-warning { background-color: #fff5f5; border-radius: 12px; padding: 16px; box-shadow: 0 4px 6px rgba(229, 62, 62, 0.1); border: 1px solid #feb2b2; text-align: center; }
    .macro-title { font-size: 14px; color: #495057; font-weight: 600; margin-bottom: 6px; }
    .macro-value { font-size: 24px; font-weight: 800; color: #1a202c; }
    .status-badge-ok { display: inline-block; background-color: #c6f6d5; color: #22543d; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 12px; }
    .status-badge-warn { display: inline-block; background-color: #fed7d7; color: #9b2c2c; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 12px; }
    
    .total-highlight-card {
        background: linear-gradient(135deg, #fff5f7 0%, #ffe6ec 100%);
        border: 2px solid #f6ad55;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 16px rgba(246, 173, 85, 0.15);
        margin-bottom: 24px;
    }
    .total-title {
        font-size: 20px;
        font-weight: 900;
        color: #9b2c2c;
        margin-bottom: 16px;
        text-align: center;
    }
    
    div[data-testid="stDataEditor"] div[role="columnheader"] { 
        background-color: #e2e8f0 !important; 
        color: #0f172a !important; 
        font-weight: 800 !important; 
        font-size: 15px !important; 
        border-bottom: 2px solid #94a3b8 !important; 
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 900 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 거시지표
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

st.title("💖 재국♡광희 맞춤형 주식 대시보드 (ver6)")
st.write("")

# 메인 탭 분리
main_tab1, main_tab2 = st.tabs(["📊 주식 대시보드", "📅 월별 배당금 입금 장부 (2026~)"])

with main_tab1:
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

    def render_portfolio_section(owner_name, portfolio_key, history_key, sheet_name):
        st.subheader(f"📊 실시간 통합 보유 현황 ({owner_name})")
        st.caption("💡 푸른색 배경의 **수량(주) ✏️**, **내 평단가 ✏️**, **현재가 ✏️** 셀을 수정한 후 저장 버튼을 누르시면 구글 시트에 자동 보관됩니다.")

        df_data = []
        total_eval_krw, total_buy_krw, monthly_est_div_krw = 0.0, 0.0, 0.0

        history_list = st.session_state.get(history_key, [])
        total_received_div_all_krw = sum(float(h.get("amount_krw", 0) or 0) for h in history_list)

        for item in st.session_state[portfolio_key]:
            ticker_name = item.get("ticker", "")
            symbol = item.get("ticker_symbol", ticker_name)
            curr = item.get("currency", "USD")

            try: qty = float(item.get("qty", 0) or 0)
            except Exception: qty = 0.0

            try: avg_p = float(item.get("avg_price", 0) or 0)
            except Exception: avg_p = 0.0

            try: last_div = float(item.get("last_div", 0) or 0)
            except Exception: last_div = 0.0

            if last_div == 0.0 and ticker_name in KR_TICKER_MAP:
                last_div = KR_TICKER_MAP[ticker_name]["default_div"]

            current_p = item.get("current_price")
            if current_p is None or float(current_p or 0) == 0:
                if ticker_name in KR_TICKER_MAP:
                    current_p = KR_TICKER_MAP[ticker_name]["default_price"]
                else:
                    current_p = fetch_realtime_price(ticker_name, symbol, curr)
                    if current_p is None or current_p == 0:
                        current_p = avg_p
            else:
                current_p = float(current_p)

            annual_div_multiplier = 4.0 if ticker_name in QUARTERLY_DIV_TICKERS else 12.0

            if curr == "USD":
                avg_p_disp = f"${avg_p:,.2f}"
                current_p_disp = f"${current_p:,.2f}"
                buy_val_krw = qty * avg_p * usd_krw
                eval_val_krw = qty * current_p * usd_krw
                invest_cost_disp = f"₩{buy_val_krw:,.0f} [${qty * avg_p:,.2f}]"
                div_per_share_disp = f"₩{last_div * usd_krw:,.0f} [${last_div:.4f}]"
                
                annual_pre_tax_div_krw = qty * (last_div * annual_div_multiplier) * usd_krw
                monthly_div_item_krw = (annual_pre_tax_div_krw / 12.0) * (1 - TAX_RATE)
            else:
                avg_p_disp = f"₩{avg_p:,.0f}"
                current_p_disp = f"₩{current_p:,.0f}"
                buy_val_krw, eval_val_krw = qty * avg_p, qty * current_p
                invest_cost_disp, div_per_share_disp = f"₩{buy_val_krw:,.0f}", f"₩{last_div:,.0f}"
                
                annual_pre_tax_div_krw = qty * (last_div * annual_div_multiplier)
                monthly_div_item_krw = (annual_pre_tax_div_krw / 12.0) * (1 - TAX_RATE)

            return_rate = ((eval_val_krw - buy_val_krw) / buy_val_krw) * 100 if buy_val_krw > 0 else 0.0
            return_rate_disp = f"🔴 +{return_rate:.2f}%" if return_rate > 0 else (f"🔵 {return_rate:.2f}%" if return_rate < 0 else "⚪ 0.00%")

            total_buy_krw += buy_val_krw
            total_eval_krw += eval_val_krw
            monthly_est_div_krw += monthly_div_item_krw

            df_data.append({
                "티커": ticker_name,
                "수량(주) ✏️": qty,
                "내 평단가 ✏️": avg_p_disp,
                "현재가 ✏️": current_p_disp,
                "총 투자비용 (수량×평단가)": invest_cost_disp,
                "1주당 배당금 (한화/달러)": div_per_share_disp,
                "월 예상 배당금 (세후)": f"₩{monthly_div_item_krw:,.0f}",
                "현재 수익률": return_rate_disp
            })

        df_display = pd.DataFrame(df_data)

        edited_df = st.data_editor(
            df_display,
            disabled=["티커", "총 투자비용 (수량×평단가)", "1주당 배당금 (한화/달러)", "월 예상 배당금 (세후)", "현재 수익률"],
            column_config={
                "수량(주) ✏️": st.column_config.NumberColumn(min_value=0, step=1, format="%d")
            },
            use_container_width=True, hide_index=True, key=f"editor_current_{portfolio_key}"
        )

        if st.button(f"💾 현재 현황 구글 시트 저장 및 계산 반영 ({owner_name})", use_container_width=True, key=f"btn_save_curr_{portfolio_key}"):
            for idx, row in edited_df.iterrows():
                st.session_state[portfolio_key][idx]["qty"] = int(row["수량(주) ✏️"])
                
                raw_avg = str(row["내 평단가 ✏️"]).replace("₩", "").replace("$", "").replace(",", "").strip()
                try: st.session_state[portfolio_key][idx]["avg_price"] = float(raw_avg)
                except Exception: pass

                raw_curr = str(row["현재가 ✏️"]).replace("₩", "").replace("$", "").replace(",", "").strip()
                try: st.session_state[portfolio_key][idx]["current_price"] = float(raw_curr)
                except Exception: pass

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
        with row2_col2: st.metric(label="🎁 올해 받은 총 배당금 (2026 장부 누적)", value=f"₩{total_received_div_all_krw:,.0f}")
        with row2_col3: st.metric(label="📅 이번달 / 올해 예상 배당금 (세후)", value=f"월 ₩{monthly_est_div_krw:,.0f}", delta=f"연간 ₩{yearly_est_div_krw:,.0f}")

        return total_buy_krw

    def render_future_target_section(owner_name, target_key, current_total_buy, sheet_name, portfolio_key):
        st.subheader(f"🎯 미래 배당 세팅 목표 ({owner_name})")
        future_df_data = []
        future_total_buy_krw, future_yearly_pre_tax_div_krw, future_yearly_post_tax_div_krw = 0.0, 0.0, 0.0

        curr_price_map = {item["ticker"]: item.get("current_price") for item in st.session_state[portfolio_key]}

        for item in st.session_state[target_key]:
            ticker_name = item.get("ticker", "")
            symbol = item.get("ticker_symbol", ticker_name)
            curr = item.get("currency", "USD")

            try: qty = float(item.get("qty", 0) or 0)
            except Exception: qty = 0.0

            try: last_div = float(item.get("last_div", 0) or 0)
            except Exception: last_div = 0.0

            if last_div == 0.0 and ticker_name in KR_TICKER_MAP:
                last_div = KR_TICKER_MAP[ticker_name]["default_div"]

            current_p = curr_price_map.get(ticker_name) or item.get("current_price")
            if current_p is None or float(current_p or 0) == 0:
                if ticker_name in KR_TICKER_MAP:
                    current_p = KR_TICKER_MAP[ticker_name]["default_price"]
                else:
                    current_p = fetch_realtime_price(ticker_name, symbol, curr)
                    if current_p is None or current_p == 0:
                        try: current_p = float(item.get("avg_price", 0) or 0)
                        except Exception: current_p = 0.0
            else:
                current_p = float(current_p)

            annual_div_multiplier = 4.0 if ticker_name in QUARTERLY_DIV_TICKERS else 12.0

            if curr == "USD":
                buy_val_krw = qty * current_p * usd_krw
                pre_tax_div_annual_krw = qty * (last_div * annual_div_multiplier) * usd_krw
                post_tax_div_annual_krw = pre_tax_div_annual_krw * (1 - TAX_RATE)
                target_price_disp = f"₩{current_p * usd_krw:,.0f} [${current_p:,.2f}]"
                invest_cost_disp = f"₩{buy_val_krw:,.0f} [${qty * current_p:,.2f}]"
                div_per_share_disp = f"${last_div:.4f}"
                monthly_div_item_krw = post_tax_div_annual_krw / 12.0
            else:
                buy_val_krw = qty * current_p
                pre_tax_div_annual_krw = qty * (last_div * annual_div_multiplier)
                post_tax_div_annual_krw = pre_tax_div_annual_krw * (1 - TAX_RATE)
                target_price_disp = f"₩{current_p:,.0f}"
                invest_cost_disp = f"₩{buy_val_krw:,.0f}"
                div_per_share_disp = f"₩{last_div:,.0f}"
                monthly_div_item_krw = post_tax_div_annual_krw / 12.0

            future_total_buy_krw += buy_val_krw
            future_yearly_pre_tax_div_krw += pre_tax_div_annual_krw
            future_yearly_post_tax_div_krw += post_tax_div_annual_krw

            future_df_data.append({
                "티커": ticker_name,
                "목표 수량(주) ✏️": qty,
                "현재가 기준 평단가": target_price_disp,
                "목표 총 필요 시드": invest_cost_disp,
                "예상 1주당 배당금 ✏️": div_per_share_disp,
                "목표 연 예상 배당금 (세후)": f"₩{post_tax_div_annual_krw:,.0f}",
                "월 예상 배당금 (세후)": f"₩{monthly_div_item_krw:,.0f}"
            })

        edited_future_df = st.data_editor(
            pd.DataFrame(future_df_data),
            disabled=["티커", "현재가 기준 평단가", "목표 총 필요 시드", "목표 연 예상 배당금 (세후)", "월 예상 배당금 (세후)"],
            column_config={
                "목표 수량(주) ✏️": st.column_config.NumberColumn(min_value=0, step=1, format="%d")
            },
            use_container_width=True, hide_index=True, key=f"editor_future_{target_key}"
        )

        if st.button(f"💾 미래 목표 구글 시트 저장 및 즉시 연산 ({owner_name})", use_container_width=True, key=f"btn_save_fut_{target_key}"):
            for idx, row in edited_future_df.iterrows():
                st.session_state[target_key][idx]["qty"] = int(row["목표 수량(주) ✏️"])
                raw_div = str(row["예상 1주당 배당금 ✏️"]).replace("₩", "").replace("$", "").replace(",", "").strip()
                try:
                    st.session_state[target_key][idx]["last_div"] = float(raw_div)
                except Exception:
                    pass
            
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

        return future_total_buy_krw, future_yearly_pre_tax_div_krw, future_yearly_post_tax_div_krw

    # 1. 재국 보유 현황 & 미래 목표
    buy_jg = render_portfolio_section("재국", "portfolio_jg", "div_history_jg", "Portfolio")
    st.markdown("---")
    fut_buy_jg, fut_pre_jg, fut_post_jg = render_future_target_section("재국", "future_target_jg", buy_jg, "FutureTarget", "portfolio_jg")

    st.markdown("---")
    st.markdown("---")

    # 2. 광희 보유 현황 & 미래 목표
    buy_gh = render_portfolio_section("광희", "portfolio_gh", "div_history_gh", "Portfolio_GH")
    st.markdown("---")
    fut_buy_gh, fut_pre_gh, fut_post_gh = render_future_target_section("광희", "future_target_gh", buy_gh, "FutureTarget_GH", "portfolio_gh")

    st.markdown("---")
    st.markdown("---")

    # 3. [강조 디자인] 재국 ♡ 광희 미래 총 배당금 종합 요약
    total_fut_buy = fut_buy_jg + fut_buy_gh
    total_fut_pre_tax = fut_pre_jg + fut_pre_gh
    total_fut_post_tax = fut_post_jg + fut_post_gh
    total_fut_monthly_post_tax = total_fut_post_tax / 12
    total_fut_yield = (total_fut_post_tax / total_fut_buy * 100) if total_fut_buy > 0 else 0.0

    st.markdown(f"""
        <div class="total-highlight-card">
            <div class="total-title">💖 재국 ♡ 광희 미래 총 배당금 종합 목표</div>
        </div>
    """, unsafe_allow_html=True)

    tot_col1, tot_col2, tot_col3, tot_col4, tot_col5 = st.columns(5)
    with tot_col1: st.metric(label="💵 목표 총 투자 금액", value=f"₩{total_fut_buy:,.0f}")
    with tot_col2: st.metric(label="💰 세전 총 예상 배당금 (연)", value=f"₩{total_fut_pre_tax:,.0f}")
    with tot_col3: st.metric(label="🎁 세후 총 예상 배당금 (연)", value=f"₩{total_fut_post_tax:,.0f}")
    with tot_col4: st.metric(label="📅 세후 총 월 예상 배당금", value=f"₩{total_fut_monthly_post_tax:,.0f}")
    with tot_col5: st.metric(label="📈 세후 총 예상 배당률 (%)", value=f"{total_fut_yield:.2f}%")


# ---------------------------------------------------------
# TAB 2: 월별 배당금 입금 장부 (가독성 및 계좌 구분 강화)
# ---------------------------------------------------------
with main_tab2:
    st.subheader("📅 월별 배당금 입금 장부 (2026년~)")
    st.caption("💡 2026년 1월부터 입금되는 월별 배당금을 계좌별로 등록하는 장부입니다.")

    owner_choice = st.radio("주주 선택", ["재국", "광희"], horizontal=True)
    history_key = "div_history_jg" if owner_choice == "재국" else "div_history_gh"
    sheet_name = "Dividend_History" if owner_choice == "재국" else "Dividend_History_GH"
    portfolio_key = "portfolio_jg" if owner_choice == "재국" else "portfolio_gh"

    available_tickers = [item["ticker"] for item in st.session_state[portfolio_key]]
    
    # 계좌 구분 옵션
    default_acc_options = [f"{owner_choice} 해외 직투 계좌", f"{owner_choice} ISA 계좌", f"{owner_choice} 연금저축 계좌", f"{owner_choice} 일반 계좌"]

    st.markdown("#### ➕ 신규 배당금 입금 등록")
    add_col1, add_col2, add_col3, add_col4 = st.columns([2, 3, 3, 2])
    with add_col1:
        input_month = st.text_input("입금 월 (YYYY-MM)", "2026-01")
    with add_col2:
        input_account = st.selectbox("계좌 선택", default_acc_options)
    with add_col3:
        input_ticker = st.selectbox("종목 선택", available_tickers)
    with add_col4:
        input_amount = st.number_input("입금 배당금 (한화 ₩)", min_value=0, value=100000, step=10000)

    st.write("")
    if st.button("➕ 배당금 입금 내역 추가 등록", use_container_width=True):
        st.session_state[history_key].append({
            "month": input_month,
            "account_type": input_account,
            "ticker": input_ticker,
            "amount_krw": input_amount
        })
        save_sheet_data(sheet_name, st.session_state[history_key])
        st.success(f"[{input_month}] [{input_account}] {input_ticker} 배당금 ₩{input_amount:,.0f}원이 등록되었습니다!")
        st.rerun()

    st.markdown("---")

    # 요약 및 월별 성장 차트 섹션
    st.markdown(f"#### 📊 [{owner_choice}] 누적 배당 요약 및 성장 추이")

    history_data = st.session_state[history_key]
    if history_data:
        df_hist_raw = pd.DataFrame(history_data)
        if "account_type" not in df_hist_raw.columns:
            df_hist_raw["account_type"] = f"{owner_choice} 직투 계좌"

        df_hist_raw["amount_krw"] = pd.to_numeric(df_hist_raw["amount_krw"], errors="coerce").fillna(0)

        total_sum = df_hist_raw["amount_krw"].sum()

        sum_col1, sum_col2 = st.columns([5, 5])
        with sum_col1:
            st.metric(label=f"🏦 [{owner_choice}] 장부 총 누적 배당금 (세후)", value=f"₩{total_sum:,.0f}")
            
            # 계좌별 & 티커별 요약 표
            st.markdown("**📌 티커 및 계좌별 누적 수령 배당금**")
            ticker_summary = df_hist_raw.groupby(["account_type", "ticker"])["amount_krw"].sum().reset_index()
            ticker_summary["비중 (%)"] = (ticker_summary["amount_krw"] / total_sum * 100).round(1)
            ticker_summary = ticker_summary.sort_values(by="amount_krw", ascending=False)
            
            st.dataframe(
                ticker_summary.rename(columns={
                    "account_type": "계좌 구분",
                    "ticker": "티커",
                    "amount_krw": "총 수령 금액 (₩)"
                }),
                column_config={
                    "계좌 구분": st.column_config.TextColumn("계좌 구분", width="medium"),
                    "티커": st.column_config.TextColumn("티커", width="medium"),
                    "총 수령 금액 (₩)": st.column_config.NumberColumn("총 수령 금액 (₩)", format="₩%d"),
                    "비중 (%)": st.column_config.NumberColumn("비중 (%)", format="%.1f%%")
                },
                use_container_width=True, hide_index=True
            )

        with sum_col2:
            st.markdown("**📈 월별 배당금 성장 추이**")
            monthly_summary = df_hist_raw.groupby("month")["amount_krw"].sum().reset_index()
            monthly_summary = monthly_summary.sort_values("month")
            monthly_summary.rename(columns={"month": "입금 월", "amount_krw": "배당금 (₩)"}, inplace=True)
            
            st.bar_chart(monthly_summary.set_index("입금 월"), use_container_width=True)

        st.markdown("---")
        st.markdown(f"#### 📜 [{owner_choice}] 배당금 입금 상세 내역 장부")

        edited_hist = st.data_editor(
            df_hist_raw[["month", "account_type", "ticker", "amount_krw"]],
            column_config={
                "month": st.column_config.TextColumn("입금 월 (YYYY-MM)", width="small"),
                "account_type": st.column_config.TextColumn("계좌 구분", width="medium"),
                "ticker": st.column_config.TextColumn("티커/종목명", width="medium"),
                "amount_krw": st.column_config.NumberColumn("입금 금액 (₩)", format="₩%d", width="large")
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_hist_{history_key}"
        )

        if st.button(f"💾 장부 수정 사항 구글 시트 저장 ({owner_choice})", use_container_width=True, key=f"btn_save_hist_{history_key}"):
            updated_hist = edited_hist.to_dict(orient="records")
            st.session_state[history_key] = updated_hist
            save_sheet_data(sheet_name, updated_hist)
            st.success(f"[{owner_choice}] 장부 변경 사항이 구글 시트에 저장되었습니다!")
            st.rerun()

    else:
        st.info("등록된 배당금 입금 내역이 없습니다. 위에서 2026년 1월 내역부터 차곡차곡 추가해 보세요!")
