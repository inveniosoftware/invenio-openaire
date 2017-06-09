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

"""Tests for OpenAIRE dataset loaders and resolvers."""

from __future__ import absolute_import, print_function

import os

import pytest
from invenio_pidstore.models import PersistentIdentifier as PID
from invenio_pidstore.models import PIDStatus
from invenio_records.api import Record as R
from jsonref import JsonRef, JsonRefError
from jsonresolver import JSONResolver
from jsonresolver.contrib.jsonref import json_loader_factory
from jsonschema.exceptions import ValidationError

from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects


def load_funders_testdata():
    """Load the funders test data."""
    testdir = os.path.dirname(__file__)
    source = os.path.join(testdir, 'testdata/fundref_test.rdf')
    harvest_fundref(source=source)


def load_grants_testdata():
    """Load the grants test data."""
    testdir = os.path.dirname(__file__)
    source = os.path.join(testdir, 'testdata/openaire_test.sqlite')
    harvest_openaire_projects(source=source)


def load_all_testdata():
    """Load the funders and grants test data."""
    load_funders_testdata()
    load_grants_testdata()


# Test the resolver rule for two possible DOI hosts: dx.doi.org and doi.org
@pytest.mark.parametrize("doi_host", ['dx.doi.org', 'doi.org'])
def test_funders_json_resolving(doi_host, app, db, es):
    """Test the loadef for the FundRef dataset."""
    # Test loading the real FundRef dataset.
    # 'grant': {'$ref': 'https://zenodo.org/funders/10.19/11/grants/22'}
    load_funders_testdata()  # Load test data
    example_funder = {
        'doi': 'http://{doi_host}/10.13039/003'.format(doi_host=doi_host),
        'name': 'Some funder',
        'acronyms': ['SF', ],
        'parent': {'$ref': 'http://{doi_host}/10.13039/002'.format(
            doi_host=doi_host)},
        'country': "US",
    }
    json_resolver = JSONResolver(
        plugins=['invenio_openaire.resolvers.funders',
                 'invenio_openaire.resolvers.grants'])
    loader_cls = json_loader_factory(json_resolver)
    loader = loader_cls()
    print(PID.query.all())
    out_json = JsonRef.replace_refs(example_funder, loader=loader)
    assert out_json['parent']['name'] == 'Department of Bar'
    assert out_json['parent']['parent']['name'] == 'University of Foo'


def test_grants_json_resolving(app, db, es, funders):
    """Test the loadef for the FundRef dataset."""
    load_grants_testdata()
    grant_ref = {'$ref': 'http://inveniosoftware.org/grants/'
                         '10.13039/501100000923::DP0667033'}
    json_resolver = JSONResolver(
        plugins=['invenio_openaire.resolvers.grants'])
    loader_cls = json_loader_factory(json_resolver)
    loader = loader_cls()
    data = JsonRef.replace_refs(grant_ref, loader=loader)
    assert data['title'].startswith('Dispersal and colonisation')

    # Invalid grant reference
    grant_ref = {'$ref': 'http://inveniosoftware.org/grants/'
                         '10.13039/invalid'}
    data = JsonRef.replace_refs(grant_ref, loader=loader)
    pytest.raises(JsonRefError, dict, data)


def test_funder_ep_resolving(app, db):
    """Test funder resolving through entry point-registered JSON resolver."""
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
    PID.create('frdoi', json1['internal_id'], object_type='rec',
               object_uuid=r1.id, status=PIDStatus.REGISTERED)
    r2 = R.create(json2)
    PID.create('frdoi', json2['internal_id'], object_type='rec',
               object_uuid=r2.id, status=PIDStatus.REGISTERED)
    assert r2.replace_refs()['parent'] == json1


def test_funder_schema_ep_resolving(app, db):
    """Test schema validation using entry-point registered schemas."""
    json_valid = {
        '$schema': (
            'http://inveniosoftware.org/schemas/funders/funder-v1.0.0.json'),
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


def test_grant_schema_ep_resolving(app, db):
    """Test schema validation using entry-point registered schemas."""
    json_valid = {
        '$schema': (
            'http://inveniosoftware.org/schemas/grants/grant-v1.0.0.json'),
        'internal_id': '10.13039/001::0001',
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
    # Should not raise validation errors
    R.create(json_valid)

    # Should raise validation error because of the field 'acronyms'
    json_invalid = dict(json_valid)
    json_invalid['identifiers'] = 'not_an_object'
    with pytest.raises(ValidationError) as exc_info:
        R.create(json_invalid)
    assert exc_info.value.instance == 'not_an_object'
