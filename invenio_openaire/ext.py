# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""OpenAIRE service integration for Invenio repositories."""

from __future__ import absolute_import, print_function

from invenio_indexer.signals import before_record_index

from . import config
from .cli import openaire
from .indexer import indexer_receiver


class InvenioOpenAIRE(object):
    """Invenio-OpenAIRE extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.cli.add_command(openaire)
        before_record_index.connect(indexer_receiver, sender=app)
        app.extensions['invenio-openaire'] = self

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith("OPENAIRE_"):
                app.config.setdefault(k, getattr(config, k))
