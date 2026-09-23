import io
import json
import threading
import unittest
from unittest.mock import patch, Mock
import server

class Probe(server.Handler):
    def __init__(self, message, session):
        self.path='/api/chat'
        raw=json.dumps({'message':message}).encode()
        self.rfile=io.BytesIO(raw)
        self.headers={'X-CSRF-Token':'test','Content-Length':str(len(raw))}
        self.s=session
    def session(self): return self.s
    def send(self, body, status=200, content_type=None): self.result=(status,body)

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.s={'csrf':'test','cart':{},'offers':{},'history':[],'last_ids':[1],'lock':threading.Lock()}
        self.catalog=server.Catalog();self.catalog.ready=True
        self.catalog.index=[{'id':1,'article':'ABC','name':'Автомат Legrand'}, {'id':2,'article':'DEF','name':'Автомат Schneider'}]
        self.catalog.detail=Mock(side_effect=lambda i:{'id':i,'article':'ABC' if i==1 else 'DEF','quantity':5})
        self.catalog.alternatives=Mock(return_value=[{'id':2,'article':'DEF','quantity':5,'alternative':{'for_article':'ABC'}}])
    def request(self, text):
        with patch.object(server,'catalog',self.catalog),patch.dict(server.os.environ,{'OPENAI_API_KEY':''}):
            h=Probe(text,self.s);h.do_POST()
        self.assertEqual(h.result[0],200)
        return h.result[1]
    def test_minimum_order_returns_policy(self):
        for q in ['Какая минимальная сумма заказа?', 'Минимальная партия заказа?', 'Условия оплаты']:
            r=self.request(q)
            self.assertIn('Общая минимальная сумма',r['answer'])
            self.assertEqual(len(r['sources']),2)
            self.assertEqual(r['products'],[])
        self.catalog.detail.assert_not_called()
    def test_analog_uses_previous_product_and_preserves_original_context(self):
        r=self.request('Есть аналог?')
        self.catalog.detail.assert_called_once_with(1)
        self.catalog.alternatives.assert_called_once()
        self.assertEqual([p['id'] for p in r['products']],[1,2])
        self.assertEqual(self.s['last_ids'],[1])
        self.assertEqual(self.s['cart'],{})
    def test_ambiguous_context_asks_for_article(self):
        self.s['last_ids']=[1,2]
        r=self.request('Есть аналог?')
        self.assertIn('несколько товаров',r['answer'])
        self.catalog.alternatives.assert_not_called()
    def test_no_context_asks_for_product(self):
        self.s['last_ids']=[]
        self.assertIn('Укажите артикул',self.request('Есть аналог?')['answer'])
        self.catalog.alternatives.assert_not_called()
    def test_explicit_article_overrides_previous_context(self):
        self.request('Аналог DEF')
        self.catalog.detail.assert_called_once_with(2)
    def test_delivery_does_not_reuse_previous_product(self):
        self.request('Какая доставка для него?')
        self.catalog.detail.assert_not_called()
        self.assertEqual(self.s['last_ids'],[1])
