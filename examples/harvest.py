# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Minimal Flask application example for development.

Run example development server:

.. code-block:: console

   $ cd examples
   $ python app.py
"""

from __future__ import absolute_import, print_function

from flask import Flask
from flask_babelex import Babel
from flask_celeryext import create_celery_app
from invenio_celery import InvenioCelery
from invenio_db import InvenioDB, db
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from invenio_openaire import InvenioOpenAIRE
from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects

# Create Flask application
app = Flask(__name__)
Babel(app)
InvenioDB(app)
InvenioRecords(app)
InvenioCelery(app)
InvenioPIDStore(app)
InvenioOpenAIRE(app)
InvenioJSONSchemas(app)
app.config.update(
    TESTING=True,
    SQLALCHEMY_DATABASE_URI='postgresql+psycopg2://postgres:postgres@localhost'
                            '/invenio_test',
    CELERY_ALWAYS_EAGER=True,
    BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_BACKEND='redis://localhost:6379/1',
    # BROKER_URL='amqp://guest:guest@localhost:5672//',
    # CELERY_ACCEPT_CONTENT=['json', 'msgpack', 'yaml'],
    # CELERY_RESULT_SERIALIZER='msgpack',
    # CELERY_TASK_SERIALIZER='msgpack',
)
# celery_ext = InvenioCelery(app)


celery = create_celery_app(app)
if __name__ == "__main__":
    with app.app_context():
        if database_exists(str(db.engine.url)):
            drop_database(str(db.engine.url))
        create_database(str(db.engine.url))
        db.create_all()
        harvest_fundref()
        harvest_openaire_projects()
