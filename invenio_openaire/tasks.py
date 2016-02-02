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

"""OpenAIRE service integration for Invenio repositories."""

from __future__ import absolute_import, print_function

from celery import shared_task
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.api import Record

from invenio_openaire.loaders import RemoteFundRefLoader, RemoteOAIRELoader


@shared_task(ignore_result=True)
def harvest_fundref(loader=None):
    """Harvest funders from FundRef and store as authority records."""
    loader = loader or RemoteFundRefLoader()
    for funder_json in loader.iter_funders():
        register_funder.delay(funder_json)


@shared_task(ignore_result=True)
def harvest_openaire_projects(loader=None):
    """Harvest grants from OpenAIRE and store as authority records."""
    loader = loader or RemoteOAIRELoader()
    for grant_json in loader.iter_grants():
        register_grant.delay(grant_json)


@shared_task(ignore_result=True)
def register_funder(funder_json):
    """Register the funder JSON in records and create a PID."""
    record = Record.create(funder_json)
    PersistentIdentifier.create(
        'fundr',
        funder_json['doi'],
        object_type='rec',
        object_uuid=record.id,
        status=PIDStatus.REGISTERED
    )
    db.session.commit()


@shared_task(ignore_result=True)
def register_grant(grant_json):
    """Register the grant JSON in records and create a PID."""
    record = Record.create(grant_json)
    PersistentIdentifier.create(
        'grant',
        grant_json['internal_id'],
        object_type='rec',
        object_uuid=record.id,
        status=PIDStatus.REGISTERED
    )
    db.session.commit()
