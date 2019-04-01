#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

log = logging.getLogger('CameraBatch')


def show():
    """
    Shows ui in maya

    :raises: None

    :return: None
    :rtype: NoneType
    """
    from .ui.ui import UI
    from .ui import utils

    cam_win = UI(utils.get_maya_window())
    cam_win.show()
