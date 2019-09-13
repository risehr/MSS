# -*- coding: utf-8 -*-
"""

    mslib.msui._tests.test_mscolab
    ~~~~~~~~~~~~~~~~~~~

    This module is used to test mscolab related gui.

    This file is part of mss.

    :copyright: Copyright 2019 Shivashis Padhi
    :license: APACHE-2.0, see LICENSE for details.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

import sys
from mslib.msui.mss_qt import QtWidgets, QtTest, QtCore
import logging
import multiprocessing
import time

from mslib.mscolab.server import db, app, initialize_managers, start_server
from mslib._tests.constants import TEST_MSCOLAB_DATA_DIR, MSCOLAB_URL_TEST
from mslib.mscolab.conf import mscolab_settings
from mslib.mscolab.models import Project
import mslib.msui.mscolab as mc


class Test_Mscolab(object):
    def setup(self):
        logging.debug("starting")
        self.application = QtWidgets.QApplication(sys.argv)
        self.window = mc.MSSMscolabWindow(data_dir=TEST_MSCOLAB_DATA_DIR, mscolab_server_url=MSCOLAB_URL_TEST)
        self.window.show()
        QtWidgets.QApplication.processEvents()
        QtTest.QTest.qWaitForWindowExposed(self.window)
        QtWidgets.QApplication.processEvents()

        self.app = app
        self.app.config['SQLALCHEMY_DATABASE_URI'] = mscolab_settings.TEST_SQLALCHEMY_DB_URI
        self.app.config['MSCOLAB_DATA_DIR'] = TEST_MSCOLAB_DATA_DIR
        self.app, sockio, cm, fm = initialize_managers(self.app)
        self.fm = fm
        self.cm = cm
        self.p = multiprocessing.Process(
            target=start_server,
            args=(self.app, sockio, cm, fm,),
            kwargs={'port': 8084})
        self.p.start()
        db.init_app(self.app)
        time.sleep(1)

    def teardown(self):
        # to disconnect connections, and clear token
        self.window.logout()
        for window in self.window.active_windows:
            window.hide()
        self.window.hide()
        QtWidgets.QApplication.processEvents()
        self.application.quit()
        QtWidgets.QApplication.processEvents()
        # close mscolab server
        self.p.terminate()

    def test_login(self):
        self._login()
        # screen shows logout button
        assert self.window.loggedInWidget.isVisible() is True
        assert self.window.loginWidget.isVisible() is False
        # test project listing visibility
        assert self.window.listProjects.model().rowCount() == 2
        # test logout
        QtTest.QTest.mouseClick(self.window.logoutButton, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert self.window.loggedInWidget.isVisible() is False
        assert self.window.loginWidget.isVisible() is True

    def _login(self):
        # login
        self.window.emailid.setText('a')
        self.window.password.setText('a')
        QtTest.QTest.mouseClick(self.window.loginButton, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()

    def test_activate_project(self):
        self._login()
        # activate a project
        self._activate_project_at_index(0)
        assert self.window.active_pid is not None

    def _activate_project_at_index(self, index):
        item = self.window.listProjects.item(index)
        point = self.window.listProjects.visualItemRect(item).center()
        QtTest.QTest.mouseClick(self.window.listProjects.viewport(), QtCore.Qt.LeftButton, pos=point)
        QtWidgets.QApplication.processEvents()
        QtTest.QTest.keyClick(self.window.listProjects.viewport(), QtCore.Qt.Key_Return)
        QtWidgets.QApplication.processEvents()

    def test_view_open(self):
        self._login()
        # test without activating project
        QtTest.QTest.mouseClick(self.window.topview, QtCore.Qt.LeftButton)
        QtTest.QTest.mouseClick(self.window.sideview, QtCore.Qt.LeftButton)
        QtTest.QTest.mouseClick(self.window.tableview, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert len(self.window.active_windows) == 0
        # test after activating project
        self._activate_project_at_index(0)
        QtTest.QTest.mouseClick(self.window.tableview, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert len(self.window.active_windows) == 1
        QtTest.QTest.mouseClick(self.window.topview, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert len(self.window.active_windows) == 2
        QtTest.QTest.mouseClick(self.window.sideview, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert len(self.window.active_windows) == 3

    def test_save_fetch(self):

        self._login()
        self._activate_project_at_index(0)
        # change waypoint
        self.window.waypoints_model.invert_direction()
        wpdata1 = self.window.waypoints_model.waypoint_data(0)
        # don't save, fetch
        QtTest.QTest.mouseClick(self.window.fetch_ft, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        wpdata2 = self.window.waypoints_model.waypoint_data(0)
        assert wpdata2.lat != wpdata1.lat
        # save, fetch
        self.window.waypoints_model.invert_direction()
        wpdata1 = self.window.waypoints_model.waypoint_data(0)
        QtTest.QTest.mouseClick(self.window.save_ft, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        time.sleep(2)  # for change to take place
        QtTest.QTest.mouseClick(self.window.fetch_ft, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        wpdata2 = self.window.waypoints_model.waypoint_data(0)
        assert wpdata2.lat == wpdata1.lat
        # to undo changes
        self.window.waypoints_model.invert_direction()
        QtTest.QTest.mouseClick(self.window.save_ft, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        # to let server process
        time.sleep(2)

    def test_autosave(self):
        self._login()
        self._activate_project_at_index(0)
        QtTest.QTest.mouseClick(self.window.autoSave, QtCore.Qt.LeftButton,
                                pos=QtCore.QPoint(2, self.window.autoSave.height() / 2))
        QtWidgets.QApplication.processEvents()
        # sleeping to let server do the change
        time.sleep(3)
        with self.app.app_context():
            project = Project.query.filter_by(id=self.window.active_pid).first()
        assert project.autosave is self.window.autoSave.isChecked()
        QtTest.QTest.mouseClick(self.window.autoSave, QtCore.Qt.LeftButton,
                                pos=QtCore.QPoint(2, self.window.autoSave.height() / 2))
        QtWidgets.QApplication.processEvents()
        # top let server process
        time.sleep(2)