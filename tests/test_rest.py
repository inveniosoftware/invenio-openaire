# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for OpenAIRE dataset loaders and resolvers."""

from __future__ import absolute_import, print_function

import json

from invenio_records_rest import InvenioRecordsREST
from invenio_records_rest.views import create_blueprint

from invenio_openaire.config import OPENAIRE_REST_ENDPOINTS


def _get_json(response, code=None):
    """Decode JSON from response."""
    data = response.get_data(as_text=True)
    if code is not None:
        assert response.status_code == code, data
    return json.loads(data)


def test_records_rest(app, db, es, grants):
    """Test Records REST."""
    app.config['RECORDS_REST_ENDPOINTS'] = OPENAIRE_REST_ENDPOINTS
    app.config['RECORDS_REST_DEFAULT_READ_PERMISSION_FACTORY'] = None
    InvenioRecordsREST(app)
    # invenio-records-rest >= 1.1.0 doesn't automatically register endpoints
    if 'invenio_records_rest.frdoi_item' not in app.url_map._rules_by_endpoint:
        app.register_blueprint(create_blueprint(OPENAIRE_REST_ENDPOINTS))

    with app.test_client() as client:
        # Item
        res = client.get("/funders/10.13039/001")
        assert res.status_code == 200
        # List
        res = client.get("/funders/")
        assert res.status_code == 200
        print(res.get_data(as_text=True))
        # Suggest
        res = client.get("/funders/_suggest?text=Uni")
        data = _get_json(res, 200)
        options = data['text'][0]['options']
        assert len(options) == 2
        assert [option['_source']['doi'] for option in options].sort() == [
                     '0.13039/501100000923', '10.13039/001'].sort()
        res = client.get("/grants/10.13039/501100000923::LP0667725")
        assert res.status_code == 200
        # List
        res = client.get("/grants/")
        assert res.status_code == 200
        # Suggest
        funder = '10.13039/501100000923'
        res = client.get(
            "/grants/_suggest?text=LP&funder={}".format(funder))
        data = _get_json(res, 200)
        options = data['text'][0]['options']
        assert len(options) == 3
        assert [(option['_source']['code'],
                 option['_source']['funder']['doi']) for option in options
                ].sort() == [
                    ('LP0989479', funder), ('LP0667725', funder),
                    ('LP0215942', funder)].sort()
