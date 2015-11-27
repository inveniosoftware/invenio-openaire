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
from mock import patch
from six import text_type

from invenio_openaire.errors import FunderNotFoundError
from invenio_openaire.loaders import FundRefDOIResolver, GeoNamesResolver, \
    LocalFundRefLoader, LocalOAIRELoader, RemoteFundRefLoader, \
    RemoteOAIRELoader


class MockSickle(object):
    """Mock of the OAI-PMH harvester.

    Load the grant XML data from file and mock the Sickle datatype.
    """

    def __init__(self, source):
        """Initialize the harvester."""
        self.source = source
        self.data = open('tests/testdata/mock_oai_pmh.txt', 'r').readlines()

    class MockRecordType(object):
        """Mock the OAI-PMH data type."""

        def __init__(self, raw_data):
            """Init the data type."""
            self.raw = raw_data

    def ListRecords(self, metadataPrefix=None, set=None):
        """Record list generator."""
        for grant_xml in self.data:
            yield self.MockRecordType(grant_xml)


class mock_requests(object):
    """Mock the requests library."""

    class MockResponse(object):
        """Mock of the Response object."""

        def __init__(self, text):
            self.text = text

    @classmethod
    def get(cls, source, stream=True):
        """Mock the get method."""
        testdata_path = os.path.join(os.path.dirname(__file__),
                                     'testdata/fundref_test.rdf')
        with open(testdata_path, 'r') as F:
            data = F.read()
        return cls.MockResponse(data)


def test_cc_resolver(app):
    """Test the GeoNames country code resolver."""
    with app.app_context():
        resolver = GeoNamesResolver()
        assert resolver.cc_from_id('8502121') == 'US'
        assert resolver.cc_from_id('8740971') == 'CH'
        assert resolver.cc_from_url(
            "http://sws.geonames.org/6252001/") == 'US'


def test_local_fundref_loader(app):
    """Test the loadef for the FundRef dataset."""
    # Test loading the real FundRef dataset.
    with app.app_context():
        frl = LocalFundRefLoader()
        json_dataset = list(frl.iter_funders())
        assert len(json_dataset) == 11565  # Current FundRef dataset size


def test_local_fundref_convert(app):
    """Test the XML to JSON conversion of local FundRef dataset."""
    # Test the keys and dict structure for test dataset
    with app.app_context():
        app.config.update(OPENAIRE_FUNDREF_LOCAL_SOURCE=os.path.join(
            os.path.dirname(__file__), 'testdata/fundref_test.rdf')
        )
        cc_data = {'1': 'US', '2': 'CH'}
        frl = LocalFundRefLoader(cc_resolver=GeoNamesResolver(cc_data=cc_data))
        d = {ds['doi']: ds for ds in frl.iter_funders()}

        assert d['10.13039/001']['name'] == 'University of Foo'
        assert len(d['10.13039/001']['acronyms']) == 2
        assert 'UoF' in d['10.13039/001']['acronyms']
        assert 'UOF' in d['10.13039/001']['acronyms']
        assert d['10.13039/001']['country'] == 'US'

        assert d['10.13039/002']['name'] == 'Department of Bar'
        assert len(d['10.13039/002']['acronyms']) == 1
        assert 'DoB' in d['10.13039/002']['acronyms']
        assert d['10.13039/002']['country'] == 'US'

        assert d['10.13039/003']['name'] == 'Department of Eggs'
        assert len(d['10.13039/003']['acronyms']) == 3
        assert 'EggsDept' in d['10.13039/003']['acronyms']
        assert 'DoE' in d['10.13039/003']['acronyms']
        assert 'DOE' in d['10.13039/003']['acronyms']
        assert d['10.13039/003']['country'] == 'US'

        assert d['10.13039/004']['name'] == 'Faculty of Spam'
        assert len(d['10.13039/004']['acronyms']) == 1
        assert 'FoS' in d['10.13039/004']['acronyms']
        assert d['10.13039/004']['country'] == 'US'

        assert d['10.13039/005']['name'] == 'University of Bacon'
        assert len(d['10.13039/005']['acronyms']) == 1
        assert 'UoB' in d['10.13039/005']['acronyms']
        assert d['10.13039/005']['country'] == 'CH'

        assert not d['10.13039/001']['parent']
        assert d['10.13039/002']['parent']
        assert {'$ref': 'http://dx.doi.org/10.13039/001'} == \
            d['10.13039/002']['parent']
        assert d['10.13039/003']['parent']
        assert {'$ref': 'http://dx.doi.org/10.13039/001'} == \
            d['10.13039/003']['parent']
        assert d['10.13039/004']['parent']
        assert {'$ref': 'http://dx.doi.org/10.13039/002'} == \
            d['10.13039/004']['parent']
        assert not d['10.13039/005']['parent']


@patch('invenio_openaire.loaders.requests', mock_requests)
def test_remote_fundref_loader(app):
    """Test the remote loadef for the FundRef dataset."""
    with app.app_context():
        cc = {'1': 'US', '2': 'CH'}
        frl = RemoteFundRefLoader(cc_resolver=GeoNamesResolver(cc_data=cc))
        json_dataset = list(frl.iter_funders())
        assert len(json_dataset) == 5


def test_local_openaire_loader(app):
    """Test the SQLite local loader."""
    with app.app_context():
        loader = LocalOAIRELoader(source='tests/testdata/openaire_test.sqlite')
        records = list(loader.iter_grants())
        assert len(records) == 10


@patch('invenio_openaire.loaders.Sickle', MockSickle)
def test_remote_openaire_loader(app):
    """Test the remote OAI-PMH OpenAIRE loader."""
    with app.app_context():
        loader = RemoteOAIRELoader()
        records = list(loader.iter_grants())
        assert len(records) == 5


def test_grant_funder_not_found(app):
    """Test the grant loading with non-existent funder."""
    with app.app_context():
        loader = LocalOAIRELoader(
            source='tests/testdata/openaire_test.sqlite',
            funder_resolver=FundRefDOIResolver(data={'foo': 'bar'}))
        with pytest.raises(FunderNotFoundError):
            list(loader.iter_grants())
