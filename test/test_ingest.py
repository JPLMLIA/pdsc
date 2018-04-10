"""
Functional Test of Ingestion process
"""
import os
import subprocess
from unittest import TestCase
from tempfile import mkdtemp
from shutil import rmtree

from cosmic_test_tools import functional

TEST_DATA = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'data'
)

@functional
class TestIngest(TestCase):

    def setUp(self):
        self.outputdir = mkdtemp()

    def test_ingest(self):
        self.assertTrue(os.path.exists(self.outputdir))
        process = subprocess.Popen([
            'pdsc_ingest',
            os.path.join(TEST_DATA, 'index.lbl'),
            self.outputdir,
            '-c', os.path.join(TEST_DATA, 'test_metadata.yaml'),
            '-e', os.path.join(TEST_DATA, 'test_extension.py')
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdoutdata, stderrdata = process.communicate()
        self.assertEquals(process.poll(), os.EX_OK)

    def tearDown(self):
        rmtree(self.outputdir)
