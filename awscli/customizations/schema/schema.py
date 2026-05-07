# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""aws schema - Introspect AWS API operation schemas as machine-readable JSON.

Usage:
    aws schema                       # list all services
    aws schema <service>             # list operations and waiters
    aws schema <service> <operation> # full operation schema

Add --docs at any level to include documentation fields (excluded by
default to keep output compact).

Example:
    aws schema s3 put-object
    aws schema lambda invoke --docs
"""
import json
import sys
from difflib import get_close_matches

from botocore import xform_name
from botocore.exceptions import DataNotFoundError, UnknownServiceError

from awscli.customizations.commands import BasicCommand

# CLI command names that differ from the botocore service name.
# If a user passes the CLI form, suggest the botocore service name.
_CLI_CMD_TO_SERVICE = {
    's3api': 's3',
    'deploy': 'codedeploy',
    'configservice': 'config',
}


def _strip_docs_recursive(obj):
    """Recursively drop 'documentation' fields (case-sensitive)."""
    if isinstance(obj, dict):
        return {
            k: _strip_docs_recursive(v)
            for k, v in obj.items()
            if k != 'documentation'
        }
    if isinstance(obj, list):
        return [_strip_docs_recursive(x) for x in obj]
    return obj


def register_schema_command(event_handlers):
    event_handlers.register(
        'building-command-table.main', SchemaCommand.add_command
    )


class SchemaCommand(BasicCommand):
    NAME = 'schema'
    DESCRIPTION = (
        'Introspect AWS API operation schemas as machine-readable JSON. '
        'Outputs the full method signature including parameters, types, '
        'required fields, and response structure.'
    )
    SYNOPSIS = 'aws schema [<service> [<operation>]] [--docs]'
    ARG_TABLE = [
        {
            'name': 'service',
            'positional_arg': True,
            'nargs': '?',
            'default': None,
            'help_text': 'The AWS service (e.g. s3, ec2, lambda)',
        },
        {
            'name': 'operation',
            'positional_arg': True,
            'nargs': '?',
            'default': None,
            'help_text': 'The operation to introspect (e.g. put-object)',
        },
        {
            'name': 'docs',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Include documentation fields in the output. '
                'Omitted by default to keep output compact.'
            ),
        },
    ]

    def __init__(self, session, stream=None, error_stream=None):
        super().__init__(session)
        if stream is None:
            stream = sys.stdout
        if error_stream is None:
            error_stream = sys.stderr
        self._stream = stream
        self._error_stream = error_stream

    def _run_main(self, parsed_args, parsed_globals):
        service_name = parsed_args.service
        operation_name = parsed_args.operation
        include_docs = parsed_args.docs

        loader = self._session.get_component('data_loader')

        if service_name is None:
            schema = self._build_top_level(loader, include_docs)
            self._write(schema)
            return 0

        if service_name in _CLI_CMD_TO_SERVICE:
            suggested = _CLI_CMD_TO_SERVICE[service_name]
            return self._error(
                f"'{service_name}' is the CLI command name. "
                f"Did you mean '{suggested}'?",
                "validationError",
            )

        if self._validate_service_name(loader, service_name) is None:
            return 1
        try:
            raw_model = loader.load_service_model(service_name, 'service-2')
        except (DataNotFoundError, UnknownServiceError) as e:
            return self._error(str(e), "validationError")

        if operation_name is None:
            schema = self._build_service_schema(
                raw_model, service_name, loader
            )
        else:
            op_name = self._find_operation_name(
                raw_model, service_name, operation_name
            )
            if op_name is None:
                return 1
            schema = self._build_operation_schema(
                raw_model, service_name, op_name, loader
            )

        if not include_docs:
            schema = _strip_docs_recursive(schema)

        self._write(schema)
        return 0

    def _write(self, schema):
        self._stream.write(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
        )

    def _build_top_level(self, loader, include_docs):
        services = loader.list_available_services('service-2')
        services_list = []
        for s in services:
            entry = {"name": s}
            if include_docs:
                try:
                    data = loader.load_service_model(s, 'service-2')
                    doc = data.get('documentation', '')
                    if doc:
                        entry["documentation"] = doc
                except (DataNotFoundError, UnknownServiceError):
                    pass
            services_list.append(entry)
        return {"services": services_list}

    def _build_service_schema(self, raw_model, service_name, loader):
        """Build service-level overview. Always includes docs; the
        caller strips them if --docs is off."""
        ops_raw = raw_model.get('operations', {})

        paginated_ops = set()
        try:
            paginators = loader.load_service_model(
                service_name, 'paginators-1'
            )
            paginated_ops = set(paginators.get('pagination', {}).keys())
        except (DataNotFoundError, UnknownServiceError):
            pass

        operations = []
        for op_name in sorted(ops_raw.keys()):
            op_raw = ops_raw[op_name]
            entry = {"name": op_name}
            if op_raw.get('documentation'):
                entry["documentation"] = op_raw['documentation']
            if op_raw.get('deprecated'):
                entry["deprecated"] = True
            if op_name in paginated_ops:
                entry["paginated"] = True
            operations.append(entry)

        output = {"service": service_name}
        if raw_model.get('documentation'):
            output["documentation"] = raw_model['documentation']
        output["operations"] = operations

        waiters = {}
        try:
            waiters_data = loader.load_service_model(
                service_name, 'waiters-2'
            )
            waiters = waiters_data.get('waiters', {})
        except (DataNotFoundError, UnknownServiceError):
            pass
        if waiters:
            output["waiters"] = []
            for name in sorted(waiters.keys()):
                entry = {"name": name}
                if waiters[name].get('description'):
                    entry["description"] = waiters[name]['description']
                output["waiters"].append(entry)

        return output

    def _validate_service_name(self, loader, service_name):
        """Return True if valid, or None after emitting a JSON error
        with nearby suggestions."""
        services = loader.list_available_services('service-2')
        if service_name in services:
            return True

        possible = get_close_matches(service_name, services, cutoff=0.6)
        msg = f"Unknown service '{service_name}'."
        if possible:
            msg += f" Did you mean: {', '.join(possible[:3])}?"
        self._error(msg, "serviceNotFound")
        return None

    def _find_operation_name(self, raw_model, service_name, operation_name):
        """Find operation by CLI-style name. Returns API name or None."""
        operations = raw_model.get('operations', {})

        for api_name in operations:
            if xform_name(api_name, '-') == operation_name:
                return api_name

        cli_names = [xform_name(op, '-') for op in operations]
        possible = get_close_matches(operation_name, cli_names, cutoff=0.6)

        msg = (
            f"Operation '{operation_name}' not found in "
            f"service '{service_name}'."
        )
        if possible:
            msg += f" Did you mean: {', '.join(possible[:3])}?"

        self._error(msg, "operationNotFound")
        return None

    def _build_operation_schema(self, raw_model, service_name, op_name,
                                loader):
        """Build operation-level schema. Always includes docs;
        the caller strips them if --docs is off."""
        op_raw = raw_model['operations'][op_name]

        reachable = {}
        self._collect_shapes(
            op_raw.get('input', {}).get('shape'),
            raw_model['shapes'], reachable,
        )
        self._collect_shapes(
            op_raw.get('output', {}).get('shape'),
            raw_model['shapes'], reachable,
        )
        for err in op_raw.get('errors', []):
            self._collect_shapes(
                err.get('shape'), raw_model['shapes'], reachable,
            )

        # 'name' is duplicated in the top-level envelope.
        operation = {k: v for k, v in op_raw.items() if k != 'name'}

        try:
            paginators = loader.load_service_model(
                service_name, 'paginators-1'
            )
            paginator = paginators.get('pagination', {}).get(op_name)
            if paginator:
                operation["pagination"] = {
                    "inputToken": paginator.get("input_token"),
                    "outputToken": paginator.get("output_token"),
                    "resultKey": paginator.get("result_key"),
                    "limitKey": paginator.get("limit_key"),
                }
        except (DataNotFoundError, UnknownServiceError):
            pass

        return {
            "service": service_name,
            "name": op_name,
            "operation": operation,
            "shapes": reachable,
        }

    def _collect_shapes(self, shape_name, all_shapes, collected, seen=None):
        """Recursively collect all shapes reachable from shape_name."""
        if shape_name is None:
            return
        if seen is None:
            seen = set()
        if shape_name in seen:
            return
        seen.add(shape_name)

        shape = all_shapes.get(shape_name)
        if shape is None:
            return
        collected[shape_name] = shape

        for member in shape.get('members', {}).values():
            self._collect_shapes(
                member.get('shape'), all_shapes, collected, seen
            )
        member_ref = shape.get('member', {})
        if isinstance(member_ref, dict):
            self._collect_shapes(
                member_ref.get('shape'), all_shapes, collected, seen
            )
        self._collect_shapes(
            shape.get('key', {}).get('shape'), all_shapes, collected, seen
        )
        self._collect_shapes(
            shape.get('value', {}).get('shape'), all_shapes, collected, seen
        )

    def _error(self, message, reason):
        error = {"error": {"message": message, "reason": reason}}
        self._error_stream.write(json.dumps(error, indent=2) + "\n")
        return 1
