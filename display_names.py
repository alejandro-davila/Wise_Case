"""Reader-facing names; source column names and codes stay unchanged for calculations."""
import re
CURRENCIES={
 'GBP':'British pounds','EUR':'Euros','USD':'United States dollars','CHF':'Swiss francs',
 'INR':'Indian rupees','PKR':'Pakistani rupees','BDT':'Bangladeshi taka','JPY':'Japanese yen',
 'PLN':'Polish zloty','NGN':'Nigerian naira','RON':'Romanian leu','CAD':'Canadian dollars',
 'ZAR':'South African rand','AUD':'Australian dollars','PHP':'Philippine pesos','LKR':'Sri Lankan rupees',
 'THB':'Thai baht','GHS':'Ghanaian cedi','KRW':'South Korean won','CZK':'Czech koruna',
 'COP':'Colombian pesos','ZMW':'Zambian kwacha','UGX':'Ugandan shillings','TZS':'Tanzanian shillings',
 'BWP':'Botswana pula','RUB':'Russian rubles','UYU':'Uruguayan pesos',
 'globalEUR':'Euros sent to a country with another local currency',
 'globalUSD':'United States dollars sent to a country with another local currency',
 'globalGBP':'British pounds sent to a country with another local currency'}

def currency_name(value):
    return CURRENCIES.get(value,value)

def readable_table(frame):
    d=frame.copy()
    for c in ['Source Currency','Target Currency','Category']:
        if c in d.columns: d[c]=d[c].map(currency_name)
    if d.index.name in ['Source Currency','Target Currency']:
        d.index=d.index.map(currency_name)
    d=d.rename(columns={c:str(c).replace('(GBP)','(£)').replace('_GBP',' (£)').replace('User ID','Customer identifier').replace('Transfer ID','Transfer identifier').replace('MCA users','Multi-currency account users') for c in d.columns})
    return d
