import threading
import unittest
from unittest.mock import patch
import server

class DemoTests(unittest.TestCase):
    def test_offline_catalog_cart_and_analog_without_network(self):
        with patch.object(server,'DEMO_MODE',True),patch.object(server,'fetch_json',side_effect=AssertionError('Network forbidden')):
            c=server.Catalog();c.load()
            self.assertTrue(c.ready)
            self.assertEqual(len(c.index),3)
            p=c.detail(c.search('310100024_')[0]['id'])
            self.assertIn('демо-снимок',p['checked_at'])
            candidates=c.alternatives(p)
            self.assertEqual(candidates[0]['article'],'010400569_')
            s={'cart':{},'offers':{},'lock':threading.Lock()}
            o=server.propose(s,candidates[0]['id'],2,c)
            server.confirm(s,o['token'],True,c)
            self.assertEqual(server.cart_view(s)['items'][0]['quantity'],2)
            self.assertIsNone(server.model_answer('Hello',[],[]))
