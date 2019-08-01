# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""PID fetchers for grants and funders."""

from __future__ import absolute_import, print_function

from invenio_pidstore.fetchers import FetchedPID


def funder_fetcher(record_uuid, data):
    """Fetch PID from funder record."""
    return FetchedPID(
        provider=None,
        pid_type='frdoi',
        pid_value=str(data['doi']),
    )


def grant_fetcher(record_uuid, data):
    """Fetch PID from grant record."""
    return FetchedPID(
        provider=None,
        pid_type='grant',
        pid_value=str(data['internal_id']),
    )
