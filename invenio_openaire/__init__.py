# SPDX-FileCopyrightText: 2015-2019 CERN.
# SPDX-License-Identifier: MIT

"""OpenAIRE service integration for Invenio repositories."""

from __future__ import absolute_import, print_function

from .ext import InvenioOpenAIRE
from .version import __version__

__all__ = ('__version__', 'InvenioOpenAIRE')
