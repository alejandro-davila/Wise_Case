"""Question 3: use observed Wise activity to supplement PartnerBank's survey."""
import altair as alt
import pandas as pd
import streamlit as st
from display_names import readable_table
from question2 import note
import scale
from animations import account_panels, adopter_grid
HEIGHT=400
MCA='Multi-currency Account'
PRODUCTS=['Send Money',MCA,'Receive','Cards']


def customer_groups(d):
    # Mutually exclusive groups; include all observed activity for each customer.
    g=d.groupby('User ID').agg(Activities=('Transfer ID','count'),Revenue=('Revenue Amount (GBP)','sum'),Volume=('Transaction Volume (GBP)','sum'),Active_months=('Month','nunique'),Products=('Product used',lambda x:set(x)))
    g['Group']=g.Products.map(lambda p:'Used a multi-currency account' if MCA in p else ('Cards / Receive without multi-currency account' if p & {'Cards','Receive'} else 'Send Money only'))
    return g


def render(current,period):
    st.info('Case question 3: The bank’s research shows interest in multi-currency accounts. How would you use Wise data to strengthen the business case?')
    st.caption(f'{period} • Illustrative activity, calculated from the workbook. We have the statement that the survey found interest, but no survey responses or customer-level survey results.')
    d=current[current.Channel.eq('Wise direct') & current.Transacted].copy()
    if d.empty:
        st.info('No completed Wise-direct activity in this period.')
        return
    d['Month']=d.Date.dt.to_period('M').dt.to_timestamp()
    users=d['User ID'].nunique()
    mca_ids=set(d.loc[d['Product used'].eq(MCA),'User ID'])
    related_ids=set(d.loc[d['Product used'].isin([MCA,'Receive','Cards']),'User ID'])
    c1,c2,c3,c4=st.columns(4)
    c1.metric('PartnerBank customers using Wise directly',f'{scale.n(users):,}')
    c2.metric('Already using a multi-currency account',f'{scale.n(len(mca_ids)):,}')
    c3.metric('Share using a multi-currency account',f'{len(mca_ids)/users:.1%}')
    c4.metric('Using accounts, cards or receiving',f'{scale.n(len(related_ids)):,}')
    st.subheader('What a multi-currency account lets customers do')
    account_panels()
    note('The survey tells us what people say they want. Their activity on Wise shows what some of PartnerBank’s customers already do. Existing account use is stronger evidence of a need than general interest alone.', 'Start with customers already using these products. Learn what they use them for and whether they would choose the same service inside PartnerBank’s app. This group is not representative of all bank customers.')

    st.header('1. Show existing demand and whether it persists')
    months=pd.date_range(current.Date.min().to_period('M').start_time,current.Date.max().to_period('M').start_time,freq='MS')
    monthly=d.groupby(['Month','Product used'])['User ID'].nunique().unstack(fill_value=0).reindex(index=months,columns=PRODUCTS,fill_value=0).fillna(0)
    monthly=monthly*scale.S
    monthly.index.name='Month'
    related=d[d['Product used'].isin([MCA,'Receive','Cards'])].groupby('Month')['User ID'].nunique().reindex(months,fill_value=0)
    g=customer_groups(d)
    seg=g.groupby('Group').agg(Customers=('Activities','size'),Activities=('Activities','sum'),Volume=('Volume','sum'),Revenue=('Revenue','sum'))
    seg['multi-currency account use']=seg.index=='Used a multi-currency account'
    left,right=st.columns(2)
    with left:
        st.subheader('Account, card and receiving users by month')
        plot=monthly[[MCA,'Receive','Cards']].reset_index().melt(id_vars='Month',var_name='Product',value_name='Customers')
        line=alt.Chart(plot).mark_line(point=True).encode(x=alt.X('Month:T',axis=alt.Axis(format='%b %Y'),title=None),y=alt.Y('Customers:Q',scale=alt.Scale(zero=True)),color=alt.Color('Product:N',legend=alt.Legend(orient='bottom')),tooltip=['Product:N',alt.Tooltip('Month:T',format='%b %Y'),'Customers:Q']).properties(height=HEIGHT)
        st.altair_chart(line,use_container_width=True)
        st.caption('Counts different people in each product each month. People may use more than one product; do not add product counts to get unique users. Axes are fixed.')
    with right:
        st.subheader('Product demand quadrants')
        prod=d.groupby('Product used').agg(Customers=('User ID','nunique'),Activities=('Transfer ID','count'),Volume=('Transaction Volume (GBP)','sum')).reset_index()
        prod[['Customers','Activities','Volume']]=prod[['Customers','Activities','Volume']]*scale.S
        prod['Average activity amount']=prod.Volume/prod.Activities
        xm=float(prod.Customers.median());ym=float(prod['Average activity amount'].median())
        prod['Demand group']=prod.apply(lambda r:('More users' if r.Customers>=xm else 'Fewer users')+' / '+('larger amounts' if r['Average activity amount']>=ym else 'smaller amounts'),axis=1)
        pts=alt.Chart(prod).mark_circle(opacity=.8).encode(x=alt.X('Customers:Q',title='Different customers',scale=alt.Scale(zero=True)),y=alt.Y('Average activity amount:Q',title='Average recorded activity (£)',scale=alt.Scale(zero=True)),size=alt.Size('Activities:Q',scale=alt.Scale(range=[150,2200]),legend=None),color=alt.Color('Product used:N',legend=alt.Legend(orient='bottom')),tooltip=list(prod.columns))
        xr=alt.Chart(pd.DataFrame({'mid':[xm]})).mark_rule(strokeDash=[5,5],color='#8a93a5').encode(x='mid:Q')
        yr=alt.Chart(pd.DataFrame({'mid':[ym]})).mark_rule(strokeDash=[5,5],color='#8a93a5').encode(y='mid:Q')
        st.altair_chart((pts+xr+yr).properties(height=HEIGHT),use_container_width=True)
        st.caption('Bubble size = recorded activity count. Lines = medians across four products. These are descriptive groups, not evidence of statistical clusters. multi-currency account activity amount is not an account balance.')
    counts=(d.groupby('Product used').agg(Customers=('User ID','nunique'),Activities=('Transfer ID','count')).reindex(PRODUCTS,fill_value=0)*scale.S).round().astype(int)
    st.dataframe(counts,width='stretch')
    note('Account, card and receiving activity can point to ongoing international needs. Monthly movement helps us see whether demand appears throughout the period rather than in one month.', 'Check the purpose of use through interviews and account-level data. We cannot infer balances held, currencies held, salary receipts, card spending or transfer purposes from product labels alone.')

    st.header('2. Compare account users with customers who only send money')
    st.caption('Customers are assigned once: any multi-currency account use → multi-currency account group; otherwise any Cards/Receive → related-products group; otherwise Send Money only. Every observed activity for each customer is included in that customer’s totals.')
    if not scale.INTERNAL:
        st.info('Revenue per customer is Wise’s own data, so it shows only in the Wise team view (sidebar). Below: how active each group is.')
        act=g.groupby('Group').agg(Customers=('Activities','size'),Median_activities=('Activities','median'),Repeat_activity_share=('Activities',lambda x:x.ge(2).mean()),Median_active_months=('Active_months','median'))
        act['Customers']=(act['Customers']*scale.S).round().astype(int)
        st.dataframe(act.rename(columns={'Median_activities':'Typical activities per customer','Repeat_activity_share':'Used it 2+ times','Median_active_months':'Typical active months'}).style.format({'Used it 2+ times':'{:.0%}','Customers':'{:,}'}),width='stretch')
    else:
     with st.container(border=True):
       scale.wise_tag('Wise team only: Wise’s revenue per customer')
       c1,c2=st.columns(2)
       customer=g.reset_index().drop(columns=['Products'])
       with c1:
           st.subheader('Recorded revenue per customer — distribution')
           box=alt.Chart(customer).mark_boxplot(extent=1.5,size=28).encode(x=alt.X('Group:N',title=None,axis=alt.Axis(labelAngle=-15,labelLimit=200)),y=alt.Y('Revenue:Q',title='Recorded Wise-direct revenue per customer (£)'),color=alt.Color('Group:N',legend=None),tooltip=['Group:N']).properties(height=HEIGHT)
           st.altair_chart(box,use_container_width=True)
           st.caption('The centre line is the median. The box shows the middle half of customers; dots beyond the whiskers are outliers. Revenue is only what this transfer-level workbook records, not complete account or card economics.')
       with c2:
           st.subheader('Usage and recorded revenue together')
           pts=alt.Chart(customer).mark_circle(size=65,opacity=.5).encode(x=alt.X('Activities:Q',title='Recorded activities per customer'),y=alt.Y('Revenue:Q',title='Recorded Wise-direct revenue per customer (£)'),color=alt.Color('Group:N',legend=alt.Legend(orient='bottom')),tooltip=['Group:N','Activities:Q',alt.Tooltip('Revenue:Q',format=',.2f'),'Active_months:Q']).properties(height=HEIGHT)
           st.altair_chart(pts,use_container_width=True)
           st.caption('Each dot represents a customer. Compare customers with similar needs and activity levels before attributing revenue differences to account use.')
       comparison=g.groupby('Group').agg(Customers=('Activities','size'),Median_activities=('Activities','median'),Median_recorded_revenue=('Revenue','median'),Mean_recorded_revenue=('Revenue','mean'),Repeat_activity_share=('Activities',lambda x:x.ge(2).mean()),Median_active_months=('Active_months','median'))
       comparison['Customers']=(comparison['Customers']*scale.S).round().astype(int)
       st.dataframe(comparison.style.format({'Median_recorded_revenue':'£{:,.2f}','Mean_recorded_revenue':'£{:,.2f}','Repeat_activity_share':'{:.1%}'}),width='stretch')
    note('This comparison describes the customers we observe. People who use accounts may already have different needs, transfer sizes or time with Wise. Two activities in a period is repeat activity, not a retention rate.', 'Compare similar customer cohorts by tenure, currency needs, transfer size and customer type. Use a pilot to measure whether offering accounts causes additional use or retention; do not assume a revenue multiple from this dataset.')

    st.header('3. Turn the survey and Wise behaviour into a pilot audience')
    c1,c2=st.columns(2)
    with c1:
        st.subheader('Source currencies used by account customers')
        st.caption('Currencies sent from are a clue to customer needs. They do not tell us which currencies are held in accounts.')
        d_mca=d[d['User ID'].isin(mca_ids)]
        currency=d_mca.groupby('Source Currency').agg(Customers=('User ID','nunique'),Recorded_volume=('Transaction Volume (GBP)','sum'))*scale.S
        currency['Customers']=currency['Customers'].round().astype(int)
        st.dataframe(readable_table(currency).style.format({'Recorded_volume':'£{:,.0f}'}),width='stretch')
    with c2:
        st.subheader('Personal versus business interest')
        st.caption('Business activity is reported separately: the bank’s current integration is personal-only.')
        personal_ids=set(d.loc[d['User type'].eq('Personal'),'User ID'])
        business_ids=set(d.loc[d['User type'].eq('Business'),'User ID'])
        segments=pd.DataFrame([{'Customer type':label,'Wise-direct customers':scale.n(len(ids)),'multi-currency account users':scale.n(len(ids & mca_ids)),'Related-product users':scale.n(len(ids & related_ids))} for label,ids in [('Personal',personal_ids),('Business',business_ids)]])
        st.dataframe(segments,hide_index=True,width='stretch')
    base=scale.n(len(personal_ids & related_ids))
    adoption=st.slider('Assumed pilot adoption among personal related-product users (%)',0,100,20,5,key='q3adopt')
    a,b,c=st.columns(3)
    a.metric('Observed personal pilot audience',f'{base:,}')
    b.metric('Assumed adoption',f'{adoption}%')
    c.metric('Potential pilot adopters',f'{round(base*adoption/100):,}')
    adopter_grid(base,adoption)
    adoption_curve=pd.DataFrame({'Assumed adoption (%)':list(range(0,101,10))})
    adoption_curve['Potential pilot adopters']=adoption_curve['Assumed adoption (%)']*base/100
    st.altair_chart(alt.Chart(adoption_curve).mark_line(point=True,color='#70d69b').encode(x='Assumed adoption (%):Q',y='Potential pilot adopters:Q',tooltip=list(adoption_curve.columns)).properties(height=HEIGHT),use_container_width=True)
    st.caption('This is a scenario for a small observed audience, not a forecast for all PartnerBank customers. Related-product users are distinct people using multi-currency account, Cards or Receive. The survey’s interested customers may overlap with this group; count each person once when matching datasets.')
    note('We can propose a pilot audience without inventing the bank’s total customer base or a survey conversion rate. Observed use and stated interest are different signals that become stronger when combined.', 'With consent and appropriate data access, link survey respondents to the bank-funded Wise cohort, validate eligibility, interview a sample and test a clearly priced account offer. Measure activation, use and customer value against a comparison group.')

    st.header('4. Evidence to bring to the bank')
    evidence=[('📝','Survey interest','What customers say they want','Survey sample, response rate, use cases and willingness to pay'),
        ('👛','Account use on Wise today','What some customers already do','Account balances, currencies held and eligible account coverage'),
        ('💳','Receive and Cards activity','Needs beyond sending money','Actual money received, card spending and why'),
        ('🔁','Repeat use','How often customers come back','Customer history over time and comparable groups'),
        ('🧪','Pilot results','Whether customers sign up inside PartnerBank','Sign-ups, active accounts, balances, extra revenue, support and compliance costs')]
    import html as _h
    cards=''.join(f'<div class="ev-card"><div class="ev-ic">{ic}</div><div class="ev-name">{_h.escape(nm)}</div>'
                  f'<div class="ev-lbl">What it tells us</div><div class="ev-val">{_h.escape(tells)}</div>'
                  f'<div class="ev-lbl">Data we still need</div><div class="ev-val">{_h.escape(need)}</div></div>' for ic,nm,tells,need in evidence)
    st.markdown("""<style>.ev-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:8px 0 12px}
@media (max-width:1200px){.ev-grid{grid-template-columns:repeat(3,1fr)}}@media (max-width:700px){.ev-grid{grid-template-columns:1fr}}
.ev-card{border:1px solid rgba(140,150,170,.45);border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:5px;text-align:center}
.ev-ic{font-size:26px}.ev-name{font-size:15px;font-weight:800;min-height:2.6em}
.ev-lbl{font-size:10.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;margin-top:6px}.ev-val{font-size:13.5px;line-height:1.45}</style>
<div class="ev-grid">"""+cards+'</div>',unsafe_allow_html=True)
    st.success(f'PartnerBank already has {scale.n(len(mca_ids)):,} identified customers using multi-currency account on Wise directly in this period, and {scale.n(len(related_ids)):,} using multi-currency account, Cards or Receive. This supports testing demand inside the bank’s app. It does not yet establish adoption, incremental revenue or retention.')
    with st.expander('Definitions and monthly data'):
        st.write('multi-currency account user = distinct PartnerBank-funded Wise customer with at least one multi-currency account-labelled activity in the selected period. Related-product user = distinct customer with multi-currency account, Receive or Cards activity. Customers can use multiple products. Current balances and actual account opening dates are unavailable.')
        st.dataframe(monthly,width='stretch')
        st.download_button('Download product demand by month',monthly.to_csv().encode(),'partnerbank_product_demand.csv','text/csv')
