import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

st.set_page_config(page_title="나만의 맞춤형 주식 대시보드", layout="wide")

TAX_RATE = 0.154  # 배당소득세율 (15.4%)
DATA_FILE = "portfolio.json"
FUTURE_DATA_FILE = "future_target.json"

# ---------------------------------------------------------
# 0. 커스텀 CSS 스타일 정의 (디자인 강화)
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* 거시 경제 카드 스타일 */
    .macro-card {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e9ecef;
        text-align: center;
    }
    .macro-card-warning {
        background-color: #fff5f5;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(229, 62, 62, 0.1);
        border: 1px solid #feb2b2;
        text-align: center;
    }
    .macro-title {
        font-size: 14px;
        color: #495057;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .macro-value {
        font-size: 24px;
        font-weight: 800;
        color: #1a202c;
    }
    .status-badge-ok {
        display: inline-block;
        background-color: #c6f6d5;
        color: #22543d;
        font-size: 12px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 12px;
    }
    .status-badge-warn {
        display: inline-block;
        background-color: #fed7d7;
        color: #9b2c2c;
        font-size: 12px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 12px;
    }

    /* Streamlit 표(data_editor) 헤더 스타일 강력 강화 */
    div[data-testid="stDataEditor"] div[role="columnheader"] {
        background-color: #e2e8f0 !important; /* 명확한 구분용 회색 배경 */
        color: #0f172a !important;            /* 진한 텍스트 색상 */
        font-weight: 800 !important;          /* 두꺼운 볼드체 */
        font-size: 15px !important;
        border-bottom: 2px solid #94a3b8 !important;
    }

    /* 수정 가능한 입력 헤더/열 배경 차별화 */
    div[data-testid="stDataEditor"] div[role="columnheader"]:nth-child(2),
    div[data-testid="stDataEditor"] div[role="columnheader"]:nth-child(3) {
        background-color: #dbeafe !important; /* 수정 가능 입력 열은 은은한 푸른빛 적용 */
        color: #1e40af !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 데이터 로드 / 저장 함수
# ---------------------------------------------------------
DEFAULT_PORTFOLIO = [
    {"ticker": "JEPQ", "ticker_symbol": "JEPQ", "qty": 660, "avg_price": 53.71, "currency": "USD", "last_div": 0.56, "total_received_div": 3101187},
    {"ticker": "QQQI", "ticker_symbol": "QQQI", "qty": 627, "avg_price": 53.07, "currency": "USD", "last_div": 0.6346, "total_received_div": 680792},
    {"ticker": "SCHD", "ticker_symbol": "SCHD", "qty": 722, "avg_price": 27.12, "currency": "USD", "last_div": 0.25, "total_received_div": 253716},
    {"ticker": "QLD",  "ticker_symbol": "QLD",  "qty": 23,  "avg_price": 84.29, "currency": "USD", "last_div": 0.03, "total_received_div": 0},
    {"ticker": "KODEX 미국배당커버드콜 액티브", "ticker_symbol": "441680.KS", "qty": 194, "avg_price": 11288, "currency": "KRW", "last_div": 99, "total_received_div": 299148},
    {"ticker": "KODEX 200타겟위클리커버드콜", "ticker_symbol": "480460.KS", "qty": 299, "avg_price": 15436, "currency": "KRW", "last_div": 262, "total_received_div": 1517126}
]

def load_portfolio():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_PORTFOLIO
    return DEFAULT_PORTFOLIO

def save_portfolio(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_future_target():
    if os.path.exists(FUTURE_DATA_FILE):
        try:
            with open(FUTURE_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return load_portfolio()
    return load_portfolio()

def save_future_target(data):
    with open(FUTURE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio()

if "future_target" not in st.session_state:
    st.session_state.future_target = load_future_target()

# ---------------------------------------------------------
# 2. 사이드바: 보유 종목 관리 (신규 추가 / 삭제)
# ---------------------------------------------------------
st.sidebar.header("⚙️ 보유 종목 관리")

with st.sidebar.expander("➕ 새 종목 추가", expanded=False):
    with st.form("add_stock_form", clear_on_submit=True):
        new_ticker = st.text_input("종목명 (표시용)", placeholder="예: TSLA")
        new_symbol = st.text_input("야후파이낸스 티커", placeholder="미국: TSLA / 한국: 133690.KS")
        new_curr = st.selectbox("통화", ["USD", "KRW"])
        new_qty = st.number_input("보유 수량(주)", min_value=1, value=10)
        new_avg = st.number_input("평단가", min_value=0.0, value=100.0)
        new_div = st.number_input("전월 확정 1주당 배당금", min_value=0.0, value=0.5)
        new_tot_div = st.number_input("올해 받은 총 배당금(원)", min_value=0, value=0)
        
        submit = st.form_submit_button("종목 추가하기")
        if submit:
            if new_ticker and new_symbol:
                item_data = {
                    "ticker": new_ticker,
                    "ticker_symbol": new_symbol,
                    "qty": int(new_qty),
                    "avg_price": float(new_avg),
                    "currency": new_curr,
                    "last_div": float(new_div),
                    "total_received_div": int(new_tot_div)
                }
                st.session_state.portfolio.append(item_data)
                save_portfolio(st.session_state.portfolio)
                
                st.session_state.future_target.append(item_data)
                save_future_target(st.session_state.future_target)

                st.success(f"{new_ticker} 추가 완료!")
                st.rerun()

with st.sidebar.expander("🗑️ 종목 삭제"):
    delete_target = st.selectbox("삭제할 종목 선택", [item["ticker"] for item in st.session_state.portfolio])
    if st.button("선택 종목 삭제"):
        st.session_state.portfolio = [item for item in st.session_state.portfolio if item["ticker"] != delete_target]
        save_portfolio(st.session_state.portfolio)
        
        st.session_state.future_target = [item for item in st.session_state.future_target if item["ticker"] != delete_target]
        save_future_target(st.session_state.future_target)

        st.warning(f"{delete_target} 삭제 완료!")
        st.rerun()

# ---------------------------------------------------------
# 3. 상단: 거시 경제 지표
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

st.title("📈 나만의 맞춤형 주식 대시보드")
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

with macro_col1:
    render_macro_card("브렌트유 시세", f"${brent:.2f}", "USD", brent >= 100)

with macro_col2:
    render_macro_card("미 10년물 국채 금리", f"{us10y:.2f}", "%", us10y >= 4.5)

with macro_col3:
    render_macro_card("환율 (USD/KRW)", f"₩{usd_krw:,.2f}", "", usd_krw >= 1450)

with macro_col4:
    render_macro_card("VIX 지수", f"{vix:.2f}", "", vix >= 40)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. 중단: 단일 통합 보유 주식 대시보드 (현재 현황)
# ---------------------------------------------------------
st.subheader("📊 실시간 통합 보유 현황")
st.caption("💡 푸른색 배경의 **수량(주) ✏️**, **내 평단가 ✏️** 셀을 직접 수정한 후 저장 버튼을 누르시면 실시간 연산이 적용됩니다.")

df_data = []
total_eval_krw = 0.0
total_buy_krw = 0.0
total_received_div_all_krw = 0.0
monthly_est_div_krw = 0.0

for item in st.session_state.portfolio:
    symbol = item.get("ticker_symbol", item["ticker"])
    qty = item["qty"]
    avg_p = item["avg_price"]
    curr = item["currency"]
    last_div = item["last_div"]
    tot_div = item["total_received_div"]
    
    total_received_div_all_krw += tot_div

    try:
        stock_info = yf.Ticker(symbol).fast_info
        current_p = stock_info['lastPrice']
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
        buy_val_krw = qty * avg_p
        eval_val_krw = qty * current_p
        
        avg_price_disp = f"₩{avg_p:,.0f}"
        current_price_disp = f"₩{current_p:,.0f}"
        invest_cost_disp = f"₩{buy_val_krw:,.0f}"
        div_per_share_disp = f"₩{last_div:,.0f}"
        monthly_div_item_krw = qty * last_div * (1 - TAX_RATE)

    return_rate = ((eval_val_krw - buy_val_krw) / buy_val_krw) * 100 if buy_val_krw > 0 else 0.0
    
    if return_rate > 0:
        return_rate_disp = f"🔴 +{return_rate:.2f}%"
    elif return_rate < 0:
        return_rate_disp = f"🔵 {return_rate:.2f}%"
    else:
        return_rate_disp = f"⚪ 0.00%"

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
    column_order=[
        "티커", "수량(주) ✏️", "내 평단가 ✏️", "내 평단가 (한화/달러)", 
        "현재가 (한화/달러)", "총 투자비용 (수량×평단가)", 
        "1주당 배당금 (한화/달러)", "월 예상 배당금 (세후)", "현재 수익률"
    ],
    use_container_width=True,
    hide_index=True,
    key="editor_current"
)

if st.button("💾 현재 현황 저장 및 실시간 계산 반영", use_container_width=True):
    for idx, row in edited_df.iterrows():
        st.session_state.portfolio[idx]["qty"] = int(row["수량(주) ✏️"])
        st.session_state.portfolio[idx]["avg_price"] = float(row["내 평단가 ✏️"])
    
    save_portfolio(st.session_state.portfolio)
    st.success("현재 보유 현황이 업데이트되었습니다!")
    st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 5. 하단: 계좌 성과 및 배당금 요약
# ---------------------------------------------------------
st.subheader("💰 계좌 성과 및 배당금 종합 요약")

account_return_rate = ((total_eval_krw - total_buy_krw) / total_buy_krw) * 100 if total_buy_krw > 0 else 0.0
yearly_est_div_krw = monthly_est_div_krw * 12
current_total_account_val = total_eval_krw + total_received_div_all_krw
portfolio_div_yield = (yearly_est_div_krw / total_eval_krw * 100) if total_eval_krw > 0 else 0.0

row1_col1, row1_col2, row1_col3 = st.columns(3)

with row1_col1:
    st.metric(label="💵 계좌 총 투자 비용 (총 매수원금)", value=f"₩{total_buy_krw:,.0f}")

with row1_col2:
    st.metric(label="🏦 현재 계좌 총 자산", value=f"₩{current_total_account_val:,.0f}", delta=f"총 평가손익: ₩{total_eval_krw - total_buy_krw:+,.0f}")

with row1_col3:
    st.metric(label="📊 순수 주식 수익률 (배당 제외)", value=f"{account_return_rate:+.2f}%")

st.write("")

row2_col1, row2_col2, row2_col3 = st.columns(3)

with row2_col1:
    st.metric(label="📈 포트폴리오 세후 예상 배당률", value=f"{portfolio_div_yield:.2f}%")

with row2_col2:
    st.metric(label="🎁 올해 받은 총 배당금", value=f"₩{total_received_div_all_krw:,.0f}")

with row2_col3:
    st.metric(label="📅 이번달 / 올해 예상 배당금 (세후)", value=f"월 ₩{monthly_est_div_krw:,.0f}", delta=f"연간 ₩{yearly_est_div_krw:,.0f}")

st.markdown("---")

# ---------------------------------------------------------
# 6. 미래 배당 세팅 목표 (현재가 자동 반영 적용)
# ---------------------------------------------------------
st.subheader("🎯 미래 배당 세팅 목표")
st.caption("💡 목표 수량 및 예상 배당금을 설정하세요. 목표 평단가는 **실시간 현재가** 기준으로 자동 계산됩니다.")

future_df_data = []
future_total_buy_krw = 0.0
future_yearly_pre_tax_div_krw = 0.0
future_yearly_post_tax_div_krw = 0.0

for item in st.session_state.future_target:
    symbol = item.get("ticker_symbol", item["ticker"])
    qty = item["qty"]
    curr = item["currency"]
    last_div = item["last_div"]

    # 실시간 현재가 불러오기 (현재가가 평단가 기준이 됨)
    try:
        stock_info = yf.Ticker(symbol).fast_info
        current_p = stock_info['lastPrice']
    except Exception:
        current_p = item["avg_price"]

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

future_df_display = pd.DataFrame(future_df_data)

edited_future_df = st.data_editor(
    future_df_display,
    disabled=["티커", "현재가 기준 평단가", "목표 총 필요 시드", "예상 1주당 배당금 (한화/달러)", "목표 연 예상 배당금 (세후)"],
    column_config={
        "목표 수량(주) ✏️": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
        "예상 1주당 배당금 ✏️": st.column_config.NumberColumn(format="$%.4f")
    },
    column_order=[
        "티커", "목표 수량(주) ✏️", "예상 1주당 배당금 ✏️",
        "현재가 기준 평단가", "목표 총 필요 시드", 
        "예상 1주당 배당금 (한화/달러)", "목표 연 예상 배당금 (세후)"
    ],
    use_container_width=True,
    hide_index=True,
    key="editor_future"
)

if st.button("💾 미래 배당 세팅 목표 저장 및 즉시 연산", use_container_width=True):
    for idx, row in edited_future_df.iterrows():
        st.session_state.future_target[idx]["qty"] = int(row["목표 수량(주) ✏️"])
        st.session_state.future_target[idx]["last_div"] = float(row["예상 1주당 배당금 ✏️"])
    
    save_future_target(st.session_state.future_target)
    st.success("미래 배당 세팅 목표 데이터가 업데이트되었습니다!")
    st.rerun()

st.write("")

# ---------------------------------------------------------
# 7. 미래 예상 배당금 요약 및 추가 필요 시드 연산
# ---------------------------------------------------------
st.markdown("#### 🔮 미래 예상 배당금 요약")

future_monthly_post_tax_div_krw = future_yearly_post_tax_div_krw / 12
future_div_yield = (future_yearly_post_tax_div_krw / future_total_buy_krw * 100) if future_total_buy_krw > 0 else 0.0

# 추가 필요 시드 연산 (현재가 기준 목표 총 금액 - 현재 계좌 매수원금)
needed_additional_seed = max(0.0, future_total_buy_krw - total_buy_krw)

f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)

with f_col1:
    st.metric(label="💵 세전 예상 총 배당금 (연간)", value=f"₩{future_yearly_pre_tax_div_krw:,.0f}")

with f_col2:
    st.metric(label="💰 세후 예상 총 배당금 (연간)", value=f"₩{future_yearly_post_tax_div_krw:,.0f}")

with f_col3:
    st.metric(label="📅 월 예상 배당금 (세후)", value=f"₩{future_monthly_post_tax_div_krw:,.0f}")

with f_col4:
    st.metric(label="📈 세후 예상 배당률 (%)", value=f"{future_div_yield:.2f}%")

with f_col5:
    st.metric(label="🎯 목표 달성 추가 필요 시드", value=f"₩{needed_additional_seed:,.0f}", delta=f"목표시드: ₩{future_total_buy_krw:,.0f}")

st.markdown("---")

# ---------------------------------------------------------
# 8. 최하단: 추가 매수 시뮬레이터
# ---------------------------------------------------------
st.subheader("🧮 추가 매수 시뮬레이터")
st.caption("구매하려는 종목과 수량을 입력하면 필요한 금액과 추가 배당금을 연산합니다.")

sim_col1, sim_col2, sim_col3 = st.columns(3)

with sim_col1:
    selected_ticker = st.selectbox("종목 선택", [item["ticker"] for item in st.session_state.portfolio])

with sim_col2:
    add_qty = st.number_input("추가 구매 수량(주)", min_value=1, value=10, step=1)

selected_item = next(item for item in st.session_state.portfolio if item["ticker"] == selected_ticker)
symbol = selected_item.get("ticker_symbol", selected_item["ticker"])
curr = selected_item["currency"]
last_div = selected_item["last_div"]

try:
    current_p = yf.Ticker(symbol).fast_info['lastPrice']
except Exception:
    current_p = selected_item["avg_price"]

if curr == "USD":
    required_cost_krw = add_qty * current_p * usd_krw
    add_monthly_div_krw = add_qty * last_div * usd_krw * (1 - TAX_RATE)
    price_str = f"₩{current_p * usd_krw:,.0f} [${current_p:,.2f}]"
else:
    required_cost_krw = add_qty * current_p
    add_monthly_div_krw = add_qty * last_div * (1 - TAX_RATE)
    price_str = f"₩{current_p:,.0f}"

add_yearly_div_krw = add_monthly_div_krw * 12

with sim_col3:
    st.write(f"**현재가:** {price_str}")

st.info(f"""
💡 **{selected_ticker}** 종목을 **{add_qty}주** 매수할 때 예상 수치:
* **필요 금액:** **₩{required_cost_krw:,.0f}**
* **월 예상 배당금 증가 (세후):** +**₩{add_monthly_div_krw:,.0f}**
* **연 예상 배당금 증가 (세후):** +**₩{add_yearly_div_krw:,.0f}**
""")