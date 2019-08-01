# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

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
