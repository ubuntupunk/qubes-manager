#!/usr/bin/python3
#
# The Qubes OS Project, https://www.qubes-os.org/
#
# Copyright (C) 2016 Marta Marczykowska-Górecka
#                                       <marmarta@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
import logging.handlers
import unittest
import unittest.mock

from PyQt6 import QtTest, QtCore
from qubesadmin import Qubes
from qubesmanager.tests import init_qtapp
from qubesmanager import create_new_vm


class NewVmTest(unittest.TestCase):
    def setUp(self):
        super(NewVmTest, self).setUp()
        self.qtapp, self.loop = init_qtapp()

        self.qapp = Qubes()

        # mock up the Create VM Thread to avoid changing system state
        self.patcher_thread = unittest.mock.patch(
            'qubesmanager.create_new_vm.CreateVMThread')
        self.mock_thread = self.patcher_thread.start()
        self.addCleanup(self.patcher_thread.stop)

        # mock the progress dialog to speed testing up
        self.patcher_progress = unittest.mock.patch(
            'PyQt6.QtWidgets.QProgressDialog')
        self.mock_progress = self.patcher_progress.start()
        self.addCleanup(self.patcher_progress.stop)

        self.dialog = create_new_vm.NewVmDlg(self.qtapp, self.qapp)

    def test_00_window_loads(self):
        self.assertGreater(self.dialog.template_vm.count(), 0,
                           "No templates shown")
        self.assertGreater(self.dialog.netvm.count(), 0, "No netvm listed")

    def test_01_cancel_works(self):
        self.__click_cancel()
        self.assertEqual(self.mock_thread.call_count, 0,
                         "Attempted to create VM on cancel")

    def test_02_create_simple_vm(self):
        self.dialog.name.setText("test-vm")
        self.__click_ok()

        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="AppVM", name="test-vm",
            label=unittest.mock.ANY, template=self.qapp.default_template,
            properties={'provides_network': False}, pool=unittest.mock.ANY)
        self.mock_thread().start.assert_called_once_with()

    def test_03_label(self):
        for i in range(self.dialog.label.count()):
            if self.dialog.label.itemText(i) == 'blue':
                self.dialog.label.setCurrentIndex(i)
                break

        self.dialog.name.setText("test-vm")
        self.__click_ok()

        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="AppVM", name="test-vm",
            label=self.qapp.labels['blue'],
            template=self.qapp.default_template,
            properties=unittest.mock.ANY, pool=unittest.mock.ANY)
        self.mock_thread().start.assert_called_once_with()

    def test_04_template(self):
        template = None
        for i in range(self.dialog.template_vm.count()):
            if not self.dialog.template_vm.itemText(i).startswith('default'):
                self.dialog.template_vm.setCurrentIndex(i)
                template = self.dialog.template_vm.currentText()
                break

        self.dialog.name.setText("test-vm")
        self.__click_ok()

        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="AppVM", name="test-vm",
            label=unittest.mock.ANY,
            template=template,
            properties=unittest.mock.ANY, pool=unittest.mock.ANY)

    def test_05_netvm(self):
        netvm = None
        for i in range(self.dialog.netvm.count()):
            if not self.dialog.netvm.itemText(i).startswith('default'):
                self.dialog.netvm.setCurrentIndex(i)
                netvm = self.dialog.netvm.currentText()
                break

        self.dialog.name.setText("test-vm")
        self.__click_ok()

        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="AppVM", name="test-vm",
            label=unittest.mock.ANY,
            template=unittest.mock.ANY,
            properties={'netvm': netvm, 'provides_network': False},
            pool=unittest.mock.ANY)

    def test_06_provides_network(self):
        self.dialog.provides_network.setChecked(True)

        self.dialog.name.setText("test-vm")
        self.__click_ok()

        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="AppVM", name="test-vm",
            label=unittest.mock.ANY,
            template=unittest.mock.ANY,
            properties={'provides_network': True},
            pool=unittest.mock.ANY)

    @unittest.mock.patch('subprocess.check_call')
    def test_07_launch_settings(self, mock_call):
        self.dialog.launch_settings.setChecked(True)

        self.dialog.name.setText("test-vm")

        self.__click_ok()

        # make sure the thread is not reporting an error
        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="AppVM", name="test-vm",
            label=unittest.mock.ANY,
            template=unittest.mock.ANY,
            properties=unittest.mock.ANY,
            pool=unittest.mock.ANY)

        self.mock_thread().msg = None
        self.dialog.create_finished()

        mock_call.assert_called_once_with(['qubes-vm-settings', "test-vm"])

    def test_08_progress_hides(self):
        self.dialog.name.setText("test-vm")

        self.__click_ok()

        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="AppVM", name="test-vm",
            label=unittest.mock.ANY,
            template=unittest.mock.ANY,
            properties=unittest.mock.ANY,
            pool=unittest.mock.ANY)

        # make sure the thread is not reporting an error
        self.mock_thread().start.assert_called_once_with()
        self.mock_thread().msg = None

        self.mock_progress().show.assert_called_once_with()

        self.dialog.create_finished()

        self.mock_progress().hide.assert_called_once_with()

    def test_09_standalone_clone(self):
        self.dialog.name.setText("test-vm")
        for i in range(self.dialog.vm_type.count()):
            opt_text = self.dialog.vm_type.itemText(i).lower()
            if "standalone" in opt_text:
                self.dialog.vm_type.setCurrentIndex(i)
                break

        self.__click_ok()
        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="StandaloneVM", name="test-vm",
            label=unittest.mock.ANY,
            template=unittest.mock.ANY,
            properties=unittest.mock.ANY,
            pool=unittest.mock.ANY)

    @unittest.mock.patch('qubesmanager.bootfromdevice.VMBootFromDeviceWindow')
    @unittest.mock.patch('qubesadmin.tools.qvm_start')
    def test_10_standalone_empty(self, mock_qvm_start, mock_bootwindow):
        self.dialog.name.setText("test-vm")
        for i in range(self.dialog.vm_type.count()):
            opt_text = self.dialog.vm_type.itemText(i).lower()
            if "standalone" in opt_text:
                self.dialog.vm_type.setCurrentIndex(i)
                break
        # select "(none)" template
        self.dialog.template_vm.setCurrentIndex(self.dialog.template_vm.count()-1)

        mock_bootwindow.return_value.cdrom_location = 'CDROM_LOCATION'

        self.__click_ok()
        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="StandaloneVM", name="test-vm",
            label=unittest.mock.ANY,
            template=None,
            properties=unittest.mock.ANY,
            pool=unittest.mock.ANY)

        self.mock_thread().msg = None
        self.dialog.create_finished()

        mock_bootwindow.return_value.exec.assert_called_once_with()
        mock_qvm_start.main.assert_called_once_with(
                ['--cdrom', 'CDROM_LOCATION', 'test-vm'])

    @unittest.mock.patch('subprocess.check_call')
    def test_11_standalone_empty_not_install(self, mock_call):
        self.dialog.name.setText("test-vm")

        for i in range(self.dialog.vm_type.count()):
            opt_text = self.dialog.vm_type.itemText(i).lower()
            if "standalone" in opt_text:
                self.dialog.vm_type.setCurrentIndex(i)
                break
        # select "(none)" template
        self.dialog.template_vm.setCurrentIndex(self.dialog.template_vm.count()-1)

        self.dialog.install_system.setChecked(False)

        self.__click_ok()
        self.mock_thread.assert_called_once_with(
            app=self.qapp, vmclass="StandaloneVM", name="test-vm",
            label=unittest.mock.ANY,
            template=None,
            properties=unittest.mock.ANY,
            pool=unittest.mock.ANY)

        self.mock_thread().msg = None
        self.dialog.create_finished()

        self.assertEqual(mock_call.call_count, 0)

    def test_12_setting_change(self):
        # cannot install system on a template-based appvm
        for i in range(self.dialog.vm_type.count()):
            opt_text = self.dialog.vm_type.itemText(i).lower()
            if "appvm" in opt_text:
                self.dialog.vm_type.setCurrentIndex(i)
                break
        self.assertFalse(self.dialog.install_system.isEnabled())
        self.assertTrue(self.dialog.launch_settings.isEnabled())
        self.assertTrue(self.dialog.template_vm.isEnabled())

        # or on a standalone vm cloned from a template
        for i in range(self.dialog.vm_type.count()):
            opt_text = self.dialog.vm_type.itemText(i).lower()
            if "standalone" in opt_text:
                self.dialog.vm_type.setCurrentIndex(i)
                break
        # select default template
        self.dialog.template_vm.setCurrentIndex(0)
        self.assertFalse(self.dialog.install_system.isEnabled())
        self.assertTrue(self.dialog.launch_settings.isEnabled())
        self.assertTrue(self.dialog.template_vm.isEnabled())

        # can install system on a truly empty AppVM
        for i in range(self.dialog.vm_type.count()):
            opt_text = self.dialog.vm_type.itemText(i).lower()
            if "standalone" in opt_text:
                self.dialog.vm_type.setCurrentIndex(i)
                break
        self.assertTrue(self.dialog.template_vm.isEnabled())
        # select "(none)" template
        self.dialog.template_vm.setCurrentIndex(self.dialog.template_vm.count()-1)
        self.assertTrue(self.dialog.install_system.isEnabled())
        self.assertTrue(self.dialog.launch_settings.isEnabled())

    def __click_ok(self):
        okwidget = self.dialog.buttonBox.button(
                    self.dialog.buttonBox.StandardButton.Ok)

        QtTest.QTest.mouseClick(okwidget, QtCore.Qt.MouseButton.LeftButton)

    def __click_cancel(self):
        cancelwidget = self.dialog.buttonBox.button(
            self.dialog.buttonBox.StandardButton.Cancel)

        QtTest.QTest.mouseClick(cancelwidget, QtCore.Qt.MouseButton.LeftButton)


# class CreatteVMThreadTest(unittest.TestCase):


if __name__ == "__main__":
    ha_syslog = logging.handlers.SysLogHandler('/dev/log')
    ha_syslog.setFormatter(
        logging.Formatter('%(name)s[%(process)d]: %(message)s'))
    logging.root.addHandler(ha_syslog)
    unittest.main()
