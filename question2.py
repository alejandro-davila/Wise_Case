"""Question 2: fee design and usage scenarios, based on completed app transfers."""
import altair as alt
import pandas as pd
import streamlit as st
import scale
from animations import fee_phones, fee_gate
HEIGHT=400


def fee_amount(amounts, rate, minimum, cap):
    return (amounts * rate/100).clip(lower=minimum,upper=cap)


def line(data,x,y,group,x_title,y_title):
    chart=alt.Chart(data).mark_line(point=True).encode(
        x=alt.X(x+':Q',title=x_title), y=alt.Y(y+':Q',title=y_title,scale=alt.Scale(zero=True)),
        color=alt.Color(group+':N',title=None,legend=alt.Legend(orient='bottom')),
        tooltip=list(data.columns)).properties(height=HEIGHT)
    st.altair_chart(chart,use_container_width=True)


def note(meaning,action):
    import html
    st.markdown('<div style="background:#142b42;color:#dceeff;padding:14px;border-radius:10px;margin:10px 0"><b style="color:#8bd0ff">What this means</b><br>'+html.escape(meaning)+'</div><div style="background:#17352b;color:#dcf5e8;padding:14px;border-radius:10px;margin:10px 0"><b style="color:#96e5b6">What PartnerBank can do</b><br>'+html.escape(action)+'</div>',unsafe_allow_html=True)


def render(current,period):
    st.info('Case question 2: The partner proposes a convenience fee. How could this affect usage, and which key performance indicators should the team monitor?')
    st.caption(f'All calculations use {period}. Data is illustrative; fee settings and usage responses below are scenarios, not observed effects.')
    app=current[current.Channel.eq('Integration') & current.Transacted].copy()
    if app.empty:
        st.info('No completed transfers through PartnerBank in this period.')
        return
    st.header('1. Test a percentage fee with a minimum and a cap')
    c1,c2,c3=st.columns(3)
    rate=c1.number_input('Added convenience fee (%)',min_value=0.0,max_value=10.0,value=0.3,step=0.05,key='q2rate')
    minimum=c2.number_input('Minimum added fee (£)',min_value=0.0,value=1.0,step=0.5,key='q2min')
    cap=c3.number_input('Maximum added fee (£)',min_value=0.0,value=15.0,step=1.0,key='q2cap')
    if cap<minimum:
        st.error('The maximum fee must be at least the minimum fee.')
        return
    st.caption('Added fee = MIN(MAX(transfer amount × percentage, minimum), cap). A zero percentage still charges the minimum; set both to zero to model no added fee. This excludes the existing transfer fee and exchange rate.')
    app['Added fee (£)']=fee_amount(app['Transaction Volume (GBP)'],rate,minimum,cap)
    # Fees use real transfer sizes (minimum and cap); totals are scaled to PartnerBank's size.
    fees=float(app['Added fee (£)'].sum())*scale.S; n=scale.n(len(app))
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Completed transfers',f'{n:,}')
    c2.metric('Added fee income if usage holds',f'£{fees:,.0f}')
    c3.metric('Average added fee per transfer',f'£{fees/n:,.2f}')
    c4.metric('Transfers reaching the cap',f'{app["Added fee (£)"].ge(cap).mean():.1%}')
    st.subheader('What the customer sees at each transfer size')
    fee_phones(rate,minimum,cap)
    note('The bank can earn additional income, but a minimum fee takes a bigger share of a small payment. A cap limits the charge on larger payments. These figures apply the proposed fee to completed transfers in the workbook.', 'Start with a small, transparent fee test. Set commercial terms with Wise before treating the calculated fee as income retained by PartnerBank; partner revenue sharing is not provided in this dataset.')
    amounts=pd.Series([50,100,200,500,1000,2000,5000,10000,20000,50000],dtype=float)
    curve=pd.DataFrame({'Transfer amount (£)':amounts,'Added fee (£)':fee_amount(amounts,rate,minimum,cap)})
    curve['Added fee as %']=curve['Added fee (£)']/amounts*100
    a,b=st.columns(2)
    with a:
        st.subheader('How the added charge changes with transfer size')
        curve['Design']='Percentage, minimum and cap'
        line(curve[['Transfer amount (£)','Added fee (£)','Design']], 'Transfer amount (£)','Added fee (£)','Design','Transfer amount (£)','Added fee (£)')
    with b:
        st.subheader('Small transfers can face the biggest burden')
        line(curve[['Transfer amount (£)','Added fee as %','Design']], 'Transfer amount (£)','Added fee as %','Design','Transfer amount (£)','Added fee as % of amount sent')
    st.dataframe(curve.drop(columns='Design').style.format({'Transfer amount (£)':'£{:,.0f}','Added fee (£)':'£{:,.2f}','Added fee as %':'{:.2f}%'}),hide_index=True,width='stretch')

    from competitors import render as render_competitors
    render_competitors(rate, minimum, cap)

    st.subheader('Taxes to keep in mind')
    st.markdown("""<style>
.tx-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:8px 0 6px}
@media (max-width:1100px){.tx-grid{grid-template-columns:repeat(2,1fr)}}
@media (max-width:600px){.tx-grid{grid-template-columns:1fr}}
.tx-card{border:1px solid rgba(140,150,170,.45);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:7px}
.tx-ic{font-size:26px;animation:txBob 3s ease-in-out infinite}
.tx-name{font-size:16px;font-weight:800}
.tx-tag{font-size:11px;font-weight:800;border-radius:999px;padding:3px 9px;max-width:max-content}
.tx-tag.g{background:#9fe870;color:#163300}.tx-tag.y{background:#f2c94c;color:#3a2a00}.tx-tag.b{background:#56c2c9;color:#002c30}
.tx-val{font-size:14px;line-height:1.45}
@keyframes txBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
</style><div class="tx-grid">
<div class="tx-card"><div class="tx-ic">💌</div><div class="tx-name">Personal transfers</div><span class="tx-tag g">No tax taken off</span>
<div class="tx-val">The UK does not take tax off money a person sends abroad. The country receiving it may have its own gift rules, but that is for the person receiving it, not the bank.</div></div>
<div class="tx-card" style="animation-delay:.3s"><div class="tx-ic">🏢</div><div class="tx-name">Business payments</div><span class="tx-tag y">Business may withhold tax</span>
<div class="tx-val">When a UK business pays things like interest or royalties abroad, it may need to keep back UK tax (often 20%). That is the business’s job, but it adds steps to a business version of the app.</div></div>
<div class="tx-card"><div class="tx-ic">🧾</div><div class="tx-name">The convenience fee</div><span class="tx-tag g">Usually no VAT</span>
<div class="tx-val">In the UK, money-transfer services are generally exempt from VAT (Value Added Tax), so the fee likely would not have VAT added. PartnerBank’s tax team should confirm.</div></div>
<div class="tx-card"><div class="tx-ic">🇺🇸</div><div class="tx-name">A US example</div><span class="tx-tag b">1% tax on cash only</span>
<div class="tx-val">Since 1 January 2026, the US charges 1% on remittances paid in cash. Transfers paid from a bank account or card are exempt, which is how PartnerBank’s customers pay.</div></div>
</div>""",unsafe_allow_html=True)
    st.caption('General information for discussion, not tax advice. Rules change and depend on the country and the customer.')

    st.header('2. What if some customers stop sending because of the fee?')
    c1,c2=st.columns(2)
    decline=c1.slider('Out of every 100 transfers, how many stop because of the fee?',0,50,10,1,key='q2drop')
    c1.caption('Example: if 10 out of 100 stop, 90 still happen. This is a guess we can test. The data cannot tell us the real number yet.')
    base_income=c2.number_input('What does PartnerBank earn on each transfer today? (£)',min_value=0.0,value=0.0,step=0.1,key='q2base')
    c2.caption('We do not know this yet. If you know it, type it in. If not, leave it at £0.')
    st.caption('To keep it simple, we assume small and big transfers drop by the same amount.')
    kept=1-decline/100; baseline=n*base_income
    new_fees=fees*kept; income=(fees+baseline)*kept; gain=income-baseline
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Transfers that still happen',f'{n*kept:,.0f}')
    c2.metric('Money from the new fee',f'£{new_fees:,.0f}')
    c3.metric('Extra money for PartnerBank',f'£{gain:,.0f}')
    c4.metric('Money still sent in the app',f'£{app["Transaction Volume (GBP)"].sum()*scale.S*kept:,.0f}')
    away=round(decline/10)
    st.subheader(f'Out of every 10 customers, {away} turn{"s" if away==1 else ""} away in this scenario')
    fee_gate(decline)
    scenario=[]
    for drop in range(0,51,5):
        keep=1-drop/100
        for label,value in [('Added fee income',fees*keep),('Change in bank income',(baseline+fees)*keep-baseline)]:
            scenario.append({'Fewer transfers (%)':drop,'Income (£)':value,'Measure':label})
    st.subheader('If more people stop, how much money is left?')
    line(pd.DataFrame(scenario),'Fewer transfers (%)','Income (£)','Measure','Assumed reduction in completed transfers (%)','Income (£)')
    if baseline+fees>0 and baseline>0:
        st.write(f'With the existing income you entered, modelled bank income breaks even at about **{fees/(baseline+fees):.1%} fewer transfers**, before costs and wider customer effects.')
    else:
        st.caption('We do not know what PartnerBank earns on each transfer today, so we cannot say yet where the fee stops paying off. Type a number in the box above to see it.')
    note('A higher charge can earn more per transfer while causing fewer people to send. Some may move to Wise directly or another provider. Some may send less often or combine payments; the effect will differ by customer and transfer size.', 'Judge the fee on incremental revenue and customer outcomes together. Use the scenario to prepare a test, not to claim a forecast of customer behaviour.')

    st.header('3. Which customers would feel the fee the most?')
    bins=[0,250,1000,5000,10000,float('inf')]
    labels=['Up to £250','£250–£1,000','£1,000–£5,000','£5,000–£10,000','Over £10,000']
    app['Transfer size']=pd.cut(app['Transaction Volume (GBP)'],bins=bins,labels=labels,include_lowest=True)
    groups=app.groupby('Transfer size',observed=True).agg(Customers=('User ID','nunique'),Transfers=('Transfer ID','count'),Volume=('Transaction Volume (GBP)','sum'),Fees=('Added fee (£)','sum')).reset_index()
    groups[['Customers','Transfers','Volume','Fees']]=groups[['Customers','Transfers','Volume','Fees']]*scale.S
    groups['Transfer size']=groups['Transfer size'].astype(str)
    groups['Fee share (%)']=groups.Fees/groups.Volume*100
    xm=float(groups.Customers.median());ym=float(groups['Fee share (%)'].median())
    def group_name(r):
        many=r.Customers>=xm; high=r['Fee share (%)']>=ym
        return ('Watch closely: lots of people, bigger fee share' if many and high else
                'Feel it most, but fewer people' if high else
                'Lots of people, small fee share' if many else 'Fewer people, small fee share')
    groups['Group']=groups.apply(group_name,axis=1)
    worst=groups.loc[groups['Fee share (%)'].idxmax()]; most=groups.loc[groups.Customers.idxmax()]
    lc=lambda t: t[0].lower()+t[1:] if t[:2] in ('Up','Ov') else t
    st.markdown(f'**What this shows:** people sending **{lc(worst["Transfer size"])}** lose the biggest share of their money to the fee '
                f'(**{worst["Fee share (%)"]:.2f}%**). Most customers send **{lc(most["Transfer size"])}** ({int(most.Customers):,} people), '
                f'where the fee is **{most["Fee share (%)"]:.2f}%**.')
    ink='#1f2430'
    order=['Watch closely: lots of people, bigger fee share','Feel it most, but fewer people','Lots of people, small fee share','Fewer people, small fee share']
    dots=alt.Chart(groups).mark_circle(opacity=.85,stroke='white',strokeWidth=1).encode(
        x=alt.X('Customers:Q',title='Number of customers'),y=alt.Y('Fee share (%):Q',title='Share of their money that goes to the fee (%)'),
        size=alt.Size('Transfers:Q',scale=alt.Scale(range=[150,2200]),legend=None),
        color=alt.Color('Group:N',scale=alt.Scale(domain=order,range=['#e8607f','#f2994a','#4f9a1f','#a8b0c3']),legend=alt.Legend(orient='bottom',title=None,labelLimit=400,columns=2,labelColor=ink,labelFontSize=13)),
        tooltip=[alt.Tooltip('Transfer size:N',title='People sending'),alt.Tooltip('Customers:Q',title='Customers',format=','),alt.Tooltip('Transfers:Q',format=','),alt.Tooltip('Fee share (%):Q',format='.2f')])
    text=alt.Chart(groups).mark_text(dy=-20,color=ink,fontSize=13,fontWeight='bold').encode(x='Customers:Q',y='Fee share (%):Q',text='Transfer size:N')
    xrule=alt.Chart(pd.DataFrame({'mid':[xm]})).mark_rule(strokeDash=[5,5],color='#5a6172').encode(x='mid:Q')
    yrule=alt.Chart(pd.DataFrame({'mid':[ym]})).mark_rule(strokeDash=[5,5],color='#5a6172').encode(y='mid:Q')
    st.altair_chart((dots+text+xrule+yrule).properties(height=HEIGHT).configure_axis(labelColor=ink,titleColor=ink,labelFontSize=12,titleFontSize=13),use_container_width=True)
    st.caption('Bigger bubble = more transfers. The dotted lines show the middle. One person can send different amounts, so they can be in more than one bubble.')

    st.header('4. Test the fee and watch these numbers')
    kpis=[
        ('💷','Revenue','Extra money PartnerBank makes for each customer in the test','Count everyone in the test, even people who do not send.','Weekly + end of test'),
        ('🔁','Conversion','Of the people who check the fee, how many send','Does this drop compared with customers who do not pay the new fee?','Weekly'),
        ('🚀','First transfer','Of new sign-ups, how many make a first transfer','New customers may be the most put off by a fee.','Weekly'),
        ('📊','Usage','How many people send, how often, and how much','Is someone gone for good, or just sending less often?','Weekly'),
        ('🔀','Switching','Customers who start using Wise directly instead','Are test customers leaving the app to send somewhere else?','Monthly'),
        ('🔄','Repeat use','Customers who come back and send again','Compare similar groups over the same amount of time.','After a few months'),
        ('🤝','Trust','Complaints, refunds and happiness scores','Complaints often show up before the money drops.','Weekly'),
        ('⚡','Reliability','Transfers that work, how fast they arrive, errors','Keep the service fast and working. This data comes from the app’s logs.','Daily'),
    ]
    import html as _h
    cards=''.join(f'<div class="kp-card"><div class="kp-top"><span class="kp-ic">{ic}</span><span class="kp-name">{_h.escape(nm)}</span><span class="kp-when">{_h.escape(when)}</span></div>'
                  f'<div class="kp-lbl">What we count</div><div class="kp-val">{_h.escape(what)}</div>'
                  f'<div class="kp-lbl">What to watch for</div><div class="kp-val">{_h.escape(watch)}</div></div>' for ic,nm,what,watch,when in kpis)
    st.markdown("""<style>
.kp-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:8px 0 14px}
@media (max-width:1100px){.kp-grid{grid-template-columns:repeat(2,1fr)}}
@media (max-width:600px){.kp-grid{grid-template-columns:1fr}}
.kp-card{border:1px solid rgba(140,150,170,.45);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.kp-top{display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap}
.kp-ic{font-size:22px}.kp-name{font-size:16px;font-weight:800;flex:1 1 calc(100% - 40px);white-space:nowrap}
.kp-when{font-size:11px;font-weight:800;background:#9fe870;color:#163300;border-radius:999px;padding:3px 9px;white-space:nowrap;flex-basis:100%;max-width:max-content;margin-top:2px}
.kp-lbl{font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;margin-top:4px}
.kp-val{font-size:14px;line-height:1.45}
</style><div class="kp-grid">"""+cards+'</div>',unsafe_allow_html=True)
    note('We cannot measure the effect of a new fee from historical data where no test was run. The workbook can describe current usage and calculate example charges.', 'Randomise eligible customers, not individual transfers, into a control and fee group. Show all costs before confirmation. Set revenue and customer guardrails, calculate the sample size, and run long enough to cover repeat transfers. Launch only if the evidence supports it.')
    with st.expander('See the calculations and export the scenarios'):
        st.code('added_fee = min(max(transfer_amount * percentage / 100, minimum), cap)\nexpected_added_fee_income = sum(added_fee) * (1 - assumed_drop)\nchange_in_bank_income = (existing_income + sum(added_fee)) * (1 - assumed_drop) - existing_income',language='python')
        st.download_button('Download fee scenarios',pd.DataFrame(scenario).to_csv(index=False).encode(),'partnerbank_fee_scenarios.csv','text/csv')
