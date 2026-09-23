import threading
import unittest
from server import UserError, propose, confirm

class Source:
    def __init__(self): self.price=100; self.amount=5
    def detail(self, _): return {'id':1,'price':self.price,'quantity':self.amount,'properties':{'KRATNOST_MIN':'1'}}

def session(): return {'cart':{},'offers':{},'lock':threading.Lock()}

class CartTests(unittest.TestCase):
    def setUp(self): self.s=session(); self.api=Source()
    def test_proposal_does_not_change_cart(self):
        propose(self.s,1,2,self.api);self.assertEqual(self.s['cart'],{})
    def test_explicit_confirmation_required(self):
        o=propose(self.s,1,2,self.api)
        with self.assertRaises(UserError): confirm(self.s,o['token'],'true',self.api)
        self.assertEqual(self.s['cart'],{})
    def test_confirmation_single_use(self):
        o=propose(self.s,1,2,self.api)
        confirm(self.s,o['token'],True,self.api)
        with self.assertRaises(UserError):confirm(self.s,o['token'],True,self.api)
        self.assertEqual(self.s['cart']['1']['quantity'],2)
    def test_stock_rechecked(self):
        o=propose(self.s,1,3,self.api); self.api.amount=1
        with self.assertRaises(UserError):confirm(self.s,o['token'],True,self.api)
        self.assertEqual(self.s['cart'],{})
    def test_existing_cart_counts_against_stock(self):
        o=propose(self.s,1,4,self.api); confirm(self.s,o['token'],True,self.api)
        with self.assertRaises(UserError):propose(self.s,1,2,self.api)
    def test_price_change_requires_new_offer(self):
        o=propose(self.s,1,1,self.api);self.api.price=200
        with self.assertRaises(UserError):confirm(self.s,o['token'],True,self.api)
        self.assertEqual(self.s['cart'],{})
    def test_cross_session_token_rejected(self):
        o=propose(self.s,1,2,self.api)
        with self.assertRaises(UserError):confirm(session(),o['token'],True,self.api)
    def test_bad_amounts(self):
        for n in [-1,0,True,'2',float('nan'),float('inf'),1.5]:
            with self.assertRaises(UserError):propose(self.s,1,n,self.api)
    def test_expired_offer(self):
        o=propose(self.s,1,1,self.api);o['expires']=0
        with self.assertRaises(UserError):confirm(self.s,o['token'],True,self.api)

if __name__=='__main__':unittest.main()
