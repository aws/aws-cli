# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import base64
import binascii

from awscli.shorthand import ModelVisitor


def add_binary_formatter(session, parsed_args, **kwargs):
    binary_format = parsed_args.cli_binary_format
    if binary_format is None:
        binary_format = session.get_config_variable('cli_binary_format')
    BinaryFormatHandler(binary_format).register(session)


class Base64DecodeVisitor(ModelVisitor):
    def _visit_scalar(self, parent, shape, name, value):
        if shape.type_name != 'blob' or not isinstance(value, str):
            return
        try:
            parent[name] = base64.b64decode(value)
        except binascii.Error:
            raise RuntimeError('Invalid base64: "%s"' % value)


def base64_decode_input_blobs(params, model, **kwargs):
    Base64DecodeVisitor().visit(params, model.input_shape)


def identity(x):
    return x


def _register_blob_parser(session, blob_parser):
    factory = session.get_component('response_parser_factory')
    factory.set_parser_defaults(blob_parser=blob_parser)


def register_identity_blob_parser(session):
    _register_blob_parser(session, identity)


class BinaryFormatHandler(object):
    _BINARY_FORMATS = {
        'base64': (base64_decode_input_blobs, register_identity_blob_parser),
        'legacy': (None, register_identity_blob_parser),
    }

    def __init__(self, binary_format):
        self._format = binary_format

    def register(self, session):
        self._register_input_formatter(session)
        self._register_output_formatter(session)

    def _register_input_formatter(self, session):
        input_handler = self._BINARY_FORMATS[self._format][0]
        if input_handler:
            session.register('provide-client-params', input_handler)

    def _register_output_formatter(self, session):
        output_handler = self._BINARY_FORMATS[self._format][1]
        if output_handler:
            output_handler(session)
