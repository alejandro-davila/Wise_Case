"""Animated pictures for Questions 2-4, in the same style as the Question 1 page."""
import html
import streamlit as st

CSS = """<style>
.an-row{display:flex;gap:14px;justify-content:center;align-items:stretch;flex-wrap:wrap;margin:6px 0}
.an-panel{flex:1 1 0;min-width:190px;max-width:320px;border:1px solid rgba(140,150,170,.35);border-radius:14px;padding:12px 10px 10px;display:flex;flex-direction:column;align-items:center}
.an-title{font-size:12px;font-weight:800;letter-spacing:.04em;margin-bottom:8px;text-align:center}
.an-title b{display:inline-flex;width:18px;height:18px;border-radius:50%;background:#9fe870;color:#163300;align-items:center;justify-content:center;font-size:10px;margin-right:5px}
.an-cap{font-size:11.5px;opacity:.7;text-align:center;margin-top:8px;min-height:2.8em}
.an-phone{width:150px;height:250px;background:#0e0f14;border-radius:24px;padding:7px;box-sizing:border-box;box-shadow:0 10px 22px rgba(0,0,0,.22)}
.an-sc{background:#f7f8f3;border-radius:18px;height:100%;color:#163300;position:relative;overflow:hidden}
.an-nt{width:50px;height:12px;background:#0e0f14;border-radius:0 0 9px 9px;margin:0 auto 6px}
.an-app{font-size:9px;color:#666;text-align:center}
.an-box{margin:6px 9px;background:#fff;border-radius:10px;padding:6px 8px;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:9px;color:#6b7262}
.an-box b{display:block;font-size:15px;color:#163300;white-space:nowrap}
.an-fee{margin:6px 9px;border-radius:10px;padding:6px 8px;background:#e9f8dc;font-size:9px;color:#335;animation:anGlow 2.6s infinite}
.an-fee b{display:block;font-size:17px;color:#163300;animation:anPop 2.6s infinite}
.an-badge{display:inline-block;margin:4px auto 0;font-size:9.5px;font-weight:900;border-radius:999px;padding:3px 8px;background:#163300;color:#9fe870}
.an-badge.min{background:#f2c94c;color:#3a2a00}.an-badge.cap{background:#56c2c9;color:#002c30}
.an-btn{position:absolute;left:10px;right:10px;bottom:12px;background:#9fe870;color:#163300;text-align:center;font-weight:900;font-size:11px;padding:8px;border-radius:999px;animation:anPulse 1.8s infinite}
.an-gate{position:relative;width:100%;max-width:640px;height:170px;margin:0 auto}
.an-door{position:absolute;right:0;top:18px;width:120px;height:90px;border-radius:14px;background:#163300;color:#9fe870;font-weight:900;font-size:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.an-exit{position:absolute;right:0;bottom:0;width:120px;height:40px;border-radius:12px;background:#f2994a;color:#3a1d00;font-weight:900;font-size:10.5px;display:flex;align-items:center;justify-content:center;text-align:center}
.an-fee-sign{position:absolute;left:44%;top:0;transform:translateX(-50%);background:#f2c94c;color:#3a2a00;font-size:10.5px;font-weight:900;border-radius:8px;padding:4px 9px}
.an-person{position:absolute;left:0;top:48px;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;background:#70d69b;opacity:0;animation:anWalkIn 5s linear infinite}
.an-person.out{background:#f2a65a;animation-name:anWalkOut}
.an-wallet{margin:4px 9px;background:#fff;border-radius:10px;padding:6px 8px;display:flex;justify-content:space-between;align-items:center;font-size:12px;font-weight:800;box-shadow:0 1px 3px rgba(0,0,0,.08);opacity:0;animation:anSlide 5s infinite}
.an-wallet.w2{animation-delay:.4s}.an-wallet.w3{animation-delay:.8s}
.an-toast{position:absolute;left:10px;right:10px;bottom:14px;background:#163300;color:#9fe870;border-radius:10px;padding:7px;text-align:center;font-size:11px;font-weight:900;opacity:0;animation:anToast 5s infinite}
.an-arrive{font-size:26px;text-align:center;margin-top:14px;animation:anDrop 2.4s ease-in infinite}
.an-card{width:120px;height:76px;margin:30px auto 8px;border-radius:12px;background:linear-gradient(135deg,#163300,#2f7d00);color:#9fe870;padding:9px;box-sizing:border-box;font-size:10px;font-weight:800;position:relative;animation:anTap 3s infinite}
.an-card i{position:absolute;left:10px;bottom:9px;width:22px;height:16px;border-radius:3px;background:#f2c94c}
.an-terminal{width:90px;height:56px;margin:0 auto;border-radius:10px;background:#1d1d28;color:#9fe870;font-size:16px;font-weight:900;display:flex;align-items:center;justify-content:center}
.an-terminal span{opacity:0;animation:anOk 3s infinite}
.an-grid{display:grid;grid-template-columns:repeat(10,26px);gap:7px;justify-content:center;margin:6px 0}
.an-dot{width:26px;height:26px;border-radius:50%;background:#e4e8df;display:flex;align-items:center;justify-content:center;font-size:13px}
.an-dot.on{background:#70d69b;animation:anFillDot 4s infinite}
.an-road{position:relative;width:100%;max-width:820px;margin:8px auto 0;height:120px}
.an-line{position:absolute;left:6%;right:6%;top:34px;border-top:3px dashed rgba(140,150,170,.6)}
.an-mile{position:absolute;top:12px;width:25%;text-align:center;transform:translateX(-50%)}
.an-mile .ic{width:46px;height:46px;border-radius:50%;margin:0 auto;background:#f7f8f3;border:3px solid #9fe870;display:flex;align-items:center;justify-content:center;font-size:21px;animation:anMile 8s infinite}
.an-mile .nm{font-size:12px;font-weight:900;margin-top:6px}.an-mile .tx{font-size:10.5px;opacity:.7;margin-top:2px}
.an-mark{position:absolute;top:22px;left:6%;width:24px;height:24px;border-radius:50%;background:#9fe870;box-shadow:0 0 0 5px rgba(159,232,112,.35);animation:anMove 8s ease-in-out infinite;z-index:2}
.an-chart{width:100%;max-width:820px;margin:0 auto;display:block}
.an-rev{stroke-dasharray:900;stroke-dashoffset:900;animation:anDraw 8s ease-out infinite}
@keyframes anGlow{0%,100%{background:#e9f8dc}50%{background:#cdf0b0}}
@keyframes anPop{0%,100%{transform:scale(1)}45%{transform:scale(1.12)}}
@keyframes anPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.04);box-shadow:0 0 0 6px rgba(159,232,112,.35)}}
@keyframes anWalkIn{0%{left:0;opacity:0}8%{opacity:1}70%{left:calc(100% - 100px);opacity:1}78%,100%{left:calc(100% - 70px);opacity:0}}
@keyframes anWalkOut{0%{left:0;top:48px;opacity:0}8%{opacity:1}40%{left:44%;top:48px}70%{left:calc(100% - 100px);top:118px;opacity:1}78%,100%{left:calc(100% - 70px);top:126px;opacity:0}}
@keyframes anSlide{0%,5%{opacity:0;transform:translateX(-14px)}15%,90%{opacity:1;transform:none}100%{opacity:0}}
@keyframes anToast{0%,45%{opacity:0;transform:translateY(10px)}55%,90%{opacity:1;transform:none}100%{opacity:0}}
@keyframes anDrop{0%{transform:translateY(-14px);opacity:0}20%{opacity:1}60%,100%{transform:translateY(10px);opacity:1}}
@keyframes anTap{0%,30%,100%{transform:translateY(0) rotate(-6deg)}45%,60%{transform:translateY(22px) rotate(0)}}
@keyframes anOk{0%,45%{opacity:0}55%,90%{opacity:1}100%{opacity:0}}
@keyframes anFillDot{0%{transform:scale(.4);opacity:.2}15%,90%{transform:scale(1);opacity:1}100%{opacity:.2}}
@keyframes anMove{0%,6%{left:6%}25%,31%{left:calc(6% + 29.3%)}50%,56%{left:calc(6% + 58.6%)}75%,100%{left:calc(94% - 24px)}}
@keyframes anMile{0%,100%{transform:scale(1)}10%{transform:scale(1.15)}}
@keyframes anDraw{0%{stroke-dashoffset:900}70%,100%{stroke-dashoffset:0}}
</style>"""


def show(markup):
    st.markdown(CSS + markup, unsafe_allow_html=True)


def _fee(amount, rate, minimum, cap):
    raw = amount * rate / 100
    fee = min(max(raw, minimum), cap)
    rule = ('min', f'Minimum £{minimum:,.0f} applies') if raw < minimum else (('cap', f'Cap £{cap:,.0f} applies') if raw > cap else ('', f'{rate:g}% of the amount'))
    return fee, rule


def fee_phones(rate, minimum, cap):
    """Three phones: small, medium and large transfers with the live fee settings."""
    panels = []
    for i, amount in enumerate([50, 500, 10000], 1):
        fee, (kind, rule) = _fee(amount, rate, minimum, cap)
        share = fee / amount * 100 if amount else 0
        panels.append(
            f'<div class="an-panel"><div class="an-title"><b>{i}</b>{["Small", "Medium", "Large"][i-1]} transfer</div>'
            '<div class="an-phone"><div class="an-sc"><div class="an-nt"></div><div class="an-app">PartnerBank</div>'
            f'<div class="an-box">You send<b>£{amount:,}</b></div>'
            f'<div class="an-fee">Convenience fee<b>£{fee:,.2f}</b></div>'
            f'<div style="text-align:center"><span class="an-badge {kind}">{html.escape(rule)}</span></div>'
            '<div class="an-btn">Send</div></div></div>'
            f'<div class="an-cap">The fee is {share:.2f}% of what this customer sends.</div></div>')
    show('<div class="an-row">' + ''.join(panels) + '</div>')


def fee_gate(decline):
    """Ten customers walk to the app; the assumed share turns away at the fee."""
    leaving = round(decline / 10)
    order = [3, 7, 1, 5, 9, 0, 2, 4, 6, 8][:leaving]
    people = ''.join(f'<div class="an-person{" out" if i in order else ""}" style="animation-delay:{i*0.5:.1f}s">👤</div>' for i in range(10))
    show('<div class="an-gate"><div class="an-fee-sign">💷 Convenience fee</div>' + people +
         f'<div class="an-door">✅ Sends in the<br>PartnerBank app<br><span style="font-size:18px">{10-leaving}/10</span></div>'
         f'<div class="an-exit">↘ Goes elsewhere · {leaving}/10</div></div>')


def account_panels():
    """What a multi-currency account lets a customer do, in three equal panels."""
    hold = ('<div class="an-panel"><div class="an-title"><b>1</b>Hold balances</div>'
            '<div class="an-phone"><div class="an-sc"><div class="an-nt"></div><div class="an-app">PartnerBank account</div>'
            '<div class="an-wallet"><span>🇬🇧 GBP</span><span>£1,200</span></div>'
            '<div class="an-wallet w2"><span>🇪🇺 EUR</span><span>€800</span></div>'
            '<div class="an-wallet w3"><span>🇺🇸 USD</span><span>$500</span></div>'
            '<div class="an-toast">+ Convert in seconds</div></div></div>'
            '<div class="an-cap">Keep several currencies in one place.</div></div>')
    receive = ('<div class="an-panel"><div class="an-title"><b>2</b>Receive money</div>'
               '<div class="an-phone"><div class="an-sc"><div class="an-nt"></div><div class="an-app">PartnerBank account</div>'
               '<div class="an-arrive">💶</div>'
               '<div class="an-box" style="text-align:center">Euro account details<b>DE•• •••• 4821</b></div>'
               '<div class="an-toast">+€250 received from a client</div></div></div>'
               '<div class="an-cap">Get paid in another currency like a local.</div></div>')
    spend = ('<div class="an-panel"><div class="an-title"><b>3</b>Spend with a card</div>'
             '<div class="an-phone"><div class="an-sc"><div class="an-nt"></div><div class="an-app">Travelling in 🇪🇸</div>'
             '<div class="an-card">PartnerBank<br>debit card<i></i></div>'
             '<div class="an-terminal"><span>€24 ✓</span></div></div></div>'
             '<div class="an-cap">Pay abroad from the right balance.</div></div>')
    show('<div class="an-row">' + hold + receive + spend + '</div>')


def adopter_grid(base, adoption):
    """Twenty dots: the share expected to adopt lights up green."""
    on = round(adoption / 5)
    dots = ''.join(f'<div class="an-dot{" on" if i < on else ""}" style="animation-delay:{i*0.12:.2f}s">{"👤" if i < on else ""}</div>' for i in range(20))
    show(f'<div class="an-grid">{dots}</div><div class="an-cap">Each dot is 5% of the {base:,} personal customers already using related products. Green = expected to adopt.</div>')


def investment_road():
    """Build → pilot → launch → scale, with revenue drawing past break-even."""
    miles = [('🛠️', 'Build', 'Product and compliance'), ('🧪', 'Pilot', 'One bank, test pricing'),
             ('🚀', 'Launch', 'More partners go live'), ('📈', 'Scale', 'Revenue compounds')]
    items = ''.join(f'<div class="an-mile" style="left:{6+i*29.33:.2f}%"><div class="ic" style="animation-delay:{i*2}s">{ic}</div>'
                    f'<div class="nm">{nm}</div><div class="tx">{tx}</div></div>' for i, (ic, nm, tx) in enumerate(miles))
    chart = ('<svg class="an-chart" viewBox="0 0 820 170" preserveAspectRatio="none" role="img" aria-label="Illustrative cumulative revenue curve crossing break-even">'
             '<line x1="40" y1="95" x2="800" y2="95" stroke="#8a93b0" stroke-dasharray="6 6" stroke-width="1.5"/>'
             '<text x="800" y="88" text-anchor="end" font-size="12" fill="#8a93b0">Break-even</text>'
             '<path class="an-rev" d="M40,120 C140,150 230,150 300,125 S470,70 560,55 S720,20 800,12" fill="none" stroke="#9fe870" stroke-width="5" stroke-linecap="round"/>'
             '<text x="44" y="160" font-size="12" fill="#8a93b0">Upfront investment</text>'
             '<text x="800" y="40" text-anchor="end" font-size="12" font-weight="700" fill="#4f9a1f">Revenue (north star) ↑</text></svg>')
    show(f'<div class="an-road"><div class="an-line"></div><div class="an-mark"></div>{items}</div>{chart}'
         '<div class="an-cap">Illustrative shape only. The model below sets the real numbers.</div>')
