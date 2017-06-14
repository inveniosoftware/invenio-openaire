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

"""OpenAIRE loader functions.

None of the functions in this module create any objects in invenio-records.
Instead they handle loading, resolving and finally converting the local XML
datasets into final JSON that's to be stored using invenio_records.

The OpenAIRE loader comes in two variants: local loader from the pre-fetched
OpenAIRE dataset using SQLite database and direct remote loader using OAI-PMH
endpint.

Both FundRef dataset loaders rely on the locally stored dataset. The remote
loader also capable of fetching it from a remote location.
"""

from __future__ import absolute_import, print_function

import json
import os
import sqlite3
import xml.etree.ElementTree as ET

import requests
from flask import current_app
from invenio_pidstore.errors import PersistentIdentifierError
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from lxml import etree
from sickle import Sickle
from six.moves.urllib.parse import quote_plus

from . import __path__ as current_package
from .errors import FunderNotFoundError, OAIRELoadingError


class JSONSchemaURLFormatter(object):
    """Formatter for '$schema' arguments in loaded JSONs."""

    def __init__(self, schemas_host=None, schemas_endpoint=None,
                 schema_file=None, schema_url=None):
        """Create a schema reference.

        Create the schema URL with host, endpoint and file, or set a fixed URL.
        Either (but not both at the same time) path to schema file is mandatory
        ('schema_file') or the absolute schema url ('schema_url').
        """
        assert (schema_file is not None) ^ (schema_url is not None), \
            "Either (but not both) 'schema_file' name or 'schema_url' are "
        "mandatory kwargs."

        self._schemas_host = schemas_host or \
            current_app.config['OPENAIRE_SCHEMAS_HOST']

        self._schemas_endpoint = schemas_endpoint or \
            current_app.config['OPENAIRE_SCHEMAS_ENDPOINT']

        self._schema_file = schema_file
        self.schema_url = schema_url or self._make_schema_url()

    def _make_schema_url(self):
        """Create the schema url from the host, endpoint and schema file."""
        return "http://{0}{1}/{2}".format(
            self._schemas_host, self._schemas_endpoint, self._schema_file)


class BaseOAIRELoader(object):
    """Base loader for the OpenAIRE dataset."""

    def __init__(self, source, funder_resolver=None, namespaces=None,
                 schema_formatter=None):
        """Init the loader."""
        self.source = source
        self.funder_resolver = funder_resolver or FundRefDOIResolver()
        self.namespaces = namespaces or \
            current_app.config['OPENAIRE_OAIPMH_NAMESPACES']
        self.schema_formatter = schema_formatter or JSONSchemaURLFormatter(
            schema_file=current_app.config['OPENAIRE_SCHEMAS_DEFAULT_GRANT'])

    def iter_grants(self):
        """Fetch and return the next grant in sequence."""
        return NotImplementedError  # pragma: no cover

    def get_all(self):
        """Fetch and return all grants."""
        return NotImplementedError  # pragma: no cover

    def get_text_node(self, tree, xpath_str):
        """Return a text node from given XML tree given an lxml XPath."""
        try:
            return tree.xpath(xpath_str, namespaces=self.namespaces)[0].text \
                or ''
        except IndexError:  # pragma: nocover
            return ''

    def get_subtree(self, tree, xpath_str):
        """Return a subtree given an lxml XPath."""
        return tree.xpath(xpath_str, namespaces=self.namespaces)

    def fundertree2json(self, tree, oai_id):
        """Convert OpenAIRE's funder XML to JSON."""
        try:
            tree = self.get_subtree(tree, 'fundingtree')[0]
        except IndexError:  # pragma: nocover
            pass

        funder_node = self.get_subtree(tree, 'funder')
        subfunder_node = self.get_subtree(tree, '//funding_level_0')

        funder_id = self.get_text_node(funder_node[0], './id') \
            if funder_node else None
        subfunder_id = self.get_text_node(subfunder_node[0], './id') \
            if subfunder_node else None
        funder_name = self.get_text_node(funder_node[0], './shortname') \
            if funder_node else ""
        subfunder_name = self.get_text_node(subfunder_node[0], './name') \
            if subfunder_node else ""

        # Try to resolve the subfunder first, on failure try to resolve the
        # main funder, on failure raise an error.
        funder_doi_url = None
        if subfunder_id:
            funder_doi_url = self.funder_resolver.resolve_by_id(subfunder_id)
        if not funder_doi_url:
            if funder_id:
                funder_doi_url = self.funder_resolver.resolve_by_id(funder_id)
        if not funder_doi_url:
            funder_doi_url = self.funder_resolver.resolve_by_oai_id(oai_id)
        if not funder_doi_url:
            raise FunderNotFoundError(oai_id, funder_id, subfunder_id)

        funder_doi = FundRefDOIResolver.strip_doi_host(funder_doi_url)
        if not funder_name:
            # Grab name from FundRef record.
            resolver = Resolver(
                pid_type='frdoi', object_type='rec', getter=Record.get_record)
            try:
                dummy_pid, funder_rec = resolver.resolve(funder_doi)
                funder_name = funder_rec['acronyms'][0]
            except PersistentIdentifierError:
                raise OAIRELoadingError(
                    "Please ensure that funders have been loaded prior to"
                    "loading grants. Could not resolve funder {0}".format(
                        funder_doi))

        return dict(
            doi=funder_doi,
            url=funder_doi_url,
            name=funder_name,
            program=subfunder_name,
        )

    def grantxml2json(self, grant_xml):
        """Convert OpenAIRE grant XML into JSON."""
        tree = etree.fromstring(grant_xml)
        ptree = self.get_subtree(
            tree, '/oai:record/oai:metadata/oaf:entity/oaf:project')[0]

        oai_id = self.get_text_node(
            tree, '/oai:record/oai:header/oai:identifier')
        modified = self.get_text_node(
            tree, '/oai:record/oai:header/oai:datestamp')
        url = self.get_text_node(ptree, 'websiteurl')
        code = self.get_text_node(ptree, 'code')
        title = self.get_text_node(ptree, 'title')
        acronym = self.get_text_node(ptree, 'acronym')
        startdate = self.get_text_node(ptree, 'startdate')
        enddate = self.get_text_node(ptree, 'enddate')

        funder = self.fundertree2json(ptree, oai_id)

        internal_id = "{0}::{1}".format(funder['doi'], code)
        eurepo_id = \
            "info:eu-repo/grantAgreement/{funder}/{program}/{code}/".format(
                funder=quote_plus(funder['name']),
                program=quote_plus(funder['program']),
                code=quote_plus(code), )

        ret_json = {
            '$schema': self.schema_formatter.schema_url,
            'internal_id': internal_id,
            'identifiers': {
                'oaf': oai_id,
                'eurepo': eurepo_id,
                'purl': url if url.startswith("http://purl.org/") else None,
            },
            'code': code,
            'title': title,
            'acronym': acronym,
            'startdate': startdate,
            'enddate': enddate,
            'funder': {'$ref': funder['url']},
            'program': funder['program'],
            'url': url,
            'remote_modified': modified,
        }
        return ret_json


class LocalOAIRELoader(BaseOAIRELoader):
    """Local OpenAIRE dataset loader.

    Load the OpenAIRE grant data from a pre-fetched local sqlite database.
    SQLite database can contain raw XML or formatted JSON grant records.
    The Loader can iterate over items in the database and return grants as
    a sequence generator, where each item in a sequece is JSON (as_json=True)
    or XML (as_json=False).
    Supported combination of input (database) and output (generator) formats:

    XML -> XML
    XML -> JSON
    JSON -> JSON
    """

    def __init__(self, source=None, **kwargs):
        """Init the loader for local database.

        :param source: path to sqlite database file.
        """
        super(LocalOAIRELoader, self).__init__(
            source or current_app.config['OPENAIRE_OAI_LOCAL_SOURCE'],
            **kwargs)
        self.db_connection = None

    def iter_grants(self, as_json=True):
        """Fetch records from the SQLite database."""
        self.db_connection = sqlite3.connect(self.source)
        n_grants, = self.db_connection.cursor().execute(
            "SELECT COUNT(1) from grants").fetchone()
        result = self.db_connection.cursor().execute(
            "SELECT data, format FROM grants"
        )
        for _ in range(int(n_grants)):
            data, data_format = result.fetchone()
            if (not as_json) and data_format == 'json':
                raise Exception("Cannot convert JSON source to XML output.")
            elif as_json and data_format == 'xml':
                data = self.grantxml2json(data)
            elif as_json and data_format == 'json':
                data = json.loads(data)
            yield data
        self.db_connection.close()


class RemoteOAIRELoader(BaseOAIRELoader):
    """Remote OpenAIRE dataset loader.

    Fetch the OpenAIRE records from a remote OAI-PMH endpoint.
    """

    def __init__(self, source=None, setspec=None, **kwargs):
        """Init the loader for remote OAI-PMH access."""
        super(RemoteOAIRELoader, self).__init__(
            source or current_app.config['OPENAIRE_OAIPMH_ENDPOINT'],
            **kwargs)
        self.client = Sickle(self.source)
        self.setspec = setspec or \
            current_app.config['OPENAIRE_OAIPMH_DEFAULT_SET'],

    def iter_grants(self, as_json=True):
        """Fetch grants from a remote OAI-PMH endpoint.

        Return the Sickle-provided generator object.
        """
        records = self.client.ListRecords(metadataPrefix='oaf',
                                          set=self.setspec)
        for rec in records:
            try:
                grant_out = rec.raw  # rec.raw is XML
                if as_json:
                    grant_out = self.grantxml2json(grant_out)
                yield grant_out
            except FunderNotFoundError as e:
                current_app.logger.warning("Funder '{0}' not found.".format(
                    e.funder_id))


class OAIREDumper(object):
    """Dumper for Open AIRE dataset.

    Fetch the OpenAIRE records from a remote OAI-PMH endpoint and dump locally.
    """

    def __init__(self, destination, setspec='projects'):
        """
        Init the dumper.

        :param commit_every_n_records: Commit to dabase every N records.
        :type commit_every_n_records: int
        """
        self.loader = RemoteOAIRELoader(setspec=setspec)
        self.destination = destination

    @staticmethod
    def _db_exists(connection):
        row = connection.execute("SELECT name FROM sqlite_master WHERE "
                                 "type='table' and name='grants'").fetchone()
        if row is None:
            return False
        elif 'grants' in row:
            return True
        else:
            raise Exception("Connected database exists, but it's not a valid"
                            "OpenAIRE schema.")

    def dump(self, as_json=True, commit_batch_size=100):
        """
        Dump the grant information to a local storage.

        :param as_json: Convert XML to JSON before saving (default: True).
        """
        connection = sqlite3.connect(self.destination)
        format_ = 'json' if as_json else 'xml'
        if not self._db_exists(connection):
            connection.execute(
                "CREATE TABLE grants (data text, format text)")

        # This will call the RemoteOAIRELoader.iter_grants and fetch
        # records from remote location.
        grants_iterator = self.loader.iter_grants(as_json=as_json)
        for idx, grant_data in enumerate(grants_iterator, 1):
            if as_json:
                grant_data = json.dumps(grant_data, indent=2)
            connection.execute(
                "INSERT INTO grants VALUES (?, ?)", (grant_data, format_))

            # Commit to database every N records
            if idx % commit_batch_size == 0:
                connection.commit()
        connection.commit()
        connection.close()


class GeoNamesResolver(object):
    """Resolver for the country codes from the GeoNames URL or ID."""

    def __init__(self, cc_fname=None, cc_data=None):
        """Init the GeoNames country code resolver.

        Provide the cc_data dictionary or create it from file:

        # cc_file:
        8502121,US
        8740971,US
        (...)

        cc_data = {'8502121':'US', '8740971':'CH', ... }
        """
        if cc_data:
            self.cc_data = cc_data
            self.cc_fname = None
        else:
            self.cc_fname = cc_fname or os.path.join(
                current_package[0],
                current_app.config['OPENAIRE_CC_SOURCE'])
            with open(self.cc_fname, 'r') as F:
                self.cc_data = {k: v[:-1] for k, v in (fi.split(',') for fi in
                                                       F.readlines())}

    def cc_from_id(self, geonames_id):
        """Resolve an ISO-3166 2-letter country code from GeoNames ID."""
        return self.cc_data[geonames_id]

    def cc_from_url(self, geonames_url):
        """Resolve an ISO-3166 2-letter country code from GeoNames URL."""
        geonames_id = geonames_url.split('/')[-2]
        return self.cc_from_id(geonames_id)


class BaseFundRefLoader(object):
    """Loader for the FundRef dataset file.

    Load the FundRef dataset from the file and convert all funders into python
    dictionaries.
    """

    def __init__(self, namespaces=None, cc_resolver=None,
                 schema_formatter=None):
        """Init the loader."""
        self.namespaces = namespaces or \
            current_app.config['OPENAIRE_FUNDREF_NAMESPACES']
        self.cc_resolver = cc_resolver or GeoNamesResolver()
        self.schema_formatter = schema_formatter or JSONSchemaURLFormatter(
            schema_file=current_app.config['OPENAIRE_SCHEMAS_DEFAULT_FUNDER'])

    def get_attrib(self, et_node, prefixed_attrib):
        """Get a prefixed attribute like 'rdf:resource' from ET node."""
        prefix, attrib = prefixed_attrib.split(':')
        return et_node.get('{{{0}}}{1}'.format(self.namespaces[prefix],
                                               attrib))

    def fundrefxml2json(self, node):
        """Convert a FundRef 'skos:Concept' node into JSON."""
        doi = FundRefDOIResolver.strip_doi_host(self.get_attrib(node,
                                                'rdf:about'))
        oaf_id = FundRefDOIResolver().resolve_by_doi(
            "http://dx.doi.org/" + doi)
        name = node.find('./skosxl:prefLabel/skosxl:Label/skosxl:literalForm',
                         namespaces=self.namespaces).text
        acronyms = [acronym.text for acronym in node.findall(
            './skosxl:altLabel/skosxl:Label/skosxl:literalForm',
            namespaces=self.namespaces)]

        # Extract acronyms
        acronyms = []
        for n in node.findall('./skosxl:altLabel/skosxl:Label',
                              namespaces=self.namespaces):
            usagenode = n.find('./fref:usageFlag', namespaces=self.namespaces)
            if usagenode is not None:
                if self.get_attrib(usagenode, 'rdf:resource') == \
                        "http://data.fundref.org/vocabulary/abbrevName":
                    label = n.find('./skosxl:literalForm',
                                   namespaces=self.namespaces)
                    if label is not None:
                        acronyms.append(label.text)

        parent_node = node.find('./skos:broader', namespaces=self.namespaces)
        if parent_node is None:
            parent = {}
        else:
            parent = {
                "$ref": self.get_attrib(parent_node, 'rdf:resource'),
            }
        country_elem = node.find('./svf:country', namespaces=self.namespaces)
        country_url = self.get_attrib(country_elem, 'rdf:resource')
        country_code = self.cc_resolver.cc_from_url(country_url)
        type_ = node.find('./svf:fundingBodyType',
                          namespaces=self.namespaces).text
        subtype = node.find('./svf:fundingBodySubType',
                            namespaces=self.namespaces).text
        country_elem = node.find('./svf:country', namespaces=self.namespaces)

        modified_elem = node.find('./dct:modified', namespaces=self.namespaces)
        created_elem = node.find('./dct:created', namespaces=self.namespaces)

        json_dict = {
            '$schema': self.schema_formatter.schema_url,
            'doi': doi,
            'identifiers': {
                'oaf': oaf_id,
            },
            'name': name,
            'acronyms': acronyms,
            'parent': parent,
            'country': country_code,
            'type': type_,
            'subtype': subtype.lower(),
            'remote_created': (created_elem.text if created_elem is not None
                               else None),
            'remote_modified': (modified_elem.text if modified_elem is not None
                                else None),
        }
        return json_dict

    def iter_funders(self):
        """Get a converted list of Funders as JSON dict."""
        root = self.doc_root
        funders = root.findall('./skos:Concept', namespaces=self.namespaces)
        for funder in funders:
            funder_json = self.fundrefxml2json(funder)
            yield funder_json


class LocalFundRefLoader(BaseFundRefLoader):
    """Load the FundRef dataset from a local file."""

    def __init__(self, namespaces=None, cc_resolver=None, source=None):
        """Init the local loader."""
        super(LocalFundRefLoader, self).__init__(
            namespaces=namespaces, cc_resolver=cc_resolver)
        self.source = source or \
            os.path.join(current_package[0],
                         current_app.config['OPENAIRE_FUNDREF_LOCAL_SOURCE'])
        self.doc_root = ET.parse(self.source).getroot()


class RemoteFundRefLoader(BaseFundRefLoader):
    """Load the FundRef dataset from a remote location."""

    def __init__(self, namespaces=None, cc_resolver=None, source=None):
        """Init the remote loader."""
        super(RemoteFundRefLoader, self).__init__(
            namespaces=namespaces, cc_resolver=cc_resolver)
        self.source = source or \
            current_app.config['OPENAIRE_FUNDREF_ENDPOINT']
        obj = requests.get(self.source, stream=True)
        funders_xml = obj.text
        self.doc_root = ET.fromstring(funders_xml)


class FundRefDOIResolver(object):
    """Resolve the FundRef funders by constant definitions."""

    def __init__(self, data=None):
        """Init the resolver."""
        fixed_funders = {
            'nhmrc_______::NHMRC': 'http://dx.doi.org/10.13039/501100000925',
            'ec__________::EC': 'http://dx.doi.org/10.13039/501100000780',
            'arc_________::ARC': 'http://dx.doi.org/10.13039/501100000923',
            'fct_________::FCT': 'http://dx.doi.org/10.13039/501100001871',
            'wt__________::WT': 'http://dx.doi.org/10.13039/100004440',
            'nsf_________::NSF': 'http://dx.doi.org/10.13039/100000001',
            'mestd_______::MESTD': 'http://dx.doi.org/10.13039/501100004564',
            'nwo_________::NWO': 'http://dx.doi.org/10.13039/501100003246',
            'irb_hr______::MZOS': 'http://dx.doi.org/10.13039/501100006588',
        }
        self.data = data or fixed_funders
        self.inverse_data = {v: k for k, v in self.data.items()}

    def resolve_by_id(self, funder_id):
        """Resolve the funder from the OpenAIRE funder id.

        If funder_id can be resolved, return a URI otherwise return None.
        """
        return self.data.get(funder_id)

    def resolve_by_oai_id(self, oai_id):
        """Resolve the funder from the OpenAIRE OAI record id.

        Hack for when funder is not provided in OpenAIRE.
        """
        if oai_id.startswith('oai:dnet:'):
            oai_id = oai_id[len('oai:dnet:'):]
        prefix = oai_id.split("::")[0]
        suffix = prefix.replace("_", "").upper()
        oaf = "{0}::{1}".format(prefix, suffix)
        return self.data.get(oaf)

    def resolve_by_doi(self, doi):
        """Resolve a DOI to an OpenAIRE id."""
        return self.inverse_data.get(doi)

    @staticmethod
    def strip_doi_host(doi_url):
        """Strip DOI URL from the domain prefix."""
        return doi_url.replace('http://dx.doi.org/', '')
