# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Harvesting task tests."""

from __future__ import absolute_import, print_function

from invenio_pidstore.models import PersistentIdentifier
from invenio_records.api import Record
from invenio_records.models import RecordMetadata

from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects


def test_harvest_openaire_projects(app, db, es, funders):
    """Test harvest_openaire_projects."""
    with app.app_context():
        # Use local OpenAIRE loader
        harvest_openaire_projects(source='tests/testdata/openaire_test.sqlite')
        assert PersistentIdentifier.query.count() == 46
        assert RecordMetadata.query.count() == 15


def test_harvest_fundref(app, db, es):
    """Test harvest_openaire_projects."""
    with app.app_context():
        harvest_fundref(source='tests/testdata/fundref_test.rdf')
        print(PersistentIdentifier.query.all())
        assert PersistentIdentifier.query.count() == 6
        assert RecordMetadata.query.count() == 5


def test_reharvest_fundref(app, db, es):
    """Test harvest_openaire_projects."""
    with app.app_context():
        harvest_fundref(source='tests/testdata/fundref_test.rdf')
        assert PersistentIdentifier.query.count() == 6
        assert RecordMetadata.query.count() == 5
        recid = PersistentIdentifier.query.first().object_uuid
        record = Record.get_record(recid)
        record['title'] = 'Foobar'
        record.commit()
        db.session.commit()
        harvest_fundref(source='tests/testdata/fundref_test.rdf')
        assert PersistentIdentifier.query.count() == 6
        assert RecordMetadata.query.count() == 5
        record = Record.get_record(recid)
        assert record['remote_modified'] != 'Foobar'


def test_harvest_all(app, db, es):
    """Test harvest_openaire_projects."""
    with app.app_context():
        harvest_fundref(source='tests/testdata/fundref_test.rdf')
        assert PersistentIdentifier.query.count() == 6
        assert RecordMetadata.query.count() == 5
        harvest_openaire_projects(source='tests/testdata/openaire_test.sqlite')
        assert PersistentIdentifier.query.count() == 46
        assert RecordMetadata.query.count() == 15
