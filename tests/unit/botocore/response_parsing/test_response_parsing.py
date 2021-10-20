# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import os
import glob
import json
import pprint
import logging
import difflib

import pytest

from tests import create_session

import botocore.session
from botocore import xform_name
from botocore import parsers

log = logging.getLogger(__name__)


SPECIAL_CASES = [
    'iam-get-user-policy.xml', # Needs the JSON decode from handlers.py
    'iam-list-roles.xml',  # Needs the JSON decode from handlers.py for the policy
    's3-get-bucket-location.xml', # Confirmed, this will need a special handler
    #'s3-list-multipart-uploads.xml',  # Bug in model, missing delimeter
    'cloudformation-get-template.xml', # Need to JSON decode the template body.
]


def _test_parsed_response(xmlfile, response_body, operation_model, expected):
    response = {
        'body': response_body,
        'status_code': 200,
        'headers': {}
    }
    for case in SPECIAL_CASES:
        if case in xmlfile:
            print("SKIP: %s" % xmlfile)
            return
    if 'errors' in xmlfile:
        response['status_code'] = 400
    # Handle the special cased __headers__ key if it exists.
    if b'__headers__' in response_body:
        loaded = json.loads(response_body.decode('utf-8'))
        response['headers'] = loaded.pop('__headers__')
        response['body'] = json.dumps(loaded).encode('utf-8')

    protocol = operation_model.service_model.protocol
    parser_cls = parsers.PROTOCOL_PARSERS[protocol]
    parser = parser_cls(timestamp_parser=lambda x: x)
    parsed = parser.parse(response, operation_model.output_shape)
    parsed = _convert_bytes_to_str(parsed)
    expected['ResponseMetadata']['HTTPStatusCode'] = response['status_code']
    expected['ResponseMetadata']['HTTPHeaders'] = response['headers']

    d2 = parsed
    d1 = expected

    if d1 != d2:
        log.debug('-' * 40)
        log.debug("XML FILE:\n" + xmlfile)
        log.debug('-' * 40)
        log.debug("ACTUAL:\n" + pprint.pformat(parsed))
        log.debug('-' * 40)
        log.debug("EXPECTED:\n" + pprint.pformat(expected))
    if not d1 == d2:
        # Borrowed from assertDictEqual, though this doesn't
        # handle the case when unicode literals are used in one
        # dict but not in the other (and we want to consider them
        # as being equal).
        print(d1)
        print()
        print(d2)
        pretty_d1 = pprint.pformat(d1, width=1).splitlines()
        pretty_d2 = pprint.pformat(d2, width=1).splitlines()
        diff = ('\n' + '\n'.join(difflib.ndiff(pretty_d1, pretty_d2)))
        raise AssertionError("Dicts are not equal:\n%s" % diff)


def _convert_bytes_to_str(parsed):
    if isinstance(parsed, dict):
        new_dict = {}
        for key, value in parsed.items():
            new_dict[key] = _convert_bytes_to_str(value)
        return new_dict
    elif isinstance(parsed, bytes):
        return parsed.decode('utf-8')
    elif isinstance(parsed, list):
        new_list = []
        for item in parsed:
            new_list.append(_convert_bytes_to_str(item))
        return new_list
    else:
        return parsed


def _xml_test_cases():
    for dp in ['responses', 'errors']:
        data_path = os.path.join(os.path.dirname(__file__), 'xml')
        data_path = os.path.join(data_path, dp)
        session = create_session()
        xml_files = glob.glob('%s/*.xml' % data_path)
        service_names = set()
        for fn in xml_files:
            service_names.add(os.path.split(fn)[1].split('-')[0])
        for service_name in service_names:
            service_model = session.get_service_model(service_name)
            service_xml_files = glob.glob('%s/%s-*.xml' % (data_path,
                                                           service_name))
            for xmlfile in service_xml_files:
                expected = _get_expected_parsed_result(xmlfile)
                operation_model = _get_operation_model(service_model, xmlfile)
                raw_response_body = _get_raw_response_body(xmlfile)
                yield xmlfile, raw_response_body, operation_model, expected


@pytest.mark.parametrize(
    "xmlfile, raw_response_body, operation_model, expected",
    _xml_test_cases()
)
def test_xml_parsing(xmlfile, raw_response_body, operation_model, expected):
    _test_parsed_response(
        xmlfile, raw_response_body, operation_model, expected
    )


def _get_raw_response_body(xmlfile):
    with open(xmlfile, 'rb') as f:
        return f.read()


def _get_operation_model(service_model, filename):
    dirname, filename = os.path.split(filename)
    basename = os.path.splitext(filename)[0]
    sn, opname = basename.split('-', 1)
    # In order to have multiple tests for the same
    # operation a '#' char is used to separate
    # operation names from some other suffix so that
    # the tests have a different filename, e.g
    # my-operation#1.xml, my-operation#2.xml.
    opname = opname.split('#')[0]
    operation_names = service_model.operation_names
    for operation_name in operation_names:
        if xform_name(operation_name) == opname.replace('-', '_'):
            return service_model.operation_model(operation_name)
    return operation


def _get_expected_parsed_result(filename):
    dirname, filename = os.path.split(filename)
    basename = os.path.splitext(filename)[0]
    jsonfile = os.path.join(dirname, basename + '.json')
    with open(jsonfile) as f:
        return json.load(f)


def _json_test_cases():
    # The outputs/ directory has sample output responses
    # For each file in outputs/ there's a corresponding file
    # in expected/ that has the expected parsed response.
    base_dir = os.path.join(os.path.dirname(__file__), 'json')
    json_responses_dir = os.path.join(base_dir, 'errors')
    expected_parsed_dir = os.path.join(base_dir, 'expected')
    session = botocore.session.get_session()
    for json_response_file in os.listdir(json_responses_dir):
        # Files look like: 'datapipeline-create-pipeline.json'
        service_name, operation_name = os.path.splitext(
            json_response_file)[0].split('-', 1)
        expected_parsed_response = os.path.join(expected_parsed_dir,
                                                json_response_file)
        raw_response_file = os.path.join(json_responses_dir,
                                         json_response_file)
        with open(expected_parsed_response) as f:
            expected = json.load(f)
        service_model = session.get_service_model(service_name)
        operation_names = service_model.operation_names
        operation_model = None
        for op_name in operation_names:
            if xform_name(op_name) == operation_name.replace('-', '_'):
                operation_model = service_model.operation_model(op_name)
        with open(raw_response_file, 'rb') as f:
            raw_response_body = f.read()
        yield raw_response_file, raw_response_body, operation_model, expected


@pytest.mark.parametrize(
    "raw_response_file, raw_response_body, operation_model, expected",
    _json_test_cases()
)
def test_json_errors_parsing(
    raw_response_file, raw_response_body, operation_model, expected
):
    _test_parsed_response(
        raw_response_file, raw_response_body, operation_model, expected
    )
