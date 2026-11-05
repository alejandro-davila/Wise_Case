"""PartnerBank QBR: Wise Platform case study. Run with: streamlit run app.py"""
import altair as alt
import pandas as pd
import streamlit as st

import analysis as a

st.set_page_config(page_title='PartnerBank QBR', layout='centered')

NAVY, ORANGE, GREY = '#163300', '#9FE870', '#868685'  # Wise forest green, bright green, grey


@st.cache_data
def data():
    d = a.load()
    return d, a.summary(d)


def money(v):
    return f'£{v / 1e6:.1f}M'


def line_chart(frame, y_title, fmt=',.0f', colors=(NAVY, ORANGE)):
    tidy = frame.reset_index().melt(frame.index.name or 'index', var_name='Series', value_name='Value')
    x = frame.index.name or 'index'
    chart = alt.Chart(tidy).mark_line(strokeWidth=3).encode(
        x=alt.X(f'{x}:T' if x == 'Month' else f'{x}:Q', title=None if x == 'Month' else x,
                axis=alt.Axis(format='%b %y') if x == 'Month' else alt.Axis()),
        y=alt.Y('Value:Q', title=y_title, axis=alt.Axis(format=fmt), scale=alt.Scale(zero=True)),
        color=alt.Color('Series:N', scale=alt.Scale(domain=list(frame.columns), range=list(colors)),
                        legend=alt.Legend(orient='bottom', title=None)),
        tooltip=[alt.Tooltip(f'{x}:T' if x == 'Month' else f'{x}:Q', title=x), 'Series:N',
                 alt.Tooltip('Value:Q', format=fmt)],
    ).properties(height=320)
    st.altair_chart(chart, use_container_width=True)


def footnote():
    st.caption('Illustrative figures from a mock dataset (10,000 records, shown ×20 to match PartnerBank’s size).')


d, s = data()
mon = s['monthly']
R = s['by_reason']

PAGES = ['Summary', '1. Quarterly review', '2. Convenience fee', '3. Multi-currency accounts',
         '4. Internal business case', 'About the data']
start = st.query_params.get('p', '0')
page = st.sidebar.radio('Contents', PAGES, index=int(start) if start.isdigit() and int(start) < len(PAGES) else 0)
st.sidebar.caption('Alejandro Davila · Wise Platform case study · Nov 2026')


# ---------------------------------------------------------------- Summary
if page == 'Summary':
    st.title('PartnerBank: Quarterly Business Review')
    st.write('Full year April 2025 to March 2026.')
    st.subheader('The partnership is growing, and the biggest opportunity is money that leaves the app today')
    st.markdown(f"""
| Question | Answer |
|---|---|
| **1. QBR** | Usage is up {s['checks_growth']:.0%} and reliable. But {s['wise_share']:.0%} of customers’ money goes to Wise directly, {s['limited_share']:.0%} because of app limits we can fix together. |
| **2. Convenience fee** | 0.3% with a £1 minimum and a £15 cap. Test it with a control group before rolling it out. |
| **3. Multi-currency accounts** | {s['mca_share']:.0%} of PartnerBank’s customers on Wise already use one. Real behaviour, not just survey interest. |
| **4. Internal case** | Judge it on new revenue Wise would not earn anyway. Fund a one-partner pilot before a full build. |
""")
    footnote()


# ---------------------------------------------------------------- Q1
elif page == '1. Quarterly review':
    st.title('1. Quarterly Business Review')
    st.caption('Written for PartnerBank.')

    st.subheader('More customers check the fee every month, and 3 in 4 of them go on to send')
    c1, c2 = st.columns(2)
    c1.metric('Customers checking the fee each month', f'{s["checks_last"]:,.0f}', f'{s["checks_growth"]:+.0%} since April')
    c2.metric('Of those, went on to send', f'{s["send_rate"]:.0%}')
    line_chart(mon[['Checked the fee', 'Sent in the app']].rename_axis('Month'), 'Customers')

    st.subheader('The service is reliable, which gives us a strong base to grow on')
    rel = s['reliability']
    c1, c2, c3 = st.columns(3)
    c1.metric('Transfers that go through', f'{rel["success"]:.1%}')
    c2.metric('Arrive in under 20 seconds', f'{rel["under_20s"]:.0%}')
    c3.metric('Time to show the fee', f'{rel["quote_ms"]:.0f} ms')

    st.subheader(f'{s["wise_share"]:.0%} of the money your customers send goes around your app, and Wise-direct use is growing {s["wise_users_growth"] / s["checks_growth"]:.1f}x as fast')
    c1, c2 = st.columns(2)
    c1.metric(f'Sent on Wise directly (vs {money(s["app_vol"])} in the app)', money(s['wise_vol']))
    c2.metric('Growth in customers using Wise directly', f'{s["wise_users_growth"]:+.0%}')
    m = mon[['Money sent in the app (£)', 'Money sent on Wise directly (£)']] / 1e6
    m.columns = ['Sent in PartnerBank app', 'Sent on Wise directly']
    line_chart(m.rename_axis('Month'), '£ millions', ',.0f')

    st.subheader(f'{s["limited_share"]:.0%} of all money ({money(s["limited"])}) goes to Wise because of a limit in today’s app')
    fix = {'Over £50,000': 'Raise the limit', 'Currency not offered': 'Add currencies',
           'Sent from euros or dollars': 'Send from EUR and USD', 'Business customer': 'Open to business',
           a.NO_LIMIT: 'Awareness, not features', 'Account, card or receiving': 'Different product (Q3)'}
    t = pd.DataFrame({'Reason': R.index, 'Money': R.map(money).values,
                      'Share of all money': (R / s['total_vol']).map('{:.0%}'.format).values,
                      'What would fix it': [fix[r] for r in R.index]})
    st.dataframe(t, hide_index=True, width='stretch')
    st.caption('The first four rows are app limits. Each transfer is counted once.')

    ms = s['missing']
    top3 = ms[['PKR', 'BDT', 'JPY']].sum() / ms.sum()
    st.subheader(f'Three currencies make up {top3:.0%} of the money going to currencies the app does not offer')
    names = {'PKR': 'Pakistani rupee', 'BDT': 'Bangladeshi taka', 'JPY': 'Japanese yen',
             'LKR': 'Sri Lankan rupee', 'KRW': 'South Korean won'}
    top = ms.head(5)
    st.dataframe(pd.DataFrame({'Currency': [f'{names.get(c, c)} ({c})' for c in top.index],
                               'Sent on Wise directly': top.map(money).values,
                               'Share of missing-currency money': (top / ms.sum()).map('{:.0%}'.format).values}),
                 hide_index=True, width='stretch')

    st.subheader('Half of new sign-ups never make a first transfer')
    c1, c2, c3 = st.columns(3)
    c1.metric('New sign-ups', f'{s["new_signups"]:,.0f}')
    c2.metric(f'Made a first transfer ({s["new_rate"]:.0%})', f'{s["new_senders"]:,.0f}')
    c3.metric('Have not sent yet', f'{s["new_signups"] - s["new_senders"]:,.0f}')

    st.subheader('What we recommend')
    share = st.slider('How much of the money we can win back do you expect to win back?', 10, 100, 50, 10, format='%d%%')
    st.write(f'At {share}%, that is about **{money(s["winback_half"] * share / 50)}** more through your app a year.')
    st.markdown(f"""
1. **Add missing currencies, starting with PKR, BDT and JPY.** {money(R['Currency not offered'])} a year, and it affects the most customers.
2. **Review the £50,000 limit.** {money(R['Over £50,000'])} a year from a small group of high-value customers.
3. **Let customers send from euros and dollars.** {money(R['Sent from euros or dollars'])} a year from balances they already hold.
4. **Fix the first-transfer journey.** {s['new_signups'] - s['new_senders']:,.0f} sign-ups have not sent yet.

Headline KPI to track monthly: the share of customers’ money sent through the app.
""")
    footnote()


# ---------------------------------------------------------------- Q2
elif page == '2. Convenience fee':
    st.title('2. The convenience fee')
    st.subheader('A small percentage fee with a minimum and a cap keeps the app competitive')
    c1, c2, c3 = st.columns(3)
    rate = c1.number_input('Fee (%)', 0.0, 5.0, a.FEE_RATE, 0.05)
    minimum = c2.number_input('Minimum (£)', 0.0, 20.0, a.FEE_MIN, 0.5)
    cap = c3.number_input('Maximum (£)', 0.0, 100.0, a.FEE_CAP, 1.0)
    cap = max(cap, minimum)
    ex = pd.DataFrame({'Customer sends': [50, 500, 2000, 10000]})
    ex['Fee'] = ex['Customer sends'].map(lambda v: a.fee(v, rate, minimum, cap))
    ex['Fee as % of transfer'] = ex.Fee / ex['Customer sends']
    st.dataframe(ex.style.format({'Customer sends': '£{:,.0f}', 'Fee': '£{:,.2f}', 'Fee as % of transfer': '{:.2%}'}),
                 hide_index=True, width='stretch')
    tips = [f'{name} (£{lvl:.2f}'.replace('.00', '') + f') on transfers under £{lvl / (rate / 100):,.0f}'
            for name, lvl in [('HSBC', 5), ('Lloyds', 9.5)] if rate and minimum < lvl < cap]
    if tips:
        st.write('Cheaper than ' + ', and '.join(tips) + '. Compare what the recipient gets too: banks also earn on the exchange rate.')
    st.caption('Competitor fees from HSBC and Lloyds UK websites, checked 2 Nov 2026.')

    st.subheader('Some customers will send less, so we should test the fee before rolling it out')
    sent = d[d.Channel.eq('Integration') & d.Transacted]
    fees = sent['Transaction Volume (GBP)'].map(lambda v: a.fee(v, rate, minimum, cap))
    drop = st.slider('Out of every 100 transfers, how many stop because of the fee?', 0, 50, 10)
    c1, c2 = st.columns(2)
    c1.metric('Fee income if nobody stops', f'£{fees.sum() * a.SCALE / 1e3:,.0f}k')
    c2.metric(f'Fee income if {drop} in 100 stop', f'£{fees.sum() * a.SCALE * (1 - drop / 100) / 1e3:,.0f}k')
    st.markdown(f"""
- Small transfers feel it most: the minimum is {minimum / 50:.0%} of a £50 transfer. But only {s['small_share']:.0%} of app transfers are £250 or less.
- The risk is customers moving to Wise directly or another provider, which grows the gap from Question 1.
- **How to test it:** split customers at random into a fee group and a no-fee group, show the full cost before they confirm, run it for at least two months, and stop early if complaints or drop-off pass agreed limits.
""")

    st.subheader('Judge the fee on revenue and on customer behaviour together')
    st.dataframe(pd.DataFrame([
        ['Fee check to send rate', 'Does the fee stop people at the last step?'],
        ['First-transfer rate', 'Do new customers still get started?'],
        ['Transfers and money per customer', 'Do people send less often or less money?'],
        ['Customers moving to Wise directly', 'Does the fee push money out of the app?'],
        ['Complaints and support contacts', 'Do customers understand the fee?'],
        ['Extra revenue per customer', 'Is it worth it after customers who stop?'],
    ], columns=['KPI', 'What it tells us']), hide_index=True, width='stretch')
    footnote()


# ---------------------------------------------------------------- Q3
elif page == '3. Multi-currency accounts':
    st.title('3. Multi-currency accounts')
    st.subheader(f'{s["mca_share"]:.0%} of PartnerBank’s customers on Wise already use a multi-currency account')
    c1, c2 = st.columns(2)
    c1.metric(f'Already use a Wise multi-currency account (of {s["wd_users"]:,.0f})', f'{s["mca_users"]:,.0f}')
    c2.metric('Use an account, card or receive money', f'{s["related_users"]:,.0f}')
    wd = d[d.Channel.eq('Wise direct') & d['Product used'].isin(['Multi-currency Account', 'Cards', 'Receive'])]
    by = wd.groupby(['Month', 'Product used'])['User ID'].nunique().unstack(fill_value=0) * a.SCALE
    by = by.rename(columns={'Multi-currency Account': 'Multi-currency account'})
    line_chart(by.rename_axis('Month'), 'Customers', colors=(NAVY, ORANGE, GREY))
    st.markdown("""
- A survey shows what customers say they would do. Wise data shows what some of them already do.
- Show how often they use it and which currencies they hold, to size what the bank is missing.
- These customers are a ready-made pilot group.
- **Caveat:** they already use Wise, so they are keener than the average customer. Use them to design the pilot, not to forecast for the whole bank.
""")
    footnote()


# ---------------------------------------------------------------- Q4
elif page == '4. Internal business case':
    st.title('4. Internal business case')
    st.caption('For the Wise team. Not for the partner.')
    st.subheader('The north star is new revenue that Wise would not earn anyway')
    k = dict(a.Q4_DEFAULTS)
    c1, c2, c3 = st.columns(3)
    k['partners'] = c1.number_input('Partners', 1, 20, k['partners'])
    k['adoption'] = c2.slider('Customers who open an account (%)', 1, 20, k['adoption'])
    k['revenue'] = c3.number_input('Revenue per account per month (£)', 0.0, 10.0, k['revenue'], 0.25)
    model = a.project(**k)
    pb = a.payback_month(model)
    c1, c2 = st.columns(2)
    c1.metric('New revenue over 3 years', f'£{model["New Wise revenue (£)"].sum() / 1e3:,.0f}k')
    c2.metric('Pays back', f'Month {pb}' if pb else 'Not within 3 years')
    run = model.set_index('Month')[['Running total after costs (£)']] / 1e3
    run.columns = ['Running total after costs']
    line_chart(run.rename_axis('Months from decision'), '£ thousands')
    st.markdown("""
- New revenue = account revenue minus revenue Wise already earns from these customers.
- Then subtract build (£300k), launch (£20k per partner), running and activation costs.
- Base case: 3 partners, 5% adoption, £2.50 a month. It adds revenue but does not pay back in 3 years.
""")
    st.subheader('Recommendation: fund a one-partner pilot with clear targets before a full build')
    st.dataframe(pd.DataFrame([
        ['Cost and payback', 'What does it cost to build, launch and run, and when does it pay back?'],
        ['Delivery effort', 'How many engineering months, and what does it delay?'],
        ['Regulatory and fraud risk', 'Holding balances brings safeguarding and licensing work.'],
        ['Confidence in the evidence', 'Is demand proven by behaviour, or only by a survey?'],
        ['Opportunity cost', 'Is revenue per engineering month higher than fixing the Send Money limits?'],
    ], columns=['Beyond revenue, weigh', 'Question to answer']), hide_index=True, width='stretch')
    st.write('**Pilot targets:** adoption rate, new revenue per account, reliability and fraud within limits, and a go or stop decision after 6 months.')
    footnote()


# ---------------------------------------------------------------- About
else:
    st.title('About the data')
    st.markdown("""
- Mock dataset of 10,000 records (April 2025 to March 2026), built around the 12 data points in the brief.
- Counts and money are multiplied by 20 to match PartnerBank’s size (about 33,000 customers checking the fee each quarter). Percentages are not affected.
- Customers are counted once per period, so yearly totals are not the sum of the months.
- Each Wise-direct transfer gets one reason, checked in this order: business, sent from another currency, same currency, missing currency, over £50,000, other product.
- Data I would want next: a link between a fee check and its transfer, sign-up dates, the partner contract, and why customers leave.
""")
    with st.expander('Monthly numbers'):
        st.dataframe(mon, width='stretch')
