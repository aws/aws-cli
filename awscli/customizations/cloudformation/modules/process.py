# Copyright 2012-2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""
Basic module processing functions.
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=fixme

import copy
import logging
import os

from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.foreach import (
    FOREACH_NAME_IS_I,
    ORIGINAL_FOREACH_NAME,
    process_foreach,
    resolve_foreach_lists,
)
from awscli.customizations.cloudformation.modules.validation import (
    PARAMETER_SCHEMA,
    ParameterValidator,
    ParameterValidationError,
)
from awscli.customizations.cloudformation.modules.functions import (
    fn_merge,
    fn_select,
    fn_insertfile,
    fn_join,
)
from awscli.customizations.cloudformation.modules.flatten import fn_flatten
from awscli.customizations.cloudformation.modules.outputs import (
    process_module_outputs,
)
from awscli.customizations.cloudformation.modules.read import (
    is_url,
    is_s3_url,
    read_source,
    get_packaged_module_path,
)
from awscli.customizations.cloudformation.modules.conditions import (
    process_conditions,
)
from awscli.customizations.cloudformation.modules.mappings import (
    process_mappings,
)
from awscli.customizations.cloudformation.modules.constants import (
    process_constants,
    replace_constants,
)
from awscli.customizations.cloudformation.modules.merge import (
    merge_props,
)
from awscli.customizations.cloudformation.modules.resolve import resolve
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation.yamlhelper import (
    yaml_parse,
)
from awscli.customizations.cloudformation.modules.names import (
    RESOURCES,
    METADATA,
    OVERRIDES,
    DEPENDSON,
    PROPERTIES,
    CREATIONPOLICY,
    UPDATEPOLICY,
    DELETIONPOLICY,
    UPDATEREPLACEPOLICY,
    NAME,
    SOURCE,
    PARAMETERS,
    MODULES,
    OUTPUTS,
    CONDITION,
    AWSTOOLSMETRICS,
    CLOUDFORMATION_PACKAGE,
    SOURCE_MAP,
    NO_SOURCE_MAP,
    VALUE,
    INVOKE,
    PACKAGES,
    TRANSFORM,
)
from awscli.customizations.cloudformation.modules.util import isdict

ORIGINAL_CONFIG = "original_config"
BASE_PATH = "base_path"
PARENT_PATH = "parent_path"
INVOKED = "invoked"

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


# pylint:disable=too-many-arguments,too-many-positional-arguments
def make_module(
    template,
    name,
    config,
    base_path,
    parent_path,
    no_source_map,
    parent_module,
    s3_client,
    invoked=False,
):
    "Create an instance of a module based on a template and the module config"
    module_config = {}
    module_config[NAME] = name
    module_config[ORIGINAL_CONFIG] = copy.deepcopy(config)
    module_config[BASE_PATH] = base_path
    module_config[INVOKED] = invoked
    if SOURCE not in config:
        msg = f"{name} missing {SOURCE}"
        raise exceptions.InvalidModulePathError(msg=msg)

    source_path = config[SOURCE]
    if source_path.startswith("$"):
        # This is a reference to a Package
        source_path = get_packaged_module_path(template, source_path)

    if not is_url(source_path) and not is_s3_url(source_path):
        relative_path = source_path
        module_config[SOURCE] = os.path.join(base_path, relative_path)
        module_config[SOURCE] = os.path.normpath(module_config[SOURCE])
    else:
        module_config[SOURCE] = source_path

    module_config[PARENT_PATH] = parent_path
    if not parent_path or parent_path == "":
        msg = "Module {name} at {source_path} has no parent_path"
        raise exceptions.InvalidModuleError(msg=msg)

    if module_config[SOURCE] == parent_path:
        msg = f"Module {name} refers to itself: {parent_path}"
        raise exceptions.InvalidModuleError(msg=msg)
    if PROPERTIES in config:
        module_config[PROPERTIES] = config[PROPERTIES]
    if OVERRIDES in config:
        module_config[OVERRIDES] = config[OVERRIDES]
    if ORIGINAL_FOREACH_NAME in config:
        module_config[ORIGINAL_FOREACH_NAME] = config[ORIGINAL_FOREACH_NAME]
    if FOREACH_NAME_IS_I in config:
        module_config[FOREACH_NAME_IS_I] = config[FOREACH_NAME_IS_I]
    module_config[NO_SOURCE_MAP] = no_source_map

    return Module(template, module_config, parent_module, s3_client)


def add_metrics_metadata(template):
    "Add metadata to the template so we know modules were used"
    if METADATA not in template:
        template[METADATA] = {}
    metadata = template[METADATA]
    if AWSTOOLSMETRICS not in metadata:
        metadata[AWSTOOLSMETRICS] = {}
    metrics = metadata[AWSTOOLSMETRICS]
    if CLOUDFORMATION_PACKAGE not in metrics:
        metrics[CLOUDFORMATION_PACKAGE] = {}
    metrics[CLOUDFORMATION_PACKAGE]["Modules"] = "true"


# pylint: disable=too-many-arguments,too-many-positional-arguments
# pylint: disable=too-many-branches
def process_module_section(
    template,
    base_path,
    parent_path,
    parent_module,
    no_metrics,
    no_source_map,
    s3_client=None,
):
    "Recursively process the Modules section of a template"

    if MODULES not in template:
        if parent_module is None:
            # This is a template with no modules.
            # Process template constants and new intrinsics.
            constants = process_constants(template)
            if constants is not None:
                replace_constants(constants, template)
            parent_module = Module(template, {NAME: "", SOURCE: ""}, None)
            if PARAMETERS in template:
                parent_module.module_parameters = template[PARAMETERS]
            process_foreach(template, parent_module)
            fn_select(template)
            fn_merge(template)
            fn_join(template)
            fn_insertfile(template, base_path)
            fn_flatten(template)

        return template

    if not isdict(template[MODULES]):
        msg = "Modules section is invalid"
        raise exceptions.InvalidModuleError(msg=msg)

    if parent_module is None:

        # This is the actual parent template, not a module

        if not no_metrics:
            add_metrics_metadata(template)

        # Make a fake Module instance to handle find_ref
        parent_module = Module(template, {NAME: "", SOURCE: ""}, None)

        if PARAMETERS in template:
            parent_module.module_parameters = template[PARAMETERS]

    # First, pre-process local modules that are looping over a list
    foreach_modules = process_foreach(template, parent_module)
    parent_module.foreach_modules = foreach_modules

    # Process each Module node separately after processing Maps
    modules = template[MODULES]
    for k, v in modules.items():
        module = make_module(
            template,
            k,
            v,
            base_path,
            parent_path,
            no_source_map,
            parent_module,
            s3_client,
        )
        template = module.process()

    # Look for getatts to a foreach list like !GetAtt Content[*].Arn
    # This should be converted to an array like
    # - !GetAtt ContentBucket0.Arn
    # - !GetAtt ContentBucket1.Arn
    # - !GetAtt ContentBucket2.Arn
    #
    # As we process module outputs, we need to remember these and
    # apply them here, since each module is processed separately
    # and it can't replace the entire 'Content[*]'
    resolve_foreach_lists(template, foreach_modules)

    # Special handling for intrinsic functions
    fn_select(template)
    fn_merge(template)
    fn_join(template)
    fn_insertfile(template, base_path)
    fn_flatten(template)

    # Remove the Modules section from the template
    del template[MODULES]

    # Remove the Packages section from the template
    if PACKAGES in template:
        del template[PACKAGES]

    # Emit the created resources into the parent
    for k, v in template[RESOURCES].items():
        parent_module.template[RESOURCES][parent_module.name + k] = v

    # Add metadata to the final template
    if not no_metrics:
        add_metrics_metadata(template)

    return template


class Module:
    """
    Process client-side modules.

    """

    def __init__(self, template, module_config, parent_module, s3_client=None):
        """
        Initialize the module with values from the parent template

        :param template The parent template dictionary
        :param module_config The configuration from the parent Modules section
        """

        # The parent template dictionary
        self.template = template
        self.parent_module = parent_module
        self.s3_client = s3_client

        self.original_module_dict = {}
        self.original_config = module_config.get(ORIGINAL_CONFIG, {})
        self.base_path = module_config.get(BASE_PATH, "")
        self.parent_path = module_config.get(PARENT_PATH, "")

        self.parent_lines = None
        if self.parent_path and self.parent_path != "":
            _, self.parent_lines = read_source(self.parent_path)

        self.invoked = module_config.get(INVOKED, False)

        # Default behavior for ForEach is to use array indexes
        self.foreach_name_is_i = True
        if FOREACH_NAME_IS_I in module_config:
            self.foreach_name_is_i = module_config[FOREACH_NAME_IS_I]

        if RESOURCES not in self.template:
            # The parent might only have Modules
            self.template[RESOURCES] = {}

        # The name of the module, which is used as a logical id prefix
        self.name = module_config[NAME]

        # Only set when we copy a module with a ForEach attribute
        self.original_foreach_name = None
        if ORIGINAL_FOREACH_NAME in module_config:
            self.original_foreach_name = module_config[ORIGINAL_FOREACH_NAME]

        # The location of the source for the module, a URI string
        self.source = module_config[SOURCE]

        # The Properties from the parent template
        self.props = {}
        if PROPERTIES in module_config:
            self.props = module_config[PROPERTIES]

        # The Overrides from the parent template
        self.overrides = {}
        if OVERRIDES in module_config:
            self.overrides = module_config[OVERRIDES]

        # Resources defined in the module
        self.resources = {}

        # Input parameters defined in the module
        self.module_parameters = {}

        # Outputs defined in the module
        self.module_outputs = {}

        # Conditions defined in the module
        self.conditions = {}

        self.mappings = {}

        # Line numbers for resources
        self.lines = {}
        self.line_numbers = None  # Added for ParameterValidator compatibility
        self.no_source_map = False
        if module_config.get(NO_SOURCE_MAP, False):
            self.no_source_map = True

        # A dictionary of foreach modules created by this module
        # If this module contains any sub-modules that use ForEach,
        # The dictionary will have the name as the key and length as the value.
        # {"Name": Length}
        self.foreach_modules = {}

        # Similar to foreeach_modules, for Resources with a ForEach
        self.resource_identifiers = {}

    def __str__(self):
        "Print out a string with module details for logs"
        return (
            f"module name: {self.name}, "
            + f"source: {self.source}, props: {self.props}"
        )

    def process(self):
        """
        Read the module source and process it.

        :return: The modified parent template dictionary
        """

        content, lines = read_source(self.source, self.s3_client)
        self.lines = lines
        self.line_numbers = (
            lines  # Set line_numbers for ParameterValidator compatibility
        )

        module_dict = yaml_parse(content)
        self.original_module_dict = copy.deepcopy(module_dict)
        return self.process_content(module_dict)

    def process_transform(self, module_dict):
        "Emit the Transform section into the parent"
        if TRANSFORM in module_dict:
            # The module has transforms. Emit them into the parent.
            if TRANSFORM not in self.template:
                self.template[TRANSFORM] = {}
            tt = self.template[TRANSFORM]
            merged = []
            mt = module_dict[TRANSFORM]
            both = [mt, tt]
            for tr in both:
                if isinstance(tr, str):
                    merged.append(tr)
                else:
                    for item in tr:
                        merged.append(item)
            self.template[TRANSFORM] = merged

    # pylint: disable=too-many-branches,too-many-statements
    def process_content(self, module_dict):
        "Process the module content and return the template"

        # Process constants
        constants = process_constants(module_dict)
        if constants is not None:
            replace_constants(constants, module_dict)

        self.process_transform(module_dict)

        # Validate parameters against schema if present
        if PARAMETER_SCHEMA in module_dict:
            try:
                # Create validator using the module instance directly
                validator = ParameterValidator(self)
                validator.validate_parameters(self.props)

                # Apply default values from schema
                if self.props is not None:
                    self.props = validator.apply_defaults(self.props)
            except ParameterValidationError as e:
                # Try to get line number for the parameter.
                # Prefer parent line number if available.
                line_number = None
                if self.parent_lines and e.param_name:
                    # Handle array indices in parameter names
                    if "[" in e.param_name:
                        base_param = e.param_name.split("[")[0]
                    else:
                        base_param = e.param_name.split(".")[0]

                    parent_prop_path = (
                        f"Modules.{self.name}.Properties.{base_param}"
                    )

                    if parent_prop_path in self.parent_lines:
                        line_number = self.parent_lines[parent_prop_path]

                # Fall back to module line number if parent
                # line number not available.
                if line_number is None:
                    if "[" in e.param_name:
                        param_base = e.param_name.split("[")[0]
                    else:
                        param_base = e.param_name.split(".")[0]

                    param_path = f"ParameterSchema.{param_base}"
                    if param_path in self.lines:
                        line_number = self.lines[param_path]

                # Update the line number in the original error
                e.line_number = line_number

                # Create a new error message
                error_msg = str(e)
                raise exceptions.InvalidModuleError(
                    msg=error_msg, line_number=line_number
                )
            except Exception as e:
                msg = (
                    f"Parameter validation failed for module {self.name}: {e}"
                )
                LOG.exception(msg)

                # Try to get line number for the ParameterSchema section
                line_number = None
                if "ParameterSchema" in self.lines:
                    line_number = self.lines["ParameterSchema"]

                raise exceptions.InvalidModuleError(
                    msg=msg, line_number=line_number
                )

        if RESOURCES not in module_dict:
            # The module may only have sub modules in the Modules section
            self.resources = {}
        else:
            # Store the resources first
            self.resources = module_dict[RESOURCES]

        if PARAMETERS in module_dict:
            self.module_parameters = module_dict[PARAMETERS]

        if OUTPUTS in module_dict:
            self.module_outputs = {}
            for k, v in module_dict[OUTPUTS].items():
                # Get rid of Value, so that we have a simple dictionary
                if VALUE in v:
                    self.module_outputs[k] = v[VALUE]
                else:
                    # Get line number for the output if available
                    line_number = None
                    output_path = f"Outputs.{k}"
                    if output_path in self.lines:
                        line_number = self.lines[output_path]
                    elif "Outputs" in self.lines:
                        line_number = self.lines["Outputs"]

                    msg = f"Output should have Value. {self.source}: {k}: {v}"
                    raise exceptions.InvalidModuleError(
                        msg=msg, line_number=line_number
                    )

        try:
            # Process conditions before recursing
            process_conditions(self, module_dict)
        except Exception as e:
            msg = f"Failed to process conditions in {self.source}: {e}"
            LOG.exception(msg)

            # Try to get line number for the condition if possible
            line_number = None
            if "Conditions" in self.lines:
                line_number = self.lines["Conditions"]

            raise exceptions.InvalidModuleError(
                msg=msg, line_number=line_number
            )

        # Recurse on nested modules
        bp = os.path.dirname(self.source)
        try:
            process_module_section(
                module_dict, bp, self.source, self, True, self.no_source_map
            )
        except Exception as e:
            msg = f"Failed to process {self.source} Modules section: {e}"
            LOG.exception(msg)
            raise exceptions.InvalidModuleError(msg=msg)

        # Call this again after recursing to pick up any unresolved
        # conditions that were emitted by sub-modules.
        process_conditions(self, module_dict)

        # Emit any unresolved mappings into the parent
        process_mappings(self, module_dict)

        # Make sure that overrides exist
        self.validate_overrides()

        if not self.invoked:

            # Process ForEach in resources before emitting them to the parent
            # template

            if RESOURCES in module_dict:
                self.resource_identifiers = process_foreach(
                    module_dict, self.parent_module
                )

                # Update resources after ForEach processing
                self.resources = module_dict[RESOURCES]

            # Process resources and put them into the parent template
            for logical_id, resource in self.resources.items():
                self.process_resource(logical_id, resource)

            # Process the module's outputs by modifying the parent
            process_module_outputs(self)

        # Look for Fn::Invoke calling this module in the parent
        # Create a fresh copy of the module so that things
        # like conditionals can be re-evaluated
        if not self.invoked:
            self.fn_invoke()

        return self.template

    def fn_invoke(self):
        """
        Resolve Fn::Invoke.

        Invoke allows you to treat a module like a function.

        Invoking the module returns its outputs with a modified
        set of parameters.
        """

        def vf(v):
            if not isdict(v.d) or INVOKE not in v.d or v.p is None:
                return

            inv = v.d[INVOKE]
            if not isinstance(inv, list) or len(inv) != 3:
                msg = f"Fn::Invoke requires 3 arguments: {inv}"
                raise exceptions.InvalidModuleError(msg=msg)
            module_name = inv[0]
            params = inv[1]
            outputs = inv[2]

            if module_name != self.name:
                return

            invoke_outputs = []
            if isinstance(outputs, list):
                invoke_outputs = outputs
            else:
                invoke_outputs.append(outputs)

            copied_module = make_module(
                self.template,
                self.name,
                copy.deepcopy(self.original_config),
                self.base_path,
                self.parent_path,
                self.no_source_map,
                self.parent_module,
                self.s3_client,
                True,
            )
            for k, val in params.items():
                copied_module.props[k] = val

            copied_module.process()

            retval = []
            for k in invoke_outputs:
                if k not in copied_module.module_outputs:
                    msg = f"Fn::Invoke output not found in {self.name}: k"
                    raise exceptions.InvalidModuleError(msg=msg)
                mo = copied_module.module_outputs[k]
                resolve(copied_module, mo)
                retval.append(mo)

            if len(retval) == 1:
                retval = retval[0]

            v.p[v.k] = retval

        Visitor(self.template).visit(vf)

    def validate_overrides(self):
        "Make sure resources referenced by overrides actually exist"
        for logical_id in self.overrides:
            if logical_id not in self.resources:
                msg = f"Override {logical_id} not found in {self.source}"
                raise exceptions.InvalidModuleError(msg=msg)

    def process_resource(self, logical_id, resource):
        "Process a single resource"

        # For each property (and property-like attribute),
        # replace the value if it appears in parent overrides.
        attrs = [
            PROPERTIES,
            CREATIONPOLICY,
            METADATA,
            UPDATEPOLICY,
            DELETIONPOLICY,
            CONDITION,
            UPDATEREPLACEPOLICY,
            DEPENDSON,
        ]
        for a in attrs:
            self.process_overrides(logical_id, resource, a)

        # Resolve refs, subs, and getatts
        #    (Process module Parameters and parent Properties)
        container = {}
        # We need the container for the first iteration of the recursion
        container[RESOURCES] = self.resources

        resolve(self, resource)

        self.template[RESOURCES][self.name + logical_id] = resource

        # DependsOn needs special handling, since it refers directly to
        # logical ids and does not use a !Ref to do so
        self.depends_on(logical_id, resource)

        # Add the source map to Metadata
        if not self.no_source_map:
            if METADATA not in resource:
                resource[METADATA] = {}
            metadata = resource[METADATA]
            if SOURCE_MAP not in metadata:
                # Don't overwrite child maps
                metadata[SOURCE_MAP] = self.get_source_map(logical_id)

    def depends_on(self, logical_id, resource):
        """
        Fix DependsOn references.

        For example, in a module included as 'Content', if we have
        DependsOn: Bucket, it needs to be DependsOn: ContentBucket.
        But, dont edit names that already refer to packaged names.
        So, if the author already has 'DependsOn: ContentBucket',
        leave it alone.
        """
        if DEPENDSON not in resource:
            return

        d = resource[DEPENDSON]
        # DependsOn can have a string or list
        # Make a new list to replace the old one
        ds = []
        replace_ds = []
        if isinstance(d, str):
            ds.append(d)
        if isinstance(d, list):
            for item in d:
                ds.append(item)

        for item in ds:
            found = False
            # Look at each other resource in this template for matching names
            for k in self.resources:
                if k == logical_id:
                    continue
                if item == k:
                    # Append the module name so it's correct in the parent
                    replace_ds.append(self.name + item)
                    found = True
                    break
            if not found:
                # We don't error here because of Overrides
                replace_ds.append(item)

        if len(replace_ds) == 1:
            resource[DEPENDSON] = replace_ds[0]
        else:
            resource[DEPENDSON] = list(set(replace_ds))

    def get_source_map(self, logical_id):
        "Get the string to put in the resource metadata source map"
        n = self.lines.get(logical_id, 0)
        return f"{self.source}:{logical_id}:{n}"

    def process_overrides(self, logical_id, resource, attr_name):
        """
        Replace overridden values in a property-like attribute of a resource.

        (Properties, Metadata, CreationPolicy, and UpdatePolicy)

        Overrides are a way to customize modules without needing a Parameter.

        Example template.yaml:

        Modules:
          Foo:
            Source: ./module.yaml
            Overrides:
              Bar:
                Properties:
                  Name: bbb

        Example module.yaml:

        Resources:
          Bar:
            Type: A::B::C
            Properties:
              Name: aaa

        Output yaml:

        Resources:
          Bar:
            Type: A::B::C
            Properties:
              Name: bbb
        """

        if logical_id not in self.overrides:
            return

        resource_overrides = self.overrides[logical_id]
        if resource_overrides is None:
            return
        if attr_name not in resource_overrides:
            return

        # Might be overriding something that's not in the module at all,
        # like a Bucket with no Properties
        if attr_name not in resource:
            if attr_name in resource_overrides:
                resource[attr_name] = resource_overrides[attr_name]
            else:
                return

        original = resource[attr_name]
        overrides = resource_overrides[attr_name]
        resource[attr_name] = merge_props(original, overrides)
