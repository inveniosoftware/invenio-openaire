# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Tests for OpenAIRE dataset loaders and resolvers."""

from __future__ import absolute_import, print_function

from invenio_pidstore.models import PersistentIdentifier
from invenio_records_rest import InvenioRecordsREST

from invenio_openaire.config import OPENAIRE_REST_ENDPOINTS
from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects


def test_records_rest(app, es):
    """Test Records REST."""
    app.config['RECORDS_REST_ENDPOINTS'] = OPENAIRE_REST_ENDPOINTS
    try:
        InvenioRecordsREST(app)
    except TypeError:
        # Temporary support Invenio-Records-REST v1.0.0a4
        del app.config['RECORDS_REST_ENDPOINTS']['frdoi']['default_media_type']
        del app.config['RECORDS_REST_ENDPOINTS']['grant']['default_media_type']
        InvenioRecordsREST(app)

    harvest_openaire_projects(path='tests/testdata/openaire_test.sqlite')
    harvest_fundref(path='tests/testdata/fundref_test.rdf')
    assert PersistentIdentifier.query.count() == 45

    with app.test_client() as client:
        res = client.get("/funders/10.13039/001")
        assert res.status_code == 200
        res = client.get("/funders/")
        assert res.status_code == 200
        res = client.get("/grants/10.13039/501100000923::LP0667725")
        assert res.status_code == 200
        res = client.get("/grants/")
        assert res.status_code == 200
