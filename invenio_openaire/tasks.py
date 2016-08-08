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

"""OpenAIRE service integration for Invenio repositories."""

from __future__ import absolute_import, print_function

from celery import shared_task
from invenio_db import db
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record

from .loaders import LocalFundRefLoader, LocalOAIRELoader, \
    RemoteFundRefLoader, RemoteOAIRELoader
from .minters import funder_minter, grant_minter


@shared_task(ignore_result=True)
def harvest_fundref(source=None):
    """Harvest funders from FundRef and store as authority records."""
    loader = LocalFundRefLoader(source=source) if source \
        else RemoteFundRefLoader()
    for funder_json in loader.iter_funders():
        register_funder.delay(funder_json)


@shared_task(ignore_result=True)
def harvest_openaire_projects(source=None, setspec=None):
    """Harvest grants from OpenAIRE and store as authority records."""
    loader = LocalOAIRELoader(source=source) if source \
        else RemoteOAIRELoader(setspec=setspec)
    for grant_json in loader.iter_grants():
        register_grant.delay(grant_json)


@shared_task(ignore_result=True)
def register_funder(data):
    """Register the funder JSON in records and create a PID."""
    create_or_update_record(data, 'frdoi',  'doi', funder_minter)


@shared_task(ignore_result=True)
def register_grant(data):
    """Register the grant JSON in records and create a PID."""
    create_or_update_record(data, 'grant', 'internal_id', grant_minter)


def create_or_update_record(data, pid_type, id_key, minter):
    """Register a funder or grant."""
    resolver = Resolver(
        pid_type=pid_type, object_type='rec', getter=Record.get_record)

    try:
        pid, record = resolver.resolve(data[id_key])
        if data['remote_modified'] != record['remote_modified']:
            record.update(data)
            record.commit()
            db.session.commit()
    except PIDDoesNotExistError:
        record = Record.create(data)
        minter(record.id, data)
        db.session.commit()
