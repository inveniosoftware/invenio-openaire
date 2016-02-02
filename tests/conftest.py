# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile

import pytest
from elasticsearch.exceptions import RequestError
from flask import Flask
from flask_celeryext import create_celery_app
from flask_cli import FlaskCLI, ScriptInfo
from invenio_celery import InvenioCelery
from invenio_db import InvenioDB, db
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_search import InvenioSearch, current_search
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from invenio_openaire import InvenioOpenAIRE


@pytest.yield_fixture()
def app(request):
    """Flask application fixture."""
    # Set temporary instance path for sqlite
    instance_path = tempfile.mkdtemp()
    app = Flask('testapp', instance_path=instance_path)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        CELERY_ALWAYS_EAGER=True,
        CELERY_RESULT_BACKEND="cache",
        CELERY_CACHE_BACKEND="memory",
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        OPENAIRE_OAI_LOCAL_SOURCE='invenio_openaire/data/oaire_local.sqlite',
        SEARCH_AUTOINDEX=[],
        TESTING=True,
    )

    FlaskCLI(app)
    InvenioDB(app)
    InvenioRecords(app)
    InvenioCelery(app)
    InvenioPIDStore(app)
    InvenioOpenAIRE(app)
    InvenioSearch(app)
    InvenioJSONSchemas(app)

    with app.app_context():
        if not database_exists(str(db.engine.url)):
            create_database(str(db.engine.url))
        db.drop_all()
        db.create_all()

        yield app

        drop_database(str(db.engine.url))
    shutil.rmtree(instance_path)


@pytest.yield_fixture()
def script_info(app):
    """CLI object."""
    with app.app_context():
        yield ScriptInfo(create_app=lambda info: app)


@pytest.yield_fixture()
def es(app):
    """Provide elasticsearch access."""
    try:
        list(current_search.create())
    except RequestError:
        list(current_search.delete(ignore=[404]))
        list(current_search.create())
    yield current_search
    list(current_search.delete(ignore=[404]))
