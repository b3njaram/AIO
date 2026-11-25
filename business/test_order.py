import unittest
from decimal import Decimal as D
from order import calculate
class CostTests(unittest.TestCase):
    def test_us(self):
        v=calculate(*map(D,['500','249','99']),6,*map(D,['12','90','60','20','25','10','3','20']))
        self.assertEqual(v[0],D('809.00'))
        self.assertEqual(v[3],D('79.73'))
        self.assertEqual(v[5],D('915.59'))
    def test_mx_support(self):
        v=calculate(D(0),D(2999),D(1199),12,D(12),D(1000),D(500),D(0),D(0),D(100),D(3),D(20))
        self.assertEqual(v[0],D('3598.50'))
    def test_invalid(self):
        with self.assertRaises(ValueError):
            calculate(D(0),D(1),D(1),6,D(0),D(0),D(0),D(0),D(0),D(0),D(90),D(20))
if __name__=='__main__': unittest.main()
