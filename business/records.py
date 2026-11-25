#!/usr/bin/env python3
"""Private, local-only cash ledger. No customer names, passwords, card data or network."""
import argparse
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import re
import sqlite3
import sys
from datetime import date

REPO = Path(__file__).resolve().parents[1]
KINDS = ('deposit', 'balance', 'refund')
def cents(text):
    try:
        d = Decimal(text)
        if not d.is_finite() or d <= 0 or d > Decimal('999999999') or d != d.quantize(Decimal('.01')):
            raise ValueError
        return int(d*100)
    except (InvalidOperation, ValueError, OverflowError):
        raise argparse.ArgumentTypeError('Enter a positive amount with at most two decimal places')
def ident(text):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', text):
        raise argparse.ArgumentTypeError('Use an ID with letters, numbers, hyphen or underscore')
    return text
def valid_date(text):
    try: return date.fromisoformat(text).isoformat()
    except ValueError: raise argparse.ArgumentTypeError('Use YYYY-MM-DD')
def open_db(path):
    path=Path(path).expanduser().resolve()
    if path==REPO or REPO in path.parents:
        raise ValueError('Keep private records outside the public Git repository')
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if not path.exists():
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        os.close(fd)
    if path.stat().st_mode & 0o077:
        raise ValueError('Ledger must have private permissions (chmod 600 on Linux)')
    db=sqlite3.connect(path)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript("""
    CREATE TABLE IF NOT EXISTS orders(
      id TEXT PRIMARY KEY, market TEXT NOT NULL CHECK(market IN ('US','MX')),
      total INTEGER NOT NULL CHECK(total>0), opened TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS cash(
      id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id),
      kind TEXT NOT NULL CHECK(kind IN ('deposit','balance','refund')),
      amount INTEGER NOT NULL CHECK(amount>0), recorded TEXT NOT NULL);
    """)
    return db
def balance(db,order):
    row=db.execute('SELECT market,total FROM orders WHERE id=?',(order,)).fetchone()
    if not row: raise ValueError('Unknown order ID')
    paid=db.execute("SELECT COALESCE(SUM(CASE kind WHEN 'refund' THEN -amount ELSE amount END),0) FROM cash WHERE order_id=?",(order,)).fetchone()[0]
    return row[0],row[1],paid
def add_payment(db,txn,order,kind,amount,when):
    if kind not in KINDS or amount<=0: raise ValueError('Invalid cash transaction')
    # Serialize concurrent writers so limits are checked on the latest balance.
    with db:
        db.execute('BEGIN IMMEDIATE')
        market,total,paid=balance(db,order)
        if kind=='refund' and amount>paid: raise ValueError('Refund exceeds net cash received')
        if kind!='refund' and paid+amount>total: raise ValueError('Cash applied exceeds agreed order total; record change separately on the receipt')
        db.execute('INSERT INTO cash VALUES(?,?,?,?,?)',(txn,order,kind,amount,when))
def money(n): return f'{Decimal(n)/100:,.2f}'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='~/.local/share/jobbi-business/cash.sqlite3')
    s=p.add_subparsers(dest='command',required=True)
    o=s.add_parser('open');o.add_argument('order',type=ident);o.add_argument('market',choices=('US','MX'));o.add_argument('total',type=cents);o.add_argument('--date',type=valid_date,default=date.today().isoformat())
    a=s.add_parser('record');a.add_argument('transaction',type=ident);a.add_argument('order',type=ident);a.add_argument('kind',choices=KINDS);a.add_argument('amount',type=cents);a.add_argument('--date',type=valid_date,default=date.today().isoformat())
    a=s.add_parser('show');a.add_argument('order',type=ident)
    s.add_parser('totals')
    args=p.parse_args()
    os.umask(0o077)
    try:
        db=open_db(args.db)
        with db:
            if args.command=='open':
                db.execute('INSERT INTO orders VALUES(?,?,?,?)',(args.order,args.market,args.total,args.date))
                print('Order recorded; no cash recorded yet')
            elif args.command=='record':
                add_payment(db,args.transaction,args.order,args.kind,args.amount,args.date)
                print('Cash transaction recorded; issue the applicable receipt')
            elif args.command=='show':
                market,total,paid=balance(db,args.order)
                cur='USD' if market=='US' else 'MXN'
                print(f'{args.order}: {cur} agreed {money(total)}, net received {money(paid)}, unpaid against original total {money(total-paid)}')
                for row in db.execute('SELECT id,kind,amount,recorded FROM cash WHERE order_id=? ORDER BY recorded,rowid',(args.order,)):
                    print(row[3],row[0],row[1],cur,money(row[2]))
                print('Refunds do not automatically cancel or revise the original order. Record cancellation/amended scope separately.')
            else:
                for market,cur in [('US','USD'),('MX','MXN')]:
                    rows=db.execute("SELECT c.kind,SUM(c.amount) FROM cash c JOIN orders o ON c.order_id=o.id WHERE o.market=? GROUP BY c.kind",(market,)).fetchall()
                    v=dict(rows)
                    received=v.get('deposit',0)+v.get('balance',0)
                    refunds=v.get('refund',0)
                    print(f'{cur}: received {money(received)}, refunded {money(refunds)}, net {money(received-refunds)}')
        db.close()
    except (ValueError, OSError, sqlite3.Error) as e:
        p.exit(1,'Error: '+str(e)+'\n')
if __name__=='__main__': main()
