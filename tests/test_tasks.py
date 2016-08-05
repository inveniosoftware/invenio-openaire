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

"""Harvesting task tests."""

from __future__ import absolute_import, print_function

from invenio_pidstore.models import PersistentIdentifier
from invenio_records.api import Record
from invenio_records.models import RecordMetadata

from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects


def test_harvest_openaire_projects(app, db):
    """Test harvest_openaire_projects."""
    with app.app_context():
        # Use local OpenAIRE loader
        harvest_openaire_projects(source='tests/testdata/openaire_test.sqlite')
        assert PersistentIdentifier.query.count() == 40
        assert RecordMetadata.query.count() == 10


def test_harvest_fundref(app, db):
    """Test harvest_openaire_projects."""
    with app.app_context():
        harvest_fundref(source='tests/testdata/fundref_test.rdf')
        print(PersistentIdentifier.query.all())
        assert PersistentIdentifier.query.count() == 6
        assert RecordMetadata.query.count() == 5


def test_reharvest_fundref(app, db):
    """Test harvest_openaire_projects."""
    with app.app_context():
        harvest_fundref(source='tests/testdata/fundref_test.rdf')
        assert PersistentIdentifier.query.count() == 6
        assert RecordMetadata.query.count() == 5
        recid = PersistentIdentifier.query.first().object_uuid
        test_date = "2002-01-01T16:00:00.000000"
        record = Record.get_record(recid)
        record['remote_modified'] = test_date
        record.commit()
        db.session.commit()
        harvest_fundref(source='tests/testdata/fundref_test.rdf')
        assert PersistentIdentifier.query.count() == 6
        assert RecordMetadata.query.count() == 5
        record = Record.get_record(recid)
        assert record['remote_modified'] != test_date


def test_harvest_all(app, db):
    """Test harvest_openaire_projects."""
    with app.app_context():
        harvest_fundref(source='tests/testdata/fundref_test.rdf')
        assert PersistentIdentifier.query.count() == 6
        assert RecordMetadata.query.count() == 5
        harvest_openaire_projects(source='tests/testdata/openaire_test.sqlite')
        assert PersistentIdentifier.query.count() == 46
        assert RecordMetadata.query.count() == 15
