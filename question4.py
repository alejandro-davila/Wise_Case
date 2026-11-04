"""Question 4: illustrative monthly investment model for Wise Platform."""
import pandas as pd
import altair as alt
import streamlit as st
from question2 import note
import scale
from animations import investment_road
HEIGHT=400


def project(months,partners,eligible,adoption,revenue,displaced,service,build,onboarding,fixed,launch,ramp,attrition,activation):
    """One launch cohort, linear acquisition ramp, monthly attrition after activation."""
    target=partners*eligible*adoption/100
    new_each=target/ramp
    active=0.0; cumul=0.0; rows=[]
    for month in range(1,months+1):
        live=month>launch
        new=new_each if live and month<=launch+ramp else 0.0
        active=active*(1-attrition/100)+new if live else 0.0
        gross=active*revenue
        lost=active*displaced
        incremental=gross-lost
        running=active*service+(fixed if live else 0)
        acquisition=new*activation
        upfront=build+partners*onboarding if month==1 else 0.0
        cash=incremental-running-acquisition-upfront
        cumul+=cash
        rows.append({'Month':month,'Active accounts':active,'New accounts':new,'Gross product revenue (£)':gross,
            'Existing revenue displaced (£)':lost,'Incremental Wise revenue (£)':incremental,'Operating cost (£)':running,
            'Activation cost (£)':acquisition,'Upfront investment (£)':upfront,'Net cash contribution (£)':cash,'Cumulative contribution (£)':cumul})
    return pd.DataFrame(rows)


def render(df,current,period):
    st.info('Case question 4: If multi-currency accounts are a new Wise Platform offering, how would you build an internal investment case and decide whether to prioritise it? The north-star measure is revenue.')
    if scale.INTERNAL:
        st.markdown('<div class="wise-hl" style="margin:14px 0;padding:12px 14px;text-align:center;font-weight:800">This whole page is Wise Platform’s internal business case. Share it with the Wise team only, not with the partner.</div>',unsafe_allow_html=True)
    if not scale.INTERNAL:
        st.warning('🔒 Internal Wise page: this is Wise Platform’s own business case. Switch the sidebar to “Wise team (internal)” before presenting it, and do not share it with the partner.')
    st.caption('Perspective: Wise Platform’s investment decision. All model inputs are editable illustrative assumptions, not published Wise unit economics or a forecast.')
    st.subheader('The path from investment to revenue')
    investment_road()
    st.header('1. Start with customer demand, then define what we must learn')
    direct=current[current.Channel.eq('Wise direct') & current.Transacted]
    users=scale.n(direct['User ID'].nunique())
    acct=direct.loc[direct['Product used'].str.contains('Multi-currency Account',case=False,na=False),'User ID'].nunique()
    acct=scale.n(acct)
    a,b,c=st.columns(3)
    a.metric('Observed bank customers using Wise directly',f'{users:,}')
    b.metric('Observed multi-currency account users',f'{acct:,}')
    c.metric('Observed account-use share',f'{acct/users:.1%}' if users else 'No data')
    note('Existing use supports investigating demand. It does not establish how many customers would adopt inside the bank, how many banks will launch, or what new revenue Wise would earn.', 'Validate signed partner demand, eligible customer numbers and willingness to pay. Use pilot evidence to replace the assumptions below before requesting a full rollout.')
    st.header('2. Model new Wise revenue and the resources needed')
    st.caption('Revenue is the primary measure. Costs, payback, delivery risk and opportunity cost determine whether the revenue is worth pursuing.')
    with st.container(border=True):
        a,b,c=st.columns(3)
        partners=a.number_input('Partners expected to launch',min_value=1,max_value=100,value=3,step=1,key='q4partners')
        eligible=b.number_input('Eligible customers per partner',min_value=0,value=100000,step=10000,key='q4eligible')
        adoption=c.slider('Customers expected to open an account (%)',0,100,5,1,key='q4adopt')
        a,b,c=st.columns(3)
        revenue=a.number_input('Product revenue per active account per month (£)',min_value=0.0,value=2.5,step=.25,key='q4revenue')
        displaced=b.number_input('Existing Wise revenue replaced per active account per month (£)',min_value=0.0,value=.5,step=.25,key='q4displaced')
        service=c.number_input('Service cost per active account per month (£)',min_value=0.0,value=.75,step=.25,key='q4service')
        st.caption('Product revenue may include agreed partner charges, transfer income and card income. Only include balance-related income where legally and commercially applicable. Subtract revenue Wise already earns that the new offering would replace; moving an existing transfer into the bank is not automatically new Wise revenue.')
        a,b,c=st.columns(3)
        build=a.number_input('One-time product build cost (£)',min_value=0.0,value=300000.0,step=25000.0,key='q4build')
        onboarding=b.number_input('One-time launch cost per partner (£)',min_value=0.0,value=20000.0,step=5000.0,key='q4onboard')
        fixed=c.number_input('Shared operating cost per live month (£)',min_value=0.0,value=5000.0,step=1000.0,key='q4fixed')
        a,b,c=st.columns(3)
        activation=a.number_input('One-time activation cost per new account (£)',min_value=0.0,value=3.0,step=1.0,key='q4activation')
        launch=b.slider('Months before launch',0,24,6,1,key='q4launch')
        ramp=c.slider('Months to reach target account openings',1,24,6,1,key='q4ramp')
        a,b=st.columns(2)
        attrition=a.slider('Active accounts lost each month (%)',0.0,10.0,1.0,.5,key='q4attrition')
        months=b.slider('Forecast length in months',12,60,36,12,key='q4months')
        st.caption('One cohort of partners launches after the delay. Account openings spread evenly over the ramp. Existing active accounts lose the selected share each month; new openings are then added. Build and partner-launch costs are charged in month one. Shared costs start when partners launch. This is a planning model before tax, discounting and working-capital effects.')
    args=dict(months=months,partners=partners,eligible=eligible,adoption=adoption,revenue=revenue,displaced=displaced,service=service,build=build,onboarding=onboarding,fixed=fixed,launch=launch,ramp=ramp,attrition=attrition,activation=activation)
    model=project(**args)
    def stable_payback(frame):
        # Require contribution to stay nonnegative through the remaining horizon.
        for i,row in frame.iterrows():
            if row['Cumulative contribution (£)']>=0 and frame.loc[i:,'Cumulative contribution (£)'].ge(0).all():
                return int(row.Month)
        return None
    payback=stable_payback(model)
    a,b,c,d=st.columns(4)
    a.metric('New Wise revenue: first 12 months',f'£{model.iloc[:12]["Incremental Wise revenue (£)"].sum():,.0f}')
    b.metric(f'New Wise revenue: {months} months',f'£{model["Incremental Wise revenue (£)"].sum():,.0f}')
    c.metric('Contribution after modelled costs',f'£{model["Cumulative contribution (£)"].iloc[-1]:,.0f}')
    d.metric('Payback',f'Month {payback}' if payback else 'Not reached in forecast')
    def fixed_line(frame,values,title):
        tidy=frame[['Month']+values].melt('Month',var_name='Measure',value_name='Pounds')
        chart=alt.Chart(tidy).mark_line(point=True).encode(x=alt.X('Month:Q',title='Months from investment decision'),y=alt.Y('Pounds:Q',title=title),color=alt.Color('Measure:N',legend=alt.Legend(orient='bottom',title=None)),tooltip=['Month:Q','Measure:N',alt.Tooltip('Pounds:Q',format=',.0f')]).properties(height=HEIGHT)
        st.altair_chart(chart,use_container_width=True)
    left,right=st.columns(2)
    with left:
        st.subheader('Revenue earned, replaced and added')
        fixed_line(model,['Gross product revenue (£)','Existing revenue displaced (£)','Incremental Wise revenue (£)'],'Revenue per month (£)')
    with right:
        st.subheader('When does the investment pay back?')
        fixed_line(model,['Cumulative contribution (£)'],'Cumulative contribution (£)')
    note('The revenue difference is what matters: product revenue minus existing Wise revenue it replaces. A project can add revenue but still fail to cover its build and operating costs within the forecast.', 'Agree a revenue hurdle, cost budget and acceptable payback with decision-makers. Check downside outcomes before committing engineering and implementation teams.')

    st.header('3. Compare outcomes and identify what drives the decision')
    scenarios=[('Downside',.5,.75,3),('Base',1,1,0),('Upside',1.5,1.25,0)]
    rows=[]
    for name,adopt_mult,rev_mult,delay in scenarios:
        a=args.copy();a['adoption']=min(100,adoption*adopt_mult);a['revenue']=revenue*rev_mult;a['launch']=launch+delay
        result=project(**a); pb=stable_payback(result)
        rows.append({'Scenario':name,'Adoption (%)':a['adoption'],'Revenue per account per month (£)':a['revenue'],'Launch month':a['launch']+1,'Incremental revenue (£)':result['Incremental Wise revenue (£)'].sum(),'Contribution (£)':result['Cumulative contribution (£)'].iloc[-1],'Payback':f'Month {pb}' if pb else 'Not reached'})
    scenario=pd.DataFrame(rows)
    st.dataframe(scenario.style.format({'Revenue per account per month (£)':'£{:,.2f}','Incremental revenue (£)':'£{:,.0f}','Contribution (£)':'£{:,.0f}'}),hide_index=True,width='stretch')
    st.caption('Downside: half the adoption, 25% less product revenue per account and a three-month delay. Upside: 50% more adoption and 25% more product revenue per account. These are stress assumptions, not probability estimates.')
    sensitivity=[]
    for ar in [0,1,2,5,10,15,20]:
        for rev in [0,1,2.5,5,7.5]:
            a=args.copy();a['adoption']=ar;a['revenue']=rev
            result=project(**a)
            sensitivity.append({'Adoption (%)':ar,'Revenue per account per month (£)':rev,'Contribution (£)':result['Cumulative contribution (£)'].iloc[-1]})
    grid=pd.DataFrame(sensitivity)
    heat=alt.Chart(grid).mark_circle(size=650).encode(x=alt.X('Adoption (%):O',title='Assumed adoption (%)'),y=alt.Y('Revenue per account per month (£):O',title='Assumed revenue per active account per month (£)'),color=alt.Color('Contribution (£):Q',scale=alt.Scale(scheme='redblue',domainMid=0),legend=alt.Legend(title='Contribution (£)')),tooltip=list(grid.columns)).properties(height=HEIGHT)
    st.altair_chart(heat,use_container_width=True)
    st.caption('Sensitivity grid: each dot is a different adoption and revenue assumption, with other inputs held fixed. Colours show contribution after modelled costs. No statistical clusters or probability of success are implied.')

    st.header('4. Prioritise this against other initiatives')
    st.dataframe(pd.DataFrame([
        ['Incremental revenue','Compare genuinely new Wise revenue over the same period; subtract displaced revenue.'],
        ['Time to revenue','Include build, regulatory approval, partner integration and customer activation delays.'],
        ['Delivery capacity','Estimate engineering weeks, implementation capacity and support needs; identify dependencies and owners.'],
        ['Partner commitment','Distinguish signed launch commitments from general interest; check reusable demand across banks.'],
        ['Cost and payback','Include onboarding, verification, compliance, support, fraud losses, maintenance and any partner payments.'],
        ['Risk and confidence','Test safeguarding, licensing, fraud, reliability and availability of credible adoption evidence.'],
        ['Opportunity cost','Compare revenue per engineering month and delivery risk with Send Money improvements and other roadmap work.'],
    ],columns=['Decision factor','What to establish']),hide_index=True,width='stretch')
    st.write('Evaluate missing-currency support, business transfers and accounts using the same horizon and incremental-revenue definition. The workbook does not contain their delivery costs or engineering estimates, so it cannot establish a credible roadmap ranking by itself.')
    st.header('5. Make a staged investment decision')
    if payback and model['Cumulative contribution (£)'].iloc[-1]>0:
        message='The base assumptions produce positive contribution and payback within the forecast. This supports further validation, not an automatic launch decision.'
    else:
        message='Under the current assumptions, the investment does not pay back within the forecast. Test whether demand, economics, timing or scope can improve before funding a full build.'
    st.info(message)
    note(message, 'Fund discovery and a limited partner pilot first. Agree launch ownership, measurable adoption and incremental-revenue goals, reliability and risk guardrails, and a review date. Release wider funding only when the evidence supports scaling.')
    with st.expander('Monthly calculations and export'):
        st.dataframe(model,width='stretch',hide_index=True)
        st.download_button('Download investment forecast',model.to_csv(index=False).encode(),'wise_platform_investment_case.csv','text/csv')
        st.code('active_accounts = previous_active_accounts * (1 - monthly_attrition) + new_accounts\nincremental_revenue = active_accounts * (product_revenue - existing_revenue_replaced)\nnet_contribution = incremental_revenue - service_cost - shared_cost - activation_cost - upfront_cost',language='python')
