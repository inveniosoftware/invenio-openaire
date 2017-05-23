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
import uuid

import pytest
from conftest import MockSickle
from invenio_pidstore.models import PersistentIdentifier
from invenio_records.api import Record
from mock import patch

from invenio_openaire.errors import FunderNotFoundError, OAIRELoadingError
from invenio_openaire.loaders import FundRefDOIResolver, GeoNamesResolver, \
    LocalFundRefLoader, LocalOAIRELoader, OAIREDumper, RemoteFundRefLoader, \
    RemoteOAIRELoader


class mock_requests(object):
    """Mock the requests library."""

    class MockResponse(object):
        """Mock of the Response object."""

        def __init__(self, text):
            """Init the response mock with fixed text."""
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
    resolver = GeoNamesResolver()
    assert resolver.cc_from_id('8502121') == 'US'
    assert resolver.cc_from_id('8740971') == 'CH'
    assert resolver.cc_from_url(
        "http://sws.geonames.org/6252001/") == 'US'

    resolver = GeoNamesResolver(cc_data={'1': 'US'})
    assert resolver.cc_from_id('1') == 'US'


def test_local_fundref_loader(app):
    """Test the loadef for the FundRef dataset."""
    # Test loading the real FundRef dataset.
    frl = LocalFundRefLoader()
    json_dataset = list(frl.iter_funders())
    assert len(json_dataset) == 11565  # Current FundRef dataset size


def test_local_fundref_convert(app):
    """Test the XML to JSON conversion of local FundRef dataset."""
    # Test the keys and dict structure for test dataset
    app.config.update(OPENAIRE_FUNDREF_LOCAL_SOURCE=os.path.join(
        os.path.dirname(__file__), 'testdata/fundref_test.rdf')
    )
    frl = LocalFundRefLoader()
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
    assert len(d['10.13039/003']['acronyms']) == 0
    assert d['10.13039/003']['country'] == 'US'

    assert d['10.13039/004']['name'] == 'Faculty of Spam'
    assert len(d['10.13039/004']['acronyms']) == 1
    assert 'FoS' in d['10.13039/004']['acronyms']
    assert d['10.13039/004']['country'] == 'US'

    assert d['10.13039/501100000923']['name'] == 'University of Bacon'
    assert len(d['10.13039/501100000923']['acronyms']) == 1
    assert 'UoB' in d['10.13039/501100000923']['acronyms']
    assert d['10.13039/501100000923']['country'] == 'CH'

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
    assert not d['10.13039/501100000923']['parent']


@patch('invenio_openaire.loaders.requests', mock_requests)
def test_remote_fundref_loader(app):
    """Test the remote loadef for the FundRef dataset."""
    frl = RemoteFundRefLoader()
    json_dataset = list(frl.iter_funders())
    assert len(json_dataset) == 5


def test_local_openaire_loader(app):
    """Test the SQLite local loader."""
    loader = LocalOAIRELoader(source='tests/testdata/openaire_test.sqlite')
    records = list(loader.iter_grants())
    assert len(records) == 10


@patch('invenio_openaire.loaders.Sickle', MockSickle)
def test_remote_openaire_loader(app, db):
    """Test the remote OAI-PMH OpenAIRE loader."""
    loader = RemoteOAIRELoader()
    pytest.raises(OAIRELoadingError, list, loader.iter_grants())

    recuuid = uuid.uuid4()
    PersistentIdentifier.create(
        'frdoi', '10.13039/501100000925',
        object_type='rec', object_uuid=recuuid, status='R')
    Record.create({'acronyms': ['EC']}, id_=recuuid)

    records = list(loader.iter_grants())
    assert len(records) == 5


@patch('invenio_openaire.loaders.Sickle', MockSickle)
def test_remote_openaire_loader_error(app):
    """Test the remote OAI-PMH OpenAIRE loader."""
    loader = RemoteOAIRELoader()
    with patch('invenio_openaire.loaders.etree.fromstring') as fs:
        fs.side_effect = FunderNotFoundError(1, 2, 3)
        records = list(loader.iter_grants())
        assert len(records) == 0


def test_grant_funder_not_found(app):
    """Test the grant loading with non-existent funder."""
    loader = LocalOAIRELoader(
        source='tests/testdata/openaire_test.sqlite',
        funder_resolver=FundRefDOIResolver(data={'foo': 'bar'}))
    with pytest.raises(FunderNotFoundError):
        list(loader.iter_grants())


@patch('invenio_openaire.loaders.Sickle', MockSickle)
def test_oaire_dumper(db, sqlite_tmpdb):
    """Test the grants dumper to local destination."""
    recuuid = uuid.uuid4()
    PersistentIdentifier.create(
        'frdoi', '10.13039/501100000925',
        object_type='rec', object_uuid=recuuid, status='R')
    Record.create({'acronyms': ['EC']}, id_=recuuid)
    dumper = OAIREDumper(destination=sqlite_tmpdb)

    # We expect to harvest 5 record from the MockSickle.
    # with 'commit_batch_size=2', we will make 3 commits to sqlite db
    dumper.dump(commit_batch_size=2)
    loader = LocalOAIRELoader(source=sqlite_tmpdb)
    records = list(loader.iter_grants())
    assert len(records) == 5
