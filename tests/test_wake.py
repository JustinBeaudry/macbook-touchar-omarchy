import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import mock_open, patch

SOURCE = Path(__file__).resolve().parents[1] / 'bin/macbook-touchbar-wake'
loader = importlib.machinery.SourceFileLoader('wake_helper', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
wake = importlib.util.module_from_spec(spec)
loader.exec_module(wake)


class IdentityTests(unittest.TestCase):
    def test_verified_identity(self):
        table = b'synthetic firmware'
        with patch.object(wake, 'SSDT6_SHA256', hashlib.sha256(table).hexdigest()):
            wake.validate_identity(wake.MODEL, wake.ACPI_DEVICE, table)

    def test_rejects_other_model_path_and_firmware(self):
        for model, path, table in (
            ('MacBookPro14,3', wake.ACPI_DEVICE, b''),
            (wake.MODEL, r'\OTHER', b''),
            (wake.MODEL, wake.ACPI_DEVICE, b'unverified'),
        ):
            with self.subTest(model=model, path=path), self.assertRaises(RuntimeError):
                wake.validate_identity(model, path, table)


class DiscoveryTests(unittest.TestCase):
    def make_node(self, base, number, interface_number='06'):
        usb = base / 'devices' / f'usb{number}'
        interface = usb / 'interface'
        hid = interface / 'hid'
        hid.mkdir(parents=True)
        (usb / 'idVendor').write_text('05ac\n')
        (usb / 'idProduct').write_text('8600\n')
        (interface / 'bInterfaceNumber').write_text(interface_number)
        node = base / 'class' / f'hidraw{number}'
        node.mkdir(parents=True)
        (node / 'device').symlink_to(hid)

    def test_selects_only_interface_six(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.make_node(base, 0, '02')
            self.make_node(base, 1)
            self.assertEqual(wake.find_panel(base / 'class'), Path('/dev/hidraw1'))

    def test_ambiguous_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.make_node(base, 0)
            self.make_node(base, 1)
            with self.assertRaises(RuntimeError):
                wake.find_panel(base / 'class')

    def test_missing_is_none(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(wake.find_panel(Path(directory)))

    def test_discovery_wait_is_bounded(self):
        with patch.object(wake, 'find_panel', return_value=None) as find, patch.object(wake.time, 'sleep') as sleep:
            with self.assertRaises(RuntimeError):
                wake.wait_for_panel()
            self.assertEqual(find.call_count, 6)
            self.assertEqual(sleep.call_count, 5)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch.object(wake, 'validate_host'),
            patch.object(wake, 'wait_for_panel', return_value=Path('/synthetic/panel')),
            patch.object(wake.os, 'open', return_value=77),
            patch.object(wake.os, 'close'),
            patch.object(wake, 'power_byte', side_effect=[1, 1, 2]),
            patch.object(wake, 'call_host_awake'),
            patch.object(wake.fcntl, 'ioctl'),
        ]
        self.validate, self.find, self.open, self.close, self.power, self.host, self.ioctl = [p.start() for p in self.patches]
        for p in self.patches:
            self.addCleanup(p.stop)

    def test_one_awake_call_and_exact_display_report(self):
        wake.wake()
        self.host.assert_called_once_with()
        self.ioctl.assert_called_once_with(77, wake.ioctl_code(0x06), bytearray([3, 2, 244, 1] + [0] * 11))
        self.close.assert_called_once_with(77)

    def test_already_awake_still_sends_host_awake_but_no_report(self):
        self.power.side_effect = [2, 2, 2]
        wake.wake()
        self.host.assert_called_once_with()
        self.ioctl.assert_not_called()

    def test_unverified_host_prevents_open_or_acpi(self):
        self.validate.side_effect = RuntimeError('unverified')
        with self.assertRaises(RuntimeError):
            wake.wake()
        self.open.assert_not_called()
        self.host.assert_not_called()

    def test_acpi_failure_prevents_report_and_is_not_retried(self):
        self.host.side_effect = RuntimeError('failed')
        with self.assertRaises(RuntimeError):
            wake.wake()
        self.host.assert_called_once_with()
        self.ioctl.assert_not_called()
        self.close.assert_called_once_with(77)

    def test_initial_hid_read_failure_prevents_acpi(self):
        self.power.side_effect = OSError('failed')
        with self.assertRaises(OSError):
            wake.wake()
        self.host.assert_not_called()
        self.close.assert_called_once_with(77)

    def test_failed_readback_is_not_retried(self):
        self.power.side_effect = [1, 1, 1]
        with self.assertRaises(RuntimeError):
            wake.wake()
        self.host.assert_called_once_with()
        self.assertEqual(self.ioctl.call_count, 1)
        self.close.assert_called_once_with(77)


class AcpiTests(unittest.TestCase):
    def test_exact_awake_method_only(self):
        opened = mock_open()
        with patch('builtins.open', opened), patch.object(wake.Path, 'read_bytes', return_value=b'0x0\0'):
            wake.call_host_awake()
        opened.assert_called_once_with('/proc/acpi/call', 'w')
        opened().write.assert_called_once_with(wake.METHOD + ' 0x1\n')

    def test_failed_result_is_error(self):
        with patch('builtins.open', mock_open()), patch.object(wake.Path, 'read_bytes', return_value=b'Error: failed\0'):
            with self.assertRaises(RuntimeError):
                wake.call_host_awake()

    def test_wrong_hid_report_id_is_error(self):
        def wrong_report(fd, code, report):
            report[0] = 4
        with patch.object(wake.fcntl, 'ioctl', side_effect=wrong_report):
            with self.assertRaises(RuntimeError):
                wake.power_byte(77)


class CommandTests(unittest.TestCase):
    def test_check_never_calls_wake(self):
        with patch.object(wake.os, 'geteuid', return_value=0), \
             patch.object(wake, 'validate_host') as validate, \
             patch.object(wake, 'find_panel', return_value=Path('/synthetic/panel')), \
             patch.object(wake.Path, 'exists', return_value=True), \
             patch.object(wake, 'wake') as recover:
            self.assertEqual(wake.main(['--check']), 0)
            validate.assert_called_once_with()
            recover.assert_not_called()

    def test_nonroot_never_calls_wake(self):
        with patch.object(wake.os, 'geteuid', return_value=1000), patch.object(wake, 'wake') as recover:
            self.assertEqual(wake.main(['--wake']), 1)
            recover.assert_not_called()

    def test_missing_acpi_call_fails_check_without_wake(self):
        with patch.object(wake.os, 'geteuid', return_value=0), \
             patch.object(wake, 'validate_host'), \
             patch.object(wake, 'find_panel', return_value=Path('/synthetic/panel')), \
             patch.object(wake.Path, 'exists', return_value=False), \
             patch.object(wake, 'wake') as recover:
            self.assertEqual(wake.main(['--check']), 1)
            recover.assert_not_called()


if __name__ == '__main__':
    unittest.main()
