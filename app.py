import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
from st_aggrid import AgGrid, GridOptionsBuilder

# -----------------------------
# 설정 및 유틸 함수
# -----------------------------
st.set_page_config(page_title="에이블리 순수익 계산기", layout="wide")
st.title("에이블리 판매자용 순수익 계산기")
# 사이드바 상단에 제작자 정보 추가
st.sidebar.markdown("### 제작자 : 쇼필공남")
def filter_by_payment_date(df, year, month):
    df['결제 완료일'] = pd.to_datetime(df['결제 완료일'], errors='coerce')
    return df[(df['결제 완료일'].dt.year == year) & (df['결제 완료일'].dt.month == month)]

fixed_cost_items = ['인건비', '소프트웨어구독료', '관리비', '통신비', '4대보험료', '보험료', '임대료']
variable_cost_items = ['사입비', '광고비', '배송비', '지급수수료', '기타여비교통비', '소모품비', '사무용품비',
                       '기타복리후생비', '식대', '차량유지비', '잡비']
etc_cost_items = ['기타지출1', '기타지출2', '기타지출3', '기타지출4']

# -----------------------------
# 사이드바 입력
# -----------------------------
st.sidebar.header("기준 연/월 입력")
year = st.sidebar.selectbox("정산 연도", list(range(2023, 2026)), index=2)
month = st.sidebar.selectbox("정산 월", list(range(1, 13)), index=0)
payment_input = st.sidebar.number_input("에이블리 결제금액 (입력)", min_value=0)

# 다음 월을 계산 (12월이면 1월로 돌아가게)
next_month = month + 1 if month < 12 else 1

st.sidebar.markdown("---")
settle_files = st.sidebar.file_uploader(f"정산 파일 4개 업로드 (예: {month}월 1차, {month}월 2차 ~ {next_month}월 1차, {next_month}월 2차)", type="csv", accept_multiple_files=True)
sales_file = st.sidebar.file_uploader(f"상품별 판매 통계 파일 ({month}월)", type="xlsx")
expense_file = st.sidebar.file_uploader(f"지출 내역 파일 ({month}월)", type="xlsx")

run = st.sidebar.button("실행하기")

# -----------------------------
# 방어 처리
# -----------------------------
if run and expense_file is None:
    st.error("지출 내역 파일이 업로드되지 않았습니다.")
    st.stop()

# -----------------------------
# 계산 시작
# -----------------------------
if run and len(settle_files) == 4 and sales_file and expense_file:
    df_settle = pd.concat([pd.read_csv(f) for f in settle_files], ignore_index=True)
    df_filtered = filter_by_payment_date(df_settle, year, month)

    df_sales = pd.read_excel(sales_file)
    if '거래액' not in df_sales.columns:
        st.error("판매 통계 파일에 '거래액' 열이 없습니다.")
        st.stop()

    total_transaction = df_sales['거래액'].sum()
    st.subheader(f"{year}년 {month}월 매출 : {total_transaction:,.0f}원")

    total_payment_excel = df_filtered['결제 금액'].sum()
    total_settlement = df_filtered['정산금'].sum()
    total_promo = df_filtered['프로모션 지원금'].sum()
    total_seller_promo = df_filtered['플랫폼 수수료'].sum()
    total_shipping = df_filtered['배송비'].sum() if '배송비' in df_filtered.columns else 0
    if '배송비' in df_filtered.columns:
        df_filtered = df_filtered.rename(columns={'배송비': '배송비(고객부담배송비)'})
    total_fee = df_filtered['결제 수수료'].sum() if '결제 수수료' in df_filtered.columns else 0

    tooltip_map = {
        '**거래액**': '''할인된 판매가 기준의 실제 거래 금액입니다.''',
        '결제금액(에이블리 기준)': '에이블리 판매자센터 기준 결제금액입니다.',
        '결제금액(정산기준)': '정산파일 기준 해당 월 결제금액 입니다.',
        '결제금액 차액': '정산하는 해당월 말일 기준 미정산된 금액입니다.',
        '배송비(고객부담배송비)': '고객이 직접 부담한 반품/교환 배송비입니다.',
        '프로모션 지원금': '에이블리에서 제공한 할인 지원금입니다.',
        '플랫폼 수수료': '에이블리가 부과하는 기본 수수료입니다.',
        '결제 수수료': '결제사에서 부과하는 수수료입니다.',
        '정산금': '판매자가 실제 입금받는 금액입니다.'
    }

    sales_summary = pd.DataFrame({
        '항목': ['**거래액**', '결제금액(에이블리 기준)', '결제금액(정산기준)', '결제금액 차액', '배송비(고객부담배송비)', '프로모션 지원금', '플랫폼 수수료', '결제 수수료', '정산금'],
        '금액': [total_transaction, payment_input, total_payment_excel, payment_input - total_payment_excel, total_shipping, total_promo, total_seller_promo, total_fee, total_settlement],
        '비율(%)': [''] * 9
    })
    sales_summary['툴팁'] = sales_summary['항목'].map(tooltip_map)
    sales_summary['금액'] = sales_summary['금액'].apply(lambda x: f"{int(x):,}" if isinstance(x, (int, float)) else x)

    gb_sales = GridOptionsBuilder.from_dataframe(sales_summary[['항목', '금액', '툴팁']])
    gb_sales.configure_column("항목", headerTooltip="매출 관련 항목", tooltipField="툴팁")
    gb_sales.configure_column("금액", headerTooltip="해당 항목의 금액")
    sales_grid_options = gb_sales.build()

    AgGrid(
        sales_summary[['항목', '금액', '툴팁']],
        gridOptions=sales_grid_options,
        height=320,
        width=700,
        fit_columns_on_grid_load=True,
        enableBrowserTooltips=True
    )

    # "왜 매출이 거래액 기준인가요?" 부분 추가
    with st.expander("왜 매출이 거래액 기준인가요?"):
        st.markdown("""
        ✅ 왜 매출은 거래액 기준으로 봐야 할까요?

        에이블리에서는 한 주문에 다양한 할인(쿠폰, 적립금, 프로모션 등)이 들어가서,  
        고객이 실제로 지불한 금액인 **결제금액**은 실제 판매가와 차이가 발생합니다.

        하지만 판매자 입장에서는 **실제 판매가(= 거래된 금액)** 기준으로  
        비용(광고비, 수수료, 인건비 등) 대비 **수익률**을 봐야 정확한 판단이 가능합니다.

        **예시**

        | 항목                     | 설명                    |
        |--------------------------|-------------------------|
        | 상품 정가                | 100,000원 (마케팅용 표시) |
        | 할인 판매가              | 50,000원 → 이게 **거래액** |
        | 쿠폰/적립금 사용 후 결제금액 | 45,000원               |

        이 때 **매출은 50,000원** (거래액) 기준으로 보는 게 맞습니다.  
        왜냐하면, **쿠폰/적립금 차감액**은 에이블리 또는 셀러 부담이고,  
        **판매가 자체가 이미 할인된 구조**라 거래액 기준이 **실질적 수익률**에 가깝기 때문입니다.
        """)

    # "왜 결제금액 차액이 발생하나요?" 부분 추가
    with st.expander("결제금액은 왜 2개이며, 왜 결제금액이 다르나요?"):
        st.markdown("""
        - 1.에이블리 결제내역은 고객이 결제하면 바로 그 금액이 포함되고, 구매확정일과 관계없이 결제된 금액이 바로 제공됩니다.
        - 2.엑셀정산세부내역 결제내역은 구매확정이 늦어지면 그 금액은 다음달에 반영 될 수 있습니다.

        **2. 결제금액 차액이 발생하는 이유**
        - 예를 들어, 1월에 결제된 주문이 4월에 구매확정이 되면 **1월의 정산에 포함되지 않고**, 4월 정산에 포함됩니다. 
        - 이때 에이블리가 제공하는 결제금액과 정산서상 결제금액의 차액이 발생하게 됩니다.
        - 결제금액 차액은 정산 하는 달 말일 기준 **미정산 된 금액**입니다

        """)
    
    seller_promo_cost = total_transaction - total_payment_excel - total_promo
    seller_promo_row = pd.DataFrame({
        '항목': ['판매자부담프로모션'],
        '금액': [seller_promo_cost],
        '분류': ['변동비']
    })

    try:
        df_exp_raw = pd.read_excel(expense_file, header=None)
        df_exp_raw = df_exp_raw[[1, 2]].copy()
        df_exp_raw.columns = ['항목', '금액']
        df_exp_raw = df_exp_raw.dropna(subset=['항목', '금액'])
    except Exception as e:
        st.error(f"지출 파일을 불러오는 중 오류 발생: {e}")
        st.stop()

    df_exp = df_exp_raw.copy()
    fee_rows = pd.DataFrame({
        '항목': ['플랫폼수수료', '결제수수료'],
        '금액': [total_seller_promo, total_fee],
        '분류': ['변동비', '변동비']
    })
    df_exp = pd.concat([df_exp, fee_rows], ignore_index=True)
    df_exp = pd.concat([df_exp, seller_promo_row], ignore_index=True)

    if '항목' not in df_exp.columns or '금액' not in df_exp.columns:
        df_exp = df_exp.iloc[:, -2:]
        df_exp.columns = ['항목', '금액']

    df_exp['항목'] = df_exp['항목'].astype(str).str.replace(r"[\s　\xa0]+", "", regex=True).str.strip()
    df_exp['금액'] = df_exp['금액'].astype(str).str.replace(',', '').str.replace('원', '').str.replace(r"[^0-9]", "", regex=True).str.strip()
    df_exp['금액'] = pd.to_numeric(df_exp['금액'], errors='coerce').fillna(0)

    df_exp.loc[df_exp['항목'] == '결제수수료', '분류'] = '변동비'
    df_exp.loc[df_exp['항목'] == '플랫폼수수료', '분류'] = '변동비'
    df_exp.loc[df_exp['항목'] == '판매자부담프로모션', '분류'] = '변동비'

    df_full = df_exp.copy()
    df_full['분류'] = df_full['분류'].fillna(df_full['항목'].apply(
        lambda x: '고정비' if x in fixed_cost_items else '변동비' if x in variable_cost_items else '기타지출'
    ))

    df_full['금액(원)'] = df_full['금액']
    df_full['비율(%)'] = (df_full['금액(원)'] / total_transaction * 100).round(2).astype(str) + '%'
    df_full['금액'] = df_full['금액(원)'].apply(lambda x: f"{int(x):,}")

    st.subheader("② 지출내역")
    df_fixed = df_full[df_full['항목'].isin(['플랫폼수수료', '결제수수료', '판매자부담프로모션'])]
    df_others = df_full[~df_full['항목'].isin(['플랫폼수수료', '결제수수료', '판매자부담프로모션'])]
    df_display = pd.concat([df_fixed, df_others], ignore_index=True)

    gb = GridOptionsBuilder.from_dataframe(df_display[['항목', '금액', '비율(%)', '분류']])
    gb.configure_column("항목", headerTooltip="지출 항목 이름")
    gb.configure_column("금액", headerTooltip="해당 항목의 지출 금액")
    gb.configure_column("비율(%)", headerTooltip="해당 항목이 거래액에서 차지하는 비율")
    gb.configure_column("분류", headerTooltip="고정비 / 변동비 / 기타지출 구분")
    grid_options = gb.build()

    AgGrid(df_display[['항목', '금액', '비율(%)', '분류']], gridOptions=grid_options, height=320, width=700, fit_columns_on_grid_load=True)

    fix_cost = df_full[df_full['분류'] == '고정비']['금액(원)'].sum()
    var_cost = df_full[df_full['분류'] == '변동비']['금액(원)'].sum()
    etc_cost = df_full[df_full['분류'] == '기타지출']['금액(원)'].sum()
    total_expense = fix_cost + var_cost + etc_cost

    net_profit = total_settlement - total_expense
    profit_ratio = (net_profit / total_transaction * 100) if total_transaction else 0

    st.metric("순수익", f"{net_profit:,.0f}원", delta=f"{profit_ratio:.2f}%")

else:
    st.info("정산 4개, 판매 통계, 지출 파일을 모두 업로드하고 실행 버튼을 눌러주세요.")
