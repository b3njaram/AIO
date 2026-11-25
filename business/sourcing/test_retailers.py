import unittest,json
from retailers import products,links
from decimal import Decimal
class RetailerTests(unittest.TestCase):
    def test_product(self):
        data={'@type':'Product','name':'WD40EFPX','url':'https://pcel.com/product','offers':{'@type':'Offer','price':'100','priceCurrency':'MXN','availability':'https://schema.org/InStock','itemCondition':'https://schema.org/NewCondition'}}
        markup='<script type="application/ld+json">'+json.dumps(data)+'</script>'
        self.assertEqual(products(markup,'https://pcel.com/search','pcel.com','MXN')[0]['price'],Decimal(100))
        self.assertEqual(products(markup,'https://pcel.com/search','pcel.com','USD'),[])
        data['url']='https://evil.example/product'
        self.assertEqual(products('<script type="application/ld+json">'+json.dumps(data)+'</script>','https://pcel.com/search','pcel.com','MXN'),[])
    def test_links(self):
        self.assertIn('amazon.com.mx',links('MX','Amazon Mexico','WD40EFPX','amazon.com.mx')[0])
if __name__=='__main__':unittest.main()
