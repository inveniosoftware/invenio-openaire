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

"""PID minters for grants and funders."""

from __future__ import absolute_import, print_function

from invenio_pidstore.models import PersistentIdentifier, PIDStatus


def funder_minter(record_uuid, data):
    """Mint PID from funder record."""
    return minter(record_uuid, data, 'frdoi', 'doi')


def grant_minter(record_uuid, data):
    """Mint PID from grant record."""
    return minter(record_uuid, data, 'grant', 'internal_id')


def minter(record_uuid, data, pid_type, key):
    """Mint PIDs for a record."""
    pid = PersistentIdentifier.create(
        pid_type,
        data[key],
        object_type='rec',
        object_uuid=record_uuid,
        status=PIDStatus.REGISTERED
    )
    for scheme, identifier in data['identifiers'].items():
        if identifier:
            PersistentIdentifier.create(
                scheme,
                identifier,
                object_type='rec',
                object_uuid=record_uuid,
                status=PIDStatus.REGISTERED
            )
    return pid
