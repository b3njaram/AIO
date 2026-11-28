import unittest
from decimal import Decimal
from search import mark_ambiguous_ebay_prices, CAT, money_label, row, screen, choose, supplier_for, safe_url
class TestSourcing(unittest.TestCase):
    def setUp(self):
        self.parts=CAT['profiles']['family']['parts']
        self.drive=self.parts[1]
    def test_different_prices_on_one_listing_require_review(self):
        url='https://www.ebay.com/itm/123456789012'
        offers=[row('US',self.drive,'eBay','WD40EFPX',url+query,Decimal(price),condition='New')
                for price,query in [('80','?var=1'),('130','?var=2')]]
        mark_ambiguous_ebay_prices(offers)
        self.assertEqual([screen(self.drive,x,'family')[0] for x in offers],['review','review'])
    def test_prices(self):
        self.assertEqual(money_label('$249.99','US',249.99),Decimal('249.99'))
        self.assertEqual(money_label('MXN $2,999.00','MX'),Decimal('2999.00'))
        self.assertIsNone(money_label('USD $50','MX',50))
        self.assertIsNone(money_label('From $10','US',10))
        self.assertIsNone(money_label('$20 - $60','US',20))
    def test_condition(self):
        def check(title,condition='',variant=False):
            return screen(self.drive,row('US',self.drive,'eBay',title,'https://www.ebay.com/itm/12345',Decimal(50),condition=condition,variant=variant),'family')[0]
        self.assertEqual(check('WD40EFPX 4TB NEW','New'),'candidate')
        self.assertEqual(check('WD40EFPX 4TB refurbished'),'reject')
        self.assertEqual(check('WD40EFPX 4TB'),'review')
        self.assertEqual(check('WD40EFPX enclosure'),'reject')
        self.assertEqual(check('WD40EFPX NEW',variant=True),'review')
        self.assertEqual(check('FOR Western Digital Red Plus WD40EFPX 4TB','New'),'review')
        self.assertEqual(check('1PC FOR Western Digital Red Plus WD40EFPX 4TB','New'),'review')
        self.assertEqual(check('WD40EFPX NEW','New other (see details)'),'review')
        self.assertEqual(check('WD40EFPX NEW'),'review')
    def test_towers(self):
        part=self.parts[0]
        self.assertEqual(len(part['queries']),3)
        self.assertTrue(all(sum(str(m) in q for m in (7060,7070,7080))==1 for q in part['queries']))
        def check(title):return screen(part,row('US',part,'eBay',title,'https://www.ebay.com/itm/123456789',Decimal(150)),'family')[0]
        self.assertEqual(check('Dell OptiPlex 7060 MT i5-8500 16GB RAM 256GB SSD'),'candidate')
        self.assertEqual(check('Dell OptiPlex 7070 Tower i5 16G 500G SSD'),'candidate')
        self.assertEqual(check('Dell OptiPlex 7080 SFF i5 16GB 256GB SSD'),'reject')
        self.assertEqual(check('Dell OptiPlex 7060 MT i5 8GB 256GB SSD'),'review')
    def test_supplier(self):
        self.assertEqual(supplier_for('US','B&H Photo Video'),'B&H')
        self.assertIsNone(supplier_for('US','unknown','https://amazon.com.evil.test/'))
        self.assertEqual(safe_url('https://a:b@example.com/'),'')
    def test_bom(self):
        self.assertEqual(choose(self.parts,[{'part':'computer','landed':'100'}]),[])
        options=[{'part':'computer','landed':'100'},{'part':'hdd','landed':'200'},{'part':'hdd','landed':'160'}]
        self.assertEqual(choose(self.parts,options)[1]['landed'],'160')
if __name__=='__main__':unittest.main()
