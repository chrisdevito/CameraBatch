#!/usr/bin/python
# -*- coding: utf-8 -*-

from .logger import myLogger
log = myLogger(debug=True)

__title__ = 'CameraBatch'
__author__ = 'Christopher DeVito'
__email__ = 'chrisdevito@chribis.com'
__url__ = ''
__version__ = '0.1.0'
__license__ = ''
__description__ = '''A Maya camera batcher.'''

from .utils import *
