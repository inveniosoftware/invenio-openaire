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
"""Tests for OpenAIRE dataset loaders and resolvers."""

from __future__ import absolute_import, print_function

import os

import pytest
from invenio_pidstore.models import PersistentIdentifier as PID
from invenio_pidstore.models import PIDStatus
from invenio_records.api import Record as R
from jsonref import JsonRef
from jsonresolver import JSONResolver
from jsonresolver.contrib.jsonref import json_loader_factory
from jsonschema.exceptions import ValidationError

from invenio_openaire.loaders import GeoNamesResolver, LocalFundRefLoader, \
    LocalOAIRELoader
from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects


def load_funders_testdata():
    """Load the funders test data."""
    testdir = os.path.dirname(__file__)
    source = os.path.join(testdir, 'testdata/fundref_test.rdf')
    # Setup the fixed lookup dictionary for country code resolver
    cc_resolver = GeoNamesResolver(cc_data={'1': 'US', '2': 'CH'})
    loader = LocalFundRefLoader(source=source,
                                cc_resolver=cc_resolver)
    harvest_fundref(loader=loader)


def load_grants_testdata():
    """Load the grants test data."""
    testdir = os.path.dirname(__file__)
    source = os.path.join(testdir, 'testdata/openaire_test.sqlite')
    loader = LocalOAIRELoader(source=source)
    harvest_openaire_projects(loader=loader)


def load_all_testdata():
    """Load the funders and grants test data."""
    load_funders_testdata()
    load_grants_testdata()


def test_funders_json_resolving(app):
    """Test the loadef for the FundRef dataset."""
    # Test loading the real FundRef dataset.
    # 'grant': {'$ref': 'https://zenodo.org/funders/10.19/11/grants/22'}
    with app.app_context():
        load_funders_testdata()  # Load test data
        example_funder = {
            'doi': 'http://dx.doi.org/13.13039/003',
            'name': 'Some funder',
            'acronyms': ['SF', ],
            'parent': {'$ref': 'http://dx.doi.org/10.13039/002'},
            'country': "US",
        }
        json_resolver = JSONResolver(
            plugins=['invenio_openaire.resolvers.funders',
                     'invenio_openaire.resolvers.grants'])
        loader_cls = json_loader_factory(json_resolver)
        loader = loader_cls()
        out_json = JsonRef.replace_refs(example_funder, loader=loader)
        assert out_json['parent']['name'] == 'Department of Bar'
        assert out_json['parent']['parent']['name'] == 'University of Foo'


def test_grants_json_resolving(app):
    """Test the loadef for the FundRef dataset."""
    with app.app_context():
        load_grants_testdata()
        grant_ref = {'$ref': 'http://inveniosoftware.org/10.13039/501100000923'
                             '/grants/DP0667033'}
        json_resolver = JSONResolver(
                plugins=['invenio_openaire.resolvers.grants'])
        loader_cls = json_loader_factory(json_resolver)
        loader = loader_cls()
        data = JsonRef.replace_refs(grant_ref, loader=loader)
        assert data['title'].startswith('Dispersal and colonisation')


def test_funder_ep_resolving(app):
    """Test funder resolving through entry point-registered JSON resolver."""
    with app.app_context():
        json1 = {
            'internal_id': '10.13039/001',
            'parent': '',
            'name': 'Foo',
        }
        json2 = {
            'internal_id': '10.13039/002',
            'parent': {'$ref': 'http://dx.doi.org/10.13039/001'},
            'name': 'Bar',
        }
        r1 = R.create(json1)
        PID.create('fundr', json1['internal_id'], object_type='rec',
                   object_uuid=r1.id, status=PIDStatus.REGISTERED)
        r2 = R.create(json2)
        PID.create('fundr', json2['internal_id'], object_type='rec',
                   object_uuid=r2.id, status=PIDStatus.REGISTERED)
        assert r2.replace_refs()['parent'] == json1


def test_funder_schema_ep_resolving(app):
    """Test schema validation using entry-point registered schemas."""
    with app.app_context():
        app.config.update(JSONSCHEMAS_HOST='inveniosoftware.org')
        json_valid = {
            '$schema': {'$ref': 'http://inveniosoftware.org/schemas/funders/'
                                'funder-v1.0.0.json'},
            'doi': '10.13039/001',
            'alternateIdentifiers': [],
            'title': 'Foobar',
            'acronyms': ['FB', 'Foo'],
            'country': 'PL',
            'type': 'org',
            'subtype': 'organization',
            'parent': {'$ref': 'http://dx.doi.org/10.13039/002'},
        }
        json_invalid = dict(json_valid)
        json_invalid['acronyms'] = 'not_a_list'
        # Should not raise validation errors
        R.create(json_valid)
        # Should raise validation error beucase of the field 'acronyms'
        with pytest.raises(ValidationError) as exc_info:
            R.create(json_invalid)
        assert exc_info.value.instance == 'not_a_list'


def test_grant_schema_ep_resolving(app):
    """Test schema validation using entry-point registered schemas."""
    with app.app_context():
        app.config.update(JSONSCHEMAS_HOST='inveniosoftware.org')
        json_valid = {
            '$schema': {'$ref': 'http://inveniosoftware.org/schemas/grants/'
                                'grant-v1.0.0.json'},
            'internal_id': '10.13039/001/grants/0001',
            'identifiers': {
                'oai_id': 'oai_id00001',
                'eurepo': '/eurepo/id00001',
            },
            'code': '0001',
            'title': 'Grant Foobar',
            'acronym': 'GF',
            'startdate': 'startdate',
            'enddate': 'startdate',
            'funder': {'$ref': 'http://dx.doi.org/10.13039/001'},
        }
        json_invalid = dict(json_valid)
        json_invalid['identifiers'] = 'not_a_list'
        # Should not raise validation errors
        R.create(json_valid)
        # Should raise validation error beucase of the field 'acronyms'
        with pytest.raises(ValidationError) as exc_info:
            R.create(json_invalid)
        assert exc_info.value.instance == 'not_a_list'
