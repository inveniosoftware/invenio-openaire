# SPDX-FileCopyrightText: 2015-2019 CERN.
# SPDX-License-Identifier: MIT

"""Module tests."""

from __future__ import absolute_import, print_function

from flask import Flask

from invenio_openaire import InvenioOpenAIRE


def test_version():
    """Test version import."""
    from invenio_openaire import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    ext = InvenioOpenAIRE(app)
    assert 'invenio-openaire' in app.extensions

    app = Flask('testapp')
    ext = InvenioOpenAIRE()
    assert 'invenio-openaire' not in app.extensions
    ext.init_app(app)
    assert 'invenio-openaire' in app.extensions
