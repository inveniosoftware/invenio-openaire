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
from os.path import dirname, join

import pytest
from elasticsearch.exceptions import RequestError
from flask import Flask
from flask.cli import ScriptInfo
from flask_login import LoginManager
from invenio_celery import InvenioCelery
from invenio_db import db as db_
from invenio_db import InvenioDB
from invenio_indexer import InvenioIndexer
from invenio_indexer.api import RecordIndexer
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_records.models import RecordMetadata
from invenio_records_rest.utils import PIDConverter, PIDPathConverter
from invenio_search import InvenioSearch, current_search
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_openaire import InvenioOpenAIRE
from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects


class MockSickle(object):
    """Mock of the OAI-PMH harvester.

    Load the grant XML data from file and mock the Sickle datatype.
    """

    def __init__(self, source):
        """Initialize the harvester."""
        self.source = source
        fname = join(dirname(__file__), 'testdata/mock_oai_pmh.txt')
        with open(fname, 'r') as f:
            self.data = f.readlines()

    class MockRecordType(object):
        """Mock the OAI-PMH data type."""

        def __init__(self, raw_data):
            """Init the data type."""
            self.raw = raw_data

    def ListRecords(self, metadataPrefix=None, set=None):
        """Record list generator."""
        for grant_xml in self.data:
            yield self.MockRecordType(grant_xml)


@pytest.yield_fixture()
def app(request):
    """Flask application fixture."""
    # Set temporary instance path for sqlite
    instance_path = tempfile.mkdtemp()
    app = Flask('testapp', instance_path=instance_path)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        INDEXER_REPLACE_REFS=True,
        CELERY_ALWAYS_EAGER=True,
        CELERY_RESULT_BACKEND="cache",
        CELERY_CACHE_BACKEND="memory",
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        JSONSCHEMAS_HOST='inveniosoftware.org',
        OPENAIRE_OAI_LOCAL_SOURCE='invenio_openaire/data/oaire_local.sqlite',
        SEARCH_AUTOINDEX=[],
        TESTING=True,
    )

    app.url_map.converters['pid'] = PIDConverter
    app.url_map.converters['pidpath'] = PIDPathConverter

    LoginManager(app)
    InvenioDB(app)
    InvenioIndexer(app)
    InvenioRecords(app)
    InvenioCelery(app)
    InvenioPIDStore(app)
    InvenioOpenAIRE(app)
    InvenioSearch(app)
    InvenioJSONSchemas(app)

    with app.app_context():
        yield app

    shutil.rmtree(instance_path)


@pytest.yield_fixture()
def db(app):
    """Setup database."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.yield_fixture()
def script_info(app, db):
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
        list(current_search.create(ignore=[400]))
    yield current_search
    list(current_search.delete(ignore=[404]))


@pytest.yield_fixture()
def funders(app, es, db):
    """Funder records fixture."""
    harvest_fundref(source='tests/testdata/fundref_test.rdf')


@pytest.yield_fixture()
def grants(app, es, db, funders):
    """Grant records fixture."""
    harvest_openaire_projects(source='tests/testdata/openaire_test.sqlite')
    records = []
    for record in RecordMetadata.query.all():
        records.append(record.id)
        RecordIndexer().index_by_id(record.id)
    es.flush_and_refresh('_all')
    yield records


@pytest.yield_fixture()
def sqlite_tmpdb():
    """Create a temporary sqlite database file."""
    fd, path = tempfile.mkstemp("_db.sqlite")

    yield path

    os.remove(path)
