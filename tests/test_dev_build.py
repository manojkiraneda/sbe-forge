"""Test the real development entry point with recording build/container tools."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DevelopmentBuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='forge dev ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.forge = self.root / 'forge checkout'
        (self.forge / 'scripts').mkdir(parents=True)
        for name in ('dev.sh', 'ci.sh', 'build-llvm.sh'):
            shutil.copy2(ROOT / 'scripts' / name, self.forge / 'scripts' / name)
        shutil.copy2(ROOT / 'Dockerfile', self.forge / 'Dockerfile')
        self.source = self.root / 'candidate llvm'
        driver = self.source / 'utils/ppe42/build-toolchain.sh'
        driver.parent.mkdir(parents=True)
        body = '''import json, os, sys
with open(os.environ['RECORD'], 'a') as log:
    log.write(json.dumps({'kind': KIND, 'args': sys.argv[1:],
                          'source': os.environ.get('SBE_LLVM_SOURCE_DIR'),
                          'build': os.environ.get('SBE_LLVM_BUILD_DIR'),
                          'install': os.environ.get('SBE_LLVM_INSTALL_DIR')}) + '\\n')
sys.exit(int(os.environ.get('FAIL_CODE', '0')) if KIND == 'driver' else 0)
'''
        self.program(driver, "KIND='driver'\n" + body)
        self.program(self.forge / 'scripts/test-firmware.sh', "KIND='firmware'\n" + body)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.program(self.bin / 'git', "raise SystemExit('Candidate checkout must not be updated')\n")
        self.program(self.bin / 'docker', '''import json, os, pathlib, sys
args = sys.argv[1:]
if args[0] == 'build':
    driver = pathlib.Path(args[-1]) / 'llvm-project/utils/ppe42/build-toolchain.sh'
    assert driver.read_text() == pathlib.Path(os.environ['EXPECTED_DRIVER']).read_text()
with open(os.environ['RECORD'], 'a') as log:
    log.write(json.dumps({'kind': 'docker', 'args': args}) + '\\n')
''')
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith('SBE_LLVM_') and k not in ('BUILD_DIR', 'PACKAGE_DIR')}
        self.env.update(PATH=str(self.bin) + ':' + os.environ['PATH'],
                        RECORD=str(self.root / 'record'), EXPECTED_DRIVER=str(driver))

    def program(self, path, code):
        path.write_text('#!' + sys.executable + '\n' + code)
        path.chmod(0o755)

    def run_dev(self, *args, expect=0, extra_env=None, script='dev.sh'):
        result = subprocess.run(['bash', str(self.forge / 'scripts' / script), *args],
                                cwd=self.root, env=dict(self.env, **(extra_env or {})),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        record = self.root / 'record'
        return [json.loads(line) for line in record.read_text().splitlines()] if record.exists() else []

    def native(self, *args, **kwargs):
        return self.run_dev('--native', '--llvm-source', str(self.source), *args, **kwargs)

    def test_all_runs_compiler_then_firmware(self):
        events = self.native('--', '-DTEST_FLAG=a b')
        self.assertEqual([e['kind'] for e in events], ['driver', 'firmware'])
        self.assertEqual(events[0]['args'], ['all', '-DTEST_FLAG=a b'])
        self.assertEqual(events[1]['install'], str(self.forge / 'build/toolchain'))

    def test_each_compiler_phase_uses_candidate_without_submodule_update(self):
        for phase in ('deps', 'prepare', 'configure', 'build-deps', 'build', 'runtime', 'stage', 'check', 'archive'):
            with self.subTest(phase=phase):
                events = self.native('--phase', phase)
                self.assertEqual(events[-1]['args'], [phase])
                self.assertEqual(events[-1]['source'], str(self.source))

    def test_firmware_does_not_require_llvm_sources(self):
        self.assertEqual([e['kind'] for e in self.run_dev('--native', '--phase', 'firmware')], ['firmware'])

    def test_ci_paths_and_explicit_overrides(self):
        events = self.native('--phase', 'configure', extra_env={'BUILD_DIR': 'cache/compiler', 'PACKAGE_DIR': 'package/tools'})
        self.assertEqual(events[0]['build'], str(self.root / 'cache/compiler'))
        self.assertEqual(events[0]['install'], str(self.root / 'package/tools'))
        events = self.native('--phase', 'check', '--install-dir', 'my tools')
        self.assertEqual(events[-1]['install'], str(self.root / 'my tools'))

    def test_parent_path_override_is_normalized_before_mounting(self):
        events = self.run_dev('--llvm-source', str(self.source), '--phase', 'check',
                              '--build-dir', 'forge checkout/../outside build')
        run = events[-1]['args']
        expected = str(self.root / 'outside build')
        self.assertIn(expected + ':' + expected + ':Z', run)
        self.assertEqual(run[run.index('--build-dir') + 1], expected)

    def test_failure_stops_before_firmware(self):
        events = self.native(extra_env={'FAIL_CODE': '19'}, expect=19)
        self.assertEqual([e['kind'] for e in events], ['driver'])

    def test_container_builds_selected_driver_and_calls_native_dev(self):
        events = self.run_dev('--llvm-source', str(self.source), '--phase', 'check')
        self.assertEqual([e['kind'] for e in events], ['docker', 'docker'])
        build, run = [e['args'] for e in events]
        self.assertFalse(Path(build[-1]).exists(), 'temporary build context was not cleaned')
        self.assertIn(str(self.source) + ':' + str(self.source) + ':Z', run)
        self.assertIn('/workspace/scripts/dev.sh', run)
        self.assertEqual(run[run.index('--phase') + 1], 'check')
        self.assertEqual(run[run.index('--install-dir') + 1], '/workspace/build/toolchain')
        self.assertIn('--native', run)

    def test_invalid_arguments_fail_before_build(self):
        for args in (('--phase', 'invalid'), ('--phase',), ('--bogus',), ('--phase', 'check', '--', '-DFOO=ON')):
            with self.subTest(args=args):
                self.assertEqual(self.run_dev(*args, expect=2), [])

    def test_help_does_not_need_checkout_or_container(self):
        self.assertEqual(self.run_dev('--help'), [])

    def test_legacy_ci_entry_uses_dev(self):
        events = self.run_dev('--phase', 'firmware', script='ci.sh')
        self.assertEqual([e['kind'] for e in events], ['firmware'])


if __name__ == '__main__':
    unittest.main()
