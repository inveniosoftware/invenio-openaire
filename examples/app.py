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
from invenio_db import InvenioDB, db
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_openaire import InvenioOpenAIRE

# Create Flask application
app = Flask(__name__)
Babel(app)
InvenioDB(app)
InvenioRecords(app)
InvenioPIDStore(app)
InvenioOpenAIRE(app)
app.config.update(TESTING=True)

with app.app_context():
    if not database_exists(str(db.engine.url)):
        create_database(str(db.engine.url))
        db.create_all()

if __name__ == "__main__":
    app.run()
