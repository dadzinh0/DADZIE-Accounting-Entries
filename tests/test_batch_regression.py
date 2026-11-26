"""Integration tests run with backend dependencies; SQLite and temporary fictional files."""
import os
import sys
import tempfile
import unittest
import uuid
import hashlib
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.getenv('TEST_BACKEND_DIR', str(Path(__file__).resolve().parents[1] / 'backend')))
try:
    import sqlalchemy
    import fastapi
    import fitz
    import pytesseract
    import argon2
except ImportError:
    sqlalchemy = None

@unittest.skipIf(sqlalchemy is None, 'Backend dependencies unavailable')
class BatchRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        environment = patch.dict(os.environ)
        environment.start()
        cls.addClassCleanup(environment.stop)
        os.environ['DATABASE_URL'] = 'sqlite:///' + (Path(cls.temp.name) / 'test.db').as_posix()
        os.environ['SESSION_SECRET'] = 'test-secret-' * 4
        os.environ['UPLOAD_DIR'] = cls.temp.name
        os.environ['FRONTEND_DIR'] = os.getenv('TEST_FRONTEND_DIR', str(Path(__file__).resolve().parents[1] / 'frontend'))
        import main
        cls.main = main
        cls.test_engine = sqlalchemy.create_engine('sqlite:///' + (Path(cls.temp.name) / 'test.db').as_posix())
        cls.engine_patch = patch.object(main, 'engine', cls.test_engine)
        cls.upload_patch = patch.object(main, 'UPLOAD_DIR', Path(cls.temp.name))
        cls.engine_patch.start()
        cls.upload_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.upload_patch.stop()
        cls.engine_patch.stop()
        cls.test_engine.dispose()
        cls.temp.cleanup()

    def setUp(self):
        self.assertEqual(self.main.engine.dialect.name, 'sqlite')
        self.main.Base.metadata.drop_all(self.test_engine)
        self.main.Base.metadata.create_all(self.test_engine)

    def add_batch(self, texts):
        m = self.main; batch = str(uuid.uuid4()); ids = []
        with m.Session(m.engine) as s:
            s.add(m.Batch(id=batch, actor='test'))
            for text in texts:
                item = str(uuid.uuid4()); data = text.encode(); ids.append(item)
                (m.UPLOAD_DIR / item).write_bytes(data)
                s.add(m.BatchItem(id=item, batch_id=batch, name='fiction.pdf', sha256=hashlib.sha256(data).hexdigest(), status='queued'))
            s.commit()
        return batch, ids

    def process(self, ids):
        m = self.main
        with patch.object(m, 'extract_document', side_effect=lambda data: ('application/pdf', m.extract(data.decode()))):
            for item in ids: m.process_batch_item(item)

    def result(self, batch):
        with self.main.Session(self.main.engine) as s: return self.main.get_batch(batch, None, s)

    def invoice(self, n):
        return f'Fournisseur: Fiction {n}\nFacture No: REF-{n}\nDate: 01/11/2026\nDevise: MAD\nHT: 100,00\nTVA: 20,00\nTTC: 120,00'

    def test_five_distinct_and_reporting(self):
        batch, ids = self.add_batch([self.invoice(i) for i in range(5)]); self.process(ids)
        items = self.result(batch)['items']
        self.assertEqual(len(items), 5)
        for item in items:
            self.assertTrue(item['supplier']); self.assertTrue(item['invoice_number']); self.assertEqual(item['amount_ttc'], '120.00')
            self.assertNotIn('duplicate_file', [i['code'] for i in item['issues']])

    def test_duplicates_same_and_earlier_batch_and_reprocess(self):
        m = self.main; batch, ids = self.add_batch([self.invoice(1), self.invoice(1)]); self.process(ids)
        items = {i['id']:i for i in self.result(batch)['items']}
        issue = items[ids[1]]['issues'][0]
        self.assertEqual(issue['duplicate_scope'], 'same_batch'); self.assertEqual(issue['original_document_id'], ids[0])
        other, other_ids = self.add_batch([self.invoice(1)]); self.process(other_ids)
        self.assertEqual(self.result(other)['items'][0]['issues'][0]['duplicate_scope'], 'earlier_upload')
        with m.Session(m.engine) as s:
            new_batch = m.reprocess_batch(batch, type('Account', (), {'username':'test'})(), s)['id']
        with m.Session(m.engine) as s:
            new_ids = list(s.scalars(m.select(m.BatchItem.id).where(m.BatchItem.batch_id == new_batch)))
        self.process(new_ids)
        self.assertEqual(self.result(new_batch)['processed'], 2)
        self.assertTrue(all(x['supplier'] for x in self.result(new_batch)['items']))

    def test_retry_is_not_duplicate_of_itself(self):
        m=self.main; batch, ids=self.add_batch([self.invoice(7)]); self.process(ids)
        with m.Session(m.engine) as s:
            s.get(m.BatchItem, ids[0]).status='queued'; s.commit()
        self.process(ids)
        self.assertNotIn('duplicate_file', [i['code'] for i in self.result(batch)['items'][0]['issues']])
