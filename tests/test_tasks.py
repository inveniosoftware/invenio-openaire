# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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
from invenio_records.models import RecordMetadata

from invenio_openaire.loaders import GeoNamesResolver, LocalFundRefLoader, \
    LocalOAIRELoader
from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects


def test_harvest_openaire_projects(app):
    """Test harvest_openaire_projects."""
    with app.app_context():
        # Use local OpenAIRE loader
        loader = LocalOAIRELoader(source='tests/testdata/openaire_test.sqlite')
        harvest_openaire_projects(loader=loader)
        assert PersistentIdentifier.query.count() == 10
        assert RecordMetadata.query.count() == 10


def test_harvest_fundref(app):
    """Test harvest_openaire_projects."""
    with app.app_context():
        # Use local FundRef loader
        source = 'tests/testdata/fundref_test.rdf'
        # Setup the fixed lookup dictionary for country code resolver
        cc_resolver = GeoNamesResolver(cc_data={'1': 'US', '2': 'CH'})
        loader = LocalFundRefLoader(source=source,
                                    cc_resolver=cc_resolver)
        harvest_fundref(loader=loader)
        assert PersistentIdentifier.query.count() == 5
        assert RecordMetadata.query.count() == 5


def test_harvest_all(app):
    """Test harvest_openaire_projects."""
    with app.app_context():
        loader = LocalOAIRELoader(source='tests/testdata/openaire_test.sqlite')
        harvest_openaire_projects(loader=loader)
        assert PersistentIdentifier.query.count() == 10
        assert RecordMetadata.query.count() == 10
        source = 'tests/testdata/fundref_test.rdf'
        # Setup the fixed lookup dictionary for country code resolver
        cc_resolver = GeoNamesResolver(cc_data={'1': 'US', '2': 'CH'})
        loader = LocalFundRefLoader(source=source,
                                    cc_resolver=cc_resolver)
        harvest_fundref(loader=loader)
        assert PersistentIdentifier.query.count() == 15
        assert RecordMetadata.query.count() == 15
