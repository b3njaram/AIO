#!/usr/bin/env python3
"""Offline costing tool. No personal data, no payment processing; no files written."""
import argparse
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

D=Decimal
MARKETS={'US':('USD',D('249'),D('99')),'MX':('MXN',D('2999'),D('1199'))}
def amount(s):
    try: v=D(s)
    except InvalidOperation: raise argparse.ArgumentTypeError('Use a decimal amount')
    if not v.is_finite() or v<0: raise argparse.ArgumentTypeError('Use a finite nonnegative amount')
    return v
def cash(v): return v.quantize(D('.01'),rounding=ROUND_HALF_UP)
def calculate(hardware, setup, renewal, months, markup, labor, support, shipping, warranty, overhead, fee_pct, floor):
    if months not in (6,12) or fee_pct>=100 or floor>=100: raise ValueError('Invalid support or percentages')
    price=cash(hardware*(1+markup/100)+setup+(renewal/2 if months==12 else 0))
    cost=hardware+labor+support+shipping+warranty+overhead
    fees=cash(price*fee_pct/100)
    contribution=cash(price-cost-fees)
    margin=(contribution/price*100) if price else D(0)
    denominator=1-(fee_pct+floor)/100
    if denominator<=0: raise ValueError('Fee plus target margin must be below 100%')
    minimum=(cost/denominator).quantize(D('.01'),rounding='ROUND_CEILING')
    return price,cash(cost),fees,contribution,cash(margin),minimum
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--market',choices=MARKETS,required=True)
    p.add_argument('--months',type=int,choices=(6,12),default=6)
    for k in ('hardware','labor','support','shipping','warranty','overhead'):
        p.add_argument('--'+k,type=amount,required=True,help='Actual estimated cost in local currency; explicitly use 0 if none')
    p.add_argument('--markup',type=amount,default=D(12))
    p.add_argument('--fee-pct',type=amount,default=D(0),help='Default zero for cash-only sales; other cash handling expenses belong in overhead')
    p.add_argument('--floor',type=amount,default=D(20),help='Minimum contribution margin percentage (proposed)')
    p.add_argument('--setup',type=amount,help='Override proposed regional setup charge')
    p.add_argument('--renewal',type=amount,help='Override proposed annual renewal rate')
    a=p.parse_args()
    currency,setup,renewal=MARKETS[a.market]
    try: price,cost,fees,profit,margin,minimum=calculate(a.hardware,a.setup if a.setup is not None else setup,a.renewal if a.renewal is not None else renewal,a.months,a.markup,a.labor,a.support,a.shipping,a.warranty,a.overhead,a.fee_pct,a.floor)
    except ValueError as e: p.error(str(e))
    for k,v in [('Proposed selling price (pre-tax)',price),('Direct cost before payment fee',cost),('Payment fee allowance (cash default zero)',fees),('Estimated contribution',profit),('Minimum price for margin floor',minimum)]:
        print(f'{k}: {currency} {v:,.2f}')
    print(f'Contribution margin: {margin:.2f}%')
    print('REVIEW REQUIRED: below target margin' if margin<a.floor else 'Margin target met (subject to verified inputs)')
    print('Not a final invoice; verify tax, legal terms, hardware, travel and support costs.')
if __name__=='__main__': main()
