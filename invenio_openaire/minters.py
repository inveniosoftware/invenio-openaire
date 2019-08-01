# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

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
