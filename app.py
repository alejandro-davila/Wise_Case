"""Question 1: run with python3 -m streamlit run app.py."""
from pathlib import Path
from display_names import currency_name, readable_table
import scale
import sqlite3
import json
import streamlit.components.v1 as components
import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="PartnerBank | Quarterly review", layout="wide")
CHART_HEIGHT = 400
DATA_FILE = Path(__file__).parent / 'Wise_Mock_Dataset_FY2026.xlsx'
MISSING = {'BDT','BWP','COP','CZK','GHS','globalEUR','globalUSD','globalGBP','JPY','KRW','LKR','PKR','RUB','THB','TZS','UGX','UYU','ZMW'}
METRIC_SQL = '''
SELECT
 COUNT(DISTINCT CASE WHEN channel='Integration' AND quoted=1 THEN user_id END) AS quotes,
 COUNT(DISTINCT CASE WHEN channel='Integration' AND transacted=1 THEN user_id END) AS active,
 COUNT(DISTINCT CASE WHEN channel='Integration' AND is_new=1 THEN user_id END) AS new_users,
 COUNT(DISTINCT CASE WHEN channel='Integration' AND is_new=1 AND transacted=1 THEN user_id END) AS new_active,
 COUNT(DISTINCT CASE WHEN channel='Wise direct' AND transacted=1 THEN user_id END) AS direct_users,
 COUNT(DISTINCT CASE WHEN channel='Wise direct' AND is_new=1 AND transacted=1 THEN user_id END) AS new_direct,
 COALESCE(SUM(CASE WHEN channel='Integration' AND transacted=1 THEN volume ELSE 0 END),0) AS app_volume,
 COALESCE(SUM(CASE WHEN channel='Wise direct' AND transacted=1 THEN volume ELSE 0 END),0) AS direct_volume,
 COALESCE(SUM(CASE WHEN channel='Wise direct' AND transacted=1 THEN revenue ELSE 0 END),0) AS direct_revenue
FROM activity WHERE date >= ? AND date < ?
'''

@st.cache_data
def load_data(path, modified):
    book = pd.ExcelFile(path)
    name = next((s for s in book.sheet_names if s.lower().startswith('transactions')), None)
    if name is None:
        raise ValueError('No Transactions sheet found. Available sheets: ' + ', '.join(book.sheet_names))
    d = pd.read_excel(book, sheet_name=name)
    d['Date'] = pd.to_datetime(d['Date'])
    d['Product used']=d['Product used'].replace({'Multi-currency Account (MCA)':'Multi-currency Account'})
    for c in ['Transacted','Got a quote','New user this month']:
        d[c] = d[c].map(lambda v: str(v).lower() in ('true','1','yes'))
    return d


def metrics(d, start, end):
    # SQL COUNT(DISTINCT) avoids adding monthly customer counts together.
    renamed = d.rename(columns={'Date':'date','User ID':'user_id','Channel':'channel',
        'Got a quote':'quoted','Transacted':'transacted','New user this month':'is_new',
        'Transaction Volume (GBP)':'volume','Revenue Amount (GBP)':'revenue'})
    with sqlite3.connect(':memory:') as con:
        renamed[['date','user_id','channel','quoted','transacted','is_new','volume','revenue']].to_sql('activity',con,index=False)
        return pd.read_sql_query(METRIC_SQL,con,params=(str(start),str(end))).iloc[0]


def ratio(a,b):
    return a/b if b else 0


def change(v, old):
    return f'{(v/old-1)*100:+.1f}% vs previous quarter' if old else None


def label_period(t):
    return f'Quarter {((t.month-4)%12)//3+1} · Fiscal year {t.year + (t.month>=4)} · {t:%b %Y}–{t+pd.DateOffset(months=2):%b %Y}'


def opportunity_flags(d):
    # Independent flags show overlap. Primary reason below counts each transfer once.
    return pd.DataFrame({
        'Business customer': d['User type'].eq('Business'),
        'Sent from a currency other than British pounds': d['Source Currency'].ne('GBP'),
        'Same-currency transfer': d['Source Currency'].eq(d['Target Currency']),
        'Unsupported target route': d['Target Currency'].isin(MISSING),
        'Over £50,000': d['Transaction Volume (GBP)'].gt(50000),
        'Other product need': d['Product used'].ne('Send Money'),
    }, index=d.index)


def dot_chart(data, category, amount, color):
    """Rank categories with circles and currency labels, without bars."""
    chart_data = pd.DataFrame({
        'Category': data[category].astype(str),
        'Amount': pd.to_numeric(data[amount]),
    })
    chart_data['Amount label'] = chart_data['Amount'].map(lambda v: f'£{v:,.0f}')
    base = alt.Chart(chart_data).encode(
        x=alt.X('Amount:Q', title='Money sent (£)', axis=alt.Axis(format='~s'),
                scale=alt.Scale(domain=[0, max(float(chart_data.Amount.max()) * 1.28, 1)])),
        y=alt.Y('Category:N', sort='-x', title=None, axis=alt.Axis(labelLimit=240)),
        tooltip=[alt.Tooltip('Category:N'), alt.Tooltip('Amount label:N', title='Money sent')],
    )
    points = base.mark_circle(size=160, color=color)
    labels = base.mark_text(align='left', dx=12, fontSize=11).encode(text='Amount label:N')
    st.altair_chart((points + labels).properties(height=CHART_HEIGHT).configure_view(strokeWidth=0), use_container_width=True)



def show_money_flow(direct, in_app=None):
    """PartnerBank app and Wise directly side by side: source → reason → destination currency."""
    if direct.empty and (in_app is None or in_app.empty):
        st.info('No completed activity in this period.')
        return
    in_app = in_app if in_app is not None else direct.iloc[0:0]
    palette = ['#f2c94c','#bb6bd9','#4f8ff7','#e8607f','#7bd88f','#ff9f7a','#a8b0c3']
    dest_colors = ['#4f8ff7','#e8607f','#f2c94c','#bb6bd9','#56c2c9','#ff9f7a','#7bd88f','#f78fb3','#9fa8ff','#c9a66b']
    amt='Transaction Volume (GBP)'
    reasons = direct.groupby('Primary opportunity')[amt].sum().sort_values(ascending=False)
    both = pd.concat([in_app.assign(Route='app'), direct.assign(Route='wise')])
    top = set(both.groupby('Target Currency')[amt].sum().nlargest(9).index)
    both['Destination'] = both['Target Currency'].where(both['Target Currency'].isin(top),'Other currencies')
    dest = both.groupby('Destination')[amt].sum().sort_values(ascending=False)
    split = both.groupby(['Destination','Route'])[amt].sum().unstack(fill_value=0)
    app_total = float(in_app[amt].sum()); wise_total = float(direct[amt].sum())
    nodes = [{'id':'all','name':'All money sent','color':'#e6e8f0','kind':'total'},
             {'id':'sApp','name':'PartnerBank app','color':'#9fe870','kind':'source'},
             {'id':'sWise','name':'Wise directly','color':'#f2994a','kind':'source'},
             {'id':'rApp','name':'✓ Sent in the app','color':'#56c2c9','kind':'reason'}]
    short={'Sent from a currency other than British pounds':'Not sent from pounds','Unsupported target route':'Currency not in the app','Supported Send Money transfer':'App could have sent it','Other product need':'Other Wise product','Business customer':'Business customer','Over £50,000':'Over £50,000','Same-currency transfer':'Same currency'}
    limits={'Over £50,000':'App limit: up to £50,000 per transfer','Unsupported target route':'App limit: 35 of 53 currencies','Sent from a currency other than British pounds':'App limit: sends from pounds only',
            'Business customer':'App limit: personal customers only','Same-currency transfer':'App limit: currency must change'}
    nodes += [{'id':'r'+str(i),'name':short.get(name,name),'color':palette[i%len(palette)],'kind':'reason','limit':limits.get(name,'')} for i,name in enumerate(reasons.index)]
    nodes += [{'id':'t'+str(i),'name':currency_name(name),'color':dest_colors[i%len(dest_colors)] if name!='Other currencies' else '#a8b0c3','kind':'dest',
               'app':float(split.loc[name].get('app',0)),'wise':float(split.loc[name].get('wise',0))} for i,name in enumerate(dest.index)]
    rmap={name:'r'+str(i) for i,name in enumerate(reasons.index)}
    tmap={name:'t'+str(i) for i,name in enumerate(dest.index)}
    links=[{'source':'all','target':'sWise','value':wise_total,'route':'wise'}]
    if app_total>0:
        links.insert(0,{'source':'all','target':'sApp','value':app_total,'route':'app'})
        links.append({'source':'sApp','target':'rApp','value':app_total,'route':'app'})
        flows_app=both[both.Route.eq('app')].groupby('Destination')[amt].sum()
        links += [{'source':'rApp','target':tmap[t],'value':float(v),'route':'app'} for t,v in flows_app.items() if v>0]
    links += [{'source':'sWise','target':rmap[name],'value':float(value),'route':'wise'} for name,value in reasons.items()]
    flows_w=both[both.Route.eq('wise')].groupby(['Primary opportunity','Destination'])[amt].sum()
    links += [{'source':rmap[r],'target':tmap[t],'value':float(v),'route':'wise'} for (r,t),v in flows_w.items() if v>0]
    assets=Path(__file__).parent/'assets'
    html=(assets/'flow.html').read_text()
    html=html.replace('__D3__',(assets/'d3.min.js').read_text()).replace('__SANKEY__',(assets/'d3-sankey.min.js').read_text())
    html=html.replace('__DATA__',json.dumps({'nodes':nodes,'links':links,'total':app_total+wise_total}).replace('</','<\\/'))
    blocked=float(reasons[[r for r in reasons.index if r in limits]].sum())
    st.markdown(f'🚫 **£{blocked:,.0f} ({blocked/(app_total+wise_total):.0%} of all money sent) went to Wise directly because of a limit in today’s app.** Remove those limits and the bank can win it back.')
    components.html(html,height=760,scrolling=False)


METRIC_NOTES = {
    'Total Integration Users': (
        'These people are interested enough to look at a transfer. More people here means more chances for PartnerBank to serve them.',
        'Make the transfer feature easy to find. Compare how many people look with how many go on to send.'),
    'Total Active Users': (
        'These customers actually used the bank’s transfer service. Repeat use can make the bank’s app part of their routine.',
        'Make repeat transfers easy with saved recipients and clear arrival times. Track whether people return.'),
    'New Users Created': (
        'New sign-ups show fresh interest in the service. Signing up alone does not mean the person has sent money.',
        'Explain the next steps clearly and help new customers reach their first transfer.'),
    'Total New Active Users': (
        'These new customers moved from signing up to using the service. Compare this number with new sign-ups to find the first-transfer gap.',
        'Find where new customers get stuck, simplify those steps and measure whether more of them send.'),
    'Total Wise Users from the Partner': (
        'These are already PartnerBank customers, but they use Wise’s app or website for this activity. Their behaviour reveals demand the bank could investigate.',
        'Check what they need and whether the bank’s integration could serve it. Test ways to bring eligible activity into the bank’s app.'),
    'New Wise Users from the Partner': (
        'These customers started using Wise directly during this period. That can be an early sign that customers are finding another way to meet their needs.',
        'Compare new Wise-direct customers over time and learn why they chose that route before expanding the integration.'),
    'Transaction Volume · PartnerBank app': (
        'This is the amount of money customers already trust the bank’s transfer feature to handle. It measures money moved, not bank revenue.',
        'Look at both customer numbers and transfer size to understand growth. Protect reliability as activity increases.'),
    'Transaction Volume · Wise directly': (
        'This money was sent by the bank’s customers through Wise directly. It is evidence of demand, but it will not all move into the bank’s app automatically.',
        'Identify eligible activity, estimate a realistic share that could move, and test adoption before investing widely.'),
    'Revenue Amount · direct-via-Wise only': (
        'This is revenue Wise recorded on direct activity. It is not money PartnerBank earned, and it is not all new revenue Wise would gain from moving the activity.',
        'Use it to understand commercial value. Use the actual partner agreement and adoption assumptions to estimate PartnerBank’s own return.'),
}


def story_note(meaning, action):
    # Fixed colours keep the business interpretation easy to find in either theme.
    import html
    st.markdown(
        '<div class="pb-notes"><div class="pb-n" style="background:#142b42;color:#dceeff;padding:12px 15px;border-radius:10px;margin:8px 0;font-size:14px;line-height:1.55">'
        '<strong style="color:#8bd0ff">What this means</strong><br>' + html.escape(meaning) + '</div>'
        '<div class="pb-n" style="background:#17352b;color:#dcf5e8;padding:12px 15px;border-radius:10px;margin:8px 0 18px;font-size:14px;line-height:1.55">'
        '<strong style="color:#96e5b6">What PartnerBank can do</strong><br>' + html.escape(action) + '</div></div>',
        unsafe_allow_html=True,
    )


PHONE_CSS = """<style>
.pb-phone{width:196px;max-width:100%;box-sizing:border-box;margin:4px auto 0;background:#0e0f14;border-radius:30px;padding:9px;box-shadow:0 12px 28px rgba(0,0,0,.28),inset 0 0 0 2px #2c2d36;font-family:inherit}
.pb-screen{background:#f7f8f3;border-radius:23px;height:360px;overflow:hidden;position:relative;color:#163300}
.pb-notch{width:70px;height:18px;background:#0e0f14;border-radius:0 0 12px 12px;margin:0 auto}
.pb-bar{display:flex;justify-content:space-between;font-size:10px;padding:2px 14px 6px;color:#555}
.pb-title{white-space:nowrap;font-weight:800;font-size:14px;padding:0 14px 8px}
.pb-box{margin:0 12px 8px;background:#fff;border-radius:12px;padding:8px 10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.pb-lbl{font-size:9.5px;color:#6b7262}.pb-amt{white-space:nowrap;font-size:15px;font-weight:800;display:flex;justify-content:space-between;align-items:center}
.pb-row{display:flex;justify-content:space-between;font-size:10.5px;padding:3px 14px;color:#333}
.pb-row b{color:#163300}
.pb-fee{background:#e9f8dc;border-radius:8px;margin:2px 12px;padding:4px 6px;animation:pbGlow 2.4s ease-in-out infinite}
.pb-btn{position:absolute;left:12px;right:12px;bottom:16px;background:#9fe870;color:#163300;text-align:center;font-weight:800;font-size:13px;padding:10px;border-radius:999px;animation:pbPulse 1.8s ease-in-out infinite}
.pb-btn.ghost{background:#fff;border:1.5px solid #9fe870;bottom:62px;animation:none}
.pb-tap{position:absolute;right:38px;bottom:22px;font-size:22px;animation:pbTap 1.8s ease-in-out infinite}
.pb-check{width:78px;height:78px;border-radius:50%;background:#9fe870;margin:26px auto 10px;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:900;color:#163300;animation:pbPop 2.6s ease-out infinite}
.pb-big{text-align:center;font-size:18px;font-weight:900}.pb-sub{text-align:center;font-size:11px;color:#555;margin:3px 8px;white-space:nowrap}
.pb-chip{display:inline-block;background:#163300;color:#9fe870;font-size:9.5px;font-weight:700;border-radius:999px;padding:3px 8px;margin:6px 3px 0}
.pb-conf{position:absolute;top:30px;font-size:14px;animation:pbFall 2.6s linear infinite}
.pb-tag{text-align:center;font-size:12px;font-weight:700;margin-top:8px;opacity:.8}
@keyframes pbPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.04);box-shadow:0 0 0 6px rgba(159,232,112,.35)}}
@keyframes pbGlow{0%,100%{background:#e9f8dc}50%{background:#cdf0b0}}
@keyframes pbTap{0%,60%,100%{transform:translate(0,0)}30%{transform:translate(-4px,-4px) scale(.9)}}
@keyframes pbPop{0%{transform:scale(.3);opacity:0}15%{transform:scale(1.12);opacity:1}25%,100%{transform:scale(1)}}
.sx-wrap{width:100%;max-width:360px;margin:6px auto 0}.sx-stage{position:relative;width:100%;max-width:420px;height:300px;margin:0 auto}
.pb-phone.sm{width:160px}.pb-phone.sm .pb-screen{height:282px}
.pb-phone.sm .pb-box b,.pb-phone.sm .pb-amt{font-size:14px}.pb-phone.sm .pb-title{font-size:13px}
.pb-phone.sm .pb-title{padding-bottom:5px}.pb-phone.sm .pb-box{margin:0 10px 6px;padding:5px 9px}.pb-phone.sm .pb-row{padding:3px 12px;white-space:nowrap;font-size:10.5px}.pb-phone.sm .pb-fee{margin:2px 10px}.pb-phone.sm .pb-btn{bottom:12px;padding:8px}.pb-phone.sm .pb-tap{bottom:16px}
.sx-ph{position:absolute;top:0;width:160px;height:300px;background:#0e0f14;border-radius:24px;padding:9px;box-sizing:border-box;box-shadow:0 12px 28px rgba(0,0,0,.28),inset 0 0 0 2px #2c2d36}
.sx-sc{background:#f7f8f3;border-radius:17px;height:100%;color:#163300;text-align:center;overflow:hidden;position:relative}
.sx-nt{width:60px;height:16px;background:#0e0f14;border-radius:0 0 11px 11px;margin:0 auto 8px}
.sx-app{font-size:10px;color:#666}.sx-h{font-size:13px;font-weight:800;margin:6px 0 2px}
.sx-amt{font-size:22px;font-weight:900;margin:8px 0}.sx-s{font-size:11px;color:#555}
.sx-av{width:46px;height:46px;border-radius:50%;margin:12px auto 4px;display:flex;align-items:center;justify-content:center;font-size:24px}
.sx-go{position:absolute;left:12px;right:12px;bottom:16px;background:#9fe870;border-radius:999px;font-size:13px;font-weight:900;padding:10px 0;animation:sxPress 3.2s infinite}
.sx-ok{position:absolute;left:0;right:0;bottom:20px;font-size:12px;font-weight:800;color:#163300;opacity:0;animation:sxOk 3.2s infinite}
.sx-in{animation:sxIn 3.2s infinite}
.sx-arc{position:absolute;left:150px;right:150px;top:150px;border-top:3px dashed #9fe870;opacity:.9}
.sx-m{position:absolute;z-index:3;left:140px;top:132px;font-size:24px;opacity:0;animation:sxFly 3.2s infinite ease-in-out}
.sx-m.b{animation-delay:.25s}.sx-m.c{animation-delay:.5s}
.sx-globe{position:absolute;left:50%;top:176px;transform:translateX(-50%);font-size:30px;animation:sxSpin 6s linear infinite}
.sx-badge{position:absolute;left:50%;top:96px;transform:translateX(-50%);background:#163300;color:#9fe870;font-size:10.5px;font-weight:800;border-radius:999px;padding:4px 9px;white-space:nowrap;z-index:2}
@keyframes sxPress{0%,8%,100%{transform:scale(1)}4%{transform:scale(.9)}}
@keyframes sxFly{0%{opacity:0;transform:translate(0,0) scale(.6)}10%{opacity:1}35%{transform:translate(55px,-38px) scale(1.15)}60%{opacity:1;transform:translate(110px,0) scale(.8)}68%,100%{opacity:0;transform:translate(118px,6px) scale(.4)}}
@keyframes sxOk{0%,60%{opacity:0;transform:scale(.6)}68%,92%{opacity:1;transform:scale(1)}100%{opacity:0}}
@keyframes sxIn{0%,58%,100%{transform:scale(1)}64%{transform:scale(1.12);color:#2f7d00}}
@keyframes sxSpin{0%{transform:translateX(-50%) rotate(0)}100%{transform:translateX(-50%) rotate(360deg)}}
.jr-stage{position:relative;width:100%;max-width:380px;height:240px;margin:8px auto 0}
.jr-jar{position:absolute;right:18px;top:40px;width:118px;height:170px;border:3px solid #b9c2b0;border-top:none;border-radius:6px 6px 26px 26px;overflow:hidden;background:rgba(255,255,255,.55)}
.jr-lid{position:absolute;right:10px;top:30px;width:134px;height:12px;border-radius:6px;background:#b9c2b0}
.jr-liq{position:absolute;left:0;right:0;bottom:0;height:var(--fill);animation:jrFill 3.5s ease-out both}
.jr-liq.g{background:linear-gradient(#b9f08f,#7fd34e)}.jr-liq.o{background:linear-gradient(#ffc98a,#f2994a)}
.jr-liq:before{content:"";position:absolute;left:-50%;top:-8px;width:200%;height:16px;border-radius:45%;background:inherit;animation:jrWave 2.4s linear infinite}
.jr-amt{position:absolute;left:0;right:0;bottom:12px;text-align:center;font-weight:900;font-size:19px;color:#163300;z-index:2}
.jr-cap{position:absolute;left:0;right:0;bottom:-24px;text-align:center;font-size:11px;font-weight:800;opacity:.8}
.jr-coin{position:absolute;font-size:20px;opacity:0;z-index:3;animation:jrDrop 2.4s ease-in infinite}
.jr-coin.d2{animation-delay:.8s}.jr-coin.d3{animation-delay:1.6s}
.jr-mini{position:absolute;left:14px;top:34px;width:96px;height:176px;background:#0e0f14;border-radius:18px;padding:5px;box-sizing:border-box}
.jr-mini .sc{background:#f7f8f3;border-radius:13px;height:100%;text-align:center;color:#163300;position:relative}
.jr-mini .nt{width:34px;height:8px;background:#0e0f14;border-radius:0 0 6px 6px;margin:0 auto 8px}
.jr-mini .t{font-size:8px;color:#666}.jr-mini .a{font-size:15px;font-weight:900;margin:10px 0 2px}
.jr-mini .b{position:absolute;left:8px;right:8px;bottom:12px;background:#9fe870;border-radius:999px;font-size:10px;font-weight:900;padding:6px 0;animation:sxPress 2.4s infinite}
.jr-bank{position:absolute;left:6px;top:58px;width:84px;text-align:center;font-size:34px}
.jr-bank div{font-size:9.5px;font-weight:800;line-height:1.2;margin-top:2px}
.jr-lap{position:absolute;left:104px;top:62px;width:104px}
.jr-lap .scr{height:66px;background:#1d1d28;border-radius:8px 8px 0 0;border:4px solid #0e0f14;color:#fff;font-size:9px;text-align:center;padding-top:10px;box-sizing:border-box}
.jr-lap .scr b{display:block;font-size:12px;color:#ffc98a;margin-top:3px}
.jr-lap .base{height:8px;background:#0e0f14;border-radius:0 0 10px 10px;margin:0 -8px}
.jr-dash{position:absolute;left:78px;top:94px;width:30px;border-top:2px dashed #f2994a;animation:jrDash 1s linear infinite}
.jr-share{position:absolute;right:30px;top:4px;background:#f2994a;color:#3a1d00;font-size:10.5px;font-weight:900;border-radius:999px;padding:3px 9px;animation:pbPulse 2s infinite}
.jr-share.g{background:#9fe870;color:#163300}
@keyframes jrFill{from{height:0}to{height:var(--fill)}}
@keyframes jrWave{from{transform:translateX(0)}to{transform:translateX(25%)}}
@keyframes jrDrop{0%{opacity:0;transform:translate(0,0) scale(.7)}12%{opacity:1}55%{transform:translate(var(--dx),-30px) scale(1)}90%{opacity:1}100%{opacity:0;transform:translate(var(--dx2),70px) scale(.8)}}
@keyframes jrDash{from{opacity:.4}50%{opacity:1}to{opacity:.4}}
.su-f{margin:0 12px 7px;background:#fff;border-radius:10px;padding:6px 9px;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:9.5px;color:#6b7262}
.su-f b{display:block;font-size:12px;color:#163300;margin-top:1px;white-space:nowrap;overflow:hidden}
.su-type{display:inline-block;overflow:hidden;white-space:nowrap;border-right:2px solid #163300;width:0;animation:suType 4s steps(12) infinite,suCaret .7s step-end infinite}
.su-plus{position:absolute;right:16px;bottom:70px;font-size:12px;font-weight:900;color:#2f7d00;background:#e9f8dc;border-radius:999px;padding:2px 8px;opacity:0;animation:suRise 4s ease-out infinite}
.su-plus.p2{right:auto;left:16px;animation-delay:1.3s}.su-plus.p3{right:70px;animation-delay:2.6s}
.ft-step{display:flex;align-items:center;gap:8px;margin:0 12px 8px;background:#fff;border-radius:10px;padding:8px 9px;font-size:11px;font-weight:700;box-shadow:0 1px 3px rgba(0,0,0,.08);opacity:.35;animation:ftOn 5s infinite}
.ft-step i{font-style:normal;width:20px;height:20px;border-radius:50%;background:#e4e8df;display:flex;align-items:center;justify-content:center;font-size:11px;animation:ftDot 5s infinite}
.ft-step.s2,.ft-step.s2 i{animation-delay:.9s}.ft-step.s3,.ft-step.s3 i{animation-delay:1.8s}
.ft-done{margin:12px 12px 0;text-align:center;background:#163300;color:#9fe870;border-radius:12px;padding:9px 4px;font-weight:900;font-size:13px;opacity:0;animation:ftDone 5s infinite}
.ft-bar{margin:4px 12px 12px;height:7px;border-radius:9px;background:#e4e8df;overflow:hidden}.ft-bar div{height:100%;background:#9fe870;animation:ftBar 5s infinite}
@property --rgA{syntax:'<number>';inherits:false;initial-value:0}
@property --rgI{syntax:'<integer>';inherits:false;initial-value:0}
@property --rgD{syntax:'<integer>';inherits:false;initial-value:0}
.rg-wrap{display:flex;flex-direction:column;align-items:center}
.rg{width:230px;height:230px;border-radius:50%;background:conic-gradient(#70d69b calc(var(--rgA)*1%),#f2a65a 0);-webkit-mask:radial-gradient(closest-side,transparent 66%,#000 67%);mask:radial-gradient(closest-side,transparent 66%,#000 67%);animation:rgFill 2.2s cubic-bezier(.2,.7,.2,1) forwards}
.rg-box{position:relative;width:230px;height:230px;margin:10px 0}
.rg-num{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:38px;font-weight:800;color:#4f9a1f;counter-reset:i var(--rgI) d var(--rgD);animation:rgCount 2.2s cubic-bezier(.2,.7,.2,1) forwards}
.rg-num:before{content:counter(i) "." counter(d) "%"}
.rg-num span{font-size:12px;font-weight:700;opacity:.6;color:inherit}
.rg-leg{display:flex;gap:16px;font-size:13px;margin-top:4px}.rg-leg i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
@keyframes rgFill{to{--rgA:var(--ra)}}
@keyframes rgCount{to{--rgI:var(--ri);--rgD:var(--rd)}}
@keyframes suType{0%,8%{width:0}45%,100%{width:9.5ch}}
@keyframes suCaret{50%{border-color:transparent}}
@keyframes suRise{0%{opacity:0;transform:translateY(10px)}15%{opacity:1}60%{opacity:1;transform:translateY(-60px)}75%,100%{opacity:0;transform:translateY(-80px)}}
@keyframes ftOn{0%,8%{opacity:.35}14%,92%{opacity:1}100%{opacity:.35}}
@keyframes ftDot{0%,8%{background:#e4e8df;transform:scale(1)}12%{transform:scale(1.3)}14%,92%{background:#9fe870}100%{background:#e4e8df}}
@keyframes ftDone{0%,52%{opacity:0;transform:scale(.7)}60%,92%{opacity:1;transform:scale(1)}100%{opacity:0}}
@keyframes ftBar{0%{width:0}50%,92%{width:100%}100%{width:0}}
.lv-pic{height:190px;display:flex;align-items:center;justify-content:center;margin:4px 0 6px}
.lv-list{width:210px;background:#f7f8f3;border-radius:16px;padding:10px;box-shadow:0 6px 16px rgba(0,0,0,.15);color:#163300}
.lv-h{font-size:10px;font-weight:800;opacity:.6;margin:0 2px 6px;text-transform:uppercase;letter-spacing:.06em}
.lv-row{display:flex;justify-content:space-between;align-items:center;background:#fff;border-radius:9px;padding:5px 8px;margin-bottom:5px;font-size:12px;font-weight:700;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.lv-new{font-size:9px;font-weight:900;background:#9fe870;color:#163300;border-radius:999px;padding:2px 7px;animation:lvNew 4s infinite}
.lv-lock{font-size:12px;animation:lvLock 4s infinite}
.lv-row.r2 .lv-new{animation-delay:.4s}.lv-row.r3 .lv-new{animation-delay:.8s}
.lv-row.pick{animation:lvPick 6s infinite}.lv-row.pick.k2{animation-delay:1.5s}.lv-row.pick.k3{animation-delay:3s}.lv-row.pick.k4{animation-delay:4.5s}
.lv-ppl{display:grid;grid-template-columns:repeat(5,34px);gap:8px}
.lv-p{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:17px;background:#70d69b}
.lv-p.o{background:#f2a65a}.lv-p.flip{animation:lvFlip 3s infinite}
.lv-plus{position:absolute;font-size:11px;font-weight:900;color:#2f7d00;background:#e9f8dc;border-radius:999px;padding:2px 7px;animation:lvPlus 3s infinite}
.lv-today{display:inline-block;font-size:11.5px;font-weight:800;background:#fde8d4;color:#7a3e00;border-radius:999px;padding:3px 10px;margin-bottom:6px}
.lv-desc{min-height:6.1em}
[data-testid="stVerticalBlock"]:has(.lv-pic)>[data-testid="stElementContainer"]:has([data-testid="stMetric"]){margin-top:auto}
.lv-chips{display:flex;flex-wrap:wrap;gap:5px;justify-content:center;max-width:270px}
.lv-chip{font-size:11px;font-weight:800;border-radius:999px;padding:3px 8px;background:#f7f8f3;color:#163300;border:1px solid #dfe5d7}
.lv-chip.top{background:#9fe870;border-color:#9fe870;animation:pbPulse 2s infinite}
.lv-kpis{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 4px}
.lv-kpi{border:1px solid rgba(140,150,170,.45);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:600}
@keyframes lvNew{0%,10%{transform:scale(0);opacity:0}20%{transform:scale(1.25);opacity:1}28%,90%{transform:scale(1)}100%{opacity:0}}
@keyframes lvLock{0%,15%{content:"";opacity:1}20%,90%{opacity:0}100%{opacity:1}}
@keyframes lvPick{0%,22%{background:#e9f8dc;box-shadow:0 0 0 2px #9fe870}27%,100%{background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.06)}}
@keyframes lvFlip{0%,35%{background:#f2a65a;transform:scale(1)}45%{transform:scale(1.25)}55%,90%{background:#70d69b;transform:scale(1)}100%{background:#f2a65a}}
@keyframes lvPlus{0%,40%{opacity:0;transform:translateY(8px)}55%{opacity:1;transform:translateY(-6px)}85%{opacity:1}100%{opacity:0;transform:translateY(-16px)}}
.fl-wrap{width:100%;max-width:560px;margin:0 auto}
.fl-share{text-align:center;margin-bottom:8px}
.fl-share span{display:inline-block;background:#9fe870;color:#163300;font-size:11px;font-weight:900;border-radius:999px;padding:3px 10px}
.fl-row{display:flex;align-items:center;justify-content:space-between;gap:4px}
.fl-step{display:flex;flex-direction:column;align-items:center;gap:6px}
.fl-lbl{font-size:10.5px;font-weight:800;white-space:nowrap;opacity:.45;animation:flLbl 6s infinite}
.fl-lbl b{display:inline-flex;width:16px;height:16px;border-radius:50%;background:#9fe870;color:#163300;align-items:center;justify-content:center;font-size:9.5px;margin-right:4px}
.fl-lbl.l2{animation-name:flLbl2}.fl-lbl.l3{animation-name:flLbl3}
.fl-phone{width:92px;height:168px;background:#0e0f14;border-radius:17px;padding:5px;box-sizing:border-box;box-shadow:0 8px 18px rgba(0,0,0,.22)}
.fl-phone .sc{background:#f7f8f3;border-radius:12px;height:100%;text-align:center;color:#163300;position:relative}
.fl-phone .nt{width:32px;height:8px;background:#0e0f14;border-radius:0 0 6px 6px;margin:0 auto 8px}
.fl-phone .t{font-size:8px;color:#666}.fl-phone .a{font-size:15px;font-weight:900;margin:8px 0 2px}
.fl-phone .b{position:absolute;left:8px;right:8px;bottom:11px;background:#9fe870;border-radius:999px;font-size:10px;font-weight:900;padding:6px 0;animation:flPress 6s infinite}
.fl-api{width:150px;height:168px;background:#15161d;border-radius:12px;box-shadow:0 8px 18px rgba(0,0,0,.25);font-family:ui-monospace,Menlo,monospace;font-size:9.5px;color:#cfd3dc;overflow:hidden}
.fl-api .hd{background:#23252f;padding:6px 8px;font-weight:800;color:#9fe870;font-family:inherit;display:flex;gap:4px;align-items:center}
.fl-api .hd i{width:6px;height:6px;border-radius:50%;background:#f2994a;display:inline-block}
.fl-api .ln{padding:4px 8px;opacity:0;animation:flLine 6s infinite;white-space:nowrap}
.fl-api .ln b{color:#56c2c9}.fl-api .ok{color:#9fe870;font-weight:800}
.fl-api .ln.n2{animation-delay:.35s}.fl-api .ln.n3{animation-delay:.7s}.fl-api .ln.n4{animation-delay:1.05s}
.fl-pay{width:110px;height:168px;background:#f7f8f3;border-radius:14px;box-shadow:0 8px 18px rgba(0,0,0,.18);color:#163300;text-align:center;padding-top:14px;box-sizing:border-box;position:relative}
.fl-pay .ic{font-size:30px}.fl-pay .nm{font-size:10px;font-weight:800;margin-top:2px}
.fl-pay .amt{font-size:16px;font-weight:900;margin:10px 0 4px;animation:flAmt 6s infinite}
.fl-pay .ck{width:36px;height:36px;border-radius:50%;background:#9fe870;margin:6px auto 0;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:18px;opacity:0;animation:flCk 6s infinite}
.fl-arrow{position:relative;flex:1;min-width:26px;height:2px;border-top:2px dashed rgba(140,150,170,.6);margin-bottom:22px}
.fl-arrow:after{content:"";position:absolute;right:-2px;top:-6px;border:5px solid transparent;border-left:7px solid rgba(140,150,170,.8)}
.fl-dot{position:absolute;top:-7px;left:0;width:12px;height:12px;border-radius:50%;background:#9fe870;box-shadow:0 0 0 3px rgba(159,232,112,.35);opacity:0;animation:flDot1 6s infinite}
.fl-dot.d2{animation-name:flDot2}
@keyframes flPress{0%,6%,100%{transform:scale(1)}3%{transform:scale(.88);background:#7fd34e}}
@keyframes flDot1{0%,8%{left:0;opacity:0}10%{opacity:1}26%{left:calc(100% - 12px);opacity:1}28%,100%{opacity:0}}
@keyframes flDot2{0%,55%{left:0;opacity:0}57%{opacity:1}70%{left:calc(100% - 12px);opacity:1}72%,100%{opacity:0}}
@keyframes flLine{0%,28%{opacity:0;transform:translateX(-6px)}33%,94%{opacity:1;transform:none}100%{opacity:0}}
@keyframes flCk{0%,72%{opacity:0;transform:scale(.4)}78%{opacity:1;transform:scale(1.2)}82%,96%{opacity:1;transform:scale(1)}100%{opacity:0}}
@keyframes flAmt{0%,72%{opacity:.3}78%,96%{opacity:1;color:#2f7d00}100%{opacity:.3}}
@keyframes flLbl{0%,28%{opacity:1}32%,100%{opacity:.45}}
@keyframes flLbl2{0%,28%{opacity:.45}32%,68%{opacity:1}72%,100%{opacity:.45}}
@keyframes flLbl3{0%,70%{opacity:.45}74%,98%{opacity:1}100%{opacity:.45}}
.fl-share.o span{background:#f2994a;color:#3a1d00}
.fl-arrow.o .fl-dot{background:#f2994a;box-shadow:0 0 0 3px rgba(242,153,74,.35)}
.fl-lbl.o b{background:#f2994a;color:#3a1d00}
.fl-phone .b.o{background:#f2994a;color:#3a1d00}
.fl-form{width:150px;height:168px;background:#f7f8f3;border-radius:12px;box-shadow:0 8px 18px rgba(0,0,0,.2);color:#163300;padding:8px;box-sizing:border-box}
.fl-form .hd{font-size:10px;font-weight:900;margin-bottom:6px}
.fl-form .fd{background:#fff;border-radius:8px;padding:4px 7px;margin-bottom:5px;font-size:8.5px;color:#6b7262;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.fl-form .fd b{display:block;font-size:11px;color:#163300;white-space:nowrap;overflow:hidden}
.fl-type{display:inline-block;overflow:hidden;white-space:nowrap;vertical-align:bottom;width:0;border-right:2px solid #f2994a;animation:flType 6s steps(10) infinite}
.fl-type.t2{animation-name:flType2}.fl-type.t3{animation-name:flType3}
@keyframes flType{0%,30%{width:0}40%,96%{width:11.5ch;border-color:transparent}100%{width:0}}
@keyframes flType2{0%,40%{width:0}50%,96%{width:8ch;border-color:transparent}100%{width:0}}
@keyframes flType3{0%,50%{width:0}60%,96%{width:9ch;border-color:transparent}100%{width:0}}
@keyframes pbFall{0%{transform:translateY(-10px) rotate(0);opacity:0}10%{opacity:1}100%{transform:translateY(170px) rotate(320deg);opacity:0}}
</style>"""

PHONES = {
'New Users Created': """<div class="pb-phone"><div class="pb-screen"><div class="pb-notch"></div>
<div class="pb-bar"><span>9:41</span><span>PartnerBank</span></div>
<div class="pb-title">Start sending abroad</div>
<div class="su-f">Name<b><span class="su-type">Alex Morgan</span></b></div>
<div class="su-f">Lives in<b>🇬🇧 United Kingdom</b></div>
<div class="su-f">Sending to<b>🇮🇳 India · 🇵🇱 Poland</b></div>
<div class="su-f">Pay from<b>💳 PartnerBank current account</b></div>
<span class="su-plus">+1 👤</span><span class="su-plus p2">+1 👤</span><span class="su-plus p3">+1 👤</span>
<div class="pb-btn">Create my account</div><div class="pb-tap">👆</div>
</div></div><div class="pb-tag">📝 Signed up</div>""",
'Total New Active Users': """<div class="pb-phone"><div class="pb-screen"><div class="pb-notch"></div>
<div class="pb-bar"><span>9:44</span><span>PartnerBank</span></div>
<div class="pb-title">Your first transfer</div>
<div class="ft-bar"><div></div></div>
<div class="ft-step"><i>✓</i>Signed up</div>
<div class="ft-step s2"><i>✓</i>Added Sam as a recipient</div>
<div class="ft-step s3"><i>✓</i>Sent £200 → 🇮🇳 INR</div>
<div class="ft-done">🎉 First transfer done!</div>
<div class="pb-btn">Send again</div>
</div></div><div class="pb-tag">🚀 Activated</div>""",
'Transaction Volume · PartnerBank app': """<div class="fl-wrap">
<div class="fl-share"><span>__APPAMT__ sent this way · __APPSHARE__ of the money</span></div>
<div class="fl-row">
<div class="fl-step"><div class="fl-phone"><div class="sc"><div class="nt"></div><div class="t">PartnerBank</div><div style="font-size:20px;margin-top:8px">🇬🇧➜🇮🇳</div><div class="a">£500</div><div class="t">Fee ???</div><div class="b">Send</div></div></div>
<div class="fl-lbl"><b>1</b>PartnerBank app</div></div>
<div class="fl-arrow"><div class="fl-dot"></div></div>
<div class="fl-step"><div class="fl-api"><div class="hd"><i></i><i style="background:#f2c94c"></i><i style="background:#9fe870"></i>&nbsp;Wise API</div>
<div class="ln"><b>POST</b> /quotes</div><div class="ln n2"><b>POST</b> /transfers</div><div class="ln n3"><b>POST</b> /payments</div><div class="ln n4 ok">← 200 OK ✓</div></div>
<div class="fl-lbl l2"><b>2</b>Wise API call</div></div>
<div class="fl-arrow"><div class="fl-dot d2"></div></div>
<div class="fl-step"><div class="fl-pay"><div class="ic">🏦</div><div class="nm">Sam’s bank · 🇮🇳</div><div class="amt">₹55,800</div><div class="ck">✓</div></div>
<div class="fl-lbl l3"><b>3</b>Payment made</div></div>
</div><div class="pb-tag" style="margin-top:10px">✅ Kept in the PartnerBank app</div></div>""",
'Transaction Volume · Wise directly': """<div class="fl-wrap">
<div class="fl-share o"><span>__DIRAMT__ sent this way · __DIRSHARE__ goes around the app</span></div>
<div class="fl-row">
<div class="fl-step"><div class="fl-phone"><div class="sc"><div class="nt"></div><div class="t">Wise app</div><div style="font-size:20px;margin-top:8px">🇬🇧➜🇮🇳</div><div class="a">£500</div><div class="t">to Sam</div><div class="b o">Continue</div></div></div>
<div class="fl-lbl o"><b>1</b>Uses the Wise app</div></div>
<div class="fl-arrow o"><div class="fl-dot"></div></div>
<div class="fl-step"><div class="fl-form"><div class="hd">🏦 Pay from your bank</div>
<div class="fd">Bank<b><span class="fl-type">PartnerBank</span></b></div>
<div class="fd">Sort code<b><span class="fl-type t2">••-••-12</span></b></div>
<div class="fd">Account number<b><span class="fl-type t3">••••5678</span></b></div></div>
<div class="fl-lbl o l2"><b>2</b>Enters bank details</div></div>
<div class="fl-arrow o"><div class="fl-dot d2"></div></div>
<div class="fl-step"><div class="fl-pay"><div class="ic">🏦</div><div class="nm">Sam’s bank · 🇮🇳</div><div class="amt">₹55,800</div><div class="ck" style="background:#f2994a;color:#3a1d00">✓</div></div>
<div class="fl-lbl o l3"><b>3</b>Transfer made</div></div>
</div><div class="pb-tag" style="margin-top:10px">🎯 The opportunity to capture</div></div>""",
'Total Integration Users': """<div class="pb-phone sm"><div class="pb-screen"><div class="pb-notch"></div>
<div class="pb-bar"><span>9:41</span><span>PartnerBank</span></div>
<div class="pb-title">Send money abroad</div>
<div class="pb-box"><div class="pb-lbl">You send</div><div class="pb-amt">£500.00 <span>🇬🇧 GBP</span></div></div>
<div class="pb-box"><div class="pb-lbl">They get</div><div class="pb-amt">₹55,800 <span>🇮🇳 INR</span></div></div>
<div class="pb-row pb-fee"><span>Fee</span><b>???</b></div>
<div class="pb-row"><span>Arrives</span><b>⚡ in seconds</b></div>
<div class="pb-btn">Continue</div><div class="pb-tap">👆</div>
</div></div><div class="pb-tag">👀 Checked the fee</div>""",
'Total Active Users': """<div class="sx-wrap"><div class="sx-stage">
<div class="sx-badge">⚡ In seconds</div><div class="sx-arc"></div>
<div class="sx-m">💷</div><div class="sx-m b">💸</div><div class="sx-m c">💷</div>
<div class="sx-globe">🌍</div>
<div class="sx-ph" style="left:0"><div class="sx-sc"><div class="sx-nt"></div><div class="sx-app">PartnerBank</div>
<div class="sx-h">Sending to Sam</div><div class="sx-av" style="background:#e9f8dc">🇬🇧</div>
<div class="sx-amt">£500</div><div class="sx-s">Fee ???</div><div class="sx-go">Send</div></div></div>
<div class="sx-ph" style="right:0"><div class="sx-sc"><div class="sx-nt"></div><div class="sx-app">Sam’s bank</div>
<div class="sx-h">Money received</div><div class="sx-av" style="background:#ffe9cc">🇮🇳</div>
<div class="sx-amt sx-in">₹55,800</div><div class="sx-s">from PartnerBank</div><div class="sx-ok">✅ Arrived in 8s</div></div></div>
</div><div class="pb-tag">💸 Sent money with the app</div></div>""",
}


WIDE_PICTURES = {'New Users Created','Total New Active Users','Total Integration Users','Total Active Users','Transaction Volume · PartnerBank app','Transaction Volume · Wise directly'}
PICTURE_VARS = {}


def phone_mock(official_name):
    picture = PHONES[official_name]
    for key, val in PICTURE_VARS.items():
        picture = picture.replace('__'+key+'__', str(val))
    height = 290 if official_name.startswith('Transaction Volume') else 420
    st.markdown(PHONE_CSS + f'<div style="height:{height}px;display:flex;flex-direction:column;justify-content:center">' + picture + '</div>', unsafe_allow_html=True)


def card_description(text):
    import html
    st.markdown('<div class="pb-desc">'+html.escape(text)+'</div>', unsafe_allow_html=True)


SYMMETRY_CSS = """<style>
[data-testid="stHorizontalBlock"]{align-items:stretch}
.wise-only-tag{display:inline-block;background:#f2c94c;color:#3a2a00;font-size:12px;font-weight:900;border-radius:999px;padding:3px 11px;letter-spacing:.02em}
[data-testid="stVerticalBlock"]:has(>[data-testid="stElementContainer"] .wise-only-tag){border:2.5px solid #f2c94c !important;border-radius:14px;background:rgba(242,201,76,.07);padding:12px}
.wise-legend{display:inline-block;background:#f2c94c;color:#3a2a00;font-size:12px;font-weight:900;border-radius:999px;padding:3px 11px}
.wise-hl{border:2.5px solid #f2c94c;border-radius:12px;background:rgba(242,201,76,.10);padding:12px 8px 8px;position:relative;display:flex;flex-direction:column;align-items:center;width:100%;box-sizing:border-box}
.wise-hl:before{content:"🔒 Wise team only";position:absolute;top:-11px;left:50%;transform:translateX(-50%);background:#f2c94c;color:#3a2a00;font-size:10px;font-weight:900;border-radius:999px;padding:1px 8px;white-space:nowrap}
.wise-inline{background:rgba(242,201,76,.25);border:1.5px solid #f2c94c;border-radius:6px;padding:0 4px}
[data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3,[data-testid="stMain"] [data-testid="stHeading"]{text-align:center}
[data-testid="stHeading"] [data-testid="stHeaderActionElements"]{display:none}
.pb-chapter{text-align:center}
[data-testid="stColumn"]>[data-testid="stVerticalBlock"]{height:100%}
[data-testid="stColumn"]>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]{flex:1 1 auto;display:flex;flex-direction:column}
[data-testid="stColumn"]>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]>[data-testid="stVerticalBlock"]{flex:1 1 auto}
[data-testid="stElementContainer"]:has(.pb-notes){margin-top:auto}
.pb-desc{font-size:14px;line-height:1.5;opacity:.9;min-height:3em;text-align:center}
[data-testid="stColumn"] [data-testid="stMetric"]{text-align:center}
[data-testid="stColumn"] [data-testid="stMetricLabel"],[data-testid="stColumn"] [data-testid="stMetricValue"],[data-testid="stColumn"] [data-testid="stMetricDelta"]{display:flex;justify-content:center}
[data-testid="stColumn"] [data-testid="stCaptionContainer"]{text-align:center}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:inherit !important;opacity:.88}
[data-testid="stMetricLabel"],[data-testid="stMetricLabel"] p{color:inherit !important;opacity:1}
[data-testid="stWidgetLabel"] p{color:inherit !important}
.pb-notes .pb-n{min-height:76px;box-sizing:border-box}
</style>"""


def metric_card(column, official_name, plain_name, value, description, delta=None):
    with column:
        with st.container(border=True):
            if official_name in WIDE_PICTURES:
                st.caption(official_name)
                st.metric(plain_name, value, delta)
                card_description(description)
                phone_mock(official_name)
            elif official_name in PHONES:
                info, picture = st.columns([1,1])
                with info:
                    st.caption(official_name)
                    st.metric(plain_name, value, delta)
                    st.caption(description)
                with picture:
                    phone_mock(official_name)
            else:
                st.caption(official_name)
                st.metric(plain_name, value, delta)
                card_description(description)
            if official_name in METRIC_NOTES:
                story_note(*METRIC_NOTES[official_name])


def breakdown_table(records, field):
    result = records.groupby(field).agg(
        Customers=('User ID', 'nunique'),
        Activities=('Transfer ID', 'count'),
        Money_sent_GBP=('Transaction Volume (GBP)', 'sum'),
    ).sort_values('Money_sent_GBP', ascending=False).reset_index()
    result[['Customers','Activities']] = (result[['Customers','Activities']]*scale.S).round().astype(int)
    result = result.rename(columns={'Money_sent_GBP': 'Money sent (£)'})
    st.dataframe(readable_table(result), hide_index=True, width='stretch',
                 column_config={'Money sent (£)': st.column_config.NumberColumn(format='£%.0f')})


def quadrant_chart(records, fields):
    """Compare observed category groups; medians are descriptive, not significance tests."""
    groups=[]
    for field in fields:
        g=records.groupby(field).agg(Customers=('User ID','nunique'),Activities=('Transfer ID','count'),
            Volume=('Transaction Volume (GBP)','sum'),Revenue=('Revenue Amount (GBP)','sum')).reset_index()
        g=g.rename(columns={field:'Category'})
        g[['Customers','Activities']]=g[['Customers','Activities']]*scale.S
        g['Metric']=field
        groups.append(g)
    g=pd.concat(groups,ignore_index=True)
    if g.empty:
        st.info('No completed activity in this period.')
        return
    g['Category']=g['Category'].map(currency_name)
    g['Average value']=g.Volume/g.Activities
    g['Group']=g.Metric+': '+g.Category.astype(str)
    # Shared reference medians are computed across the plotted category groups.
    xm,ym=float(g.Customers.median()),float(g['Average value'].median())
    g['Demand group']=g.apply(lambda r: ('More customers' if r.Customers>=xm else 'Fewer customers')+' / '+('larger amounts' if r['Average value']>=ym else 'smaller amounts'),axis=1)
    g['Money sent']=g.Volume.map(lambda v:f'£{v:,.0f}')
    g['Wise revenue']=g.Revenue.map(lambda v:f'£{v:,.0f}')
    g['Average amount']=g['Average value'].map(lambda v:f'£{v:,.0f}')
    dots=alt.Chart(g).mark_circle(opacity=.78,stroke='white',strokeWidth=.6).encode(
        x=alt.X('Customers:Q',title='Different customers',scale=alt.Scale(zero=True)),
        y=alt.Y('Average value:Q',title='Average amount per activity (£)',scale=alt.Scale(zero=True),axis=alt.Axis(format='~s')),
        size=alt.Size('Volume:Q',title='Money sent (£)',scale=alt.Scale(range=[100,2400]),legend=None),
        color=alt.Color('Demand group:N',title='Observed group'),
        shape=alt.Shape('Metric:N',legend=None),
        tooltip=['Metric:N','Category:N','Customers:Q','Activities:Q','Money sent:N','Average amount:N','Wise revenue:N','Demand group:N'])
    labels=alt.Chart(g).mark_text(dy=-15,fontSize=11,color='#b8c5d6').encode(x='Customers:Q',y='Average value:Q',text='Category:N')
    vertical=alt.Chart(pd.DataFrame({'mid':[xm]})).mark_rule(strokeDash=[5,5],color='#8a93a5').encode(x='mid:Q')
    horizontal=alt.Chart(pd.DataFrame({'mid':[ym]})).mark_rule(strokeDash=[5,5],color='#8a93a5').encode(y='mid:Q')
    st.altair_chart((dots+labels+vertical+horizontal).properties(height=CHART_HEIGHT).interactive(),use_container_width=True)
    st.caption('Right = more customers; higher = larger average amounts; bigger circles = more money moved. Dashed lines show category medians for this chart. Hover for exact money and Wise revenue. These are descriptive groups, not statistical or machine-learning clusters.')


TAX_EVENTS = [('2025-04-06','6 Apr: new UK tax year starts'),('2026-01-31','31 Jan: UK tax return deadline')]


def fixed_line_chart(frame, events=None):
    """Fixed axes: hover details without scroll zoom or drag panning. Optional dated markers."""
    chart_data=frame.rename_axis('Month').reset_index().melt(id_vars='Month',var_name='Metric',value_name='Value')
    chart=alt.Chart(chart_data).mark_line(point=True).encode(
        x=alt.X('Month:T',title='Month',axis=alt.Axis(format='%b %Y')),
        y=alt.Y('Value:Q',title=None,scale=alt.Scale(zero=True),axis=alt.Axis(format='~s')),
        color=alt.Color('Metric:N',title=None,legend=alt.Legend(orient='bottom')),
        tooltip=[alt.Tooltip('Month:T',format='%b %Y'), 'Metric:N',alt.Tooltip('Value:Q',format=',.1f')]
    )
    if events:
        lo,hi=frame.index.min(),frame.index.max()+pd.offsets.MonthEnd(0)
        ev=pd.DataFrame([{'Month':pd.Timestamp(d),'Event':t} for d,t in events if lo<=pd.Timestamp(d)<=hi])
        if not ev.empty:
            ev['Value']=float(frame.max().max())*1.08
            ev['Low']=0.0
            rules=alt.Chart(ev).mark_rule(strokeDash=[6,4],color='#b7791f',strokeWidth=2).encode(x=alt.X('Month:T',title='Month',axis=alt.Axis(format='%b %Y')),y=alt.Y('Low:Q',title=None,scale=alt.Scale(zero=True),axis=alt.Axis(format='~s')),y2='Value:Q',tooltip=['Event:N',alt.Tooltip('Month:T',title='Date',format='%d %b %Y')])
            mid=lo+(hi-lo)/2
            left=alt.Chart(ev[ev.Month<mid]).mark_text(align='left',dx=6,fontSize=12,fontWeight='bold',color='#8a5a00').encode(x=alt.X('Month:T',title='Month',axis=alt.Axis(format='%b %Y')),y=alt.Y('Value:Q',title=None,scale=alt.Scale(zero=True),axis=alt.Axis(format='~s')),text='Event:N')
            right=alt.Chart(ev[ev.Month>=mid]).mark_text(align='right',dx=-6,fontSize=12,fontWeight='bold',color='#8a5a00').encode(x=alt.X('Month:T',title='Month',axis=alt.Axis(format='%b %Y')),y=alt.Y('Value:Q',title=None,scale=alt.Scale(zero=True),axis=alt.Axis(format='~s')),text='Event:N')
            chart=chart+rules+left+right
    st.altair_chart(chart.properties(height=CHART_HEIGHT,padding={'left':48,'right':12,'top':8,'bottom':4}),use_container_width=True)


def conversion_ring(sent, total, title):
    """Animated ring: fills to the share who sent while the number counts up."""
    sent=scale.n(sent); total=scale.n(total)
    share=sent/total*100 if total else 0
    whole, tenth = int(share), int(round((share-int(share))*10))
    if tenth==10: whole, tenth = whole+1, 0
    with st.container(border=True):
        st.markdown('**'+title+'**')
        st.markdown(PHONE_CSS+f'<div class="rg-wrap"><div class="rg-box"><div class="rg" style="--ra:{share:.1f}"></div>'
            f'<div class="rg-num" style="--ri:{whole};--rd:{tenth}"><span>sent money</span></div></div>'
            '<div class="rg-leg"><span><i style="background:#70d69b"></i>Sent money</span><span><i style="background:#f2a65a"></i>Did not send</span></div></div>',
            unsafe_allow_html=True)
        st.caption(f'{sent:,} sent money · {max(0,total-sent):,} did not · {total:,} people in this group.')


STORY_STEPS=['Momentum','The opportunity','Currency coverage','Activation','Revenue upside','Growth levers']


def story_banner(title, body):
    import html
    st.markdown('<div style="background:#163300;color:#e9f7df;padding:22px 26px;border-radius:14px;margin:6px 0 12px">'
        '<div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#9fe870;font-weight:700">The story in one line</div>'
        '<div style="font-size:23px;font-weight:700;line-height:1.35;margin:6px 0 10px">'+html.escape(title)+'</div>'
        '<div style="font-size:15px;line-height:1.6;color:#cfe8c0">'+html.escape(body)+'</div></div>',unsafe_allow_html=True)


def story_map():
    chips=''.join(f'<a href="#ch{i}" target="_self" style="text-decoration:none;display:inline-block;margin:0 8px 8px 0;padding:6px 12px;border-radius:999px;border:1px solid rgba(140,150,170,.45);font-size:13px;color:inherit">'
        f'<b style="color:#4f9a1f">{i}</b>&nbsp; {name}</a>' for i,name in enumerate(STORY_STEPS,1))
    st.markdown('<div style="margin-bottom:6px">'+chips+'</div>',unsafe_allow_html=True)


def chapter(num, beat, headline, sub):
    import html
    st.markdown(f'<div id="ch{num}" class="pb-chapter" style="margin:30px 0 8px;border-top:1px solid rgba(140,150,170,.35);padding-top:18px">'
        f'<span style="background:#9fe870;color:#163300;font-weight:800;border-radius:999px;padding:3px 11px;font-size:13px">{num}</span>'
        f'<span style="margin-left:10px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;opacity:.65;font-weight:700">{html.escape(beat)}</span>'
        f'<div style="font-size:27px;font-weight:750;line-height:1.25;margin-top:10px">{html.escape(headline)}</div>'
        f'<div style="font-size:15px;opacity:.72;margin-top:6px;line-height:1.5">{html.escape(sub)}</div></div>',unsafe_allow_html=True)


MISSING_ORDER = ['PKR','BDT','JPY','LKR','KRW','THB','CZK','COP','GHS','UGX','TZS','ZMW','BWP','UYU','RUB','globalEUR','globalUSD','globalGBP']
LEVER_PICTURES = {
'source': """<div class="lv-list"><div class="lv-h">Pay from</div>
<div class="lv-row pick"><span>🇬🇧 British pounds</span><span>✓</span></div>
<div class="lv-row pick k2"><span>🇪🇺 Euros</span><span class="lv-new" style="animation:none">NEW</span></div>
<div class="lv-row pick k3"><span>🇺🇸 US dollars</span><span class="lv-new" style="animation:none">NEW</span></div>
<div class="lv-row pick k4"><span>🇨🇭 Swiss francs</span><span class="lv-new" style="animation:none">NEW</span></div></div>""",
'same': """<div class="lv-list"><div class="lv-h">Send to</div>
<div class="lv-row"><span>£ ➜ 🇮🇳 rupees</span><span>✓</span></div>
<div class="lv-row"><span>£ ➜ 🇪🇺 euros</span><span>✓</span></div>
<div class="lv-row r2"><span>£ ➜ £ in 🇪🇸 Spain</span><span class="lv-new">NEW</span></div>
<div class="lv-row r3"><span>£ ➜ £ in 🇦🇪 Dubai</span><span class="lv-new">NEW</span></div></div>""",
'missing': "__MISSINGCHIPS__",
'business': """<div class="lv-list"><div class="lv-h">Account type</div>
<div class="lv-row"><span>👤 Personal</span><span>✓</span></div>
<div class="lv-row r2"><span>🏢 Small business</span><span class="lv-new">NEW</span></div>
<div class="lv-row r3"><span>🧾 Pay suppliers abroad</span><span class="lv-new">NEW</span></div>
<div class="lv-row r3"><span>👷 Pay staff abroad</span><span class="lv-new">NEW</span></div></div>""",
'limit': """<div class="lv-list"><div class="lv-h">Amount</div>
<div class="lv-row"><span>£5,000 · tuition</span><span>✓</span></div>
<div class="lv-row"><span>£50,000 · today’s limit</span><span>✓</span></div>
<div class="lv-row r2"><span>£75,000 · home deposit</span><span class="lv-new">NEW</span></div>
<div class="lv-row r3"><span>£120,000 · moving savings</span><span class="lv-new">NEW</span></div></div>""",
'activation': """<div style="position:relative"><div class="lv-ppl">
<div class="lv-p">👤</div><div class="lv-p">👤</div><div class="lv-p">👤</div><div class="lv-p">👤</div><div class="lv-p">👤</div>
<div class="lv-p o flip">👤</div><div class="lv-p o">👤</div><div class="lv-p o">👤</div><div class="lv-p o">👤</div><div class="lv-p o">👤</div></div>
<span class="lv-plus" style="left:-6px;top:28px">+1 sender</span>
<div style="display:flex;gap:14px;justify-content:center;font-size:11px;margin-top:10px"><span><b style="color:#4f9a1f">●</b> Sent</span><span><b style="color:#f2a65a">●</b> Not yet</span></div></div>""",
}


def ask_card(column, num, title, detail, size, value, picture, today):
    import html
    with column:
        with st.container(border=True):
            st.markdown(f'**{num}. {title}**')
            st.markdown('<div class="lv-today">Today: '+html.escape(today)+'</div><div class="pb-desc lv-desc">'+html.escape(detail)+'</div>', unsafe_allow_html=True)
            st.markdown(PHONE_CSS+'<div class="lv-pic">'+picture+'</div>', unsafe_allow_html=True)
            st.metric(size, value)


def reliability_cards(period_rows):
    """Service quality from the workbook's reliability and telemetry columns."""
    sent=period_rows[period_rows.Transacted]
    def rates(g):
        done=g['Transfer status'].eq('Completed')
        arrived=g.loc[done,'Arrival time (seconds)'].dropna()
        return done.mean() if len(g) else 0, arrived.le(20).mean() if len(arrived) else 0
    in_app=sent[sent.Channel.eq('Integration')]; wise=sent[sent.Channel.eq('Wise direct')]
    app_ok,app_fast=rates(in_app); wise_ok,wise_fast=rates(wise)
    quotes=period_rows[period_rows.Channel.eq('Integration')]
    api=quotes['Quote API response (ms)'].dropna()
    err=quotes['API error'].fillna(0).mean() if len(quotes) else 0
    support=in_app['Support contact'].astype(bool).mean()*1000 if len(in_app) else 0
    st.subheader('Reliability: the service customers trust')
    cards=[('✅','Transfers that worked',f'{app_ok:.1%}',f'Wise directly: {wise_ok:.1%}'),
           ('⚡','Arrived in under 20 seconds',f'{app_fast:.0%}',f'Wise directly: {wise_fast:.0%}'),
           ('📶','Fee shown in the app in',f'{api.median():.0f} ms' if len(api) else '—',f'Slowest 5%: {api.quantile(.95):.0f} ms · errors {err:.1%}' if len(api) else ''),
           ('💬','Support contacts',f'{support:.0f}',f'per 1,000 transfers in the app')]
    html_cards=''.join(f'<div class="rl-card"><div class="rl-ic">{ic}</div><div class="rl-lbl">{lbl}</div><div class="rl-val">{val}</div><div class="rl-sub">{sub}</div></div>' for ic,lbl,val,sub in cards)
    st.markdown("""<style>.rl-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:6px 0}
@media (max-width:900px){.rl-grid{grid-template-columns:repeat(2,1fr)}}
.rl-card{border:1px solid rgba(140,150,170,.45);border-radius:14px;padding:14px;text-align:center}
.rl-ic{font-size:26px}.rl-lbl{font-size:13px;font-weight:700;margin-top:4px}.rl-val{font-size:30px;font-weight:900;color:#4f9a1f;margin:4px 0}.rl-sub{font-size:12.5px}</style><div class="rl-grid">"""+html_cards+'</div>',unsafe_allow_html=True)
    st.caption('From the workbook’s reliability columns: transfer status, arrival time, quote response time, API errors and support contacts. For context, Wise reports that about 77% of its transfers arrive instantly (Wise Q1 FY27 trading update). Illustrative figures.')


def main():
    PAGES=['Question 1 — Quarterly review','Question 2 — Convenience fee','Question 3 — Multi-currency accounts','Question 4 — Investment case']
    qp=st.query_params
    if 'case_question' not in st.session_state and qp.get('q') in ('1','2','3','4'):
        st.session_state['case_question']=PAGES[int(qp.get('q'))-1]
    if 'audience' not in st.session_state and qp.get('view') in ('partner','wise'):
        st.session_state['audience']='Wise team (internal)' if qp.get('view')=='wise' else 'Partner (PartnerBank)'
    page=st.sidebar.radio('Case study question',['Question 1 — Quarterly review','Question 2 — Convenience fee','Question 3 — Multi-currency accounts','Question 4 — Investment case'],key='case_question')
    if st.session_state.get('_last_page')!=page:
        st.session_state['_last_page']=page
        # Jump to the top of the page when a different question is picked.
        components.html(f"""<script>
const d=window.parent.document; const go=()=>{{window.parent.scrollTo(0,0);
['[data-testid="stMain"]','[data-testid="stAppViewContainer"]','section.main','.main'].forEach(q=>{{const e=d.querySelector(q); if(e) e.scrollTop=0;}});}};
go(); setTimeout(go,150); setTimeout(go,600); /* {page} */
</script>""",height=0)
    st.title('PartnerBank — '+('Quarterly Business Review' if page.startswith('Question 1') else 'Convenience fee analysis' if page.startswith('Question 2') else 'Multi-currency account demand' if page.startswith('Question 3') else 'Wise Platform investment case'))
    st.caption('Illustrative figures for discussion purposes only.')
    st.markdown(SYMMETRY_CSS, unsafe_allow_html=True)
    if not DATA_FILE.exists():
        st.error(f'Workbook not found: {DATA_FILE}')
        return
    df = load_data(str(DATA_FILE), DATA_FILE.stat().st_mtime)
    st.sidebar.header('Review period')
    quarters = pd.date_range(df.Date.min().to_period('Q-MAR').start_time, df.Date.max(),freq='QS-APR')
    periods = {}
    for fy in sorted({d.year + (d.month >= 4) for d in df.Date}):
        fy_start = pd.Timestamp(year=fy-1, month=4, day=1)
        periods[f'Full year · Fiscal year {fy} (Apr {fy-1}–Mar {fy})'] = (fy_start, fy_start+pd.DateOffset(years=1), 'year')
    for q in quarters:
        periods[label_period(q)] = (pd.Timestamp(q), pd.Timestamp(q)+pd.DateOffset(months=3), 'quarter')
    selected = st.sidebar.selectbox('View period', list(periods), index=0)
    start, end, period_kind = periods[selected]
    prev = start - pd.DateOffset(months=12 if period_kind=='year' else 3)
    current = df[df.Date.ge(start)&df.Date.lt(end)].copy()
    view=st.sidebar.radio('👥 Who is this view for?',['Partner (PartnerBank)','Wise team (internal)'],key='audience',
        help='Partner view hides Wise’s own revenue. Wise team view shows everything, including the internal business case numbers.')
    scale.INTERNAL = view.startswith('Wise')
    if scale.INTERNAL:
        st.sidebar.markdown('<span class="wise-legend">🔒 Yellow border = Wise team only</span>',unsafe_allow_html=True)
    full=st.sidebar.toggle('📏 Show at PartnerBank’s full size',value=True,key='full_scale',help=f'Multiplies customer counts and money totals by ×{scale.FACTOR} to match PartnerBank’s size. Percentages do not change.')
    scale.S = scale.FACTOR if full else 1
    m = metrics(df,start,end)*scale.S
    previous = metrics(df,prev,start)*scale.S
    comparison_available = prev >= df.Date.min().normalize()
    st.sidebar.caption('Headline figures count each customer once in the selected period. Full-year user totals are not the sum of monthly users.')
    if start < df.Date.min().normalize() or end > df.Date.max().normalize()+pd.Timedelta(days=1):
        st.sidebar.caption('This period has only partial data in the workbook.')
    st.caption(f'Selected period: {selected}')
    st.sidebar.caption(f'Source: {DATA_FILE.name} · {len(df):,} records')
    if full:
        st.info(f'📏 Shown at PartnerBank’s full size: customer counts and money are the 10,000-record sample × {scale.FACTOR}, so they match the QBR deck (about 33,000 customers checking the fee each quarter). Percentages are unchanged. Illustrative figures.')
    if page.startswith('Question 4'):
        import sys
        project_dir=str(Path(__file__).parent)
        if project_dir not in sys.path:
            sys.path.insert(0,project_dir)
        from question4 import render
        render(df,current,selected)
        return
    if page.startswith('Question 3'):
        import sys
        project_dir=str(Path(__file__).parent)
        if project_dir not in sys.path:
            sys.path.insert(0,project_dir)
        from question3 import render
        render(current,selected)
        return
    if page.startswith('Question 2'):
        import sys
        project_dir=str(Path(__file__).parent)
        if project_dir not in sys.path:
            sys.path.insert(0,project_dir)
        from question2 import render
        render(current,selected)
        return

    # ---------- Data for the story (same period as the sidebar) ----------
    monthly=[]
    for month,g in current.groupby(current.Date.dt.to_period('M')):
        mm=metrics(g,month.start_time,month.end_time+pd.Timedelta(nanoseconds=1))
        monthly.append({'Month':month.start_time,'Checked the fee':int(mm.quotes),'Sent through PartnerBank':int(mm.active),
            'On Wise directly':int(mm.direct_users),'PartnerBank volume (£)':float(mm.app_volume),
            'Wise-direct volume (£)':float(mm.direct_volume),
            'New sign-ups':int(mm.new_users),'New customers who sent':int(mm.new_active),
            'New customers on Wise directly':int(mm.new_direct),'Wise-direct revenue (£)':float(mm.direct_revenue)})
    monthly=pd.DataFrame(monthly).set_index('Month')*scale.S
    app=current[current.Channel.eq('Integration')]
    quoted=set(app.loc[app['Got a quote'],'User ID'])
    active=set(app.loc[app.Transacted,'User ID'])
    new_signup_ids=set(app.loc[app['New user this month'],'User ID'])
    new_sender_ids=set(app.loc[app['New user this month'] & app.Transacted,'User ID'])
    direct=current[current.Channel.eq('Wise direct')&current.Transacted].copy()
    flags=opportunity_flags(direct)
    direct['Primary opportunity']='Supported Send Money transfer'
    for reason in reversed(list(flags.columns)):
        direct.loc[flags[reason],'Primary opportunity']=reason
    # Limits and flags use real transfer sizes above; only totals shown below are scaled.
    MONEY_COLS=['Transaction Volume (GBP)','Revenue Amount (GBP)']
    current[MONEY_COLS]=current[MONEY_COLS]*scale.S
    direct[MONEY_COLS]=direct[MONEY_COLS]*scale.S

    first,last=monthly.iloc[0],monthly.iloc[-1]
    span=f'{monthly.index[0]:%b %Y} to {monthly.index[-1]:%b %Y}'
    g_quotes=(last['Checked the fee']/first['Checked the fee']-1)*100 if first['Checked the fee'] else 0
    g_direct=(last['On Wise directly']/first['On Wise directly']-1)*100 if first['On Wise directly'] else 0
    direct_share=ratio(m.direct_volume,m.app_volume+m.direct_volume)
    send_rate=ratio(len(quoted&active),len(quoted))
    new_rate=ratio(m.new_active,m.new_users)
    missing_by_ccy=direct[direct['Target Currency'].isin(MISSING)].groupby('Target Currency')['Transaction Volume (GBP)'].sum().sort_values(ascending=False)
    top_missing=list(missing_by_ccy.index[:3])
    non_gbp=direct[direct['Source Currency'].ne('GBP')]
    non_gbp_by_ccy=non_gbp.groupby('Source Currency')['Transaction Volume (GBP)'].sum().sort_values(ascending=False)
    period_word='a year' if period_kind=='year' else 'this quarter'
    names=lambda codes: ', '.join(currency_name(c) for c in codes)

    # ---------- The story in one line ----------
    story_banner(
        'Strong momentum, and a clear growth opportunity: a growing share of your customers’ money flows to Wise directly, and most of it can be captured in your app.',
        f'Over {span}, more of PartnerBank’s customers checked the fee and sent money in the app. At the same time, '
        f'{direct_share:.0%} of their money went through Wise directly, for things the app cannot do yet. '
        'This page shows where the momentum is, where the opportunity sits, and the revenue upside of capturing it.')
    story_map()
    DATA_POINTS=[('Total Integration Users',1),('Total Active Users',1),('New Users Created',4),('Total New Active Users',4),
        ('Total Wise Users from the Partner',2),('New Wise Users from the Partner',2),('Source Currency',3),('Target Currency',3),
        ('Transaction Volume',2),('Revenue Amount',5),('Product used',3),('User type',3)]
    chips=''.join((f'<span class="dp-chip">🔒 {n} <b>Wise team view</b></span>' if n=='Revenue Amount' and not scale.INTERNAL else f'<a href="#ch{c}" target="_self" class="dp-chip">✓ {n} <b>ch {c}</b></a>') for n,c in DATA_POINTS)
    st.markdown("""<style>.dp-box{border:1px dashed rgba(140,150,170,.55);border-radius:14px;padding:10px 14px;margin:4px 0 8px;text-align:center}
.dp-title{font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px}
.dp-chip{display:inline-block;margin:3px;padding:4px 10px;border-radius:999px;background:rgba(159,232,112,.16);border:1px solid rgba(159,232,112,.6);font-size:12.5px;color:inherit;text-decoration:none}
.dp-chip b{color:#4f9a1f;margin-left:4px}</style><div class="dp-box"><div class="dp-title">All 12 case study data points are covered · click one to jump to it</div>"""+chips+'</div>',unsafe_allow_html=True)

    # ---------- 1. What is working ----------
    chapter(1,'Momentum',
        f'Engagement is up {g_quotes:.0f}%: more customers check the fee every month',
        f'{int(first["Checked the fee"]):,} → {int(last["Checked the fee"]):,} customers a month ({span}). {send_rate:.0%} convert to a transfer.')
    cols=st.columns(2)
    for col,(key,official,plain,description) in zip(cols,[
        ('quotes','Total Integration Users','Checked the fee in the app','People who saw the fee, the amount the other person would get, and when it would arrive in PartnerBank’s app.'),
        ('active','Total Active Users','Sent money through PartnerBank','People who completed at least one transfer through PartnerBank’s app.')]):
        delta=change(m[key],previous[key]).replace('previous quarter','previous year' if period_kind=='year' else 'previous quarter') if comparison_available and previous[key] else None
        metric_card(col,official,plain,f'{m[key]:,.0f}',description,delta)
    st.subheader('Customers by month')
    fixed_line_chart(monthly[['Checked the fee','Sent through PartnerBank','On Wise directly']],TAX_EVENTS)
    st.caption('December is the peak (holiday sending). February rises right after the UK tax return deadline on 31 January, when people move money to pay tax bills.')
    reliability_cards(current)

    # ---------- 2. The twist ----------
    chapter(2,'The opportunity',
        f'Untapped opportunity: customers using Wise directly grew {g_direct:.0f}%'+(f', {g_direct/g_quotes:.1f}× as fast' if g_quotes>0 and g_direct>g_quotes else ''),
        f'{direct_share:.0%} of customer money flows outside the app: £{m.direct_volume:,.0f} on Wise directly vs £{m.app_volume:,.0f} in the app. That is the size of the opportunity.')
    c1,c2=st.columns(2)
    metric_card(c1,'Total Wise Users from the Partner','Customers using Wise directly',f'{m.direct_users:,.0f}','PartnerBank customers who sent money in Wise’s app or website, paid from their PartnerBank account.')
    metric_card(c2,'New Wise Users from the Partner','New customers using Wise directly',f'{m.new_direct:,.0f}','Those Wise-direct customers marked as new during the selected period.')
    st.subheader('Transaction Volume: money sent by month (£)')
    fixed_line_chart(monthly[['PartnerBank volume (£)','Wise-direct volume (£)']],TAX_EVENTS)
    st.caption('Dashed lines mark UK tax dates. Personal transfers abroad are not taxed when they are sent, but tax deadlines change when people move money.')
    top_volume=max(m.app_volume,m.direct_volume) or 1
    short_money=lambda v: f'£{v/1e6:.1f}M' if v>=1e6 else f'£{v/1e3:.0f}k'
    PICTURE_VARS.update(APPAMT=short_money(m.app_volume),DIRAMT=short_money(m.direct_volume),
        APPFILL=round(80*m.app_volume/top_volume),DIRFILL=round(80*m.direct_volume/top_volume),
        APPSHARE=f'{1-direct_share:.0%}',DIRSHARE=f'{direct_share:.0%}')
    c1,c2=st.columns(2)
    metric_card(c1,'Transaction Volume · PartnerBank app','Money sent through PartnerBank',f'£{m.app_volume:,.0f}','Adds the value of completed transfers through the bank’s app. A customer can make several transfers.')
    metric_card(c2,'Transaction Volume · Wise directly','Money sent directly through Wise',f'£{m.direct_volume:,.0f}','Adds the value of completed activity on Wise, funded from PartnerBank accounts.')

    # ---------- 3. Why: currencies and needs ----------
    chapter(3,'Opportunity 1: currency coverage',
        'Expanding currency coverage unlocks demand customers already have',
        f'£{non_gbp["Transaction Volume (GBP)"].sum():,.0f} was sent from {names(non_gbp_by_ccy.index)} (the app only sends from British pounds), and '
        f'£{missing_by_ccy.sum():,.0f} went to currencies the app doesn’t offer, led by {names(top_missing)}.')
    st.caption('Read left to right: all the money PartnerBank customers sent (100%) → how much went through the bank’s app vs Wise directly → why → where it went. Each currency shows its app vs Wise split. 🚫 marks money that went to Wise because of a limit in today’s app (from the case study). Wider bands mean more money. Point at anything for details.')
    show_money_flow(direct, current[current.Channel.eq('Integration')&current.Transacted])
    summary=direct.groupby('Primary opportunity').agg(Customers=('User ID','nunique'),Transfers=('Transfer ID','count'),
        Volume_GBP=('Transaction Volume (GBP)','sum')).sort_values('Volume_GBP',ascending=False)
    summary[['Customers','Transfers']]=(summary[['Customers','Transfers']]*scale.S).round().astype(int)
    st.dataframe(summary.rename(columns={'Volume_GBP':'Money sent (£)'}).style.format({'Money sent (£)':'£{:,.0f}','Customers':'{:,}','Transfers':'{:,}'}),width='stretch')
    overlapping=scale.n(flags.sum(axis=1).gt(1).sum())
    st.caption(f'{overlapping:,} transfers meet more than one condition. Each transfer is counted once, in this order: business → source other than British pounds → same currency → unsupported route → over £50,000 → other product.')
    supported=direct[direct['Primary opportunity'].eq('Supported Send Money transfer')]
    st.write(f'**£{supported["Transaction Volume (GBP)"].sum():,.0f}** went through Wise directly even though the app could have handled it. That points to awareness and experience, not missing features.')
    with st.expander('Source Currency and Target Currency in detail'):
        quadrant_chart(direct,['Source Currency','Target Currency'])
        c1,c2=st.columns(2)
        with c1:
            st.markdown('**Source Currency: money sent from**')
            breakdown_table(direct,'Source Currency')
        with c2:
            st.markdown('**Target Currency: money sent to**')
            breakdown_table(direct,'Target Currency')
    with st.expander('Product used and User type in detail'):
        c1,c2=st.columns(2)
        with c1:
            st.markdown('**Product used**')
            breakdown_table(direct,'Product used')
        with c2:
            st.markdown('**User type: personal or business**')
            breakdown_table(direct,'User type')
        st.caption('The app serves personal customers only, so business activity always goes to Wise directly.')
    with st.expander('See needs that overlap'):
        overlap_table=pd.DataFrame([{'Need':c,'Transfers':int(flags[c].sum()),'Volume (£)':direct.loc[flags[c],'Transaction Volume (GBP)'].sum()} for c in flags])
        st.dataframe(overlap_table,hide_index=True,width='stretch')
        st.caption('Overlapping amounts must not be added together.')

    # ---------- 4. Why: first transfers ----------
    chapter(4,'Opportunity 2: activation',
        f'Activation opportunity: only {new_rate:.0%} of new sign-ups make a first transfer',
        f'{m.new_users:,.0f} people signed up and {m.new_active:,.0f} sent money, leaving {m.new_users-m.new_active:,.0f} new customers ready to activate.')
    c1,c2=st.columns(2)
    metric_card(c1,'New Users Created','New sign-ups',f'{m.new_users:,.0f}','People marked as new who signed up through PartnerBank’s app.')
    metric_card(c2,'Total New Active Users','New customers who sent money',f'{m.new_active:,.0f}','People marked as new who also made a transfer through PartnerBank’s app.')
    left,right=st.columns(2)
    with left:
        conversion_ring(len(new_signup_ids&new_sender_ids),len(new_signup_ids),'New customers who signed up')
    with right:
        conversion_ring(len(quoted&active),len(quoted),'Everyone who checked the fee')
    st.subheader('New customers by month: sign-up to first transfer')
    fixed_line_chart(monthly[['New sign-ups','New customers who sent','New customers on Wise directly']])
    st.caption('Uses the workbook’s “New user this month” flag. Without sign-up dates this is not a full cohort analysis.')

    # ---------- 5. What it is worth ----------
    movable=direct[direct['Primary opportunity'].ne('Other product need')].copy()
    share=st.session_state.get('winback',50)
    captured=movable['Transaction Volume (GBP)'].sum()*share/100
    chapter(5,'Revenue upside',
        f'Capturing {share}% of the opportunity brings £{captured:,.0f} back into the app {period_word}',
        'Fee revenue: ??? The convenience fee is not set yet. It is decided in Question 2.')
    st.slider('What share of this opportunity could the app capture?',10,100,50,10,format='%d%%',key='winback')
    by_reason=movable.groupby('Primary opportunity').agg(Transfers=('Transfer ID','count'),Money=('Transaction Volume (GBP)','sum')).sort_values('Money',ascending=False)
    by_reason['Transfers']=(by_reason.Transfers*scale.S).round().astype(int).map('{:,}'.format)
    by_reason['At chosen share']=(by_reason.Money*share/100).map(lambda v:f'£{v:,.0f}')
    by_reason['Money']=by_reason.Money.map(lambda v:f'£{v:,.0f}')
    by_reason['Fee revenue']='???'
    st.dataframe(by_reason.rename(columns={'Money':'Money sent (£)','At chosen share':f'Brought back at {share}% (£)'}),width='stretch')
    st.caption('Excludes accounts, cards and receiving money (that is Question 3). Not every transfer will move, so use the slider to test scenarios.')

    # ---------- Most populous countries on the brief's missing-currency list ----------
    st.subheader('Biggest opportunity: the most populous countries the app cannot send to yet')
    st.markdown('From the case study’s list of 18 missing currencies, these three countries have the most people. Customers already send there today, just not through PartnerBank’s app.')
    COMMUNITIES=[('🇵🇰','Pakistan','PKR','Pakistani rupees',240.5),('🇧🇩','Bangladesh','BDT','Bangladeshi taka',171.5),('🇯🇵','Japan','JPY','Japanese yen',124.5)]
    done=current[current.Transacted]
    cards=[]; total_rev=0.0; total_money=0.0
    for flag,country,ccy,ccy_name,people in COMMUNITIES:
        dx=done[done['Target Currency'].eq(ccy)&done.Channel.eq('Wise direct')]
        on_wise=dx['Transaction Volume (GBP)'].sum()
        rate=dx['Revenue Amount (GBP)'].sum()/on_wise if on_wise else 0
        extra=on_wise*share/100
        rev=extra*rate; total_rev+=rev; total_money+=extra
        badge=f'<span class="cm-tag miss">Not in the app yet · add {ccy_name}</span>'
        cards.append(f'''<div class="cm-card"><div class="cm-flag">{flag}</div><div class="cm-name">{country}</div>
<div class="cm-pop">About <b>{people:,.0f} million</b> people live here</div>{badge}
<div class="cm-row"><span>Sent on Wise directly today</span><b>£{on_wise:,.0f}</b></div>
<div class="cm-row"><span>Transfers · customers</span><b>{scale.n(len(dx)):,} · {scale.n(dx["User ID"].nunique()):,}</b></div>
<div class="cm-row up"><span>Brought into the app ({share}%)</span><b>+£{extra:,.0f}</b></div>
<div class="cm-big">{(f'<div class="wise-hl"><span><span class="cm-arrow">▲</span> +£{rev:,.0f}</span><small>potential Wise revenue {period_word}*</small></div>') if scale.INTERNAL else '<span><span class="cm-arrow">▲</span> Fee value ???</span><small>set in Question 2</small>'}</div>
<div class="cm-grow">Adds <b>{(extra/m.app_volume*100 if m.app_volume else 0):.1f}%</b> to all money sent through the app</div></div>''')
    st.markdown("""<style>
.cm-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:10px 0 8px}
@media (max-width:900px){.cm-grid{grid-template-columns:1fr}}
.cm-card{border:1px solid rgba(140,150,170,.45);border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:8px}
.cm-flag{font-size:44px;line-height:1;text-align:center;animation:txBob 3s ease-in-out infinite}
.cm-name{font-size:20px;font-weight:900;text-align:center}
.cm-pop{font-size:13.5px;min-height:2.9em;text-align:center}
.cm-tag{font-size:11.5px;font-weight:800;border-radius:999px;padding:3px 10px;max-width:max-content;margin:0 auto}
.cm-tag.ok{background:#9fe870;color:#163300}.cm-tag.miss{background:#fde8d4;color:#7a3e00}
.cm-row{display:flex;justify-content:space-between;font-size:14px;border-bottom:1px dashed rgba(140,150,170,.4);padding:4px 0}
.cm-row.up b{color:#2f7d00}
.cm-big{margin-top:6px;font-size:30px;font-weight:900;color:#2f7d00;display:flex;flex-direction:column;align-items:center;text-align:center}
.cm-big small{font-size:12px;font-weight:700;color:inherit;opacity:.8}
.cm-arrow{display:inline-block;font-size:18px;animation:cmUp 1.6s ease-in-out infinite}
.cm-grow{font-size:13.5px;text-align:center}
@keyframes cmUp{0%,100%{transform:translateY(2px);opacity:.6}50%{transform:translateY(-4px);opacity:1}}
@keyframes txBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
</style><div class="cm-grid">"""+''.join(cards)+'</div>',unsafe_allow_html=True)
    st.markdown(f'**Together:** these three countries could bring **+£{total_money:,.0f}** into PartnerBank’s app (**+{(total_money/m.app_volume*100 if m.app_volume else 0):.1f}%** more money through the app)'+(f' and <span class="wise-inline">🔒 <b>+£{total_rev:,.0f}</b> in potential Wise revenue {period_word}*</span>.' if scale.INTERNAL else '. PartnerBank’s fee value: **???** until Question 2.'),unsafe_allow_html=True)
    st.caption(f'How it works: money brought into the app = money sent on Wise directly × {share}% (the slider above). '+
               ('*Potential Wise revenue uses the revenue per £1 sent in the data’s Revenue Amount for each country (about 0.5p per £1). PartnerBank’s own fee is ??? until Question 2. ' if scale.INTERNAL else 'PartnerBank’s fee value is ??? until the fee is set in Question 2. ')+
               'Population: World Bank, 2023 estimates. Russia (about 144 million) is larger than Japan but is left out because UK sanctions restrict payments there. Money figures are illustrative.')
    amounts=monthly[['PartnerBank volume (£)','Wise-direct volume (£)']+(['Wise-direct revenue (£)'] if scale.INTERNAL else [])]
    growth_box=st.container(border=scale.INTERNAL)
    with growth_box:
        if scale.INTERNAL:
            scale.wise_tag('Wise team only: includes the Wise-direct revenue line')
        st.subheader('Growth since the first month (first month = 100)')
        fixed_line_chart(amounts.div(amounts.iloc[0].replace(0,float('nan'))).mul(100))
    if scale.INTERNAL:
     with st.container(border=True):
      scale.wise_tag('Wise team only: Wise’s own revenue')
      with st.expander('Revenue Amount (recorded by Wise)'):
        st.metric('Revenue recorded on Wise-direct transfers',f'£{m.direct_revenue:,.0f}')
        st.caption('This is Wise’s revenue on direct activity, not PartnerBank income. PartnerBank’s fee income is modelled above.')

    # ---------- 6. Growth levers: today's limits become opportunities ----------
    vol=direct['Transaction Volume (GBP)']
    def opp(mask):
        return f'£{vol[mask].sum():,.0f}', f'{scale.n(mask.sum()):,} transfers · {scale.n(direct.loc[mask,"User ID"].nunique()):,} customers on Wise directly'
    chips=''.join(f'<span class="lv-chip{" top" if c in top_missing else ""}">{c}</span>' for c in MISSING_ORDER)
    pics=dict(LEVER_PICTURES, missing=f'<div class="lv-chips">{chips}</div>')
    chapter(6,'Growth levers','Six growth opportunities, tracked every month',
        'Each one turns a limit of today’s app into a way to win back money customers already send. Fee value: ??? until the fee is set in Question 2.')
    cards=[
        ('Send from euros and dollars','Only sends from British pounds','Let customers pay from the euros, dollars and Swiss francs they already hold.',flags['Sent from a currency other than British pounds'],'source'),
        ('Allow same-currency transfers','Only sends when the currency changes','Let customers send pounds to a pounds account abroad, like a Spanish or Dubai bank.',flags['Same-currency transfer'],'same'),
        ('Add the 18 missing currencies','35 of 53 currencies','Start with '+names(top_missing)+'. “Global” means sending a currency to a country that uses another one, like US dollars to Canada.',flags['Unsupported target route'],'missing'),
        ('Open it to business customers','Personal customers only','Small businesses paying suppliers or staff abroad already do it on Wise directly.',flags['Business customer'],'business'),
        ('Raise the £50,000 limit','Up to £50,000 per transfer','Big moments, like a down payment on a home or a tuition payment, go elsewhere today.',flags['Over £50,000'],'limit'),
    ]
    rows=[st.columns(3),st.columns(3)]
    slots=[rows[0][0],rows[0][1],rows[0][2],rows[1][0],rows[1][1],rows[1][2]]
    for i,(title,today,detail,mask,key) in enumerate(cards):
        amount,label=opp(mask)
        if not mask.any():
            amount,label='£0 in this data','Check with real data: none of these transfers are in the sample'
        ask_card(slots[i],str(i+1),title,detail,label,amount,pics[key],today)
    stuck=m.new_users-m.new_active
    ask_card(slots[5],'6','Get sign-ups to a first transfer','Show the fee, arrival time and saved recipients up front, so sign-ups finish their first transfer.',
        f'{stuck:,.0f} stuck · each +10 points adds',f'+{round(m.new_users*0.10):,.0f} senders',pics['activation'],f'Only {new_rate:.0%} of new sign-ups send')
    st.caption('A transfer can fit more than one opportunity (for example, a business sending euros), so do not add these amounts together.')
    kpis=['🔁 Fee-check-to-send conversion','🚀 Sign-up-to-first-transfer activation','👛 Share of wallet in the app','🌍 Volume from euros and dollars','💷 Fee revenue']
    st.markdown('**KPIs tracked monthly**<div class="lv-kpis">'+''.join(f'<span class="lv-kpi">{k}</span>' for k in kpis)+'</div>',unsafe_allow_html=True)
    st.caption('\\* Illustrative figures for discussion purposes only.')

    with st.expander('Data quality, metric definitions and calculation query'):
        completed_app=df[df.Channel.eq('Integration')&df.Transacted]
        checks={
            'Transfer IDs unique':df['Transfer ID'].is_unique,
            'Integration source always British pounds':completed_app['Source Currency'].eq('GBP').all(),
            'Integration transfers cross-currency':completed_app['Source Currency'].ne(completed_app['Target Currency']).all(),
            'Integration customers personal':completed_app['User type'].eq('Personal').all(),
            'Integration amounts ≤ £50,000':completed_app['Transaction Volume (GBP)'].le(50000).all(),
            'Integration target routes supported':~completed_app['Target Currency'].isin(MISSING).any(),
            'New active users ≤ new sign-ups':m.new_active<=m.new_users,
        }
        st.dataframe(pd.DataFrame([{'Check':k,'Result':'Pass' if v else 'Review'} for k,v in checks.items()]),hide_index=True)
        st.code(METRIC_SQL,language='sql')
        st.write('Users can use both channels. Do not add channel user counts to obtain unique people. Signup dates, quote-to-transfer IDs, partner pricing and delivery costs require additional data. Reliability (status, arrival time, API speed and errors, support contacts) comes from the workbook’s telemetry columns. Global currency routes require destination-country detail or explicit global currency codes.')
    with st.expander('Monthly numbers and source records'):
        if scale.INTERNAL:
            st.markdown('<span class="wise-inline">🔒 Wise team only: the revenue columns in these tables</span>',unsafe_allow_html=True)
        shown=monthly if scale.INTERNAL else monthly.drop(columns=['Wise-direct revenue (£)'],errors='ignore')
        st.dataframe(shown,width='stretch')
        st.download_button('Download monthly metrics',shown.to_csv().encode(),'partnerbank_monthly_metrics.csv','text/csv')
        st.dataframe(readable_table(current if scale.INTERNAL else current.drop(columns=['Revenue Amount (GBP)'])),width='stretch',hide_index=True)

if __name__=='__main__':
    main()
