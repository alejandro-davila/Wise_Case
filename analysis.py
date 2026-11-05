from pathlib import Path
import pandas as pd

DATA_FILE = Path(__file__).parent / 'Wise_Mock_Dataset_FY2026.xlsx'
SCALE = 20  # 10,000-row sample x20 = PartnerBank's size (33,000 fee checks a quarter in the brief)

MISSING = {'BDT', 'BWP', 'COP', 'CZK', 'GHS', 'globalEUR', 'globalUSD', 'globalGBP', 'JPY',
           'KRW', 'LKR', 'PKR', 'RUB', 'THB', 'TZS', 'UGX', 'UYU', 'ZMW'}

REASONS = [
    ('Business customer', lambda d: d['User type'].eq('Business')),
    ('Sent from euros or dollars', lambda d: d['Source Currency'].ne('GBP')),
    ('Same-currency transfer', lambda d: d['Source Currency'].eq(d['Target Currency'])),
    ('Currency not offered', lambda d: d['Target Currency'].isin(MISSING)),
    ('Over £50,000', lambda d: d['Transaction Volume (GBP)'].gt(50000)),
    ('Account, card or receiving', lambda d: d['Product used'].ne('Send Money')),]
LIMITS = [r for r, _ in REASONS if r != 'Account, card or receiving']
NO_LIMIT = 'No limit (app could have sent it)'

FEE_RATE, FEE_MIN, FEE_CAP = 0.3, 1.0, 15.0 

def load(path=DATA_FILE):
    d = pd.read_excel(path, sheet_name='Transactions')
    d['Date'] = pd.to_datetime(d['Date'])
    d['Month'] = d['Date'].dt.to_period('M').dt.start_time
    d['Product used'] = d['Product used'].replace({'Multi-currency Account (MCA)': 'Multi-currency Account'})
    for c in ['Transacted', 'Got a quote', 'New user this month']:
        d[c] = d[c].map(lambda v: str(v).lower() in ('true', '1', 'yes'))
    return d

def add_reason(direct):
    direct = direct.copy()
    direct['Reason'] = NO_LIMIT
    for name, test in reversed(REASONS):
        direct.loc[test(direct), 'Reason'] = name
    return direct

def fee(amount, rate=FEE_RATE, minimum=FEE_MIN, cap=FEE_CAP):
    return min(max(amount * rate / 100, minimum), cap)

def monthly(d):
    app = d[d.Channel.eq('Integration')]
    wise = d[d.Channel.eq('Wise direct') & d.Transacted]
    rows = []
    for m, g in d.groupby('Month'):
        a, w = app[app.Month.eq(m)], wise[wise.Month.eq(m)]
        rows.append({
            'Month': m,
            'Checked the fee': a.loc[a['Got a quote'], 'User ID'].nunique() * SCALE,
            'Sent in the app': a.loc[a.Transacted, 'User ID'].nunique() * SCALE,
            'Used Wise directly': w['User ID'].nunique() * SCALE,
            'Money sent in the app (£)': a.loc[a.Transacted, 'Transaction Volume (GBP)'].sum() * SCALE,
            'Money sent on Wise directly (£)': w['Transaction Volume (GBP)'].sum() * SCALE,
        })
    return pd.DataFrame(rows).set_index('Month')

---------------------------------------
def summary(d):
    app = d[d.Channel.eq('Integration')]
    sent = app[app.Transacted]
    wise = add_reason(d[d.Channel.eq('Wise direct') & d.Transacted])
    mon = monthly(d)
    first, last = mon.iloc[0], mon.iloc[-1]

    quoted, senders = set(app.loc[app['Got a quote'], 'User ID']), set(sent['User ID'])
    new = set(app.loc[app['New user this month'], 'User ID'])
    new_sent = set(app.loc[app['New user this month'] & app.Transacted, 'User ID'])

    app_vol = sent['Transaction Volume (GBP)'].sum() * SCALE
    wise_vol = wise['Transaction Volume (GBP)'].sum() * SCALE
    total = app_vol + wise_vol

    by_reason = (wise.groupby('Reason')['Transaction Volume (GBP)'].sum() * SCALE).sort_values(ascending=False)
    limited = by_reason[by_reason.index.isin(LIMITS)].sum()

    missing = (wise[wise['Target Currency'].isin(MISSING)]
               .groupby('Target Currency')['Transaction Volume (GBP)'].sum() * SCALE).sort_values(ascending=False)
           
---------------------------------------
    ok = sent['Transfer status'].eq('Completed') if 'Transfer status' in sent else None
    rel = {}
    if ok is not None:
        rel['success'] = ok.mean()
        rel['under_20s'] = sent.loc[ok, 'Arrival time (seconds)'].dropna().le(20).mean()
        rel['quote_ms'] = app['Quote API response (ms)'].median()

---------------------------------------

    wd = d[d.Channel.eq('Wise direct')]
    wd_users = set(wd['User ID'])
    mca = set(wd.loc[wd['Product used'].eq('Multi-currency Account'), 'User ID'])
    related = set(wd.loc[wd['Product used'].isin(['Multi-currency Account', 'Receive', 'Cards']), 'User ID'])

    fees = sent['Transaction Volume (GBP)'].map(fee)
    return {
        'months': (mon.index[0], mon.index[-1]),
        'checks_first': first['Checked the fee'], 'checks_last': last['Checked the fee'],
        'checks_growth': last['Checked the fee'] / first['Checked the fee'] - 1,
        'wise_users_growth': last['Used Wise directly'] / first['Used Wise directly'] - 1,
        'send_rate': len(quoted & senders) / len(quoted),
        'new_signups': len(new) * SCALE, 'new_senders': len(new_sent) * SCALE,
        'new_rate': len(new_sent) / len(new),
        'app_vol': app_vol, 'wise_vol': wise_vol, 'total_vol': total,
        'wise_share': wise_vol / total,
        'by_reason': by_reason, 'limited': limited, 'limited_share': limited / total,
        'missing': missing,
        'winback_half': by_reason[by_reason.index != 'Account, card or receiving'].sum() * 0.5,
        'reliability': rel,
        'fee_income': fees.sum() * SCALE, 'fee_avg': fees.mean(),
        'small_share': sent['Transaction Volume (GBP)'].le(250).mean(),
        'wd_users': len(wd_users) * SCALE, 'mca_users': len(mca) * SCALE,
        'mca_share': len(mca) / len(wd_users), 'related_users': len(related) * SCALE,
        'monthly': mon,
    }


if __name__ == '__main__':
    s = summary(load())
    for k, v in s.items():
        if k != 'monthly':
            print(k, '=', v if not isinstance(v, float) else round(v, 4))


---------------------------------------

Q4_DEFAULTS = dict(months=36, partners=3, eligible=100000, adoption=5, revenue=2.5, displaced=0.5,
                   service=0.75, build=300000, onboarding=20000, fixed=5000, launch=6, ramp=6,
                   attrition=1.0, activation=3.0)


def project(months, partners, eligible, adoption, revenue, displaced, service, build, onboarding,
            fixed, launch, ramp, attrition, activation):
---------------------------------------
    new_each = partners * eligible * adoption / 100 / ramp
    active = cumul = 0.0
    rows = []
    for month in range(1, months + 1):
        live = month > launch
        new = new_each if live and month <= launch + ramp else 0.0
        active = active * (1 - attrition / 100) + new if live else 0.0
        incremental = active * (revenue - displaced)
        cost = active * service + (fixed if live else 0) + new * activation
        upfront = build + partners * onboarding if month == 1 else 0.0
        cumul += incremental - cost - upfront
        rows.append({'Month': month, 'Active accounts': active, 'Gross revenue (£)': active * revenue,
                     'Revenue Wise would earn anyway (£)': active * displaced,
                     'New Wise revenue (£)': incremental, 'Running total after costs (£)': cumul})
    return pd.DataFrame(rows)


def payback_month(model):
    c = model['Running total after costs (£)']
    for i in range(len(c)):
        if (c.iloc[i:] >= 0).all():
            return int(model.Month.iloc[i])
    return None
