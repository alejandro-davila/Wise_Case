# PartnerBank QBR - Wise Platform case study
# run: streamlit run app.py

import json
from pathlib import Path

import pandas as pd
import streamlit as st

import analysis as a

st.set_page_config(page_title="PartnerBank QBR", layout="wide")

HERE = Path(__file__).parent
notes = json.loads((HERE / "slide_notes.json").read_text())


@st.cache_data
def get_data():
    d = a.load()
    return d, a.summary(d)


def m(v):
    return f"£{v / 1e6:.1f}M"


def show_notes(key):
    if key in notes:
        with st.expander("Notes"):
            st.write(notes[key])


d, s = get_data()
R = s["by_reason"]

pages = ["Summary", "1. Quarterly review", "2. Convenience fee",
         "3. Multi-currency accounts", "4. Internal business case", "About the data"]
p = st.query_params.get("p", "0")
page = st.sidebar.radio("Contents", pages, index=int(p) if p.isdigit() and int(p) < len(pages) else 0)
st.sidebar.caption("Alejandro Davila, Nov 2026")
st.sidebar.caption("Illustrative figures from a mock dataset.")


if page == "Summary":
    st.title("PartnerBank QBR")
    st.write("Full year, April 2025 to March 2026.")
    st.header("The partnership is growing, and the biggest opportunity is money that leaves the app today")
    st.table(pd.DataFrame({
        "Question": ["1. QBR", "2. Convenience fee", "3. Multi-currency accounts", "4. Internal case"],
        "Answer": [
            f"Usage is up {s['checks_growth']:.0%} and reliable, but {s['wise_share']:.0%} of customers' money goes to Wise directly, "
            f"{s['limited_share']:.0%} because of app limits we can fix together.",
            "0.3% with a £1 minimum and a £15 cap. Test it with a control group first.",
            f"{s['mca_share']:.0%} of PartnerBank's customers on Wise already use one.",
            "Judge it on new revenue Wise wouldn't earn anyway. Pilot with one partner first.",
        ],
    }).set_index("Question"))
    show_notes("Summary")


elif page == "1. Quarterly review":
    st.title("1. Quarterly review")

    st.header("More customers check the fee every month, and 3 in 4 go on to send")
    c1, c2 = st.columns(2)
    c1.metric("Customers checking the fee (March)", f"{s['checks_last']:,.0f}", f"{s['checks_growth']:+.0%} since April")
    c2.metric("Went on to send", f"{s['send_rate']:.0%}")
    show_notes("Momentum")

    st.header("The service is reliable")
    rel = s["reliability"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Transfers that go through", f"{rel['success']:.1%}")
    c2.metric("Arrive in under 20 seconds", f"{rel['under_20s']:.0%}")
    c3.metric("Time to show the fee", f"{rel['quote_ms']:.0f} ms")
    show_notes("Service quality")

    st.header(f"{s['wise_share']:.0%} of the money goes around the app")
    c1, c2 = st.columns(2)
    c1.metric("Sent on Wise directly", m(s["wise_vol"]))
    c2.metric("Sent in the app", m(s["app_vol"]))
    st.image(str(HERE / "images" / "sankey_app.png"))
    st.caption("Read left to right. Thicker bands mean more money. The four growth opportunities are circled in red.")
    show_notes("The opportunity")

    st.header(f"Four growth opportunities: {m(s['limited'])} ({s['limited_share']:.0%} of all money)")
    fix = {"Over £50,000": "Raise the limit", "Currency not offered": "Add currencies",
           "Sent from euros or dollars": "Send from EUR and USD", "Business customer": "Open to business",
           a.NO_LIMIT: "Awareness", "Account, card or receiving": "Different product (Q3)"}
    st.table(pd.DataFrame({
        "Reason": R.index,
        "Money": [m(v) for v in R],
        "Share of all money": [f"{v / s['total_vol']:.0%}" for v in R],
        "Opportunity": [fix[r] for r in R.index],
    }).set_index("Reason"))
    st.caption("The first four rows are app limits. Each transfer is counted once.")
    show_notes("Growth opportunities")

    ms = s["missing"]
    top3 = ms[["PKR", "BDT", "JPY"]].sum() / ms.sum()
    st.header(f"Three currencies make up {top3:.0%} of the missing-currency money")
    st.table(pd.DataFrame({
        "Sent on Wise directly": [m(v) for v in ms.head(5)],
        "Share": [f"{v / ms.sum():.0%}" for v in ms.head(5)],
    }, index=ms.head(5).index))
    show_notes("Currency coverage")

    st.header("Half of new sign-ups never make a first transfer")
    c1, c2, c3 = st.columns(3)
    c1.metric("New sign-ups", f"{s['new_signups']:,.0f}")
    c2.metric("Made a first transfer", f"{s['new_senders']:,.0f}")
    c3.metric("Haven't sent yet", f"{s['new_signups'] - s['new_senders']:,.0f}")
    show_notes("Activation")

    st.header("What we recommend")
    share = st.slider("How much of it do we win back? (%)", 10, 100, 50, 10)
    st.write(f"At {share}%, that's about **{m(s['winback_half'] * share / 50)}** more through the app a year.")
    st.write(f"""
1. Add missing currencies, starting with PKR, BDT and JPY ({m(R['Currency not offered'])})
2. Review the £50,000 limit ({m(R['Over £50,000'])})
3. Let customers send from euros and dollars ({m(R['Sent from euros or dollars'])})
4. Fix the first-transfer journey ({s['new_signups'] - s['new_senders']:,.0f} sign-ups waiting)

KPI to track every month: share of customers' money sent through the app.
""")
    show_notes("What we recommend")


elif page == "2. Convenience fee":
    st.title("2. Convenience fee")

    st.header("A small % fee with a minimum and a cap")
    c1, c2, c3 = st.columns(3)
    rate = c1.number_input("Fee (%)", 0.0, 5.0, a.FEE_RATE, 0.05)
    low = c2.number_input("Minimum (£)", 0.0, 20.0, a.FEE_MIN, 0.5)
    cap = max(c3.number_input("Maximum (£)", 0.0, 100.0, a.FEE_CAP, 1.0), low)
    amounts = [50, 500, 2000, 10000]
    fees = [a.fee(x, rate, low, cap) for x in amounts]
    st.table(pd.DataFrame({
        "Fee": [f"£{f:.2f}" for f in fees],
        "% of transfer": [f"{f / x:.2%}" for f, x in zip(fees, amounts)],
    }, index=[f"£{x:,}" for x in amounts]))
    st.write("HSBC charges £5 and Lloyds £9.50 (UK websites, 2 Nov 2026). "
             "At 0.3% PartnerBank is cheaper than HSBC under £1,667 and Lloyds under £3,167.")
    show_notes("Fee design")

    st.header("Test it before rolling it out")
    sent = d[d.Channel.eq("Integration") & d.Transacted]
    income = sent["Transaction Volume (GBP)"].map(lambda x: a.fee(x, rate, low, cap)).sum() * a.SCALE
    drop = st.slider("Out of 100 transfers, how many stop because of the fee?", 0, 50, 10)
    c1, c2 = st.columns(2)
    c1.metric("Fee income if nobody stops", f"£{income / 1e3:,.0f}k")
    c2.metric(f"If {drop} in 100 stop", f"£{income * (1 - drop / 100) / 1e3:,.0f}k")
    st.write(f"""
- Small transfers feel it most (£1 is 2% of £50), but only {s['small_share']:.0%} of transfers are £250 or less.
- Risk: people move to Wise directly or another provider.
- Test: random fee group vs no-fee group, at least two months, stop rules agreed upfront.
""")
    show_notes("Effect on usage")

    st.header("KPIs")
    st.table(pd.DataFrame({
        "What it tells us": [
            "Does the fee stop people at the last step?",
            "Do new customers still get started?",
            "Do people send less?",
            "Does it push money out of the app?",
            "Do customers understand the fee?",
            "Is it worth it after people who stop?",
        ]}, index=["Fee check to send rate", "First-transfer rate", "Transfers per customer",
                   "Moving to Wise directly", "Complaints", "Extra revenue per customer"]))
    show_notes("KPIs")


elif page == "3. Multi-currency accounts":
    st.title("3. Multi-currency accounts")
    st.header(f"{s['mca_share']:.0%} of PartnerBank's customers on Wise already use one")
    c1, c2, c3 = st.columns(3)
    c1.metric("Customers on Wise directly", f"{s['wd_users']:,.0f}")
    c2.metric("Use a multi-currency account", f"{s['mca_users']:,.0f}")
    c3.metric("Use an account, card or receive", f"{s['related_users']:,.0f}")
    st.write("""
- The survey shows what people say. This shows what they already do.
- These customers are a ready-made pilot group.
- But they already chose Wise, so they're keener than average. Use them for the pilot, not to forecast the whole bank.
""")
    show_notes("Evidence")


elif page == "4. Internal business case":
    st.title("4. Internal business case")
    st.caption("For the Wise team, not the partner.")
    st.header("North star: new revenue Wise wouldn't earn anyway")
    k = dict(a.Q4_DEFAULTS)
    c1, c2, c3 = st.columns(3)
    k["partners"] = c1.number_input("Partners", 1, 20, k["partners"])
    k["adoption"] = c2.number_input("Adoption (%)", 1, 20, k["adoption"])
    k["revenue"] = c3.number_input("Revenue per account per month (£)", 0.0, 10.0, k["revenue"], 0.25)
    model = a.project(**k)
    pb = a.payback_month(model)
    c1, c2, c3 = st.columns(3)
    c1.metric("New revenue, 3 years", f"£{model['New Wise revenue (£)'].sum() / 1e3:,.0f}k")
    c2.metric("After costs, 3 years", f"£{model['Running total after costs (£)'].iloc[-1] / 1e3:,.0f}k")
    c3.metric("Pays back", f"Month {pb}" if pb else "Not in 3 years")
    st.caption("Costs: £300k build, £20k per partner, £0.75/account/month to run, £5k/month shared, £3 to activate. "
               "£0.50 of the £2.50 is revenue Wise already gets.")
    show_notes("Wise internal")

    st.header("Recommendation: pilot with one partner first")
    st.write("""
Besides revenue, weigh:
- cost and payback
- engineering time and what it delays
- regulatory and fraud risk (holding balances)
- how strong the evidence is
- opportunity cost vs fixing the Send Money limits

Pilot targets: adoption, revenue per account, reliability and fraud. Go / stop after 6 months.
""")
    show_notes("Wise internal 2")


else:
    st.title("About the data")
    st.write("""
- Mock dataset, 10,000 rows, April 2025 to March 2026, built around the 12 data points in the brief.
- Counts and money are x20 to match PartnerBank's size (~33,000 fee checks a quarter). Percentages don't change.
- Customers are counted once per period.
- Each Wise-direct transfer gets one reason, checked in order: business, other source currency,
  same currency, missing currency, over £50,000, other product.
""")
    with st.expander("Monthly numbers"):
        st.dataframe(s["monthly"])
    show_notes("Appendix")
