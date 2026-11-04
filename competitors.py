"""Published United Kingdom personal-transfer fee context; manually verified official pages."""
import altair as alt
import pandas as pd
import streamlit as st

HSBC='https://www.hsbc.co.uk/international/money-transfer/'
LLOYDS='https://www.lloydsbank.com/help-guidance/everyday-banking/payments-and-transfers/send-international-payment.html'
NATWEST='https://www.natwest.com/banking-with-natwest/how-to/send-money-abroad.html'
REVOLUT='https://www.revolut.com/legal/personal-current-account-fees/'
REV_FX='https://help.revolut.com/en-GB/help/wealth/exchanging-money/how-much-does-it-cost-to-make-an-exchange/will-i-be-charged-for-exchanging-foreign-currencies/'


CARD_CSS = """<style>
.cp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:8px 0 14px}
.cp-card{border:1px solid rgba(140,150,170,.4);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:9px}
.cp-card.pb{border:2px solid #9fe870;background:rgba(159,232,112,.08)}
.cp-name{font-size:16px;font-weight:800;line-height:1.3}
.cp-prod{font-size:12px;opacity:.85;margin-top:-6px}
.cp-lbl{font-size:10.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;opacity:.85}
.cp-val{font-size:13.5px;line-height:1.45}
.cp-src{margin-top:auto;font-size:12.5px;font-weight:700}
.cp-src a{color:#4f9a1f;text-decoration:none}
</style>"""


def provider_cards(rows):
    import html
    cards=[]
    for r in rows:
        name,_,product=r['Provider / product'].partition(' — ')
        src=f'<a href="{r["Official source"]}" target="_blank">View official pricing ↗</a>' if r['Official source'] else 'Illustrative design for this case study'
        cards.append(f'<div class="cp-card{" pb" if name.startswith("PartnerBank") else ""}">'
            f'<div class="cp-name">{html.escape(name)}</div><div class="cp-prod">{html.escape(product)}</div>'
            + ''.join(f'<div><div class="cp-lbl">{k}</div><div class="cp-val">{html.escape(r[k])}</div></div>' for k in ['Transfer fee','Exchange-rate cost','Conditions'])
            + f'<div class="cp-src">{src}</div></div>')
    st.markdown(CARD_CSS+'<div class="cp-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)


def render(rate,minimum,cap):
    st.subheader('Competitor context — what other providers charge')
    st.caption('HSBC = Hongkong and Shanghai Banking Corporation. United Kingdom personal products • official pages checked 2 November 2026 • published pricing, not live transfer quotes or an industry average. Prices vary by account, route and payment method.')
    rows=[
        {'Provider / product':'HSBC — standard online/app','Transfer fee':'£5 for non-euro payments and euros outside the European Economic Area (EEA); £0 to HSBC accounts or euros within the EEA','Exchange-rate cost':'HSBC rate includes a conversion charge; get a quote','Conditions':'Premier/Private and Global Money have fee exceptions. Other-bank charges can apply.','Official source':HSBC},
        {'Provider / product':'HSBC — Global Money','Transfer fee':'£0 HSBC fee','Exchange-rate cost':'HSBC exchange rate applies; compare the amount the recipient gets','Conditions':'Eligible current account and app required. Distinct product from standard payments.','Official source':HSBC},
        {'Provider / product':'Lloyds — personal international payments','Transfer fee':'£9.50 for non-euro payments; £0 for euro payments','Exchange-rate cost':'Published standard margin 3.55% for £0–£10,000; lower tiers for larger amounts','Conditions':'Account exceptions apply; intermediary/recipient bank charges can apply.','Official source':LLOYDS},
        {'Provider / product':'NatWest — personal online/app','Transfer fee':'£0 sending fee','Exchange-rate cost':'Margin varies; main page states a maximum of 3.25%','Conditions':'Optional £10 handling-fee arrangement; other-bank deductions may still apply. Confirm live quote.','Official source':NATWEST},
        {'Provider / product':'Revolut — Standard','Transfer fee':'£0 for euros within the Single Euro Payments Area (SEPA); outside SEPA the fee depends on currency and destination','Exchange-rate cost':'1% fair-usage fee above £1,000 rolling-month exchange allowance; Standard weekend exchange fee 1%','Conditions':'Plan, allowance used and timing matter. Check non-SEPA fees in the app; third-party fees may apply.','Official source':REVOLUT},
        {'Provider / product':'PartnerBank — proposed added fee','Transfer fee':f'{rate:g}% with £{minimum:g} minimum and £{cap:g} cap','Exchange-rate cost':'Underlying service charges and rate must be added separately','Conditions':'Illustrative convenience-fee design; not a live quote or total cost.','Official source':None},
    ]
    provider_cards(rows)
    st.subheader('Who charges what to send money?')
    route=st.selectbox('Where is the money going?',['To a country that does not use euros (like India)','To a country that uses euros (like Spain)'],key='competitor_route')
    euro='uses euros' in route
    def crossing(level):
        point=level/(rate/100) if rate else None
        return point if point and minimum<level<cap else None
    if not euro:
        tips=[]
        for name,level in [('HSBC',5),('Lloyds',9.5)]:
            x=crossing(level)
            if x: tips.append(f'PartnerBank is cheaper than {name} (£{level:,.2f}'.replace('.00','')+f') when you send less than **£{x:,.0f}**.')
        tips.append(f'PartnerBank’s fee never goes above **£{cap:g}**, no matter how much you send.')
        st.markdown('**What this shows:** ' + ' '.join(tips))
    else:
        st.markdown(f'**What this shows:** to euro countries, HSBC, Lloyds and NatWest all show a £0 sending fee. PartnerBank’s new fee would be between £{minimum:g} and £{cap:g}.')
    names={'PartnerBank (new fee)':None,'HSBC':5,'Lloyds':9.5,'NatWest':0}
    comparison=[]
    for amount in [50,100,250,500,1000,2000,5000,10000]:
        for provider,fixed in names.items():
            fee=min(max(amount*rate/100,minimum),cap) if fixed is None else (0 if euro else fixed)
            if provider=='NatWest': fee=0
            comparison.append({'Amount sent (£)':amount,'Sending fee (£)':fee,'Who':provider})
    data=pd.DataFrame(comparison)
    order=list(names)
    chart=alt.Chart(data).mark_line(point=True).encode(
        x=alt.X('Amount sent (£):Q',title='How much you send (£)',axis=alt.Axis(format=',.0f')),
        y=alt.Y('Sending fee (£):Q',title='Sending fee (£)',scale=alt.Scale(zero=True)),
        color=alt.Color('Who:N',scale=alt.Scale(domain=order,range=['#4f9a1f','#4f8ff7','#f2994a','#bb6bd9']),legend=alt.Legend(orient='bottom',title=None)),
        strokeWidth=alt.condition(alt.datum.Who=='PartnerBank (new fee)',alt.value(5),alt.value(2)),
        tooltip=[alt.Tooltip('Who:N'),alt.Tooltip('Amount sent (£):Q',format=',.0f'),alt.Tooltip('Sending fee (£):Q',format=',.2f')]).properties(height=400)
    st.altair_chart(chart,use_container_width=True)
    st.caption('Tip: point at a dot to see the exact fee. NatWest’s line sits at £0. This chart only shows the sending fee. It does not include the exchange rate, which can cost more than the fee.')
    amount=st.number_input('Try an amount (£)',min_value=1.0,value=1000.0,step=100.0,key='competitor_example')
    added=min(max(amount*rate/100,minimum),cap)
    st.markdown(f'If you send **£{amount:,.0f}**, PartnerBank’s new fee is **£{added:,.2f}**. That is **{added/amount*100:,.0f}p for every £1** you send.' if added/amount*100>=1 else
                f'If you send **£{amount:,.0f}**, PartnerBank’s new fee is **£{added:,.2f}**. That is **{added/amount*10000:,.0f}p for every £100** you send.')
    st.info('💡 A £0 fee does not always mean free. Banks can also make money on the exchange rate. The fair test is simple: for the same £, who gives the other person the most money?')
    st.markdown(f'Where these prices come from: [HSBC]({HSBC}) · [Lloyds]({LLOYDS}) · [NatWest]({NATWEST}) · [Revolut transfer fees]({REVOLUT}) · [Revolut exchange fees]({REV_FX})')
    st.caption('NatWest shows two different exchange-rate numbers on its website (3.25% and 2.75%). We used 3.25% from its main page. Always check a live quote before comparing.')
