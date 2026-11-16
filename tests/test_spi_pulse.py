import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'bin/macbook-spi-wake-pulse'
loader = importlib.machinery.SourceFileLoader('spi_helper', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
spi = importlib.util.module_from_spec(spec)
loader.exec_module(spi)


class PulseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir(mode=0o700)
        self.targets = {name: self.root / name for name in ('parent', 'controller')}
        for path in self.targets.values():
            path.write_text('auto\n')
        self.patches = [patch.object(spi, 'STATE_DIR', self.state), patch.object(spi, 'TARGETS', self.targets), patch.object(spi, 'validate_host')]
        self.directory, self.target_patch, self.validate = [p.start() for p in self.patches]
        for p in self.patches:
            self.addCleanup(p.stop)

    def policies(self):
        return {name: path.read_text().strip() for name, path in self.targets.items()}

    def test_pulse_saves_then_restores_original_policies(self):
        def observe_sleep(seconds):
            self.assertEqual(seconds, 2)
            self.assertEqual(self.policies(), {'parent': 'on', 'controller': 'on'})
            self.assertEqual(spi.load_state(), {'parent': 'auto', 'controller': 'auto'})
        with patch.object(spi.time, 'sleep', side_effect=observe_sleep):
            spi.pulse()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})
        self.assertFalse((self.state / spi.STATE_FILE).exists())

    def test_preserves_preexisting_on_policy(self):
        self.targets['parent'].write_text('on')
        with patch.object(spi.time, 'sleep'):
            spi.pulse()
        self.assertEqual(self.policies(), {'parent': 'on', 'controller': 'auto'})

    def test_exception_during_pulse_restores(self):
        with patch.object(spi.time, 'sleep', side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):
                spi.pulse()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})

    def test_unverified_host_makes_no_power_write(self):
        self.validate.side_effect = RuntimeError('unverified')
        with self.assertRaises(RuntimeError):
            spi.pulse()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})
        self.assertFalse((self.state / spi.STATE_FILE).exists())

    def test_existing_state_refuses_overlapping_pulse(self):
        spi.save_state({'parent': 'auto', 'controller': 'auto'})
        with self.assertRaises(FileExistsError):
            spi.pulse()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})
        self.assertTrue((self.state / spi.STATE_FILE).exists())

    def test_state_file_is_private(self):
        spi.save_state({'parent': 'auto', 'controller': 'auto'})
        self.assertEqual((self.state / spi.STATE_FILE).stat().st_mode & 0o777, 0o600)

    def test_unsafe_state_directory_refused(self):
        self.state.chmod(0o755)
        with self.assertRaises(RuntimeError):
            spi.pulse()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})

    def test_symlink_state_file_refused(self):
        other = self.root / 'other'
        other.write_text('{}')
        (self.state / spi.STATE_FILE).symlink_to(other)
        with self.assertRaises(OSError):
            spi.load_state()

    def test_malformed_record_cannot_supply_a_path_or_policy(self):
        for record in (
            {'version': 1, 'originals': {'/other/path': 'on'}},
            {'version': 1, 'originals': {'parent': 'arbitrary', 'controller': 'auto'}},
            {'version': True, 'originals': {'parent': 'auto', 'controller': 'auto'}},
            {'version': 1, 'originals': [], 'extra': 1},
        ):
            with self.subTest(record=record):
                path = self.state / spi.STATE_FILE
                path.write_text(json.dumps(record))
                path.chmod(0o600)
                with self.assertRaises(RuntimeError):
                    spi.restore()
                self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})
                path.unlink()

    def test_oversized_record_refused(self):
        path = self.state / spi.STATE_FILE
        path.write_text(' ' * 1025)
        path.chmod(0o600)
        with self.assertRaises(RuntimeError):
            spi.load_state()

    def test_missing_record_is_safe_noop(self):
        spi.restore()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})

    def test_partial_power_write_failure_still_restores_both(self):
        real_write = Path.write_text
        def failing_write(path, value, *args, **kwargs):
            if path == self.targets['controller'] and value == 'on\n':
                raise OSError('synthetic write failure')
            return real_write(path, value, *args, **kwargs)
        with patch.object(Path, 'write_text', failing_write):
            with self.assertRaises(OSError):
                spi.pulse()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})

    def test_restore_failure_retains_record_for_independent_retry(self):
        spi.save_state({'parent': 'auto', 'controller': 'auto'})
        for path in self.targets.values():
            path.write_text('on')
        real_write = Path.write_text
        def failing_write(path, value, *args, **kwargs):
            if path == self.targets['controller']:
                raise OSError('synthetic restore failure')
            return real_write(path, value, *args, **kwargs)
        with patch.object(Path, 'write_text', failing_write):
            with self.assertRaises(RuntimeError):
                spi.restore()
        self.assertTrue((self.state / spi.STATE_FILE).exists())
        self.assertEqual(self.targets['parent'].read_text().strip(), 'auto')
        spi.restore()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})
        self.assertFalse((self.state / spi.STATE_FILE).exists())

    def test_independent_restore_after_sigkill_of_synthetic_worker(self):
        # All paths are temporary regular files; no hardware or real service calls.
        program = '''
import os, runpy, signal, sys
from pathlib import Path
ns = runpy.run_path(sys.argv[1])
f = ns['pulse']; g = f.__globals__
g['STATE_DIR'] = Path(sys.argv[2])
g['TARGETS'] = {name: Path(sys.argv[3]) / name for name in ('parent', 'controller')}
g['validate_host'] = lambda: None
def killed(seconds):
    os.kill(os.getpid(), signal.SIGKILL)
g['time'].sleep = killed
f()
'''
        result = subprocess.run([sys.executable, '-c', program, str(SOURCE), str(self.state), str(self.root)], capture_output=True)
        self.assertEqual(result.returncode, -signal.SIGKILL)
        self.assertEqual(self.policies(), {'parent': 'on', 'controller': 'on'})
        spi.restore()
        self.assertEqual(self.policies(), {'parent': 'auto', 'controller': 'auto'})

    def test_check_does_not_pulse_or_save_state(self):
        with patch.object(spi.os, 'geteuid', return_value=0), patch.object(spi, 'pulse') as pulse:
            self.assertEqual(spi.main(['--check']), 0)
            pulse.assert_not_called()
        self.assertFalse((self.state / spi.STATE_FILE).exists())

    def test_nonroot_cli_refused(self):
        with patch.object(spi.os, 'geteuid', return_value=1000), patch.object(spi, 'pulse') as pulse:
            self.assertEqual(spi.main(['--pulse']), 1)
            pulse.assert_not_called()


class HostGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.pci = root / 'pci'
        self.controller = self.pci / 'pxa2xx-spi.3'
        self.device = self.controller / 'spi_master/spi2/spi-APP000D:00'
        self.device.mkdir(parents=True)
        (self.pci / 'vendor').write_text('0x8086')
        (self.pci / 'device').write_text('0x9d2a')
        self.model = root / 'model'
        self.model.write_text('MacBookPro14,2')
        def mapped_path(value):
            if value == '/sys/class/dmi/id/product_name':
                return self.model
            if value == '/sys/bus/spi/devices/spi-APP000D:00':
                return self.device
            return Path(value)
        for mocked in (patch.object(spi, 'PCI', self.pci), patch.object(spi, 'CONTROLLER', self.controller), patch.object(spi, 'Path', side_effect=mapped_path)):
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_expected_model_device_and_hierarchy(self):
        spi.validate_host()

    def test_wrong_model_refused(self):
        self.model.write_text('MacBookPro14,3')
        with self.assertRaises(RuntimeError):
            spi.validate_host()

    def test_wrong_pci_device_refused(self):
        (self.pci / 'device').write_text('0xffff')
        with self.assertRaises(RuntimeError):
            spi.validate_host()

    def test_wrong_keyboard_parent_refused(self):
        self.device = self.pci / 'other-device'
        with self.assertRaises(RuntimeError):
            spi.validate_host()


class IntegrationContractTests(unittest.TestCase):
    def test_systemd_has_independent_cleanup_and_no_restart_loop(self):
        unit = (SOURCE.parents[1] / 'systemd/macbook-spi-wake-pulse.service').read_text()
        self.assertIn('ExecStopPost=/usr/local/libexec/macbook-spi-wake-pulse --restore', unit)
        self.assertIn('TimeoutStartSec=5s', unit)
        self.assertIn('RuntimeDirectoryPreserve=yes', unit)
        self.assertIn('Restart=no', unit)

    def test_trigger_does_not_wait_for_pulse(self):
        dropin = (SOURCE.parents[1] / 'systemd/80-macbook-spi-wake-pulse.conf').read_text()
        self.assertIn('--no-block start macbook-spi-wake-pulse.service', dropin)


if __name__ == '__main__':
    unittest.main()
