import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, os.getenv('TEST_BACKEND_DIR', str(Path(__file__).resolve().parents[1] / 'backend')))
try:
    from main import batch_name
except ImportError:
    batch_name = None

@unittest.skipIf(batch_name is None, 'Backend dependencies unavailable')
class BatchNameTests(unittest.TestCase):
    def test_sequence_and_morocco_date(self):
        batch = SimpleNamespace(created_at=datetime(2026, 11, 21, 0, 22, tzinfo=timezone.utc))
        self.assertEqual(batch_name(batch, 3), 'PHI-INV-B3-21-11-2026')

if __name__ == '__main__': unittest.main()
