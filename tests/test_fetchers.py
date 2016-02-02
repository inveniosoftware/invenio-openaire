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

"""PID Fetchers tests."""

from __future__ import absolute_import, print_function

import uuid

from invenio_openaire.fetchers import funder_fetcher, grant_fetcher


def test_funder_fetcher():
    """Test funder fetcher."""
    val = '10.13039/001'
    pid = funder_fetcher(uuid.uuid4(), dict(doi=val))
    assert pid.provider is None
    assert pid.pid_type is 'frdoi'
    assert pid.pid_value is val


def test_grant_fetcher():
    """Test grant fetcher."""
    val = '10.13039/001::01'
    pid = grant_fetcher(uuid.uuid4(), dict(internal_id=val))
    assert pid.provider is None
    assert pid.pid_type is 'grant'
    assert pid.pid_value is val
