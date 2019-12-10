#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import logging
from .widgets import (CameraList, ObjectItem, LineEditWidget)
from .models import Camera

from maya import (OpenMaya, cmds, mel)

from functools import partial
from collections import defaultdict

try:
    from ..packages.Qt import (QtWidgets, QtCore, QtTest)
except ImportError:
    pass

from .. import api
reload(api)

this_package = os.path.abspath(os.path.dirname(__file__))
this_path = partial(os.path.join, this_package)

log = logging.getLogger("CameraBatch")


class UI(QtWidgets.QDialog):
    """
    :class:`UI` inherits a QDialog and customizes it.
    """
    def __init__(self, parent=None):

        super(UI, self).__init__(parent)

        # Set window
        self.setWindowTitle("Camera Batch")
        self.resize(450, 275)

        # Grab stylesheet
        with open(this_path("style.css")) as f:
            self.setStyleSheet(f.read())

        # Center to frame.
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        # Our main layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.maya_hooks = MayaHooks(parent=self)
        self.maya_hooks.before_scene_changed.connect(self.clear_lists)
        self.maya_hooks.before_scene_export.connect(self.export_timer)
        self.maya_hooks.render_finished.connect(self.render_next)
        self.maya_hooks.render_cancelled.connect(self.render_stop)

        self.camera_nodes = []

        self.create_layout()
        self.create_connections()
        self.create_tooltips()

        self.setLayout(self.layout)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def create_layout(self):
        """
        Creates layout.

        :raises: None

        :return: None
        :rtype: NoneType
        """
        self.label = QtWidgets.QLabel("Camera List:")
        self.cam_list = CameraList(self)

        self.up_button = QtWidgets.QPushButton("Move Up")
        self.up_button.setMinimumWidth(100)
        self.up_button.setMinimumHeight(25)

        self.down_button = QtWidgets.QPushButton("Move Down")
        self.down_button.setMinimumWidth(100)
        self.down_button.setMinimumHeight(25)

        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.setMinimumWidth(100)
        self.add_button.setMinimumHeight(25)

        self.remove_button = QtWidgets.QPushButton("Remove")
        self.remove_button.setMinimumWidth(100)
        self.remove_button.setMinimumHeight(25)

        self.batch_button = QtWidgets.QPushButton("Batch Cameras")
        self.batch_button.setMinimumHeight(40)

        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.cam_layout = QtWidgets.QHBoxLayout()
        self.button_layout = QtWidgets.QVBoxLayout()
        self.add_remove_layout = QtWidgets.QVBoxLayout()
        self.file_layout = QtWidgets.QHBoxLayout()

        self.button_layout.addWidget(self.up_button, 1)
        self.button_layout.addWidget(self.down_button, 1)
        self.button_layout.addWidget(self.add_button, 1)
        self.button_layout.addWidget(self.remove_button, 1)
        self.button_layout.setContentsMargins(5, 0, 0, 0)

        self.cam_layout.addWidget(self.cam_list, 1)
        self.cam_layout.addLayout(self.button_layout)

        self.layout.addWidget(self.label)
        self.layout.addLayout(self.cam_layout)
        self.layout.addWidget(self.line, 1)
        self.layout.addLayout(self.file_layout)
        self.layout.addWidget(self.batch_button)

    def create_connections(self):
        """
        Creates connections to buttons.

        :raises: None

        :return: None
        :rtype: NoneType
        """
        self.up_button.clicked.connect(self.move_items_up)
        self.down_button.clicked.connect(self.move_items_down)
        self.remove_button.clicked.connect(self.delete_obj_items)
        self.add_button.clicked.connect(self.add_clicked)
        self.batch_button.clicked.connect(self.batch_cameras)
        self.cam_list.itemSelectionChanged.connect(self.select_cameras)

    def create_tooltips(self):
        """
        Creates tool tips for various widgets.

        :raises: None

        :return: None
        :rtype: NoneType
        """
        self.up_button.setToolTip("Move all selected cameras up by one index.")
        self.down_button.setToolTip("Move all selected cameras"
                                    " down by one index.")
        self.remove_button.setToolTip("Remove all selected"
                                      " cameras from list.")
        self.add_button.setToolTip("Add all selected camera from list.")
        self.batch_button.setToolTip("Create a batch camera.")
        self.cam_list.setToolTip("Cameras added to the list"
                                 " are in order\n of the camera"
                                 " to be batched.")

    def clear_lists(self):
        """
        Clears list

        :raises: None

        :return: None
        :rtype: NoneType
        """
        self.maya_hooks.clear_callbacks()
        self.cam_list.clear()

    def add_clicked(self):
        """
        Add button

        :raises: None

        :return: None
        :rtype: NoneType
        """
        nodes = cmds.ls(selection=True)

        for node in nodes:

            if cmds.objExists(node + ".start_frame"):
                start_frame = cmds.getAttr(node + ".start_frame")
            else:
                start_frame = 1

            if cmds.objExists(node + ".end_frame"):
                end_frame = cmds.getAttr(node + ".end_frame")
            else:
                end_frame = 10

            if len(self.cam_list.findItems(
                "{0}\t{1} - {2}".format(node, start_frame, end_frame),
                    QtCore.Qt.MatchExactly)):
                log.info("%s already added to the list." % node)
                continue

            self.new_obj_item(Camera(node))

    def new_obj_item(self, node):
        """
        Creates a new obj item

        :raises: None

        :return: None
        :rtype: NoneType
        """
        item = ObjectItem(node)

        self.cam_list.addItem(item)

        # Add delete callbacks
        del_callback = partial(self.delete_obj_item, item)
        ren_callback = partial(self.rename_obj_item, item)
        start_callback = partial(self.start_obj_item, item)
        end_callback = partial(self.end_obj_item, item)

        self.maya_hooks.add_about_to_delete_callback(node, del_callback)
        self.maya_hooks.add_named_changed_callback(node, ren_callback)
        self.maya_hooks.add_frame_changed_callback(
            node, [start_callback, end_callback])

    def batch_cameras(self):
        """
        Sequences the camera/images

        :raises: None

        :return: None
        :rtype: NoneType
        """
        self.camera_nodes = []

        for i in xrange(self.cam_list.count()):
            self.camera_nodes.append(self.cam_list.item(i).camera)

        if not self.camera_nodes:
            log.error("No cameras added to sequence list.")
            raise RuntimeError("No cameras added to sequence list.")

        if not cmds.file(query=True, sceneName=True):
            raise RuntimeError("Save your scene first!")

        self.render_next()

    def export_timer(self):
        try:
            license_info = cmds.fileInfo("license", query=True)[0]
            if license_info == "student":
                timer = QtCore.QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(self.press_enter)
                timer.start(300)
        except Exception:
            return

    def press_enter(self):
        QtTest.QTest.keyPress(None, QtCore.Qt.Key.Key_Enter)

    def render_next(self):

        if self.camera_nodes:
            api.batch_camera(self.camera_nodes[0])
            log.info("Rendering {0} {1} - {2}....".format(
                self.camera_nodes[0].name,
                self.camera_nodes[0].start_frame,
                self.camera_nodes[0].end_frame))
            self.camera_nodes.pop(0)
            return

        log.info("All renders finished!")

    def render_stop(self):
        self.camera_nodes = []
        mel.eval("cancelBatchRender;")
        log.info("All renders cancelled!")

    def delete_obj_item(self, item):
        """
        Deletes selected items

        :raises: None

        :return: None
        :rtype: NoneType
        """
        try:
            self.cam_list.takeItem(self.cam_list.indexFromItem(item).row())
        except RuntimeError as e:
            if "Internal C++ object (ObjectItem) already deleted" in str(e):
                pass
                raise

    def delete_obj_items(self):
        """
        Deletes selected items

        :raises: None

        :return: None
        :rtype: NoneType
        """
        try:
            for item in self.cam_list.selectedItems():
                self.cam_list.takeItem(
                    self.cam_list.indexFromItem(item).row())
        except RuntimeError as e:
            if "Internal C++ object (ObjectItem) already deleted" in str(e):
                pass
                raise

    def rename_obj_item(self, item, old_name, new_name):

        try:
            item.rename(new_name)

        except RuntimeError as e:
            if "Internal C++ object (ObjectItem) already deleted" in str(e):
                pass
                raise

    def start_obj_item(self, item, new_start):

        try:
            item.start_frame(new_start)

        except RuntimeError as e:
            if "Internal C++ object (ObjectItem) already deleted" in str(e):
                pass
                raise

    def end_obj_item(self, item, new_end):

        try:
            item.end_frame(new_end)

        except RuntimeError as e:
            if "Internal C++ object (ObjectItem) already deleted" in str(e):
                pass
                raise

    def move_items_up(self):
        """
        Moves selected items up

        :raises: None

        :return: None
        :rtype: NoneType
        """
        newIndexes = []
        lastIndex = self.cam_list.count() - 1
        indexes = sorted([[self.cam_list.indexFromItem(item).row(), item]
                          for item in self.cam_list.selectedItems()])

        for oldIndex, item in indexes:

            newIndex = oldIndex - 1

            if newIndex < 0:
                newIndex = lastIndex

            newIndexes.append(newIndex)

            if newIndex == self.cam_list.indexFromItem(item).row():
                continue

            self.cam_list.takeItem(oldIndex)
            self.cam_list.insertItem(newIndex, item)

        [self.cam_list.item(ind).setSelected(True) for ind in newIndexes]

    def move_items_down(self):
        """
        Moves selected items down

        :raises: None

        :return: None
        :rtype: NoneType
        """
        newIndexes = []
        lastIndex = self.cam_list.count() - 1
        indexes = sorted(
            [[self.cam_list.indexFromItem(item).row(), item]
             for item in self.cam_list.selectedItems()], reverse=True)

        for oldIndex, item in indexes:

            newIndex = oldIndex + 1

            if newIndex > lastIndex:
                newIndex = 0

            newIndexes.append(newIndex)

            if newIndex == self.cam_list.indexFromItem(item).row():
                continue

            self.cam_list.takeItem(oldIndex)
            self.cam_list.insertItem(newIndex, item)

        [self.cam_list.item(ind).setSelected(True) for ind in newIndexes]

    def select_cameras(self):

        selected_items = [item.camera.name
                          for item in self.cam_list.selectedItems()]

        if selected_items:
            cmds.select(selected_items)

    def closeEvent(self, event):

        if self.camera_nodes:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Cancel Render?",
                "Closing the Batch Camera tool cancels renders."
                " Do you want to cancel renders?",
                QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.No:
                event.ignore()
            else:
                self.render_stop()
                self.maya_hooks.clear_callbacks()
                self.maya_hooks.clear_scene_callbacks()
                super(UI, self).closeEvent(event)

        else:
            self.maya_hooks.clear_callbacks()
            self.maya_hooks.clear_scene_callbacks()
            super(UI, self).closeEvent(event)

    def keyPressEvent(self, event):
        '''
        Override key focus issue.
        '''
        if event.key() in (QtCore.Qt.Key.Key_Shift, QtCore.Qt.Key.Key_Control):
            event.accept()
        else:
            event.ignore()


class MayaHooks(QtCore.QObject):
    '''Manage all Maya Message Callbacks (Hooks)'''

    before_scene_changed = QtCore.Signal()
    before_scene_export = QtCore.Signal()
    scene_selection_changed = QtCore.Signal()
    render_finished = QtCore.Signal()
    render_cancelled = QtCore.Signal()

    def __init__(self, parent=None):
        super(MayaHooks, self).__init__(parent=parent)

        self.callback_ids = defaultdict(list)
        self.scene_callback_ids = []
        self.output_callback_ids = []

        before_change_messages = [
            OpenMaya.MSceneMessage.kBeforeOpen,
            OpenMaya.MSceneMessage.kBeforeNew,
        ]
        for i, msg in enumerate(before_change_messages):
            callback_id = OpenMaya.MSceneMessage.addCallback(
                msg,
                self.emit_before_scene_changed
            )
            self.scene_callback_ids.append(callback_id)

        callback_output_id = OpenMaya.MCommandMessage.addCommandOutputCallback(
            self.emit_output_changed)

        callback_save_id = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeExport,
            self.emit_before_scene_export)

        self.output_callback_ids.append(callback_output_id)
        self.scene_callback_ids.append(callback_save_id)

    def emit_before_scene_changed(self, *args):
        self.before_scene_changed.emit()

    def emit_output_changed(self, msg, msgType, *args):

        if "[Redshift] License returned" in msg:
            self.render_finished.emit()

        elif msg == ("Rendering Completed. "
                     "See mayaRenderLog.txt for information."):
            self.render_finished.emit()

        elif msg == "Render Cancelled. ":
            self.render_cancelled.emit()

    def emit_before_scene_export(self, *args):
        self.before_scene_export.emit()

    def emit_scene_selection_changed(self, *args):
        self.scene_selection_changed.emit()

    def add_named_changed_callback(self, node, callback):

        mobject = node.__mobject__()

        def maya_callback(mobject, old_name, data):
            new_name = OpenMaya.MFnDependencyNode(mobject).name()
            callback(old_name, new_name)

        callback_id = OpenMaya.MNodeMessage.addNameChangedCallback(
            mobject,
            maya_callback,
        )
        self.callback_ids[node].append(callback_id)

    def add_frame_changed_callback(self, node, callbacks):

        mobject = node.__mobject__()

        def maya_callback(msg, src_plug, dest_plug, data):

            if msg != 2056:
                return

            src_plug_name = src_plug.partialName()

            if src_plug_name == "start_frame":
                new_frame = cmds.getAttr(
                    OpenMaya.MFnDependencyNode(
                        mobject).name() + ".start_frame")
                callbacks[0](new_frame)

            elif src_plug_name == "end_frame":
                new_frame = cmds.getAttr(
                    OpenMaya.MFnDependencyNode(
                        mobject).name() + ".end_frame")
                callbacks[1](new_frame)

            else:
                return

        callback_id = OpenMaya.MNodeMessage.addAttributeChangedCallback(
            mobject,
            maya_callback,
        )
        self.callback_ids[node].append(callback_id)

    def add_about_to_delete_callback(self, node, callback):

        mobject = node.__mobject__()

        def maya_callback(depend_node, dg_modifier, data):

            callback_ids = self.callback_ids.pop(node, None)
            if callback_ids:
                for callback_id in callback_ids:
                    OpenMaya.MMessage.removeCallback(callback_id)
            callback()

        callback_id = OpenMaya.MNodeMessage.addNodeAboutToDeleteCallback(
            mobject,
            maya_callback,
        )
        self.callback_ids[node].append(callback_id)

    def clear_callbacks(self):
        for node, callback_ids in self.callback_ids.items():
            for callback_id in callback_ids:
                OpenMaya.MMessage.removeCallback(callback_id)
        self.callback_ids = defaultdict(list)

    def clear_scene_callbacks(self):
        for callback_id in self.scene_callback_ids:
            OpenMaya.MMessage.removeCallback(callback_id)
        for callback_id in self.output_callback_ids:
            OpenMaya.MNodeMessage.removeCallback(callback_id)
        self.scene_callback_ids = []
        self.output_callback_ids = []
