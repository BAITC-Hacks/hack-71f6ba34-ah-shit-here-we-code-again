import base64
import io
import unittest
import zipfile
from uploads import validate_upload
from analogs import comparison

class UploadTests(unittest.TestCase):
    def body(self, raw=b'%PDF-1.4\ntest', **kw):
        return dict(filename='test.pdf',data=base64.b64encode(raw).decode(),consent=True,**kw)
    def test_requires_explicit_consent(self):
        b=self.body();b['consent']='yes'
        with self.assertRaises(ValueError): validate_upload(b)
    def test_wrong_signature(self):
        with self.assertRaises(ValueError):validate_upload(self.body(b'not pdf'))
    def test_size_limit(self):
        with self.assertRaises(ValueError):validate_upload(self.body(b'%PDF-'+b'x'*(2*1024*1024)))
    def test_expansion_limit(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('word/document.xml',b'x'*(21*1024*1024))
        b=self.body(stream.getvalue());b['filename']='test.docx'
        with self.assertRaises(ValueError):validate_upload(b)
    def test_legacy_rejected_explicitly(self):
        b=self.body();b['filename']='old.doc'
        with self.assertRaisesRegex(ValueError,'DOC/XLS'):validate_upload(b)

class AnalogTests(unittest.TestCase):
    def setUp(self):
        props={'TIP_USTROYSTVA':'Автомат','KOLICHESTVO_POLYUSOV':'2','NOMINALNYY_TOK':'16 А','NOMINALNOE_NAPRYAZHENIE':'230В','KHARAKTERISTIKA_SRABATYVANIYA':'C'}
        self.a={'id':1,'quantity':0,'properties':props}
        self.b={'id':2,'quantity':3,'properties':dict(props)}
    def test_match_is_qualified_candidate(self):
        self.assertIn('специалист',comparison(self.a,self.b)['caution'])
    def test_wrong_current_rejected(self):
        self.b['properties']['NOMINALNYY_TOK']='25А'
        self.assertIsNone(comparison(self.a,self.b))
    def test_missing_characteristic_rejected(self):
        del self.b['properties']['KHARAKTERISTIKA_SRABATYVANIYA']
        self.assertIsNone(comparison(self.a,self.b))
    def test_conflicting_source_rejected(self):
        self.a['warnings']=['conflict'];self.assertIsNone(comparison(self.a,self.b))
    def test_no_stock_rejected(self):
        self.b['quantity']=0;self.assertIsNone(comparison(self.a,self.b))
