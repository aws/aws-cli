# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import inspect

from botocore.compat import OrderedDict
from botocore.docs.example import ResponseExampleDocumenter
from botocore.docs.method import (
    document_custom_method,
    document_model_driven_method,
    get_instance_public_methods,
)
from botocore.docs.params import ResponseParamsDocumenter
from botocore.docs.sharedexample import document_shared_examples
from botocore.docs.utils import DocumentedShape, get_official_service_name


class ClientDocumenter(object):
    def __init__(self, client, shared_examples=None):
        self._client = client
        self._shared_examples = shared_examples
        if self._shared_examples is None:
            self._shared_examples = {}
        self._service_name = self._client.meta.service_model.service_name

    def document_client(self, section):
        """Documents a client and its methods

        :param section: The section to write to.
        """
        self._add_title(section)
        self._add_class_signature(section)
        client_methods = get_instance_public_methods(self._client)
        self._add_client_intro(section, client_methods)
        self._add_client_methods(section, client_methods)

    def _add_title(self, section):
        section.style.h2('Client')

    def _add_client_intro(self, section, client_methods):
        section = section.add_new_section('intro')
        # Write out the top level description for the client.
        official_service_name = get_official_service_name(
            self._client.meta.service_model)
        section.write(
            'A low-level client representing %s' % official_service_name)
        section.style.new_line()
        section.include_doc_string(self._client.meta.service_model.documentation)

        # Write out the client example instantiation.
        self._add_client_creation_example(section)

        # List out all of the possible client methods.
        section.style.new_line()
        section.write('These are the available methods:')
        section.style.new_line()
        class_name = self._client.__class__.__name__
        for method_name in sorted(client_methods):
            section.style.li(':py:meth:`~%s.Client.%s`' % (
                class_name, method_name))

    def _add_class_signature(self, section):
        section.style.start_sphinx_py_class(
            class_name='%s.Client' % self._client.__class__.__name__)

    def _add_client_creation_example(self, section):
        section.style.start_codeblock()
        section.style.new_line()
        section.write(
            'client = session.create_client(\'{service}\')'.format(
                service=self._service_name)
        )
        section.style.end_codeblock()

    def _add_client_methods(self, section, client_methods):
        section = section.add_new_section('methods')
        for method_name in sorted(client_methods):
            self._add_client_method(
                section, method_name, client_methods[method_name])

    def _add_client_method(self, section, method_name, method):
        section = section.add_new_section(method_name)
        if self._is_custom_method(method_name):
            self._add_custom_method(section, method_name, method)
        else:
            self._add_model_driven_method(section, method_name)

    def _is_custom_method(self, method_name):
        return method_name not in self._client.meta.method_to_api_mapping

    def _add_custom_method(self, section, method_name, method):
        document_custom_method(section, method_name, method)

    def _add_method_exceptions_list(self, section, operation_model):
        error_section = section.add_new_section('exceptions')
        error_section.style.new_line()
        error_section.style.bold('Exceptions')
        error_section.style.new_line()
        client_name = self._client.__class__.__name__
        for error in operation_model.error_shapes:
            class_name = '%s.Client.exceptions.%s' % (client_name, error.name)
            error_section.style.li(':py:class:`%s`' % class_name)

    def _add_model_driven_method(self, section, method_name):
        service_model = self._client.meta.service_model
        operation_name = self._client.meta.method_to_api_mapping[method_name]
        operation_model = service_model.operation_model(operation_name)

        example_prefix = 'response = client.%s' % method_name
        document_model_driven_method(
            section, method_name, operation_model,
            event_emitter=self._client.meta.events,
            method_description=operation_model.documentation,
            example_prefix=example_prefix,
        )

        # Add any modeled exceptions
        if operation_model.error_shapes:
            self._add_method_exceptions_list(section, operation_model)

        # Add the shared examples
        shared_examples = self._shared_examples.get(operation_name)
        if shared_examples:
            document_shared_examples(
                section, operation_model, example_prefix, shared_examples)


class ClientExceptionsDocumenter(object):
    _USER_GUIDE_LINK = (
        'https://boto3.amazonaws.com/'
        'v1/documentation/api/latest/guide/error-handling.html'
    )
    _GENERIC_ERROR_SHAPE = DocumentedShape(
        name='Error',
        type_name='structure',
        documentation=(
            'Normalized access to common exception attributes.'
        ),
        members=OrderedDict([
            ('Code', DocumentedShape(
                name='Code',
                type_name='string',
                documentation=(
                    'An identifier specifying the exception type.'
                ),
            )),
            ('Message', DocumentedShape(
                name='Message',
                type_name='string',
                documentation=(
                    'A descriptive message explaining why the exception '
                    'occured.'
                ),
            )),
        ]),
    )

    def __init__(self, client):
        self._client = client
        self._service_id = self._client.meta.service_model.service_id

    def document_exceptions(self, section):
        self._add_title(section)
        self._add_overview(section)
        self._add_exceptions_list(section)
        self._add_exception_classes(section)

    def _add_title(self, section):
        section.style.h2('Client Exceptions')

    def _add_overview(self, section):
        section.style.new_line()
        section.write(
            'Client exceptions are available on a client instance '
            'via the ``exceptions`` property. For more detailed instructions '
            'and examples on the exact usage of client exceptions, see the '
            'error handling '
        )
        section.style.external_link(
            title='user guide',
            link=self._USER_GUIDE_LINK,
        )
        section.write('.')
        section.style.new_line()

    def _exception_class_name(self, shape):
        cls_name = self._client.__class__.__name__
        return '%s.Client.exceptions.%s' % (cls_name, shape.name)

    def _add_exceptions_list(self, section):
        error_shapes = self._client.meta.service_model.error_shapes
        if not error_shapes:
            section.style.new_line()
            section.write('This client has no modeled exception classes.')
            section.style.new_line()
            return
        section.style.new_line()
        section.write('The available client exceptions are:')
        section.style.new_line()
        for shape in error_shapes:
            class_name = self._exception_class_name(shape)
            section.style.li(':py:class:`%s`' % class_name)

    def _add_exception_classes(self, section):
        for shape in self._client.meta.service_model.error_shapes:
            self._add_exception_class(section, shape)

    def _add_exception_class(self, section, shape):
        class_section = section.add_new_section(shape.name)
        class_name = self._exception_class_name(shape)
        class_section.style.start_sphinx_py_class(class_name=class_name)
        self._add_top_level_documentation(class_section, shape)
        self._add_exception_catch_example(class_section, shape)
        self._add_response_attr(class_section, shape)
        class_section.style.end_sphinx_py_class()

    def _add_top_level_documentation(self, section, shape):
        if shape.documentation:
            section.style.new_line()
            section.include_doc_string(shape.documentation)
            section.style.new_line()

    def _add_exception_catch_example(self, section, shape):
        section.style.new_line()
        section.style.bold('Example')
        section.style.start_codeblock()
        section.write('try:')
        section.style.indent()
        section.style.new_line()
        section.write('...')
        section.style.dedent()
        section.style.new_line()
        section.write('except client.exceptions.%s as e:' % shape.name)
        section.style.indent()
        section.style.new_line()
        section.write('print(e.response)')
        section.style.dedent()
        section.style.end_codeblock()

    def _add_response_attr(self, section, shape):
        response_section = section.add_new_section('response')
        response_section.style.start_sphinx_py_attr('response')
        self._add_response_attr_description(response_section)
        self._add_response_example(response_section, shape)
        self._add_response_params(response_section, shape)
        response_section.style.end_sphinx_py_attr()

    def _add_response_attr_description(self, section):
        section.style.new_line()
        section.include_doc_string(
            'The parsed error response. All exceptions have a top level '
            '``Error`` key that provides normalized access to common '
            'exception atrributes. All other keys are specific to this '
            'service or exception class.'
        )
        section.style.new_line()

    def _add_response_example(self, section, shape):
        example_section = section.add_new_section('syntax')
        example_section.style.new_line()
        example_section.style.bold('Syntax')
        example_section.style.new_paragraph()
        documenter = ResponseExampleDocumenter(
            service_id=self._service_id,
            operation_name=None,
            event_emitter=self._client.meta.events,
        )
        documenter.document_example(
            example_section, shape, include=[self._GENERIC_ERROR_SHAPE],
        )

    def _add_response_params(self, section, shape):
        params_section = section.add_new_section('Structure')
        params_section.style.new_line()
        params_section.style.bold('Structure')
        params_section.style.new_paragraph()
        documenter = ResponseParamsDocumenter(
            service_id=self._service_id,
            operation_name=None,
            event_emitter=self._client.meta.events,
        )
        documenter.document_params(
            params_section, shape, include=[self._GENERIC_ERROR_SHAPE],
        )
