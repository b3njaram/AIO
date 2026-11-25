import tempfile, unittest
from pathlib import Path
from records import open_db, add_payment, balance, cents
class RecordTests(unittest.TestCase):
    def test_cash_and_refund(self):
        with tempfile.TemporaryDirectory() as d:
            db=open_db(Path(d)/'test.sqlite3')
            with db: db.execute("INSERT INTO orders VALUES('x','US',10000,'2026-11-24')")
            add_payment(db,'a','x','deposit',4000,'2026-11-24')
            add_payment(db,'b','x','balance',6000,'2026-11-24')
            with self.assertRaises(ValueError): add_payment(db,'c','x','balance',1,'2026-11-24')
            with self.assertRaises(ValueError): add_payment(db,'c','x','refund',10001,'2026-11-24')
            add_payment(db,'c','x','refund',1000,'2026-11-24')
            self.assertEqual(balance(db,'x'),('US',10000,9000))
            db.close()
    def test_amount(self):
        self.assertEqual(cents('123.45'),12345)
        for v in ('NaN','Infinity','0','-1','0.001'):
            with self.assertRaises(Exception): cents(v)
if __name__=='__main__': unittest.main()
