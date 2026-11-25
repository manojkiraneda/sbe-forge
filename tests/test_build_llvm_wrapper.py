"""Check delegation to the pinned LLVM build driver without building LLVM."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

WRAPPER = Path(__file__).resolve().parents[1] / 'scripts/build-llvm.sh'


class BuildWrapperTest(unittest.TestCase):
    def test_arguments_paths_and_exit_status(self):
        with tempfile.TemporaryDirectory(prefix='forge build ') as temporary:
            root = Path(temporary)
            (root / 'scripts').mkdir()
            shutil.copy2(WRAPPER, root / 'scripts/build-llvm.sh')
            driver = root / 'llvm-project/utils/ppe42/build-toolchain.sh'
            driver.parent.mkdir(parents=True)
            driver.write_text('''#!/usr/bin/env python3
import json, os, sys
print(json.dumps([sys.argv[1:], os.environ['SBE_LLVM_BUILD_DIR'], os.environ['SBE_LLVM_INSTALL_DIR']]))
sys.exit(17)
''')
            driver.chmod(0o755)
            env = dict(os.environ)
            env.pop('SBE_LLVM_SOURCE_DIR', None)
            env.pop('SBE_LLVM_BUILD_DIR', None)
            env.pop('SBE_LLVM_INSTALL_DIR', None)
            result = subprocess.run(['bash', str(root / 'scripts/build-llvm.sh'), 'configure',
                                     '-DCMAKE_INSTALL_MESSAGE=NEVER'], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 17)
            self.assertEqual(json.loads(result.stdout), [
                ['configure', '-DCMAKE_INSTALL_MESSAGE=NEVER'],
                str(root / 'build/llvm'), str(root / 'build/toolchain')])


if __name__ == '__main__':
    unittest.main()
