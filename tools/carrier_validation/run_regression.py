"""Run repository tests with empty configuration and outbound network blocked."""
import os,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'DriverAPI'));sys.path.insert(0,str(ROOT/'tests'))
with patch.dict(os.environ,{},clear=True),patch('socket.socket.connect',side_effect=AssertionError('Regression suite prohibits network')):
 suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 sys.exit(0 if result.wasSuccessful() else 1)
