#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from maya import (cmds, mel)

log = logging.getLogger('CameraBatch')


def batch_camera(camera):

    cmds.setAttr("defaultRenderGlobals.startFrame", camera.start_frame)
    cmds.setAttr("defaultRenderGlobals.endFrame", camera.end_frame)

    for cam in cmds.ls(type="camera"):
        cmds.setAttr(cam + ".renderable", False)

    cmds.setAttr(camera.name + ".renderable", True)

    mel.eval("mayaBatchRender;")
