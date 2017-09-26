# Copyright 2017 Square, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pylink.enums as enums
from pylink.errors import JLinkException, JLinkDataException
import pylink.jlink as jlink
import pylink.protocols.swd as swd
import pylink.structs as structs
import pylink.unlockers.unlock_kinetis as unlock_kinetis
import pylink.util as util

import mock

import StringIO
import ctypes
import itertools
import unittest


class TestJLink(unittest.TestCase):
    """Tests the ``jlink`` submodule."""

    def setUp(self):
        """Called before each test.

        Performs setup.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.lib = mock.Mock()
        self.dll = mock.Mock()
        self.lib.dll.return_value = self.dll
        self.jlink = jlink.JLink(self.lib)

    def tearDown(self):
        """Called after each test.

        Performs teardown.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        del self.jlink

    @mock.patch('pylink.jlink.library')
    def test_jlink_initialize_no_lib(self, mock_lib):
        """TEsts initializing a ``JLink`` without a provided library.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        jlink.JLink()

    def test_jlink_initialize_invalid_dll(self):
        """Tests initializing a ``JLink`` with an invalid DLL.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.lib.dll.return_value = None

        with self.assertRaises(TypeError):
            jlink.JLink(self.lib)

    def test_jlink_initialize_provided_dll(self):
        """Tests initializing a ``JLink`` with a provided valid DLL.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        jlink.JLink(self.lib)

    def test_jlink_open_required_not_open(self):
        """Tests calling a method when ``open_required()`` is specified.

        This test checks that if we call a method that has specified that
        ``open_required()`` is needed, and we're not open, that a
        ``JLinkException`` is raised.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_IsOpen.return_value = False

        my_jlink = jlink.JLink(self.lib)

        with self.assertRaisesRegexp(JLinkException, 'DLL is not open'):
            my_jlink.update_firmware()

    def test_jlink_open_required_no_emu(self):
        """Tests calling a method when ``open_required()`` is specified.

        This test checks that if we call a method that has specified that
        ``open_required()`` is needed, and we're open, but no emulator is
        connected, that a ``JLinkException`` is raised.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_IsOpen.return_value = True
        self.dll.JLINKARM_EMU_IsConnected.return_value = False

        my_jlink = jlink.JLink(self.lib)

        with self.assertRaisesRegexp(JLinkException, 'connection has been lost'):
            my_jlink.update_firmware()

    def test_jlink_open_required_is_opened(self):
        """Tests calling a method when ``open_required()`` is specified.

        This test checks that if we call a method that has specified that
        ``open_required()`` is needed, and we're open and have a connected
        emulator, that we succeed.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        firmware = 0xdeadbeef

        self.dll.JLINKARM_IsOpen.return_value = True
        self.dll.JLINKARM_EMU_IsConnected.return_value = True
        self.dll.JLINKARM_UpdateFirmwareIfNewer.return_value = firmware

        my_jlink = jlink.JLink(self.lib)
        my_jlink.update_firmware()

    def test_jlink_connection_required_not_connected(self):
        """Tests calling a method when ``connection_required()`` is specified.

        This test checks that if we call a method that has specified that
        ``connection_required()`` is needed, and we're not connected, that
        an error is raised.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_IsOpen.return_value = True
        self.dll.JLINKARM_EMU_IsConnected.return_value = True
        self.dll.JLINKARM_IsConnected.return_value = False

        my_link = jlink.JLink(self.lib)

        with self.assertRaisesRegexp(JLinkException, 'Target is not connected'):
            my_link.cpu_capability(1)

    def test_jlink_connection_required_is_connected(self):
        """Tests calling a method when ``connection_required()`` is specified.

        We should succeed if connected.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_IsOpen.return_value = True
        self.dll.JLINKARM_EMU_IsConnected.return_value = True
        self.dll.JLINKARM_IsConnected.return_value = True

        my_link = jlink.JLink(self.lib)
        my_link.cpu_capability(1)

    def test_jlink_minimum_required(self):
        """Tests that the minimum required decorator handles versions correctly.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 49801
        with self.assertRaisesRegexp(JLinkException, 'Version'):
            self.jlink.erase_licenses()

        self.dll.JLINKARM_GetDLLVersion.return_value = 49800
        with self.assertRaisesRegexp(JLinkException, 'Version'):
            self.jlink.erase_licenses()

        self.dll.JLINKARM_GetDLLVersion.return_value = 39804
        with self.assertRaisesRegexp(JLinkException, 'Version'):
            self.jlink.erase_licenses()

        self.dll.JLINKARM_GetDLLVersion.return_value = 49802
        self.jlink.erase_licenses()

        self.dll.JLINKARM_GetDLLVersion.return_value = 50000
        self.jlink.erase_licenses()

        self.dll.JLINKARM_GetDLLVersion.return_value = 61009
        self.jlink.erase_licenses()

    def test_jlink_interface_required_wrong_interface(self):
        """Tests calling a method when ``interface_required()`` is specified.

        If a given method requires we have a specific target interface, and we
        do not, and it has specified ``interface_required()``, it should
        generate an error.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        my_jlink = jlink.JLink(self.lib)
        self.assertEqual(enums.JLinkInterfaces.JTAG, my_jlink.tif)

        with self.assertRaisesRegexp(JLinkException, 'Unsupported for current interface.'):
            my_jlink.swd_read8(0)

    def test_jlink_interface_required_correct_interface(self):
        """Tests calling a method when ``interface_required()`` is specified.

        If a given method requires we have a specific target interface, and we
        do, and it has specified ``interface_required()``, we should succeed.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        my_jlink = jlink.JLink(self.lib)
        self.assertEqual(enums.JLinkInterfaces.JTAG, my_jlink.tif)

        my_jlink._tif = enums.JLinkInterfaces.SWD
        my_jlink.swd_read8(0)

    def test_jlink_opened(self):
        """Tests the J-Link ``opened()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        # DLL has not been succesfully opened.  No J-Link connection.
        self.dll.JLINKARM_IsOpen.return_value = 0
        self.assertFalse(self.jlink.opened())

        # DLL has been opened successfully.
        self.dll.JLINKARM_IsOpen.return_value = 1
        self.assertTrue(self.jlink.opened())

    def test_jlink_connected(self):
        """Tests the J-Link ``connected()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        # Connection to J-Link established.
        self.dll.JLINKARM_EMU_IsConnected.return_value = 1
        self.assertTrue(self.jlink.connected())

        # Connection to J-Link is not established.
        self.dll.JLINKARM_EMU_IsConnected.return_value = 0
        self.assertFalse(self.jlink.connected())

    def test_jlink_target_connected(self):
        """Tests the J-Link ``target_connected()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        # If not connected
        self.dll.JLINKARM_IsConnected.return_value = 0
        self.assertFalse(self.jlink.target_connected())

        # If connected
        self.dll.JLINKARM_IsConnected.return_value = 1
        self.assertTrue(self.jlink.target_connected())

    def test_jlink_log_handler(self):
        """Tests the J-Link ``log_handler`` setter/getter.

        As long as the DLL is not open, we can set a log handler, which is
        made into a ``ctypes`` function.  Once one is set, it is used for all
        DLL logging.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        def foo():
            return None

        original_log_handler = self.jlink.log_handler
        self.dll.JLINKARM_IsOpen.return_value = 1
        self.jlink.log_handler = foo

        log_handler = self.jlink.log_handler
        self.assertEqual(original_log_handler, log_handler)

        self.dll.JLINKARM_IsOpen.return_value = 0
        self.jlink.log_handler = foo

        log_handler = self.jlink.log_handler
        self.assertTrue(log_handler)
        self.assertNotEqual(original_log_handler, log_handler)

    def test_jlink_detailed_log_handler(self):
        """Tests the J-Link ``detailed_log_handler`` setter/getter.

        As long as the DLL is not open, we can set a detailed log handler,
        which is made into a ``ctypes`` function.  Once one is set, it is used
        for all DLL detailed logging.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        def foo():
            return None

        original_log_handler = self.jlink.detailed_log_handler
        self.dll.JLINKARM_IsOpen.return_value = 1
        self.jlink.detailed_log_handler = foo

        log_handler = self.jlink.detailed_log_handler
        self.assertEqual(original_log_handler, log_handler)

        self.dll.JLINKARM_IsOpen.return_value = 0
        self.jlink.detailed_log_handler = foo

        log_handler = self.jlink.detailed_log_handler
        self.assertTrue(log_handler)
        self.assertNotEqual(original_log_handler, log_handler)

    def test_jlink_error_handler(self):
        """Tests the J-Link ``error_handler`` setter/getter.

        As long as the DLL is not open, we can set an error handler which is
        made into a ``ctypes`` funciton.  Once one is set, it is used for all
        DLL error logging.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        def foo():
            return None

        original_error_handler = self.jlink.error_handler
        self.dll.JLINKARM_IsOpen.return_value = 1
        self.jlink.error_handler = foo

        error_handler = self.jlink.error_handler
        self.assertEqual(original_error_handler, error_handler)

        self.dll.JLINKARM_IsOpen.return_value = 0
        self.jlink.error_handler = foo

        error_handler = self.jlink.error_handler
        self.assertTrue(error_handler)
        self.assertNotEqual(original_error_handler, error_handler)

    def test_jlink_warning_handler(self):
        """Tests the J-Link ``warning_handler`` setter/getter.

        As long as the DLL is not open, we can set an warning handler which is
        made into a ``ctypes`` funciton.  Once one is set, it is used for all
        DLL warning logging.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        def foo():
            return None

        original_warning_handler = self.jlink.warning_handler
        self.dll.JLINKARM_IsOpen.return_value = 1
        self.jlink.warning_handler = foo

        warning_handler = self.jlink.warning_handler
        self.assertEqual(original_warning_handler, warning_handler)

        self.dll.JLINKARM_IsOpen.return_value = 0
        self.jlink.warning_handler = foo

        warning_handler = self.jlink.warning_handler
        self.assertTrue(warning_handler)
        self.assertNotEqual(original_warning_handler, warning_handler)

    def test_jlink_num_connected_emulators(self):
        """Tests the J-Link ``num_connected_emulators()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EMU_GetNumDevices.return_value = 1
        self.assertEqual(1, self.jlink.num_connected_emulators())

        self.dll.JLINKARM_EMU_GetNumDevices.return_value = 0
        self.assertEqual(0, self.jlink.num_connected_emulators())

    def test_jlink_connected_emulators(self):
        """Tests the J-Link ``connected_emulators()`` method.

        This method returns a list of ``structs.JLinkConnectInfo`` structures
        provided that is succeeds, otherwise raises a ``JLinkException``.  The
        returned list may be empty.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        # >= 0, total number of emulators which have been found
        self.dll.JLINKARM_EMU_GetList.return_value = 0

        connected_emulators = self.jlink.connected_emulators()
        self.assertTrue(isinstance(connected_emulators, list))
        self.assertEqual(0, len(connected_emulators))

        # < 0, Error
        self.dll.JLINKARM_EMU_GetList.return_value = -1

        with self.assertRaises(JLinkException):
            connected_emulators = self.jlink.connected_emulators()

        # < 0, Error
        self.dll.JLINKARM_EMU_GetList = mock.Mock()
        self.dll.JLINKARM_EMU_GetList.side_effect = [1, -1]

        with self.assertRaises(JLinkException):
            connected_emulators = self.jlink.connected_emulators()

        # >= 0, total number of emulators which have been found
        self.dll.JLINKARM_EMU_GetList = mock.Mock()
        self.dll.JLINKARM_EMU_GetList.return_value = 1

        connected_emulators = self.jlink.connected_emulators()
        self.assertTrue(isinstance(connected_emulators, list))
        self.assertEqual(1, len(connected_emulators))
        self.assertTrue(isinstance(connected_emulators[0], structs.JLinkConnectInfo))

    def test_jlink_num_supported_devices(self):
        """Tests the J-Link ``num_supported_devices()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_DEVICE_GetInfo.return_value = 0
        self.assertEqual(self.jlink.num_supported_devices(), 0)

        self.dll.JLINKARM_DEVICE_GetInfo.return_value = 1
        self.assertEqual(self.jlink.num_supported_devices(), 1)

    def test_jlink_supported_device(self):
        """Tests the J-Link ``supported_device()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_DEVICE_GetInfo.return_value = 1

        with self.assertRaisesRegexp(ValueError, 'Invalid index.'):
            dev = self.jlink.supported_device('dog')

        with self.assertRaisesRegexp(ValueError, 'Invalid index.'):
            dev = self.jlink.supported_device(-1)

        with self.assertRaisesRegexp(ValueError, 'Invalid index.'):
            dev = self.jlink.supported_device(1)

        dev = self.jlink.supported_device(0)
        self.assertTrue(isinstance(dev, structs.JLinkDeviceInfo))

    def test_jlink_open_unspecified(self):
        """Tests the J-Link ``open()`` method with an unspecified method.

        When opening a connection to an emulator, we need to specify
        by which method we are connecting to the emulator.  If neither USB or
        Ethernet or specified, then we should raise an error.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(AttributeError):
            self.jlink.open()

    def test_jlink_open_ethernet_failed(self):
        """Tests the J-Link ``open()`` method over Ethernet failing.

        If we fail to select a J-Link over ethernet, it should raise an error.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SelectIP.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.open(ip_addr='127.0.0.1:80')

        self.dll.JLINKARM_SelectIP.assert_called_once()

    @mock.patch('pylink.jlock.JLock', new=mock.Mock())
    def test_jlink_open_ethernet(self):
        """Tests the J-Link ``open()`` method over Ethernet succeeding.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLNKARM_SelectIP.return_value = 0
        self.dll.JLINKARM_OpenEx.return_value = 0
        self.dll.JLINKARM_GetSN.return_value = 123456789

        self.jlink.open(ip_addr='127.0.0.1:80')

        self.dll.JLINKARM_SelectIP.assert_called_once()

    @mock.patch('pylink.jlock.JLock', new=mock.Mock())
    def test_jlink_open_ethernet_and_serial_number(self):
        """Tests the J-Link ``open()`` method over Ethernet succeeding with
        identification done by serial number.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_OpenEx.return_value = 0

        self.jlink.open(serial_no=123456789, ip_addr='127.0.0.1:80')

        self.assertEqual(0, self.dll.JLINKARM_EMU_SelectIP.call_count)
        self.assertEqual(1, self.dll.JLINKARM_EMU_SelectIPBySN.call_count)

    def test_jlink_open_serial_number_failed(self):
        """Tests the J-Link ``open()`` method over USB by serial number, but
        failing.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EMU_SelectByUSBSN.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.open(serial_no=123456789)

        self.assertEqual(0, self.dll.JLINKARM_OpenEx.call_count)

    @mock.patch('pylink.jlock.JLock', new=mock.Mock())
    def test_jlink_open_serial_number(self):
        """Tests the J-Link ``open()`` method over USB by serial number and
        succeeding.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EMU_SelectByUSBSN.return_value = 0
        self.dll.JLINKARM_OpenEx.return_value = 0
        self.jlink.open(serial_no=123456789)
        self.assertEqual(1, self.dll.JLINKARM_OpenEx.call_count)

    @mock.patch('pylink.jlock.JLock', new=mock.Mock())
    def test_jlink_open_dll_failed(self):
        """Tests the J-Link ``open()`` method failing to open the DLL.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EMU_SelectByUSBSN.return_value = 0

        buf = ctypes.create_string_buffer('Error!', 32)
        self.dll.JLINKARM_OpenEx.return_value = ctypes.addressof(buf)

        with self.assertRaisesRegexp(JLinkException, 'Error!'):
            self.jlink.open(serial_no=123456789)

        self.assertEqual(1, self.dll.JLINKARM_OpenEx.call_count)

    @mock.patch('pylink.jlock.JLock')
    def test_jlink_open_lock_failed(self, mock_jlock):
        """Tests the J-Link ``open()`` method failing if the lockfile is held.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_jlock (Mock): the mocked lock instance

        Returns:
          ``None``
        """
        mock_lock = mock.Mock()
        mock_jlock.return_value = mock_lock
        mock_lock.acquire.return_value = False

        self.dll.JLINKARM_EMU_SelectByUSBSN.return_value = 0
        self.dll.JLINKARM_OpenEx.return_value = 0

        with self.assertRaisesRegexp(JLinkException, 'J-Link is already open.'):
            self.jlink.open(serial_no=123456789)

        self.dll.JLINKARM_OpenEx.assert_not_called()

    def test_jlink_close(self):
        """Tests the J-Link ``close()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.close()
        self.assertEqual(1, self.dll.JLINKARM_Close.call_count)

    def test_jlink_test(self):
        """Tests the J-Link self test.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_Test.return_value = 0
        self.assertTrue(self.jlink.test())

        self.dll.JLINKARM_Test.return_value = 1
        self.assertFalse(self.jlink.test())

    def test_jlink_invalidate_firmware(self):
        """Tests invaliding the J-Link firmware.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        mocked = mock.Mock()
        self.jlink.exec_command = mocked

        self.jlink.invalidate_firmware()
        self.assertEqual(1, self.jlink.exec_command.call_count)
        self.jlink.exec_command.assert_called_with('InvalidateFW')

    def test_jlink_update_firmware(self):
        """Tests the J-Link ``update_firmware()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        firmware = 0xdeadbeef
        self.dll.JLINKARM_UpdateFirmwareIfNewer.return_value = firmware

        self.assertEqual(firmware, self.jlink.update_firmware())

    def test_jlink_sync_firmware_outdated(self):
        """Tests syncing the J-Link firmware when it is outdated.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.firmware_newer = mock.Mock()
        self.jlink.firmware_newer.return_value = False

        self.jlink.firmware_outdated = mock.Mock()
        self.jlink.firmware_outdated.side_effect = [True, False, True, True]

        self.jlink.invalidate_firmware = mock.Mock()
        self.jlink.update_firmware = mock.Mock()
        self.jlink.update_firmware.side_effect = [JLinkException(''), None]

        self.jlink.open = mock.Mock()
        self.jlink.open.return_value = None

        self.dll.JLINKARM_GetSN.return_value = 0xdeadbeef

        self.assertEqual(None, self.jlink.sync_firmware())
        self.assertEqual(0, self.jlink.invalidate_firmware.call_count)
        self.assertEqual(1, self.jlink.update_firmware.call_count)
        self.assertEqual(1, self.dll.JLINKARM_GetSN.call_count)

        self.jlink.open.assert_called_with(serial_no=0xdeadbeef)

        # Firmware still outdated after syncing.
        with self.assertRaises(JLinkException):
            self.jlink.sync_firmware()

    def test_jlink_sync_firmware_newer(self):
        """Tests syncing the J-Link firmware when it is newer than the DLL.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.firmware_newer = mock.Mock()
        self.jlink.firmware_newer.side_effect = [True, False, True, True]

        self.jlink.firmware_outdated = mock.Mock()
        self.jlink.firmware_outdated.return_value = False

        self.jlink.invalidate_firmware = mock.Mock()
        self.jlink.update_firmware = mock.Mock()
        self.jlink.update_firmware.side_effect = [JLinkException(''), None]

        self.jlink.open = mock.Mock()
        self.jlink.open.return_value = None

        self.dll.JLINKARM_GetSN.return_value = 0xdeadbeef

        self.assertEqual(None, self.jlink.sync_firmware())
        self.assertEqual(1, self.jlink.invalidate_firmware.call_count)
        self.assertEqual(1, self.jlink.update_firmware.call_count)
        self.assertEqual(1, self.dll.JLINKARM_GetSN.call_count)

        self.jlink.open.assert_called_with(serial_no=0xdeadbeef)

        # Firmware still newer after syncing.
        with self.assertRaises(JLinkException):
            self.jlink.sync_firmware()

    def test_jlink_sync_firmware_in_sync(self):
        """Tests syncing the J-Link firmware when it is in sync.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.firmware_newer = mock.Mock()
        self.jlink.firmware_newer.return_value = False

        self.jlink.firmware_outdated = mock.Mock()
        self.jlink.firmware_outdated.return_value = False

        self.jlink.invalidate_firmware = mock.Mock()
        self.jlink.update_firmware = mock.Mock()

        self.dll.JLINKARM_GetSN.return_value = 0xdeadbeef

        self.assertEqual(None, self.jlink.sync_firmware())
        self.assertEqual(0, self.jlink.invalidate_firmware.call_count)
        self.assertEqual(0, self.jlink.update_firmware.call_count)
        self.assertEqual(1, self.dll.JLINKARM_GetSN.call_count)

    def test_jlink_exec_command_error_string(self):
        """Tests the J-Link ``exec_command()`` when an error string is
        returned.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        def foo(cmd, err_buf, err_buf_len):
            for (index, ch) in enumerate('Error!'):
                err_buf[index] = ch
            return 0

        self.dll.JLINKARM_ExecCommand = foo

        with self.assertRaisesRegexp(JLinkException, 'Error!'):
            self.jlink.exec_command('SupplyPower = 1')

    def test_jlink_exec_command_error_code(self):
        """Tests the J-Link ``exec_command()`` when an error code is returned.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0

        self.jlink.exec_command('SupplyPowerf = 1')

    def test_jlink_exec_command_success(self):
        """Tests the J-Link ``exec_command()`` succeeding.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0
        self.assertEqual(0, self.jlink.exec_command('SupplyPower = 1'))

        self.dll.JLINKARM_ExecCommand.return_value = 1
        self.assertEqual(1, self.jlink.exec_command('SupplyPower = 1'))

        self.dll.JLINKARM_ExecCommand.return_value = -1
        self.assertEqual(-1, self.jlink.exec_command('SupplyPower = 1'))

    def test_jlink_enable_dialog_boxes(self):
        """Tests enabling the dialog boxes shown by the DLL.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 50200
        self.jlink.exec_command = mock.Mock()
        self.jlink.enable_dialog_boxes()
        self.jlink.exec_command.assert_called_with('SetBatchMode = 0')

    def test_jlink_disable_dialog_boxes(self):
        """Tests disabling the dialog boxes shown by the DLL.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 50200
        self.jlink.exec_command = mock.Mock()
        self.jlink.disable_dialog_boxes()
        self.jlink.exec_command.assert_any_call('SilentUpdateFW')
        self.jlink.exec_command.assert_any_call('SuppressInfoUpdateFW')
        self.jlink.exec_command.assert_any_call('SetBatchMode = 1')

    def test_jlink_jtag_configure(self):
        """Tests the J-Link ``jtag_configure()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaisesRegexp(ValueError, 'IR'):
            self.jlink.jtag_configure('sdafas', 0)

        with self.assertRaisesRegexp(ValueError, 'Data bits'):
            self.jlink.jtag_configure(0, 'asfadsf')

        self.assertEqual(None, self.jlink.jtag_configure(0, 0))
        self.assertEqual(1, self.dll.JLINKARM_ConfigJTAG.call_count)

        self.assertEqual(None, self.jlink.jtag_configure())
        self.assertEqual(2, self.dll.JLINKARM_ConfigJTAG.call_count)

    def test_jlink_coresight_configure_swd(self):
        """Tests Coresight Configure over SWD.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD
        self.assertEqual(enums.JLinkInterfaces.SWD, self.jlink.tif)

        self.dll.JLINKARM_GetDLLVersion.return_value = 49805
        self.dll.JLINKARM_CORESIGHT_Configure.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.coresight_configure()

        self.dll.JLINKARM_CORESIGHT_Configure.return_value = 0

        self.jlink.coresight_configure()
        self.dll.JLINKARM_CORESIGHT_Configure.assert_called_with('')

    def test_jlink_coresight_configure_jtag(self):
        """Tests Coresight Configure over JTAG.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.JTAG
        self.assertEqual(enums.JLinkInterfaces.JTAG, self.jlink.tif)

        self.dll.JLINKARM_GetDLLVersion.return_value = 49805
        self.jlink.coresight_configure(perform_tif_init=False)

        self.dll.JLINKARM_CORESIGHT_Configure.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.coresight_configure()

        self.dll.JLINKARM_CORESIGHT_Configure.return_value = 0

        self.jlink.coresight_configure(dr_post=2, ir_post=3, perform_tif_init=False)

        arg = self.dll.JLINKARM_CORESIGHT_Configure.call_args[0][0]
        self.assertTrue(len(arg) > 0)
        self.assertTrue('PerformTIFInit=0' in arg)
        self.assertTrue('DRPost=2' in arg)
        self.assertTrue('IRPost=3' in arg)

    @mock.patch('time.sleep')
    def test_jlink_connect_failed(self, mock_sleep):
        """Tests J-Link ``connect()`` failing due to hardware issue.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked sleep function

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0
        self.dll.JLINKARM_Connect.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.connect('device')

        self.assertEqual(1, self.dll.JLINKARM_ExecCommand.call_count)
        self.assertEqual(1, self.dll.JLINKARM_Connect.call_count)

    @mock.patch('time.sleep')
    def test_jlink_connect_auto(self, mock_sleep):
        """Tests J-Link ``connect()`` with ``auto`` speed.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked sleep function

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0
        self.dll.JLINKARM_Connect.return_value = 0

        self.jlink.num_supported_devices = mock.Mock()
        self.jlink.num_supported_devices.return_value = 1
        self.jlink.supported_device = mock.Mock()
        self.jlink.supported_device.return_value = mock.Mock()
        self.jlink.supported_device.return_value.name = 'device'

        self.assertEqual(None, self.jlink.connect('device', speed='auto'))

        self.assertEqual(1, self.dll.JLINKARM_ExecCommand.call_count)
        self.assertEqual(1, self.dll.JLINKARM_Connect.call_count)

    @mock.patch('time.sleep')
    def test_jlink_connect_adaptive(self, mock_sleep):
        """Tests J-Link ``connect()`` with ``adaptive`` speed.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked sleep function

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0
        self.dll.JLINKARM_Connect.return_value = 0

        self.jlink.num_supported_devices = mock.Mock()
        self.jlink.num_supported_devices.return_value = 1
        self.jlink.supported_device = mock.Mock()
        self.jlink.supported_device.return_value = mock.Mock()
        self.jlink.supported_device.return_value.name = 'device'

        self.assertEqual(None, self.jlink.connect('device', speed='adaptive'))

        self.assertEqual(1, self.dll.JLINKARM_ExecCommand.call_count)
        self.assertEqual(1, self.dll.JLINKARM_Connect.call_count)

    @mock.patch('time.sleep')
    def test_jlink_connect_speed_invalid(self, mock_sleep):
        """Tests J-Link ``connect()`` fails if speed is invalid.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked sleep function

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0
        self.dll.JLINKARM_Connect.return_value = 0

        with self.assertRaises(TypeError):
            self.jlink.connect('device', speed=-1)

        self.assertEqual(1, self.dll.JLINKARM_ExecCommand.call_count)
        self.assertEqual(0, self.dll.JLINKARM_Connect.call_count)

    @mock.patch('time.sleep')
    def test_jlink_connect_speed(self, mock_sleep):
        """Tests J-Link ``connect()`` with a numerical speed.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked sleep function

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0
        self.dll.JLINKARM_Connect.return_value = 0

        self.jlink.num_supported_devices = mock.Mock()
        self.jlink.num_supported_devices.return_value = 1
        self.jlink.supported_device = mock.Mock()
        self.jlink.supported_device.return_value = mock.Mock()
        self.jlink.supported_device.return_value.name = 'device'

        self.jlink.connect('device', speed=10)

        self.assertEqual(1, self.dll.JLINKARM_ExecCommand.call_count)
        self.assertEqual(1, self.dll.JLINKARM_Connect.call_count)

    @mock.patch('time.sleep')
    def test_jlink_connect_verbose(self, mock_sleep):
        """Tests J-Link ``connect()`` with verbose logging.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked sleep function

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0
        self.dll.JLINKARM_Connect.return_value = 0

        self.jlink.num_supported_devices = mock.Mock()
        self.jlink.num_supported_devices.return_value = 1
        self.jlink.supported_device = mock.Mock()
        self.jlink.supported_device.return_value = mock.Mock()
        self.jlink.supported_device.return_value.name = 'device'

        self.jlink.connect('device', speed=10, verbose=True)

        self.assertEqual(2, self.dll.JLINKARM_ExecCommand.call_count)
        self.assertEqual(1, self.dll.JLINKARM_Connect.call_count)

    @mock.patch('time.sleep')
    def test_jlink_connect_supported_device_not_found(self, mock_sleep):
        """Tests J-Link ``connect()`` when the supported device is not found.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked sleep function

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ExecCommand.return_value = 0
        self.dll.JLINKARM_Connect.return_value = 0

        self.jlink.num_supported_devices = mock.Mock()
        self.jlink.num_supported_devices.return_value = 0

        with self.assertRaisesRegexp(JLinkException, 'Unsupported device'):
            self.jlink.connect('device')

    def test_jlink_error(self):
        """Tests the J-Link ``error`` property.

        Should be ``None`` on no error, otherwise a non-zero integer value.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_HasError.return_value = 0
        self.assertEqual(None, self.jlink.error)

        self.dll.JLINKARM_HasError.return_value = 1
        self.assertEqual(1, self.jlink.error)

    def test_jlink_clear_error(self):
        """Tests clearing the J-Link error.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_HasError.return_value = 0

        self.assertEqual(None, self.jlink.clear_error())
        self.dll.JLINKARM_ClrError.assert_called_once()

    def test_jlink_compile_date(self):
        """Tests the J-Link ``compile_date`` property.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        date = '2016-09-09'
        buf = ctypes.create_string_buffer(date, 32)
        self.dll.JLINKARM_GetCompileDateTime.return_value = ctypes.addressof(buf)

        self.assertEqual(date, self.jlink.compile_date)

    def test_jlink_version(self):
        """Tests the J-Link ``version`` property.

        The return value when querying the DLL for its version is a 32-bit DLL
        version number interpreted as Mmmrr where M is the major number, mm is
        the minor number, and rr is the revision number.

        Input:
          25402

        Output:
          2.54b

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 25402
        self.assertEqual('2.54b', self.jlink.version)

        self.dll.JLINKARM_GetDLLVersion.return_value = 60000
        self.assertEqual('6.00', self.jlink.version)

        self.dll.JLINKARM_GetDLLVersion.return_value = 60002
        self.assertEqual('6.00b', self.jlink.version)

        self.dll.JLINKARM_GetDLLVersion.return_value = 49805
        self.assertEqual('4.98e', self.jlink.version)

    def test_jlink_compatible_firmware_version(self):
        """Tests that getting a compatible firmware version from the DLL.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        firmware = 'J-Trace Cortex-M Rev.3 compiled Mar 30 2015 13:52:25'

        def set_firmware_string(buf, buf_size):
            ctypes.memmove(buf, firmware, len(firmware))

        self.dll.JLINKARM_GetFirmwareString = set_firmware_string

        self.dll.JLINKARM_GetEmbeddedFWString.return_value = -1
        with self.assertRaises(JLinkException):
            self.jlink.compatible_firmware_version

        self.dll.JLINKARM_GetEmbeddedFWString.return_value = 0
        self.dll.JLINKARM_GetEmbeddedFWString.assert_called()
        self.assertEqual('', self.jlink.compatible_firmware_version)

    def test_jlink_firmware_outdated(self):
        """Tests checking if the J-Link firmware is outdated.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        old = 'J-Trace Cortex-M Rev.3 compiled Mar 30 2015 13:52:25'
        new = 'J-Trace Cortex-M Rev.3 compiled Jun 30 2016 16:58:07'

        def set_embedded_fw_string(identifier, buf, buf_size):
            ctypes.memmove(buf, old, len(old))
            return 0

        def set_firmware_string(buf, buf_size):
            ctypes.memmove(buf, new, len(new))
            return 0

        self.dll.JLINKARM_GetFirmwareString = set_firmware_string
        self.dll.JLINKARM_GetEmbeddedFWString = set_embedded_fw_string

        self.assertFalse(self.jlink.firmware_outdated())

        new, old = old, new
        self.assertTrue(self.jlink.firmware_outdated())

    def test_jlink_firmware_newer(self):
        """Tests checking if the J-Link firmware is newer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        old = 'J-Trace Cortex-M Rev.3 compiled Mar 30 2015 13:52:25'
        new = 'J-Trace Cortex-M Rev.3 compiled Jun 30 2016 16:58:07'

        def set_embedded_fw_string(identifier, buf, buf_size):
            ctypes.memmove(buf, old, len(old))
            return 0

        def set_firmware_string(buf, buf_size):
            ctypes.memmove(buf, new, len(new))
            return 0

        self.dll.JLINKARM_GetFirmwareString = set_firmware_string
        self.dll.JLINKARM_GetEmbeddedFWString = set_embedded_fw_string

        self.assertTrue(self.jlink.firmware_newer())

        new, old = old, new
        self.assertFalse(self.jlink.firmware_newer())

    def test_jlink_hardware_info_invalid(self):
        """Tests the J-Link ``hardware_info`` property when it fails to read info.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetHWInfo.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.hardware_info

    def test_jlink_hardware_info_valid(self):
        """Tests the J-Link ``hardware_info`` property when info is read.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetHWInfo.return_value = 0

        result = self.jlink.hardware_info
        self.assertTrue(all(map(lambda x: x == 0, result)))

    def test_jlink_hardware_status_invalid(self):
        """Tests the J-Link ``hardware_status`` property on failure to read.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetHWStatus.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.hardware_status

    def test_jlink_hardware_status_valid(self):
        """Tests the J-Link ``hardware_status`` property on successful read.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetHWStatus.return_value = 0

        stat = self.jlink.hardware_status
        self.assertTrue(isinstance(stat, structs.JLinkHardwareStatus))

    def test_jlink_hardware_version(self):
        """Tests the J-Link ``hardware_version`` property.

        Input:
          20330

        Output:
          2.03

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetHardwareVersion.return_value = 20330

        self.assertEqual('2.03', self.jlink.hardware_version)

    def test_jlink_firmware_version(self):
        """Tests the J-Link ``firmware_version`` property.

        Example Firmware Strings:
          ``Firmware: J-Link compiled Nov 17 2005 16:12:19``
          ``Firmware: J-Link compiled Nov 09 2005 19:32:24 -- Update --``
          ``Firmware: J-Link compiled Nov 17 2005 16:12:19 ARM Rev.5``

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        firmware_strings = [
            'Firmware: J-Link compiled Nov 17 2005 16:12:19',
            'Firmware: J-Link compiled Nov 09 2005 19:32:24 -- Update --',
            'Firmware: J-Link compiled Nov 17 2005 16:12:19 ARM Rev.5'
        ]

        def get_firmware_string(buf, buf_size):
            firmware_string = firmware_strings.pop(0)
            ctypes.memmove(buf, firmware_string, len(firmware_string))

        self.dll.JLINKARM_GetFirmwareString = get_firmware_string

        while len(firmware_strings) > 0:
            firmware_string = firmware_strings[0]
            self.assertEqual(firmware_string, self.jlink.firmware_version)

    def test_jlink_capabilities(self):
        """Tests the J-Link ``capabilities`` property.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetEmuCaps.return_value = 0
        self.assertEqual(0, self.jlink.capabilities)
        self.assertEqual(1, self.dll.JLINKARM_GetEmuCaps.call_count)

    def test_jlink_extended_capabilities(self):
        """Tests the J-Link ``extended_capabilities`` property.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        result = self.jlink.extended_capabilities
        self.assertTrue(all(map(lambda x: x == 0, result)))
        self.assertEqual(1, self.dll.JLINKARM_GetEmuCapsEx.call_count)

    def test_jlink_has_extended_capability(self):
        """Tests the J-Link ``extended_capability()`` method for checking if an
        emulator has a capability.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EMU_HasCapEx.return_value = 0
        self.assertFalse(self.jlink.extended_capability(0))
        self.assertEqual(1, self.dll.JLINKARM_EMU_HasCapEx.call_count)

        self.dll.JLINKARM_EMU_HasCapEx.return_value = 1
        self.assertTrue(self.jlink.extended_capability(0))
        self.assertEqual(2, self.dll.JLINKARM_EMU_HasCapEx.call_count)

    def test_jlink_features_no_features(self):
        """Tests the J-Link ``features`` property returns an empty list.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        result = self.jlink.features
        self.assertTrue(isinstance(result, list))
        self.assertEqual(0, len(result))

    def test_jlink_features_has_features(self):
        """Tests the J-Link ``features`` property returns a feature list.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        feature_string = 'RDI, JFlash, FlashDL'

        def func(b):
            ctypes.memmove(b, feature_string, len(feature_string))

        self.dll.JLINKARM_GetFeatureString = func

        result = self.jlink.features

        self.assertTrue(isinstance(result, list))
        self.assertEqual(3, len(result))
        self.assertEqual('RDI', result[0])
        self.assertEqual('JFlash', result[1])
        self.assertEqual('FlashDL', result[2])

    def test_jlink_product_name_empty(self):
        """Tests the J-Link ``product_name`` property on empty name.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.assertEqual('', self.jlink.product_name)

    def test_jlink_serial_number(self):
        """Tests the J-Link ``serial_number`` property returns a serial number.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        serial = 0xdeadbeef
        self.dll.JLINKARM_GetSN.return_value = serial
        self.assertEqual(serial, self.jlink.serial_number)

    def test_jlink_oem_failed(self):
        """Tests the J-Link ``oem`` property raises an exception on failure.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetOEMString.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.oem

        self.dll.JLINKARM_GetOEMString.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.oem

    def test_jlink_no_oem(self):
        """Tests the J-Link ``oem`` property when there is no OEM.

        SEGGER branded devices have no OEM, so we should get back an empty
        string (`None`) in this instance.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetOEMString.return_value = 0
        self.assertEqual(None, self.jlink.oem)

    def test_jlink_has_oem(self):
        """Tests the J-Link ``oem`` property when there is an OEM.

        Possible OEMs are: MIDAS, SAM-ICE, DIGI-LINK, Freescale, IAR, and NXP.

        Args:
          self (TestJLink): the ``TestJLink`` instanace

        Returns:
          ``None``
        """
        oems = ['MIDAS', 'SAM-ICE', 'DIGI-LINK', 'Freescale', 'IAR', 'NXP']

        def func(buf):
            oem = oems.pop(0)
            ctypes.memmove(buf, oem, len(oem))
            return 0

        self.dll.JLINKARM_GetOEMString = func

        while len(oems) > 0:
            oem = oems[0]
            self.assertEqual(oem, self.jlink.oem)

    def test_jlink_index(self):
        """Tests the J-Link ``index`` property.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetSelDevice.return_value = 2
        self.assertEqual(2, self.jlink.index)

    def test_jlink_speed_getter(self):
        """Tests getting the speed of the J-Link emulator connection.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetSpeed.return_value = 1
        self.assertEqual(1, self.jlink.speed)
        self.assertEqual(1, self.dll.JLINKARM_GetSpeed.call_count)

    def test_jlink_set_speed_too_fast(self):
        """Tests that an error is raised when specifying a too fast speed.

        When setting the speed of a JTAG communication, there is a maximum
        value that can be given.  This checks that an error is raised if the
        value passed is too large.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaisesRegexp(ValueError, 'exceeds max speed'):
            self.jlink.set_speed(jlink.JLink.MAX_JTAG_SPEED + 1)

        self.assertEqual(0, self.dll.JLINKARM_SetSpeed.call_count)

    def test_jlink_set_speed_too_slow(self):
        """Tests that an error is raised when specifying a too slow speed.

        When setting the speed of a JTAG communication, there is a minimum
        value that can be given.  This checks that an error is raised if the
        value passed is too small.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaisesRegexp(ValueError, 'is too slow'):
            self.jlink.set_speed(jlink.JLink.MIN_JTAG_SPEED - 1)

        self.assertEqual(0, self.dll.JLINKARM_SetSpeed.call_count)

    def test_jlink_set_speed_non_number(self):
        """Tests that an error is raised when specifying a non-numeric speed.

        If we give a speed, the speed must be a natural number.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(TypeError):
            self.jlink.set_speed(-1)

        with self.assertRaises(TypeError):
            self.jlink.set_speed('dog')

        self.assertEqual(0, self.dll.JLINKARM_SetSpeed.call_count)

    def test_jlink_set_speed_auto(self):
        """Tests setting an automatic speed.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_speed(auto=True)
        self.dll.JLINKARM_SetSpeed.assert_called_once_with(0)

    def test_jlink_set_speed_adaptive(self):
        """Tests setting an adaptive speed.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_speed(adaptive=True)
        self.dll.JLINKARM_SetSpeed.assert_called_once_with(jlink.JLink.ADAPTIVE_JTAG_SPEED)

    def test_jlink_set_speed_speed(self):
        """Tests setting a valid numeric speed.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_speed(12)
        self.dll.JLINKARM_SetSpeed.assert_called_once_with(12)

    def test_jlink_set_max_speed(self):
        """Tests the J-Link ``set_max_speed()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.assertEqual(None, self.jlink.set_max_speed())
        self.assertEqual(1, self.dll.JLINKARM_SetMaxSpeed.call_count)

    def test_jlink_speed_info(self):
        """Tests the J-Link ``speed_info`` property.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        info = self.jlink.speed_info
        self.assertTrue(isinstance(info, structs.JLinkSpeedInfo))

    def test_jlink_builtin_licenses_fail_to_read(self):
        """Tests the J-Link ``licenses`` property generates an error.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_GetAvailableLicense.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.licenses

    def test_jlink_builtin_licenses_empty(self):
        """Tests that the J-Link ``buitlin_licenses`` property returns an empty
        string.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_GetAvailableLicense.return_value = 0
        self.assertEqual('', self.jlink.licenses)

    def test_jlink_custom_licenses_fail_to_read(self):
        """Tests the J-Link fail to read the custom licenses.

        Two possible fail conditions:
          - JLink error.
          - Unsupported on current SDK.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 49800

        with self.assertRaisesRegexp(JLinkException, 'Version 4.98b required'):
            self.jlink.custom_licenses

        self.dll.JLINKARM_GetDLLVersion.return_value = 49802
        self.dll.JLINK_EMU_GetLicenses.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.custom_licenses

    def test_jlink_custom_licenses_empty(self):
        """Tests that the J-Link when there are no custom licenses.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 49802
        self.dll.JLINK_EMU_GetLicenses.return_value = 0
        self.assertEqual('', self.jlink.custom_licenses)

    def test_jlink_add_license_failure(self):
        """Tests add license failing due to the possible error states.

        Error states are:
          - Unsupported SDK.
          - Unspecified (error code -1).
          - Failed to read / write license area (error code -2).
          - Not enough space to store license (error code -3).

        Args:
          self (TestJLink): the ``TestJLink`` instnace

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 49800

        with self.assertRaisesRegexp(JLinkException, 'Version 4.98b required'):
            self.jlink.add_license('license')

        self.dll.JLINKARM_GetDLLVersion.return_value = 49801

        with self.assertRaisesRegexp(JLinkException, 'Version 4.98b required'):
            self.jlink.add_license('license')

        self.dll.JLINKARM_GetDLLVersion.return_value = 49802

        self.dll.JLINK_EMU_AddLicense.return_value = -1

        with self.assertRaisesRegexp(JLinkException, 'Unspecified error'):
            self.jlink.add_license('license')

        self.dll.JLINK_EMU_AddLicense.return_value = -2

        with self.assertRaisesRegexp(JLinkException, 'read/write'):
            self.jlink.add_license('license')

        self.dll.JLINK_EMU_AddLicense.return_value = -3

        with self.assertRaisesRegexp(JLinkException, 'space'):
            self.jlink.add_license('license')

    def test_jlink_add_license(self):
        """Tests adding a license and succeeding.

        The second time a same license is added to a device, the J-Link returns
        to indicate that the license already exists.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 49802
        self.dll.JLINK_EMU_AddLicense.return_value = 0
        self.assertTrue(self.jlink.add_license('license'))

        self.dll.JLINK_EMU_AddLicense.return_value = 1
        self.assertFalse(self.jlink.add_license('license'))

    def test_jlink_erase_licenses_failed(self):
        """Tests when erasing licenses fails.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 49800

        with self.assertRaisesRegexp(JLinkException, 'Version 4.98b required'):
            self.jlink.erase_licenses()

        self.dll.JLINKARM_GetDLLVersion.return_value = 49802
        self.dll.JLINK_EMU_EraseLicenses.return_value = -1
        self.assertFalse(self.jlink.erase_licenses())

    def test_jlink_erase_license_success(self):
        """Tests when erasing licenses succeeds.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetDLLVersion.return_value = 49802
        self.dll.JLINK_EMU_EraseLicenses.return_value = 0
        self.assertTrue(self.jlink.erase_licenses())

    def test_jlink_tif(self):
        """Tests the J-Link ``tif`` getter.

        When a J-Link is created, this should be JTAG.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.assertEqual(enums.JLinkInterfaces.JTAG, self.jlink.tif)

    def test_jlink_supported_tifs(self):
        """Tests the J-Link ``supported_tifs`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.assertEqual(0, self.jlink.supported_tifs())

    def test_jlink_set_tif_unsupported(self):
        """Tests that an exception is raised when setting an unsupported TIF.

        If the target interface is not supported by the J-Link, trying to set
        it will raise an exception.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.supported_tifs = mock.Mock()
        self.jlink.supported_tifs.return_value = 0

        with self.assertRaises(JLinkException):
            self.jlink.set_tif(enums.JLinkInterfaces.SPI)

    def test_jlink_set_tif_failed(self):
        """Tests for failing to set the TIF.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.supported_tifs = mock.Mock()
        self.jlink.supported_tifs.return_value = (1 << enums.JLinkInterfaces.JTAG)

        self.dll.JLINKARM_TIF_Select.return_value = 1
        self.assertFalse(self.jlink.set_tif(enums.JLinkInterfaces.JTAG))

    def test_jlink_set_tif_success(self):
        """Tests for successfully setting a TIF.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.supported_tifs = mock.Mock()
        self.jlink.supported_tifs.return_value = (1 << enums.JLinkInterfaces.JTAG)

        self.dll.JLINKARM_TIF_Select.return_value = 0
        self.assertTrue(self.jlink.set_tif(enums.JLinkInterfaces.JTAG))

    def test_jlink_gpio_properties_failure(self):
        """Tests for failing to get the emulator's GPIO descriptors.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_EMU_GPIO_GetProps.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.gpio_properties()

        self.assertEqual(1, self.dll.JLINK_EMU_GPIO_GetProps.call_count)

        self.dll.JLINK_EMU_GPIO_GetProps = mock.Mock()
        self.dll.JLINK_EMU_GPIO_GetProps.side_effect = [1, -1]

        with self.assertRaises(JLinkException):
            self.jlink.gpio_properties()

        self.assertEqual(2, self.dll.JLINK_EMU_GPIO_GetProps.call_count)

    def test_jlink_gpio_properties_success(self):
        """Tests for succeeding in getting the emulator's GPIO descriptors.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_EMU_GPIO_GetProps.side_effect = [1, 1]

        props = self.jlink.gpio_properties()
        self.assertEqual(2, self.dll.JLINK_EMU_GPIO_GetProps.call_count)
        self.assertTrue(isinstance(props, list))
        self.assertEqual(1, len(props))
        self.assertTrue(all(map(lambda x: isinstance(x, structs.JLinkGPIODescriptor), props)))

    def test_jlink_gpio_get_failure(self):
        """Tests when getting GPIO pin states returns an error.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_EMU_GPIO_GetState.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.gpio_get()

        with self.assertRaises(JLinkException):
            self.jlink.gpio_get([1, 2, 3])

    def test_jlink_gpio_get_success(self):
        """Tests getting the GPIO pin states successfully.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_EMU_GPIO_GetState.return_value = 0

        res = self.jlink.gpio_get([])

        self.assertTrue(isinstance(res, list))
        self.assertEqual(0, len(res))

    def test_jlink_gpio_set_length_mismatch(self):
        """Tests failure to set GPIO pin states due to length mismatch.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(ValueError):
            self.jlink.gpio_set([], [0])

        with self.assertRaises(ValueError):
            self.jlink.gpio_set([0], [])

        with self.assertRaises(ValueError):
            self.jlink.gpio_set([2, 3, 4], [0, 1])

    def test_jlink_gpio_set_failure(self):
        """Tests failure to set the GPIO pin states.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        pins = [2, 3]
        statuses = [1, 0]
        self.dll.JLINK_EMU_GPIO_SetState.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.gpio_set(pins, statuses)

    def test_jlink_gpio_set_success(self):
        """Tests succussfully setting the GPIO pin states.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_EMU_GPIO_SetState.return_value = 0

        pins = [2, 3]
        statuses = [1, 0]
        res = self.jlink.gpio_set(pins, statuses)

        self.assertTrue(isinstance(res, list))
        self.assertEqual(2, len(res))

    def test_jlink_comm_supported(self):
        """Tests the J-Link ``comm_supported()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EMU_COM_IsSupported.return_value = 0
        self.assertFalse(self.jlink.comm_supported())

        self.dll.JLINKARM_EMU_COM_IsSupported.return_value = 1
        self.assertTrue(self.jlink.comm_supported())

    @mock.patch('pylink.unlockers.unlock')
    def test_jlink_unlock_kinetis(self, mock_unlock):
        """Tests calling unlock on a connected Kinetis device.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_unlock (Mock): mocked unlock call

        Returns:
          ``None``
        """
        device = mock.Mock()
        device.manufacturer = 'Freescale'
        mock_unlock.side_effect = [True, False]

        self.jlink._device = device

        self.assertEqual(True, self.jlink.unlock())

        mock_unlock.assert_called_with(self.jlink, device.manufacturer)

        with self.assertRaisesRegexp(JLinkException, 'Failed to unlock device'):
            self.jlink.unlock()

    def test_jlink_cpu_capability(self):
        """Tests the J-Link ``cpu_capability()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EMU_HasCPUCap.return_value = 0
        self.assertFalse(self.jlink.cpu_capability(0))

        self.dll.JLINKARM_EMU_HasCPUCap.return_value = 1
        self.assertTrue(self.jlink.cpu_capability(0))

    def test_jlink_set_trace_source(self):
        """Tests the J-Link ``set_trace_source()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        source = 0xdeadbeef
        self.jlink.set_trace_source(source)
        self.dll.JLINKARM_SelectTraceSource.assert_called_with(source)

    def test_jlink_set_etb_trace(self):
        """Tests setting ETB as the trace source.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_etb_trace()
        self.dll.JLINKARM_SelectTraceSource.assert_called_with(0)

    def test_jlink_set_etm_trace(self):
        """Tests setting ETM as the trace source.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_etm_trace()
        self.dll.JLINKARM_SelectTraceSource.assert_called_with(1)

    def test_jlink_power_on(self):
        """Tests the J-Link ``power_on()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.exec_command = mock.Mock()
        self.jlink.power_on()
        self.jlink.exec_command.assert_called_once_with('SupplyPower = 1')

        self.jlink.exec_command = mock.Mock()
        self.jlink.power_on(default=True)
        self.jlink.exec_command.assert_called_once_with('SupplyPowerDefault = 1')

    def test_jlink_power_off(self):
        """Tests the J-Link ``power_off()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.exec_command = mock.Mock()
        self.jlink.power_off()
        self.jlink.exec_command.assert_called_once_with('SupplyPower = 0')

        self.jlink.exec_command = mock.Mock()
        self.jlink.power_off(default=True)
        self.jlink.exec_command.assert_called_once_with('SupplyPowerDefault = 0')

    def test_jlink_set_reset_strategy(self):
        """Tests the J-Link ``set_reset_strategy()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        strategy = 1
        self.dll.JLINKARM_SetResetType.return_value = 0

        self.assertEqual(0, self.jlink.set_reset_strategy(strategy))
        self.dll.JLINKARM_SetResetType.assert_called_once_with(strategy)

    def test_jlink_set_reset_pin(self):
        """Tests the J-Link ``set_reset_pin_*`` methods.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_reset_pin_high()
        self.dll.JLINKARM_SetRESET.assert_called_once()

        self.jlink.set_reset_pin_low()
        self.dll.JLINKARM_ClrRESET.assert_called_once()

    def test_jlink_set_tck_pin(self):
        """Tests the J-Link ``set_tck_pin_*`` methods.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SetTCK.return_value = 0
        self.jlink.set_tck_pin_high()
        self.dll.JLINKARM_SetTCK.assert_called_once()

        self.dll.JLINKARM_SetTCK.return_value = -1
        with self.assertRaisesRegexp(JLinkException, 'Feature not supported'):
            self.jlink.set_tck_pin_high()

        self.dll.JLINKARM_ClrTCK.return_value = 0
        self.jlink.set_tck_pin_low()
        self.dll.JLINKARM_ClrTCK.assert_called_once()

        self.dll.JLINKARM_ClrTCK.return_value = -1
        with self.assertRaisesRegexp(JLinkException, 'Feature not supported'):
            self.jlink.set_tck_pin_low()

    def test_jlink_set_tdi_pin(self):
        """Tests the J-Link ``set_tdi_pin_*`` methods.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_tdi_pin_high()
        self.dll.JLINKARM_SetTDI.assert_called_once()

        self.jlink.set_tdi_pin_low()
        self.dll.JLINKARM_ClrTDI.assert_called_once()

    def test_jlink_set_tms_pin(self):
        """Tests the J-Link ``set_tms_pin_*`` methods.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_tms_pin_high()
        self.dll.JLINKARM_SetTMS.assert_called_once()

        self.jlink.set_tms_pin_low()
        self.dll.JLINKARM_ClrTMS.assert_called_once()

    def test_jlink_set_trst_pin(self):
        """Tests the J-Link ``set_trst_pin_*`` methods.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.set_trst_pin_high()
        self.dll.JLINKARM_SetTRST.assert_called_once()

        self.jlink.set_trst_pin_low()
        self.dll.JLINKARM_ClrTRST.assert_called_once()

    def test_jlink_erase_failed_to_halt(self):
        """Tests the J-Link ``erase()`` method when device fails to halt.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.halted = mock.Mock()
        self.jlink.halted.side_effect = JLinkException(-1)

        self.jlink.halt = mock.Mock()

        self.dll.JLINK_EraseChip.return_value = 0
        self.assertEqual(0, self.jlink.erase())

        self.assertEqual(1, self.dll.JLINK_EraseChip.call_count)
        self.assertEqual(0, self.jlink.halt.call_count)

    def test_jlinK_erase_failed(self):
        """Tests the J-Link ``erase()`` method when it fails to erase.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.halted = mock.Mock()
        self.jlink.halted.side_effect = JLinkException(-1)

        self.jlink.halt = mock.Mock()

        self.dll.JLINK_EraseChip.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.erase()

        self.assertEqual(1, self.dll.JLINK_EraseChip.call_count)
        self.assertEqual(0, self.jlink.halt.call_count)

    def test_jlink_erase_success(self):
        """Tests a successful erase of the target.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.halted = mock.Mock()
        self.jlink.halted.return_value = False

        self.jlink.halt = mock.Mock()

        self.dll.JLINK_EraseChip.return_value = 1
        self.assertEqual(1, self.jlink.erase())

        self.assertEqual(1, self.dll.JLINK_EraseChip.call_count)
        self.assertEqual(1, self.jlink.halt.call_count)

    def test_jlink_flash_invalid_flags(self):
        """Tests trying to flash with invalid flags that an error is raised.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(JLinkException):
            self.jlink.flash([0], 0, flags=-1)

        with self.assertRaises(JLinkException):
            self.jlink.flash([0], 0, flags=1)

    def test_jlink_flash_fail_to_flash(self):
        """Tests when the flash fails.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EndDownload.return_value = -1

        self.jlink.power_on = mock.Mock()
        self.jlink.erase = mock.Mock()
        self.jlink.memory_write = mock.Mock()

        self.jlink.halted = mock.Mock()
        self.jlink.halted.return_value = True

        with self.assertRaises(JLinkException):
            self.jlink.flash([0], 0)

    def test_jlink_flash_success(self):
        """Tests a successful flash.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_EndDownload.return_value = 0

        self.jlink.power_on = mock.Mock()
        self.jlink.erase = mock.Mock()
        self.jlink.memory_write = mock.Mock()

        self.jlink.halt = mock.Mock()
        self.jlink.halted = mock.Mock()
        self.jlink.halted.return_value = True

        # With a progress callback.
        self.assertEqual(0, self.jlink.flash([0], 0, util.noop))
        self.dll.JLINK_SetFlashProgProgressCallback.assert_called_once()

        arg = self.dll.JLINK_SetFlashProgProgressCallback.call_args[0][0]
        self.assertTrue(callable(arg))

        # Without a progress callback
        self.assertEqual(0, self.jlink.flash([0], 0))
        self.dll.JLINK_SetFlashProgProgressCallback.assert_called_with(0)

        # Halted exception
        self.jlink.halted.side_effect = JLinkException(-1)
        self.assertEqual(0, self.jlink.flash([0], 0))
        self.jlink.halted.side_effect = None

        # Not halted
        self.jlink.halted.return_value = False
        self.assertEqual(0, self.jlink.flash([0], 0))
        self.jlink.halt.assert_called_once()

        # Halted
        self.jlink.halted.return_value = True
        self.assertEqual(0, self.jlink.flash([0], 0))
        self.jlink.halt.assert_called_once()

    def test_jlink_flash_file_fail_to_flash(self):
        """Tests when the flash fails.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_DownloadFile.return_value = -1

        self.jlink.halted = mock.Mock()
        self.jlink.halted.return_value = True

        self.jlink.power_on = mock.Mock()
        self.jlink.erase = mock.Mock()

        with self.assertRaises(JLinkException):
            self.jlink.flash_file('path', 0)

    def test_jlink_flash_file_success(self):
        """Tests a successful flash.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_DownloadFile.return_value = 0

        self.jlink.halted = mock.Mock()
        self.jlink.halted.return_value = True

        self.jlink.halt = mock.Mock()
        self.jlink.power_on = mock.Mock()
        self.jlink.erase = mock.Mock()

        # With a progress callback.
        self.assertEqual(0, self.jlink.flash_file('path', 0, util.noop))
        self.dll.JLINK_SetFlashProgProgressCallback.assert_called_once()

        arg = self.dll.JLINK_SetFlashProgProgressCallback.call_args[0][0]
        self.assertTrue(callable(arg))

        # Without a progress callback
        self.assertEqual(0, self.jlink.flash_file('path', 0))
        self.dll.JLINK_SetFlashProgProgressCallback.assert_called_with(0)

        # Halted exception
        self.jlink.halted.side_effect = JLinkException(-1)
        self.assertEqual(0, self.jlink.flash_file('path', 0))
        self.jlink.halted.side_effect = None

        # Not halted
        self.jlink.halted.return_value = False
        self.assertEqual(0, self.jlink.flash_file('path', 0))
        self.jlink.halt.assert_called_once()

        # Halted
        self.jlink.halted.return_value = True
        self.assertEqual(0, self.jlink.flash_file('path', 0))
        self.jlink.halt.assert_called_once()

    def test_jlink_reset_fail(self):
        """Tests J-Link ``reset()`` when it fails.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_Reset.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.reset()

        self.dll.JLINKARM_SetResetDelay.assert_called_once()

    def test_jlink_reset_halt(self):
        """Tests J-Link ``reset()`` success with halt.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_Reset.return_value = 0

        self.assertEqual(0, self.jlink.reset())

        self.dll.JLINKARM_Reset.assert_called_once()
        self.dll.JLINKARM_Go.assert_not_called()
        self.dll.JLINKARM_SetResetDelay.assert_called_once()

    def test_jlink_reset_no_halt(self):
        """Tests J-Link ``reset()`` without halt.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_Reset.return_value = 0

        self.assertEqual(0, self.jlink.reset(halt=False))

        self.dll.JLINKARM_Reset.assert_called_once()
        self.dll.JLINKARM_Go.assert_called_once()
        self.dll.JLINKARM_SetResetDelay.assert_called_once()

    def test_jlink_reset_tap(self):
        """Tests resetting the TAP controller.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.reset_tap()
        self.dll.JLINKARM_ResetTRST.assert_called_once()

    def test_jlink_restart_invalid_instructions(self):
        """Tests J-Link ``restart()`` with an invalid number of ops to
        simulate.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(ValueError):
            self.jlink.restart(-1)

        with self.assertRaises(ValueError):
            self.jlink.restart('dog')

    def test_jlink_restart_not_halted(self):
        """Tests J-Link ``restart()`` when the target is not halted.

        If the target is not halted, ``restart()`` is a no-op.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.halted = mock.Mock()
        self.jlink.halted.return_value = False

        self.assertEqual(False, self.jlink.restart())

    def test_jlink_restarted(self):
        """Tests J-Link ``restart()`` successfully restarting the target.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.halted = mock.Mock()
        self.jlink.halted.return_value = True

        self.assertEqual(True, self.jlink.restart())
        self.dll.JLINKARM_GoEx.called_once_with(0, 0)

        self.dll.JLINKARM_GoEx = mock.Mock()

        self.assertEqual(True, self.jlink.restart(10, skip_breakpoints=True))
        self.dll.JLINKARM_GoEx.called_once_with(10, enums.JLinkFlags.GO_OVERSTEP_BP)

    @mock.patch('time.sleep')
    def test_jlink_halt_failure(self, mock_sleep):
        """Tests J-Link ``halt()`` failure.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked ``time.sleep()`` call

        Returns:
          ``None``
        """
        self.dll.JLINKARM_Halt.return_value = 1
        self.assertEqual(False, self.jlink.halt())

        self.dll.JLINKARM_Halt.return_value = -1
        self.assertEqual(False, self.jlink.halt())

        self.assertEqual(0, mock_sleep.call_count)

    @mock.patch('time.sleep')
    def test_jlink_halt_success(self, mock_sleep):
        """Tests J-Link ``halt()`` success.

        Args:
          self (TestJLink): the ``TestJLink`` instance
          mock_sleep (Mock): mocked ``time.sleep()`` call

        Returns:
          ``None``
        """
        self.dll.JLINKARM_Halt.return_value = 0
        self.assertEqual(True, self.jlink.halt())
        self.assertEqual(1, mock_sleep.call_count)

    def test_jlink_halted_on_error(self):
        """Tests when querying if the target is halted fails.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_IsHalted.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.halted()

    def test_jlink_halted_on_success(self):
        """Tests when querying if the target is halted succeeds.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_IsHalted.return_value = 1
        self.assertEqual(True, self.jlink.halted())

        self.dll.JLINKARM_IsHalted.return_value = 255
        self.assertEqual(True, self.jlink.halted())

        self.dll.JLINKARM_IsHalted.return_value = 0
        self.assertEqual(False, self.jlink.halted())

    def test_jlink_core_id(self):
        """Tests the J-Link ``core_id()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        core_id = 1337
        self.dll.JLINKARM_GetId.return_value = core_id
        self.assertEqual(core_id, self.jlink.core_id())

    def test_jlink_core_cpu(self):
        """Tests the J-Link ``core_cpu()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        core_cpu = 234881279
        self.dll.JLINKARM_CORE_GetFound.return_value = core_cpu
        self.assertEqual(core_cpu, self.jlink.core_cpu())

    def test_jlink_core_name(self):
        """Tests retrieving the CPU core's name.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        core_cpu = 234881279
        core_name = 'Cortex-M4'
        self.dll.JLINKARM_CORE_GetFound.return_value = core_cpu

        def write_core_name(cpu, buf, buf_size):
            for (index, ch) in enumerate(core_name):
                buf[index] = ch
            self.assertEqual(cpu, core_cpu)

        self.dll.JLINKARM_Core2CoreName.side_effect = write_core_name

        self.assertEqual(core_name, self.jlink.core_name())

        self.dll.JLINKARM_CORE_GetFound.assert_called_once()
        self.dll.JLINKARM_Core2CoreName.assert_called_once()

    def test_jlink_ir_len(self):
        """Tests the J-Link ``ir_len()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        ir_len = 2
        self.dll.JLINKARM_GetIRLen.return_value = ir_len
        self.assertEqual(ir_len, self.jlink.ir_len())

    def test_jlink_scan_len(self):
        """Tests the J-Link ``scan_len()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        scan_len = 2
        self.dll.JLINKARM_GetScanLen.return_value = scan_len
        self.assertEqual(scan_len, self.jlink.scan_len())

    def test_jlink_scan_chain_len(self):
        """Tests getting the scan chain length of the J-Link.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        scan_chain = 1

        self.dll.JLINKARM_MeasureSCLen.return_value = -1
        with self.assertRaises(JLinkException):
            self.jlink.scan_chain_len(scan_chain)

        self.dll.JLINKARM_MeasureSCLen.return_value = 0
        self.assertEqual(0, self.jlink.scan_chain_len(scan_chain))

    def test_jlink_device_family(self):
        """Tests the J-Link ``device_family()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        family = enums.JLinkDeviceFamily.CORTEX_M1
        self.dll.JLINKARM_GetDeviceFamily.return_value = family
        self.assertEqual(family, self.jlink.device_family())

        family = enums.JLinkDeviceFamily.CORTEX_M3
        self.dll.JLINKARM_GetDeviceFamily.return_value = family
        self.assertEqual(family, self.jlink.device_family())

    def test_jlink_register_list(self):
        """Tests the J-Link ``register_list()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetRegisterList.return_value = 0

        res = self.jlink.register_list()
        self.assertTrue(isinstance(res, list))
        self.assertEqual(0, len(res))

    def test_jlink_register_name(self):
        """Tests the J-Link ``register_name()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        register_name = 'Name'
        buf = ctypes.create_string_buffer(register_name, len(register_name))
        self.dll.JLINKARM_GetRegisterName.return_value = ctypes.addressof(buf)

        self.assertEqual(register_name, self.jlink.register_name(0))

    def test_jlink_cpu_speed_error(self):
        """Tests the J-Link ``cpu_speed()`` method on error.

        Args:
          self (TestJlink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_MeasureCPUSpeedEx.return_value = -1
        with self.assertRaises(JLinkException):
            self.jlink.cpu_speed()

    def test_jlink_cpu_speed_success(self):
        """Tests the J-Link ``cpu_speed()`` method on success.

        There are three cases:
          - When silent option is passed.
          - When silent option is not passed.
          - When CPU speed is not supported.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        # Unsupported
        self.dll.JLINKARM_MeasureCPUSpeedEx.return_value = 0
        self.assertEqual(0, self.jlink.cpu_speed())

        # Silent option not passed
        self.dll.JLINKARM_MeasureCPUSpeedEx.return_value = 1
        self.assertEqual(1, self.jlink.cpu_speed())
        self.dll.JLINKARM_MeasureCPUSpeedEx.assert_called_with(-1, 1, 0)

        # Silent option passed
        self.dll.JLINKARM_MeasureCPUSpeedEx.return_value = 1
        self.assertEqual(1, self.jlink.cpu_speed(silent=True))
        self.dll.JLINKARM_MeasureCPUSpeedEx.assert_called_with(-1, 1, 1)

    def test_jlink_cpu_halt_reasons_failure(self):
        """Tests failing to get the CPU halt reasons.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetMOEs.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.cpu_halt_reasons()

    def test_jlink_cpu_halt_reasons_success(self):
        """Tests successfully getting the CPU halt reasons.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetMOEs.return_value = 0

        halt_reasons = self.jlink.cpu_halt_reasons()
        self.assertTrue(isinstance(halt_reasons, list))
        self.assertEqual(0, len(halt_reasons))

        self.dll.JLINKARM_GetMOEs.return_value = 1

        halt_reasons = self.jlink.cpu_halt_reasons()
        self.assertTrue(isinstance(halt_reasons, list))
        self.assertEqual(1, len(halt_reasons))
        self.assertTrue(isinstance(halt_reasons[0], structs.JLinkMOEInfo))

    def test_jlink_jtag_create_clock(self):
        """Tests creating a JTAG clock on TCK.

        Should return the status of the TDO pin: either 0 or 1.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_Clock.return_value = 0
        self.assertEqual(0, self.jlink.jtag_create_clock())

        self.dll.JLINKARM_Clock.return_value = 1
        self.assertEqual(1, self.jlink.jtag_create_clock())

    def test_jlink_jtag_send_invalid_bits(self):
        """Tests passing an invalid number of bits to ``jtag_send()``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        tms = 0
        tdi = 0

        num_bits = 0
        with self.assertRaises(ValueError):
            self.jlink.jtag_send(tms, tdi, num_bits)

        num_bits = -1
        with self.assertRaises(ValueError):
            self.jlink.jtag_send(tms, tdi, num_bits)

        num_bits = 33
        with self.assertRaises(ValueError):
            self.jlink.jtag_send(tms, tdi, num_bits)

    def test_jlink_jtag_send_success(self):
        """Tests successfully sending data via JTAG.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        tms = 0
        tdi = 0
        num_bits = 1

        self.assertEqual(None, self.jlink.jtag_send(tms, tdi, num_bits))

    def test_jlink_jtag_flush(self):
        """Tests successfully flushing the JTAG buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.jtag_flush()
        self.dll.JLINKARM_WriteBits.assert_called_once()

    def test_jlink_swd_read8(self):
        """Tests the J-Link ``swd_read8()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        val = 10
        self.dll.JLINK_SWD_GetU8.return_value = val

        self.assertEqual(val, self.jlink.swd_read8(0))

    def test_jlink_swd_read16(self):
        """Tests the J-Link ``swd_read16()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        val = 10
        self.dll.JLINK_SWD_GetU16.return_value = val

        self.assertEqual(val, self.jlink.swd_read16(0))

    def test_jlink_swd_read32(self):
        """Tests the J-Link ``swd_read32()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        val = 10
        self.dll.JLINK_SWD_GetU32.return_value = val

        self.assertEqual(val, self.jlink.swd_read32(0))

    def test_jlink_swd_write_fail(self):
        """Tests the J-Link ``swd_write()`` method on failure.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        self.dll.JLINK_SWD_StoreRaw.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swd_write(0, 0, 32)

    def test_jlink_swd_write_success(self):
        """Tests the J-Link ``swd_write()`` method on success.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        bitpos = 1
        self.dll.JLINK_SWD_StoreRaw.return_value = bitpos

        self.assertEqual(bitpos, self.jlink.swd_write(8, 8, 8))
        self.dll.JLINK_SWD_StoreRaw.assert_called_once()

    def test_jlink_swd_write8(self):
        """Tests the J-Link ``swd_write8()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        self.jlink.swd_write = mock.Mock()
        self.jlink.swd_write8(0, 0)
        self.jlink.swd_write.assert_called_once_with(0, 0, 8)

    def test_jlink_swd_write16(self):
        """Tests the J-Link ``swd_write16()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        self.jlink.swd_write = mock.Mock()
        self.jlink.swd_write16(0, 0)
        self.jlink.swd_write.assert_called_once_with(0, 0, 16)

    def test_jlink_swd_write32(self):
        """Tests the J-Link ``swd_write32()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        self.jlink.swd_write = mock.Mock()
        self.jlink.swd_write32(0, 0)
        self.jlink.swd_write.assert_called_once_with(0, 0, 32)

    def test_jlink_swd_sync(self):
        """Tests the J-Link ``swd_sync()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink._tif = enums.JLinkInterfaces.SWD

        self.assertEqual(None, self.jlink.swd_sync())
        self.dll.JLINK_SWD_SyncBits.assert_called_once()

        self.assertEqual(None, self.jlink.swd_sync(pad=True))
        self.dll.JLINK_SWD_SyncBytes.assert_called_once()

    def test_jlink_flash_write_access_width(self):
        """Tests calling the flash write methods with variable access width.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        addr = 0xdeadbeef
        self.jlink.flash_write = mock.Mock()
        self.jlink.flash_write8(addr, [0xFF])
        self.jlink.flash_write.assert_called_with(addr, [0xFF], 8)

        self.jlink.flash_write16(addr, [0xFFFF])
        self.jlink.flash_write.assert_called_with(addr, [0xFFFF], 16)

        self.jlink.flash_write32(addr, [0xFFFFFFFF])
        self.jlink.flash_write.assert_called_with(addr, [0xFFFFFFFF], 32)

    def test_jlink_code_memory_read_invalid(self):
        """Tests failing to read code memory.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadCodeMem.return_value = -1
        with self.assertRaises(JLinkException):
            self.jlink.code_memory_read(0, 1)

    def test_jlink_code_memory_read_success(self):
        """Tests successfully reading code memory.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadCodeMem.return_value = 0

        res = self.jlink.code_memory_read(0, 1)
        self.assertTrue(isinstance(res, list))
        self.assertEqual(0, len(res))

        self.dll.JLINKARM_ReadCodeMem.return_value = 1

        res = self.jlink.code_memory_read(0, 1)
        self.assertTrue(isinstance(res, list))
        self.assertEqual(1, len(res))
        self.assertTrue(isinstance(res[0], int))

    def test_jlink_num_memory_zones(self):
        """Tests the J-Link ``num_memory_zones()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_GetMemZones.return_value = -1
        with self.assertRaises(JLinkException):
            self.jlink.num_memory_zones()

        self.dll.JLINK_GetMemZones.return_value = 2
        self.assertEqual(2, self.jlink.num_memory_zones())

    def test_jlink_memory_zones_empty(self):
        """Tests the J-Link ``memory_zones()`` method with no zones.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.num_memory_zones = mock.Mock()
        self.jlink.num_memory_zones.return_value = 0

        res = self.jlink.memory_zones()
        self.assertTrue(isinstance(res, list))
        self.assertEqual(0, len(res))

        self.assertEqual(0, self.dll.JLINK_GetMemZones.call_count)

    def test_jlink_memory_zones_failure(self):
        """Tests the J-Link ``memory_zones()`` method on failure.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.num_memory_zones = mock.Mock()
        self.jlink.num_memory_zones.return_value = 1

        self.dll.JLINK_GetMemZones.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.memory_zones()

    def test_jlink_memory_zones_success(self):
        """Tests the J-Link ``memory_zones()`` on success.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.num_memory_zones = mock.Mock()
        self.jlink.num_memory_zones.return_value = 1

        res = self.jlink.memory_zones()
        self.assertTrue(isinstance(res, list))
        self.assertEqual(1, len(res))
        self.assertTrue(all(map(lambda x: isinstance(x, structs.JLinkMemoryZone), res)))

        self.assertEqual(1, self.dll.JLINK_GetMemZones.call_count)

    def test_jlink_memory_read_failure(self):
        """Tests a memory read that fails to read.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadMemEx.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.memory_read(0, 1)

    def test_jlink_memory_read_invalid_access(self):
        """Tests the memory read fails when given an invalid access width.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(ValueError):
            self.jlink.memory_read(0, 0, nbits=42)

        with self.assertRaises(ValueError):
            self.jlink.memory_read(0, 0, nbits=13)

        with self.assertRaises(ValueError):
            self.jlink.memory_read(0, 0, nbits=-1)

    def test_jlink_memory_read_zoned(self):
        """Tests a memory read of a zoned memory region.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadMemZonedEx.return_value = 0

        res = self.jlink.memory_read(0, 1, 'zone')

        self.assertTrue(isinstance(res, list))
        self.assertEqual(0, len(res))

        self.dll.JLINKARM_ReadMemZonedEx.assert_called_once()
        self.dll.JLINKARM_ReadMemEx.assert_not_called()

    def test_jlink_memory_read_unzoned(self):
        """Tests a memory read of an unzoned region.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadMemEx.return_value = 0

        res = self.jlink.memory_read(0, 1)

        self.assertTrue(isinstance(res, list))
        self.assertEqual(0, len(res))

        self.dll.JLINKARM_ReadMemEx.assert_called_once()
        self.dll.JLINKARM_ReadMemZonedEx.assert_not_called()

    def test_jlink_memory_read_access(self):
        """Tests the different memory read access bits.

        There are three types of ways to access memory: by byte, by halfword,
        and by word.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        num_units = 4
        accesses = [1, 2, 4]

        def write_to_memory(addr, buf_size, buf, access):
            self.assertEqual(num_units * access, buf_size)

            # Write a byte first
            buf[0] = 0xFF

            # Write a halfword next
            buf[1] = 0xFF00

            # Write a word next
            buf[2] = 0xFFFF0000

            # Write a long word next
            buf[3] = 0xFFFFFFFF00000000

            self.assertEqual(accesses.pop(0), access)

            return num_units

        self.dll.JLINKARM_ReadMemEx.side_effect = write_to_memory
        self.dll.JLINKARM_ReadMemEx.return_value = num_units

        res = self.jlink.memory_read(0, num_units, nbits=8)
        self.assertEqual(num_units, len(res))
        self.assertEqual(0xFF, res[0])
        self.assertEqual(0x00, res[1])
        self.assertEqual(0x00, res[2])
        self.assertEqual(0x00, res[3])

        res = self.jlink.memory_read(0, num_units, nbits=16)
        self.assertEqual(num_units, len(res))
        self.assertEqual(0xFF, res[0])
        self.assertEqual(0xFF00, res[1])
        self.assertEqual(0x00, res[2])
        self.assertEqual(0x00, res[3])

        res = self.jlink.memory_read(0, num_units, nbits=32)
        self.assertEqual(num_units, len(res))
        self.assertEqual(0xFF, res[0])
        self.assertEqual(0xFF00, res[1])
        self.assertEqual(0xFFFF0000, res[2])
        self.assertEqual(0x00, res[3])

    def test_jlink_memory_read_byte_halfword_word(self):
        """Tests the memory read functions for bytes, halfwords and words.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.memory_read = mock.Mock()

        self.jlink.memory_read8(0, 0)
        self.jlink.memory_read.assert_called_with(0, 0, nbits=8, zone=None)

        self.jlink.memory_read16(0, 0)
        self.jlink.memory_read.assert_called_with(0, 0, zone=None, nbits=16)

        self.jlink.memory_read32(0, 0)
        self.jlink.memory_read.assert_called_with(0, 0, zone=None, nbits=32)

    def test_jlink_memory_read_longword(self):
        """Tests the memory read function for a longword.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadMemU64.return_value = -1
        with self.assertRaises(JLinkException):
            self.jlink.memory_read64(0, 0)

        self.dll.JLINKARM_ReadMemU64.return_value = 0

        res = self.jlink.memory_read64(0, 0)
        self.assertTrue(isinstance(res, list))
        self.assertEqual(0, len(res))

    def test_jlink_memory_write_invalid_access(self):
        """Tests the memory write fails when given an invalid access width.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(ValueError):
            self.jlink.memory_write(0, [0], nbits=42)

        with self.assertRaises(ValueError):
            self.jlink.memory_write(0, [0], nbits=13)

        with self.assertRaises(ValueError):
            self.jlink.memory_write(0, [0], nbits=-1)

    def test_jlink_memory_write_failure(self):
        """Tests a memory write that fails to write.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_WriteMemEx.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.memory_write(0, [0])

    def test_jlink_memory_write_zoned(self):
        """Tests a memory write to a zoned memory region.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_WriteMemZonedEx.return_value = 0
        self.assertEqual(0, self.jlink.memory_write(0, [0], 'zone'))
        self.dll.JLINKARM_WriteMemZonedEx.assert_called_once()
        self.dll.JLINKARM_WriteMemEx.assert_not_called()

    def test_jlink_memory_write_unzoned(self):
        """Tests a memory write to an unzoned memory region.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_WriteMemEx.return_value = 0
        self.assertEqual(0, self.jlink.memory_write(0, [0]))
        self.dll.JLINKARM_WriteMemEx.assert_called_once()
        self.dll.JLINKARM_WriteMemZonedEx.assert_not_called()

    def test_jlink_memory_write_access_width(self):
        """Tests the access width specified memory writes.

        There are three types of memory accesses: bytes, half words, and full
        word access.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        num_units = 4
        accesses = [1, 2, 4]

        def read_from_memory(addr, buf_size, buf, access):
            self.assertEqual(num_units * access, buf_size)
            self.assertEqual(accesses.pop(0), access)

            if access == 1:
                self.assertEqual(0xFF, buf[0])
                self.assertEqual(0x00, buf[1])
                self.assertEqual(0x00, buf[2])
                self.assertEqual(0x00, buf[3])
            elif access == 2:
                self.assertEqual(0xFF, buf[0])
                self.assertEqual(0xFF00, buf[1])
                self.assertEqual(0x00, buf[2])
                self.assertEqual(0x00, buf[3])
            elif access == 4:
                self.assertEqual(0xFF, buf[0])
                self.assertEqual(0xFF00, buf[1])
                self.assertEqual(0xFFFF0000, buf[2])
                self.assertEqual(0x00, buf[3])

            return num_units

        self.dll.JLINKARM_WriteMemEx.side_effect = read_from_memory
        self.dll.JLINKARM_WriteMemEx.return_value = num_units

        data = [0xFF, 0xFF00, 0xFFFF0000, 0xFFFFFFFF00000000]

        self.assertEqual(num_units, self.jlink.memory_write8(0, data))
        self.assertEqual(num_units, self.jlink.memory_write16(0, data))
        self.assertEqual(num_units, self.jlink.memory_write32(0, data))

        self.assertEqual(0, len(accesses))

    def test_jlink_memory_write_no_access_width(self):
        """Tests memory write with an unspecified access width and intger size.

        When a memory write occurs, the data must either be written into an
        array of 8-bit unsigned integers, 16-bit unsigned integers, or 32-bit
        unsigned intgers.  Since a list of any sized integers can be passed in,
        we hvae to ensure we properly pack it into 8-bit unsigned integers.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        data = [1 << 8, 1 << 16, 1 << 32]

        self.dll.JLINKARM_WriteMemEx.return_value = 0
        self.jlink.memory_write(0, data)

        _, num_bytes, data, width = self.dll.JLINKARM_WriteMemEx.call_args[0]
        self.assertEqual(0, width)
        self.assertEqual(10, num_bytes)
        self.assertEqual(10, len(data))

        # 1 << 8
        self.assertEqual(1, data[0])
        self.assertEqual(0, data[1])

        # 1 << 16
        self.assertEqual(1, data[2])
        self.assertEqual(0, data[3])
        self.assertEqual(0, data[4])

        # 1 << 32
        self.assertEqual(1, data[5])
        self.assertEqual(0, data[6])
        self.assertEqual(0, data[7])
        self.assertEqual(0, data[8])
        self.assertEqual(0, data[9])

    def test_jlink_memory_write_long_word(self):
        """Tests the ``memory_write64()`` method.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        long_word = 0xFFFFFFFF00000000

        self.jlink.memory_write32 = mock.Mock()

        self.jlink.memory_write64(0, [long_word])

        first, last = self.jlink.memory_write32.call_args[0][1]
        self.assertEqual(last, 0xFFFFFFFF)
        self.assertEqual(first, 0x00000000)

    def test_jlink_register_read_single(self):
        """Tests reading a single register at a time.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadReg.return_value = 0xFF
        self.assertEqual(0xFF, self.jlink.register_read(0))

    def test_jlink_register_read_multiple_failure(self):
        """Tests failing to read multiple registers at once.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadRegs.return_value = -1
        with self.assertRaises(JLinkException):
            self.jlink.register_read_multiple([2, 3, 4])

    def test_jlink_register_read_multiple_success(self):
        """Tests successfully reading multiple registers at once.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadRegs.return_value = 0

        res = self.jlink.register_read_multiple(list(range(10)))

        self.assertTrue(isinstance(res, list))
        self.assertEqual(10, len(res))
        self.assertTrue(all(x == 0 for x in res))

    def test_jlink_register_write_single_failure(self):
        """Tests failing to write to a single register.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_WriteReg.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.register_write(0, 0xFF)

    def test_jlink_register_write_single_success(self):
        """Tests successfully writing to a single register.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_WriteReg.return_value = 0
        self.assertEqual(0xFF, self.jlink.register_write(0, 0xFF))

    def test_jlink_register_write_multiple_failure(self):
        """Tests failing to write to multiple registers at once.

        There are two conditions to failure:
          - The number of values aren't equal to the number of registers; or
          - The J-Link fails to write to the registers.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaisesRegexp(ValueError, 'equal number'):
            self.jlink.register_write_multiple([2, 3], [1])

        with self.assertRaisesRegexp(ValueError, 'equal number'):
            self.jlink.register_write_multiple([2, 3], [1, 4, 5])

        self.dll.JLINKARM_WriteRegs.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.register_write_multiple([2, 3, 4], [2, 3, 4])

    def test_jlink_register_write_multiple_success(self):
        """Tests succussfully writing to multiple registers at once.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_WriteRegs.return_value = 0

        res = self.jlink.register_write_multiple([0, 1], [0xFF, 0xFF])
        self.assertEqual(None, res)

        indices, values, _, count = self.dll.JLINKARM_WriteRegs.call_args[0]
        self.assertEqual(2, count)
        self.assertEqual(list(indices), [0, 1])
        self.assertEqual(list(values), [0xFF] * count)

    def test_jlink_ice_register_read_success(self):
        """Tests successfully reading from an ICE register.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ReadICEReg.return_value = 0x123456789
        self.assertEqual(0x123456789, self.jlink.ice_register_read(0x08))

    def test_jlink_ice_register_write_success(self):
        """Tests successfully writing to an ARM ICE register.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.assertEqual(None, self.jlink.ice_register_write(0x08, 0x123456789, True))
        self.dll.JLINKARM_WriteICEReg.assert_called_with(0x08, 0x123456789, 1)

        self.assertEqual(None, self.jlink.ice_register_write(0x08, 0x123456789, False))
        self.dll.JLINKARM_WriteICEReg.assert_called_with(0x08, 0x123456789, 0)

    def test_jlink_etm_supported_arm_7_9_supported(self):
        """Tests when ETM is supported on an ARM 7/9 core.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ETM_IsPresent.return_value = 1
        self.assertTrue(self.jlink.etm_supported())

        self.dll.JLINKARM_ETM_IsPresent.assert_called_once()
        self.dll.JLINKARM_GetDebugInfo.assert_not_called()

    def test_jlink_etm_supported_cortex_m_supported(self):
        """Tests when ETM is supported on a Cortex-M core.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ETM_IsPresent.return_value = 0
        self.dll.JLINKARM_GetDebugInfo.return_value = 0

        self.assertTrue(self.jlink.etm_supported())

        self.dll.JLINKARM_ETM_IsPresent.assert_called_once()
        self.dll.JLINKARM_GetDebugInfo.assert_called_once()

    def test_jlink_etm_supported_not_supported(self):
        """Tests when ETM is not supported on a Cortex-M core.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_ETM_IsPresent.return_value = 0
        self.dll.JLINKARM_GetDebugInfo.return_value = 1

        self.assertFalse(self.jlink.etm_supported())

        self.dll.JLINKARM_ETM_IsPresent.assert_called_once()
        self.dll.JLINKARM_GetDebugInfo.assert_called_once()

    def test_jlink_etm_register_read(self):
        """Tests reading an ETM register.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        index = 0xdeadbeef
        self.jlink.etm_register_read(index)
        self.dll.JLINKARM_ETM_ReadReg.assert_called_once_with(index)

    def test_jlink_etm_register_write(self):
        """Tests writing to an ETM register.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        index = 0xdeadbeef
        value = 0x1337
        self.jlink.etm_register_write(index, value)
        self.dll.JLINKARM_ETM_WriteReg.assert_called_once_with(index, value, 0)

    def test_jlink_coresight_read_failure(self):
        """Tests the ``coresight_read()`` method on failure to read.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_CORESIGHT_ReadAPDPReg.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.coresight_read([0], [0xFF])

    def test_jlink_coresight_read_success(self):
        """Tests the ``coresight_read()`` method on successful read.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_CORESIGHT_ReadAPDPReg.return_value = 0

        self.assertEqual(0, self.jlink.coresight_read(0, True))
        self.assertEqual(0, self.jlink.coresight_read(0, False))

    def test_jlink_coresight_write_failure(self):
        """Tests the ``coresight_write()`` method on failure to write.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_CORESIGHT_WriteAPDPReg.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.coresight_write(0, 0)

    def test_jlink_coresight_write_success(self):
        """Tests the ``coresight_write()`` method on successful write.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_CORESIGHT_WriteAPDPReg.return_value = 0

        self.assertEqual(0, self.jlink.coresight_write(0, 0, True))
        self.dll.JLINKARM_CORESIGHT_WriteAPDPReg.assert_called_with(0, 1, 0)

        self.assertEqual(0, self.jlink.coresight_write(0, 0, False))
        self.dll.JLINKARM_CORESIGHT_WriteAPDPReg.assert_called_with(0, 0, 0)

    def test_jlink_reset_pulls_reset(self):
        """Tests setting / unsetting the RESET pin.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.enable_reset_pulls_reset()
        self.dll.JLINKARM_ResetPullsRESET.assert_called_with(1)

        self.jlink.disable_reset_pulls_reset()
        self.dll.JLINKARM_ResetPullsRESET.assert_called_with(0)

    def test_jlink_reset_pulls_trst(self):
        """Tests setting / unsetting the TRST pin.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.enable_reset_pulls_trst()
        self.dll.JLINKARM_ResetPullsTRST.assert_called_with(1)

        self.jlink.disable_reset_pulls_trst()
        self.dll.JLINKARM_ResetPullsTRST.assert_called_with(0)

    def test_jlink_reset_inits_registers(self):
        """Tests setting registers to initialize or not on reset.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.enable_reset_inits_registers()
        self.dll.JLINKARM_SetInitRegsOnReset.assert_called_with(1)

        self.jlink.disable_reset_inits_registers()
        self.dll.JLINKARM_SetInitRegsOnReset.assert_called_with(0)

    def test_jlink_set_little_endian(self):
        """Tests setting the endianess of the target to little endian.

        Args:
          self (TestJlink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SetEndian.return_value = 1
        self.assertTrue(self.jlink.set_little_endian())
        self.dll.JLINKARM_SetEndian.assert_called_with(0)

        self.dll.JLINKARM_SetEndian.return_value = 0
        self.assertFalse(self.jlink.set_little_endian())
        self.dll.JLINKARM_SetEndian.assert_called_with(0)

    def test_jlink_set_big_endian(self):
        """Tests setting the endianess of the target to big endian.

        Args:
          self (TestJlink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SetEndian.return_value = 0
        self.assertTrue(self.jlink.set_big_endian())
        self.dll.JLINKARM_SetEndian.assert_called_with(1)

        self.dll.JLINKARM_SetEndian.return_value = 1
        self.assertFalse(self.jlink.set_big_endian())
        self.dll.JLINKARM_SetEndian.assert_called_with(1)

    def test_jlink_set_vector_catch(self):
        """Tests setting a vector catch.

        A vector catch is used to have the CPU halt when certain events occur.

        There are two conditions when setting a vector catch: either it
        succeeds or it fails with a ``JLinkException``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_WriteVectorCatch.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.set_vector_catch(0xFF)

        self.dll.JLINKARM_WriteVectorCatch.return_value = 0
        self.assertEqual(None, self.jlink.set_vector_catch(0xFF))

    def test_jlink_step(self):
        """Tests stepping the target CPU.

        There are two possible ways to step: a normal step or a step in THUMB
        mode.  A step can also fail with a ``JLinkException``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_Step.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.step()

        self.dll.JLINKARM_Step.return_value = 0
        self.assertEqual(None, self.jlink.step())

        self.dll.JLINKARM_StepComposite.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.step(thumb=True)

        self.dll.JLINKARM_Step.return_value = -1
        self.dll.JLINKARM_StepComposite.return_value = 0
        self.assertEqual(None, self.jlink.step(thumb=True))

    def test_jlink_enable_software_breakpoints(self):
        """Tests enabling the software breakpoints.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.enable_soft_breakpoints()
        self.dll.JLINKARM_EnableSoftBPs.assert_called_with(1)

    def test_jlink_disable_software_breakpoints(self):
        """Tests disabling the software breakpoints.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.disable_soft_breakpoints()
        self.dll.JLINKARM_EnableSoftBPs.assert_called_with(0)

    def test_jlink_num_active_breakpoints(self):
        """Tests querying the number of active breakpoints.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        num_active_breakpoints = 20

        self.dll.JLINKARM_GetNumBPs.return_value = num_active_breakpoints
        self.assertEqual(num_active_breakpoints, self.jlink.num_active_breakpoints())

    def test_jlink_num_available_breakpoints(self):
        """Tests querying the number of available breakpoints.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        breakpoint_types = dict((
            (enums.JLinkBreakpoint.ARM,      1),
            (enums.JLinkBreakpoint.THUMB,    2),
            (enums.JLinkBreakpoint.SW_RAM,   3),
            (enums.JLinkBreakpoint.SW_FLASH, 4),
            (enums.JLinkBreakpoint.HW,       5)
        ))

        num_breakpoints = sum(breakpoint_types.values())

        def get_num_bp_units(flags):
            if flags == enums.JLinkBreakpoint.ANY:
                return num_breakpoints

            count = 0
            for (mask, value) in breakpoint_types.iteritems():
                if flags & mask:
                    count = count + value

            return count

        self.dll.JLINKARM_GetNumBPUnits = get_num_bp_units
        self.assertEqual(num_breakpoints, self.jlink.num_available_breakpoints())

        count = breakpoint_types[enums.JLinkBreakpoint.ARM]
        self.assertEqual(count, self.jlink.num_available_breakpoints(arm=True))

        flags = [enums.JLinkBreakpoint.THUMB, enums.JLinkBreakpoint.SW_RAM]
        count = sum(breakpoint_types[f] for f in flags)
        self.assertEqual(count, self.jlink.num_available_breakpoints(thumb=True, ram=True))

    def test_jlink_breakpoint_info(self):
        """Tests querying for the breakpoint information.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetBPInfoEx.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.breakpoint_info(0x1)

        self.dll.JLINKARM_GetBPInfoEx.return_value = 0

        with self.assertRaises(ValueError):
            self.jlink.breakpoint_info()

        bp = self.jlink.breakpoint_info(0x1)
        self.assertTrue(isinstance(bp, structs.JLinkBreakpointInfo))

    def test_jlink_breakpoint_find(self):
        """Tests searching for a breakpoint.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_FindBP.return_value = 0
        self.assertEqual(0, self.jlink.breakpoint_find(0x1337))

        self.dll.JLINKARM_FindBP.return_value = 1
        self.assertEqual(1, self.jlink.breakpoint_find(0x1337))

    def test_jlink_breakpoint_set(self):
        """Tests setting a breakpoint.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        addr = 0x1337

        self.dll.JLINKARM_SetBPEx.return_value = 0
        with self.assertRaises(JLinkException):
            self.jlink.breakpoint_set(addr)

        self.dll.JLINKARM_SetBPEx.return_value = 1
        self.assertEqual(1, self.jlink.breakpoint_set(addr))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.ANY)

        self.dll.JLINKARM_SetBPEx.return_value = 2
        self.assertEqual(2, self.jlink.breakpoint_set(addr, arm=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.ARM | enums.JLinkBreakpoint.ANY)

        self.dll.JLINKARM_SetBPEx.return_value = 3
        self.assertEqual(3, self.jlink.breakpoint_set(addr, thumb=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.THUMB | enums.JLinkBreakpoint.ANY)

    def test_jlink_software_breakpoint_set(self):
        """Tests setting a software breakpoint.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        addr = 0x1337

        self.dll.JLINKARM_SetBPEx.return_value = 0
        with self.assertRaises(JLinkException):
            self.jlink.software_breakpoint_set(addr)

        self.dll.JLINKARM_SetBPEx.return_value = 1
        self.assertEqual(1, self.jlink.software_breakpoint_set(addr))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.SW)

        self.assertEqual(1, self.jlink.software_breakpoint_set(addr, arm=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.SW | enums.JLinkBreakpoint.ARM)

        self.assertEqual(1, self.jlink.software_breakpoint_set(addr, thumb=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.SW | enums.JLinkBreakpoint.THUMB)

        self.assertEqual(1, self.jlink.software_breakpoint_set(addr, arm=True, flash=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.SW_FLASH | enums.JLinkBreakpoint.ARM)

        self.assertEqual(1, self.jlink.software_breakpoint_set(addr, arm=True, ram=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.SW_RAM | enums.JLinkBreakpoint.ARM)

        self.assertEqual(1, self.jlink.software_breakpoint_set(addr, thumb=True, ram=True, flash=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.SW | enums.JLinkBreakpoint.THUMB)

    def test_jlink_hardware_breakpoint_set(self):
        """Tests setting a hardware breakpoint.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        addr = 0x1337

        self.dll.JLINKARM_SetBPEx.return_value = 0
        with self.assertRaises(JLinkException):
            self.jlink.hardware_breakpoint_set(addr)

        self.dll.JLINKARM_SetBPEx.return_value = 1
        self.assertEqual(1, self.jlink.hardware_breakpoint_set(addr))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.HW)

        self.assertEqual(1, self.jlink.hardware_breakpoint_set(addr, arm=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.HW | enums.JLinkBreakpoint.ARM)

        self.assertEqual(1, self.jlink.hardware_breakpoint_set(addr, thumb=True))
        self.dll.JLINKARM_SetBPEx.assert_called_with(addr, enums.JLinkBreakpoint.HW | enums.JLinkBreakpoint.THUMB)

    def test_jlink_breakpoint_clear(self):
        """Tests clearing breakpoints.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        handle = 0x1

        self.jlink.breakpoint_clear(handle)
        self.dll.JLINKARM_ClrBPEx.assert_called_with(handle)

        self.jlink.breakpoint_clear_all()
        self.dll.JLINKARM_ClrBPEx.assert_called_with(0xFFFFFFFF)

    def test_jlink_num_active_watchpoints(self):
        """Tests getting the number of active watchpoints.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetNumWPs.return_value = 0
        self.assertEqual(0, self.jlink.num_active_watchpoints())
        self.dll.JLINKARM_GetNumWPs.assert_called_once()

    def test_jlink_num_available_watchpoints(self):
        """Tests getting the number of available watchpoints.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_GetNumWPUnits.return_value = 0
        self.assertEqual(0, self.jlink.num_available_watchpoints())
        self.dll.JLINKARM_GetNumWPUnits.assert_called_once()

    def test_jlink_watchpoint_info_failure(self):
        """Tests that errors are generated when watchpoint info fails.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        handle = 0x1
        self.dll.JLINKARM_GetWPInfoEx.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.watchpoint_info(handle)

        self.dll.JLINKARM_GetWPInfoEx.return_value = 0

        with self.assertRaises(ValueError):
            self.jlink.watchpoint_info()

        self.dll.JLINKARM_GetWPInfoEx.side_effect = [1, -1]

        with self.assertRaises(JLinkException):
            self.jlink.watchpoint_info(1)

    def test_jlink_watchpoint_info_success(self):
        """Tests successfully getting information about a watchpoint.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        handle = 0x1
        self.dll.JLINKARM_GetWPInfoEx.return_value = 1

        wp = self.jlink.watchpoint_info(handle=1)
        self.assertEqual(None, wp)

        self.dll.JLINKARM_GetWPInfoEx.return_value = 1

        wp = self.jlink.watchpoint_info(index=0x0)
        self.assertTrue(isinstance(wp, structs.JLinkWatchpointInfo))

    def test_jlink_watchpoint_set_invalid_access(self):
        """Tests setting a watchpoint failing due to bad access size.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        addr = 0xdeadbeef

        with self.assertRaises(ValueError):
            self.jlink.watchpoint_set(addr, access_size=3)

        with self.assertRaises(ValueError):
            self.jlink.watchpoint_set(addr, access_size=19)

    def test_jlink_watchpoint_set_failure(self):
        """Tests setting a watchpoint failing due to an event error.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        addr = 0xdeadbeef

        self.dll.JLINKARM_SetDataEvent.return_value = -1
        with self.assertRaises(JLinkDataException):
            self.jlink.watchpoint_set(addr)

        wp = self.dll.JLINKARM_SetDataEvent.call_args[0][0].contents
        self.assertTrue(isinstance(wp, structs.JLinkDataEvent))
        self.assertTrue((3 < 1) | (1 << 4), wp.AccessMask)

    def test_jlink_watchpoint_set_success(self):
        """Tests successfully setting a watchpoint.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        kwargs = {
            'addr': 0xA0000000,
            'addr_mask': 0x00000000,
            'data': 0x0,
            'data_mask': 0xFFFFFFFF,
            'access_size': 32,
            'read': True,
            'write': True,
            'privileged': False
        }

        self.dll.JLINKARM_SetDataEvent.return_value = 0
        self.assertEqual(0, self.jlink.watchpoint_set(**kwargs))

        wp = self.dll.JLINKARM_SetDataEvent.call_args[0][0].contents
        self.assertTrue(isinstance(wp, structs.JLinkDataEvent))

        # We should have a data watchpoint on address 0xA0000000, matching any
        # data access, any access (R/W), 32-bit access size.
        self.assertEqual(1 << 0, wp.Type)
        self.assertEqual(ctypes.sizeof(wp), wp.SizeOfStruct)
        self.assertEqual(0xA0000000, wp.Addr)
        self.assertEqual(0x00000000, wp.AddrMask)
        self.assertEqual(0x0, wp.Data)
        self.assertEqual(0xFFFFFFFF, wp.DataMask)
        self.assertEqual(2 << 1, wp.Access)
        self.assertEqual((1 << 0) | (1 << 4), wp.AccessMask)

        kwargs = {
            'addr': 0xA0000000,
            'addr_mask': 0x0000000F,
            'data': 0x11223340,
            'data_mask': 0x0000000F,
            'access_size': 16,
            'read': False,
            'write': True,
            'privileged': False
        }

        self.dll.JLINKARM_SetDataEvent.return_value = 1
        self.assertEqual(0, self.jlink.watchpoint_set(**kwargs))

        wp = self.dll.JLINKARM_SetDataEvent.call_args[0][0].contents
        self.assertTrue(isinstance(wp, structs.JLinkDataEvent))

        # We should have a data watchpoint on address 0xA0000000 - 0xA000000F,
        # matching data 0x11223340 - 0x1122334F, write accesses only, 16-bit
        # access size.
        self.assertEqual(1 << 0, wp.Type)
        self.assertEqual(ctypes.sizeof(wp), wp.SizeOfStruct)
        self.assertEqual(0xA0000000, wp.Addr)
        self.assertEqual(0x0000000F, wp.AddrMask)
        self.assertEqual(0x11223340, wp.Data)
        self.assertEqual(0x0000000F, wp.DataMask)
        self.assertEqual((1 << 1) | (1 << 0), wp.Access)
        self.assertEqual(1 << 4, wp.AccessMask)

        kwargs = {
            'addr': 0xA0000000,
            'addr_mask': 0x00000000,
            'data': 0x11223340,
            'data_mask': 0x00000000,
            'access_size': 8,
            'read': True,
            'write': False,
            'privileged': True
        }

        self.dll.JLINKARM_SetDataEvent.return_value = 1
        self.assertEqual(0, self.jlink.watchpoint_set(**kwargs))

        wp = self.dll.JLINKARM_SetDataEvent.call_args[0][0].contents
        self.assertTrue(isinstance(wp, structs.JLinkDataEvent))

        # We should have a data watchpoint on address 0xA0000000, matching data
        # 0x11223340, read access only, 8-bit access size, and privileged.
        self.assertEqual(1 << 0, wp.Type)
        self.assertEqual(ctypes.sizeof(wp), wp.SizeOfStruct)
        self.assertEqual(0xA0000000, wp.Addr)
        self.assertEqual(0x0, wp.AddrMask)
        self.assertEqual(0x11223340, wp.Data)
        self.assertEqual(0x0, wp.DataMask)
        self.assertEqual((0 << 0) | (0 << 1) | (1 << 4), wp.Access)
        self.assertEqual(0, wp.AccessMask)

    def test_jlink_watchpoint_clear(self):
        """Tests clearing watchpoints.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        handle = 0x1

        self.jlink.watchpoint_clear(handle)
        self.dll.JLINKARM_ClrDataEvent.assert_called_with(handle)

        self.jlink.watchpoint_clear_all()
        self.dll.JLINKARM_ClrDataEvent.assert_called_with(0xFFFFFFFF)

    def test_jlink_disassemble_instruction_invalid_address(self):
        """Tests passing an invalid instruction to ``disassemble_instruction()``

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(TypeError):
            self.jlink.disassemble_instruction('0xdeadbeef')

    def test_jlink_disassemble_instruction_failed(self):
        """Tests failing to disassemble an instruction.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        address = 0xdeadbeef

        self.dll.JLINKARM_DisassembleInst.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.disassemble_instruction(address)

    def test_jlink_disassemble_instruction_success(self):
        """Tests succeeding to disassemble an instruction.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        address = 0xdeadbeef
        self.dll.JLINKARM_DisassembleInst.return_value = 0
        self.assertEqual('', self.jlink.disassemble_instruction(address))

    def test_jlink_strace_configure_invalid_width(self):
        """Tests specifying in invalid width to the STRACE configure.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(ValueError):
            self.jlink.strace_configure('4')

        with self.assertRaises(ValueError):
            self.jlink.strace_configure(32)

    def test_jlink_strace_configure_failed(self):
        """Tests failing to configure the port width.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_STRACE_Config.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.strace_configure(4)

    def test_jlink_strace_configure_success(self):
        """Tests successfully configuring the STRACE port width.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_STRACE_Config.return_value = 0

        self.assertEqual(None, self.jlink.strace_configure(4))

        self.dll.JLINK_STRACE_Config.assert_called_with('PortWidth=4')

    def test_jlink_strace_start_failed(self):
        """Tests failing to start STRACE.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_STRACE_Start.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.strace_start()

    def test_jlink_strace_start_success(self):
        """Tests successfully starting STRACE.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_STRACE_Start.return_value = 0
        self.assertEqual(None, self.jlink.strace_start())

    def test_jlink_strace_stop_failed(self):
        """Tests failing to stop STRACE.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_STRACE_Stop.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.strace_stop()

    def test_jlink_strace_stop_success(self):
        """Tests successfully stopping STRACE.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_STRACE_Stop.return_value = 0
        self.assertEqual(None, self.jlink.strace_stop())

    def test_jlink_strace_read_invalid_instruction_count(self):
        """Tests passing an invalid number of instructions to read over STRACE.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(ValueError):
            self.jlink.strace_read(-1)

        with self.assertRaises(ValueError):
            self.jlink.strace_read(0x10001)

    def test_jlink_strace_read_failed(self):
        """Tests when an STRACE read fails.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        num_instructions = 0x10000

        self.dll.JLINK_STRACE_Read.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.strace_read(num_instructions)

    def test_jlink_strace_read_success(self):
        """Tests successfully reading from STRACE.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        num_instructions = 0x10000

        self.dll.JLINK_STRACE_Read.return_value = 0
        self.assertEqual([], self.jlink.strace_read(num_instructions))

        self.dll.JLINK_STRACE_Read.assert_called_once()

    def test_jlink_strace_trace_events(self):
        """Tests setting the trace events for the STRACE.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        methods = [
            self.jlink.strace_code_fetch_event,
            self.jlink.strace_data_load_event,
            self.jlink.strace_data_store_event
        ]

        events = [0, 2, 3]
        kwargs = {
            'operation': 3,
            'address': 0x4000194,
            'address_range': 0x10
        }

        for (event, method) in zip(events, methods):
            self.dll.JLINK_STRACE_Control.return_value = -1
            self.dll.JLINK_STRACE_Control.side_effect = None

            with self.assertRaises(JLinkException):
                method(**kwargs)

            def trace_event(command, pointer):
                obj = ctypes.cast(pointer, ctypes.POINTER(structs.JLinkStraceEventInfo)).contents
                self.assertEqual(0, command)
                self.assertEqual(event, obj.Type)
                self.assertEqual(kwargs.get('operation'), obj.Op)
                self.assertEqual(kwargs.get('address'), obj.Addr)
                self.assertEqual(kwargs.get('address_range'), obj.AddrRangeSize)
                return 0

            self.dll.JLINK_STRACE_Control.return_value = 0
            self.dll.JLINK_STRACE_Control.side_effect = trace_event

            self.assertEqual(0, method(**kwargs))

        return None

    def test_jlink_strace_trace_data_access_event(self):
        """Tests STRACE for tracing a data access event.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        op, addr, data, addr_range = 3, 0x4000194, 0x1337, 0x10
        self.dll.JLINK_STRACE_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.strace_data_access_event(op, addr, data)

        self.dll.JLINK_STRACE_Control.return_value = 0

        self.jlink.strace_data_access_event(op, addr, data, address_range=addr_range)

    def test_jlink_strace_clear_failed(self):
        """Tests failing to clear the STRACE trace events.

        This test verifies both the singular trace event clear and the multiple
        trace event clear.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_STRACE_Control.return_value = -1

        handle = 0xdeadbeef
        with self.assertRaises(JLinkException):
            self.jlink.strace_clear(handle)

        args, _ = self.dll.JLINK_STRACE_Control.call_args
        self.assertTrue(1 in args)

        with self.assertRaises(JLinkException):
            self.jlink.strace_clear_all()

        self.dll.JLINK_STRACE_Control.assert_called_with(2, 0)

    def test_jlink_strace_clear_success(self):
        """Tests failing succeeding in clearing the STRACE trace events.

        This test verifies both the singular trace event clear and the multiple
        trace event clear.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINK_STRACE_Control.return_value = 0

        handle = 0xdeadbeef
        self.assertEqual(None, self.jlink.strace_clear(handle))

        args, _ = self.dll.JLINK_STRACE_Control.call_args
        self.assertTrue(1 in args)

        self.assertEqual(None, self.jlink.strace_clear_all())
        self.dll.JLINK_STRACE_Control.assert_called_with(2, 0)

    def test_jlink_strace_set_buffer_size_failed(self):
        """Tests failing to set the STRACE buffer size.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        size = 256
        self.dll.JLINK_STRACE_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.strace_set_buffer_size(size)

    def test_jlink_strace_set_buffer_size_success(self):
        """Tests successfully setting the STRACE buffer size.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        size = 256
        self.dll.JLINK_STRACE_Control.return_value = 0

        self.jlink.strace_set_buffer_size(size)

        args, _ = self.dll.JLINK_STRACE_Control.call_args
        self.assertTrue(3 in args)

    def test_jlink_trace_start_failed(self):
        """Tests failing to start the trace.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_start()

    def test_jlink_trace_start_success(self):
        """Tests succeeding in starting the trace.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(None, self.jlink.trace_start())
        self.dll.JLINKARM_TRACE_Control.assert_called_once_with(0, 0)

    def test_jlink_trace_stop_failed(self):
        """Tests failing to stop tracing.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_stop()

    def test_jlink_trace_stop_success(self):
        """Tests succeeding in stopping tracing.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(None, self.jlink.trace_stop())
        self.dll.JLINKARM_TRACE_Control.assert_called_once_with(1, 0)

    def test_jlink_trace_flush_failed(self):
        """Tests failing to flush the trace buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_flush()

    def test_jlink_trace_flush_success(self):
        """Tests successfully flushing the trace buffer successfully.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(None, self.jlink.trace_flush())
        self.dll.JLINKARM_TRACE_Control.assert_called_once_with(2, 0)

    def test_jlink_trace_sample_count(self):
        """Tests getting the sample count from the TRACE API.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        capacity = 256

        self.dll.JLINKARM_TRACE_Control.return_value = 1
        self.jlink.trace_max_buffer_capacity = lambda: capacity

        with self.assertRaises(JLinkException):
            self.jlink.trace_sample_count()

        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(capacity, self.jlink.trace_sample_count())

        args, _ = self.dll.JLINKARM_TRACE_Control.call_args
        self.assertTrue(0x10 in args)

    def test_jlink_trace_buffer_capacity(self):
        """Tests getting the current capacity of the TRACE buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 1
        with self.assertRaises(JLinkException):
            self.jlink.trace_buffer_capacity()

        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(0, self.jlink.trace_buffer_capacity())

        args, _ = self.dll.JLINKARM_TRACE_Control.call_args
        self.assertTrue(0x11 in args)

    def test_jlink_trace_set_buffer_capacity(self):
        """Tests setting the buffer capacity.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        capacity = 256
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_set_buffer_capacity(capacity)

        def set_buffer_capacity(command, pointer):
            c_uint = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32)).contents
            self.assertEqual(0x12, command)
            self.assertEqual(capacity, c_uint.value)
            return 0

        self.dll.JLINKARM_TRACE_Control = set_buffer_capacity

        self.assertEqual(None, self.jlink.trace_set_buffer_capacity(capacity))

    def test_jlink_trace_min_buffer_capacity(self):
        """Tests querying the TRACE buffer's minimum capacity.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_min_buffer_capacity()

        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(0, self.jlink.trace_min_buffer_capacity())

        args, _ = self.dll.JLINKARM_TRACE_Control.call_args
        self.assertTrue(0x13 in args)

    def test_jlink_trace_max_buffer_capacity(self):
        """Tests querying the TRACE buffer's maximum capacity.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_max_buffer_capacity()

        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(0, self.jlink.trace_max_buffer_capacity())

        args, _ = self.dll.JLINKARM_TRACE_Control.call_args
        self.assertTrue(0x14 in args)

    def test_jlink_trace_set_format(self):
        """Tests setting the format of the TRACE buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        fmt = 0xdeadbeef
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_set_format(fmt)

        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(None, self.jlink.trace_set_format(fmt))

        args, _ = self.dll.JLINKARM_TRACE_Control.call_args
        self.assertTrue(0x20 in args)

    def test_jlink_trace_format(self):
        """Tests querying the current format of the TRACE buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_format()

        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(0, self.jlink.trace_format())

        args, _ = self.dll.JLINKARM_TRACE_Control.call_args
        self.assertTrue(0x21 in args)

    def test_jlink_trace_region_count(self):
        """Tessts querying the number of TRACE regions.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_region_count()

        self.dll.JLINKARM_TRACE_Control.return_value = 0
        self.assertEqual(0, self.jlink.trace_region_count())

        args, _ = self.dll.JLINKARM_TRACE_Control.call_args
        self.assertTrue(0x30 in args)

    def test_jlink_trace_region(self):
        """Tests querying the J-Link for a TRACE region.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        region_index = 0xdeadbeef

        self.dll.JLINKARM_TRACE_Control.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_region(region_index)

        self.dll.JLINKARM_TRACE_Control.return_value = 0

        region = self.jlink.trace_region(region_index)
        self.assertEqual(ctypes.sizeof(region), region.SizeOfStruct)
        self.assertEqual(region_index, region.RegionIndex)

        args, _ = self.dll.JLINKARM_TRACE_Control.call_args
        self.assertTrue(0x32 in args)

    def test_jlink_trace_read_failed(self):
        """Tests failing to read from the TRACE buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        offset = 0
        num_items = 13

        self.dll.JLINKARM_TRACE_Read.return_value = 1

        with self.assertRaises(JLinkException):
            self.jlink.trace_read(offset, num_items)

    def test_jlink_trace_read_success(self):
        """Tests successfully reading from the TRACE buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        offset = 0
        num_items = 0

        self.dll.JLINKARM_TRACE_Read.return_value = 0
        self.assertEqual([], self.jlink.trace_read(offset, num_items))

    def test_jlink_swo_start(self):
        """Tests starting to collect SWO data.

        On error, an exception is generated, otherwise the result is ``None``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_start()

        self.dll.JLINKARM_SWO_Control.return_value = 0

        self.assertEqual(False, self.jlink.swo_enabled())
        self.assertEqual(None, self.jlink.swo_start())
        self.assertEqual(True, self.jlink.swo_enabled())

        arg = self.dll.JLINKARM_SWO_Control.call_args[0][0]
        self.assertEqual(0, arg)

        self.assertEqual(True, self.jlink.swo_enabled())
        self.assertEqual(None, self.jlink.swo_start())
        self.assertEqual(True, self.jlink.swo_enabled())

    def test_jlink_swo_enable(self):
        """Tests enabling SWO output on the target device.

        SWO output can also be enabled by calling ``.swo_enable()``, which on
        error should raise an exception, otherwise return ``None``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_EnableTarget.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_enable(0)

        self.dll.JLINKARM_SWO_EnableTarget.return_value = 0

        self.assertEqual(None, self.jlink.swo_enable(0))
        self.assertEqual(True, self.jlink.swo_enabled())

        self.dll.JLINKARM_SWO_EnableTarget.assert_called_with(0, 9600, 0, 0x01)

        self.assertEqual(None, self.jlink.swo_enable(0))
        self.assertEqual(True, self.jlink.swo_enabled())

    def test_jlink_swo_disable(self):
        """Tests disabling the stimulus ports.

        On error, this should raise an exception, otherwise return ``None``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_DisableTarget.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_disable(0)

        self.dll.JLINKARM_SWO_DisableTarget.return_value = 0

        self.assertEqual(None, self.jlink.swo_disable(0))

        self.dll.JLINKARM_SWO_DisableTarget.assert_called_with(0)

    def test_jlink_swo_stop(self):
        """Tests disabling SWO output.

        On error, this should raise an exception, otherwise return ``None``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_stop()

        self.dll.JLINKARM_SWO_Control.return_value = 0

        self.assertEqual(None, self.jlink.swo_stop())

        self.dll.JLINKARM_SWO_Control.assert_called_with(1, 0)

    def test_jlink_swo_flush(self):
        """Tests flushing the SWO buffer.

        On error, this should raise an exception, otherwise return ``None``.

        Flushing without a byte count should flush all data in the buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_flush(1)

        self.dll.JLINKARM_SWO_Control.return_value = 0
        self.assertEqual(None, self.jlink.swo_flush(1))

        arg = self.dll.JLINKARM_SWO_Control.call_args[0][0]
        self.assertEqual(2, arg)

        val = self.dll.JLINKARM_SWO_Control.call_args[0][1]
        self.assertEqual(1, val._obj.value)

        num_bytes = 1337
        self.jlink.swo_num_bytes = mock.Mock()
        self.jlink.swo_num_bytes.return_value = num_bytes

        self.dll.JLINKARM_SWO_Control.return_value = 0
        self.assertEqual(None, self.jlink.swo_flush())

        arg = self.dll.JLINKARM_SWO_Control.call_args[0][0]
        self.assertEqual(2, arg)

        val = self.dll.JLINKARM_SWO_Control.call_args[0][1]
        self.assertEqual(1337, val._obj.value)

    def test_jlink_swo_speed_info(self):
        """Tests getting the device speed info.

        On error, this should raise an exception, otherwise return the speed
        information.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_speed_info()

        self.dll.JLINKARM_SWO_Control.return_value = 0

        info = self.jlink.swo_speed_info()

        self.assertTrue(isinstance(info, structs.JLinkSWOSpeedInfo))

        arg = self.dll.JLINKARM_SWO_Control.call_args[0][0]
        self.assertEqual(3, arg)

    def test_jlink_swo_num_bytes_in_buffer(self):
        """Tests getting the number of bytes in the SWO buffer.

        On error, this should raise an exception, otherwise return the number
        of bytes in the SWO buffer.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_num_bytes()

        self.dll.JLINKARM_SWO_Control.return_value = 0

        self.assertEqual(0, self.jlink.swo_num_bytes())

        arg = self.dll.JLINKARM_SWO_Control.call_args[0][0]
        self.assertEqual(10, arg)

    def test_jlink_swo_set_host_buffer_size(self):
        """Tests setting the host buffer size.

        On error, this should raise an exception, otherwise return ``None``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_set_host_buffer_size(0)

        self.dll.JLINKARM_SWO_Control.return_value = 0

        self.assertEqual(None, self.jlink.swo_set_host_buffer_size(0))

        arg = self.dll.JLINKARM_SWO_Control.call_args[0][0]
        self.assertEqual(20, arg)

    def test_jlink_swo_set_emu_buffer_size(self):
        """Tests setting the emulator's buffer size.

        On error, this should raise an exception, otherwise return ``None``.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_Control.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_set_emu_buffer_size(0)

        self.dll.JLINKARM_SWO_Control.return_value = 0

        self.assertEqual(None, self.jlink.swo_set_emu_buffer_size(0))

        arg = self.dll.JLINKARM_SWO_Control.call_args[0][0]
        self.assertEqual(21, arg)

    def test_jlink_swo_get_supported_speeds(self):
        """Tests getting the J-Link's and target's supported speeds.

        On error this should raise an exception, otherwise return a list of the
        supported speeds.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.dll.JLINKARM_SWO_GetCompatibleSpeeds.return_value = -1

        with self.assertRaises(JLinkException):
            self.jlink.swo_supported_speeds(0)

        self.dll.JLINKARM_SWO_GetCompatibleSpeeds.return_value = 0

        supported_speeds = self.jlink.swo_supported_speeds(0)

        self.assertTrue(isinstance(supported_speeds, list))
        self.assertEqual(0, sum(supported_speeds))

    def test_jlink_swo_read(self):
        """Tests reading data from the SWO buffer.

        Reading can flush in addition to just reading the bytes.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        self.jlink.swo_flush = mock.Mock()

        num_bytes = 10

        # Read without flushing
        res = self.jlink.swo_read(0, num_bytes)

        self.assertTrue(isinstance(res, list))
        self.assertEqual(num_bytes, len(res))
        self.jlink.swo_flush.assert_not_called()

        # Read with flushing
        res = self.jlink.swo_read(0, num_bytes, True)

        self.assertTrue(isinstance(res, list))
        self.assertEqual(num_bytes, len(res))
        self.jlink.swo_flush.assert_called_once_with(num_bytes)

    def test_jlink_swo_read_stimulus_invalid(self):
        """Tests for an invalid port when reading data from a stimulus port.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        with self.assertRaises(ValueError):
            self.jlink.swo_read_stimulus(-1, 0)

        with self.assertRaises(ValueError):
            self.jlink.swo_read_stimulus(32, 0)

    def test_jlink_swo_read_stimulus(self):
        """Tests reading data from the stimulus port successfully.

        Args:
          self (TestJLink): the ``TestJLink`` instance

        Returns:
          ``None``
        """
        num_bytes = 10
        self.dll.JLINKARM_SWO_ReadStimulus.return_value = num_bytes

        res = self.jlink.swo_read_stimulus(0, num_bytes)

        self.assertTrue(isinstance(res, list))
        self.assertEqual(num_bytes, len(res))


if __name__ == '__main__':
    unittest.main()