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
This file implements local module support for the package command.

See tests/unit/customizations/cloudformation/modules for examples of what the
Modules section of a template looks like, and how modules are used from parent
templates.

See the public documentation for a full description of the feature.

```

"""

# pylint: disable=fixme,too-many-instance-attributes,too-many-lines

import copy
import logging
import os

from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation import yamlhelper
from awscli.customizations.cloudformation.module_functions import (
    fn_merge,
    fn_select,
    fn_insertfile,
)
from awscli.customizations.cloudformation.module_merge import (
    isdict,
    merge_props,
)
from awscli.customizations.cloudformation.module_maps import (
    process_module_maps,
    resolve_mapped_lists,
    ORIGINAL,
    getatt_map_list,
)
from awscli.customizations.cloudformation.module_constants import (
    process_constants,
    replace_constants,
)

from awscli.customizations.cloudformation.parse_sub import WordType
from awscli.customizations.cloudformation.parse_sub import (
    parse_sub,
    is_sub_needed,
)
from awscli.customizations.cloudformation.module_conditions import (
    parse_conditions,
    process_resource_conditions,
)
from awscli.customizations.cloudformation.module_read import (
    read_source,
    is_url,
)

LOG = logging.getLogger(__name__)

RESOURCES = "Resources"
METADATA = "Metadata"
OVERRIDES = "Overrides"
DEPENDSON = "DependsOn"
PROPERTIES = "Properties"
CREATIONPOLICY = "CreationPolicy"
UPDATEPOLICY = "UpdatePolicy"
DELETIONPOLICY = "DeletionPolicy"
UPDATEREPLACEPOLICY = "UpdateReplacePolicy"
DEFAULT = "Default"
NAME = "Name"
SOURCE = "Source"
REF = "Ref"
SUB = "Fn::Sub"
GETATT = "Fn::GetAtt"
PARAMETERS = "Parameters"
MODULES = "Modules"
TYPE = "Type"
LOCAL_MODULE = "LocalModule"
OUTPUTS = "Outputs"
MAP = "Map"
CONDITIONS = "Conditions"
CONDITION = "Condition"
IF = "Fn::If"
AWSTOOLSMETRICS = "AWSToolsMetrics"
CLOUDFORMATION_PACKAGE = "CloudFormationPackage"
SOURCE_MAP = "SourceMap"
NO_SOURCE_MAP = "NoSourceMap"
VALUE = "Value"


# pylint:disable=too-many-arguments,too-many-positional-arguments
def make_module(
    template,
    name,
    config,
    base_path,
    parent_path,
    no_source_map,
    parent_module,
):
    "Create an instance of a module based on a template and the module config"
    module_config = {}
    module_config[NAME] = name
    if SOURCE not in config:
        msg = f"{name} missing {SOURCE}"
        raise exceptions.InvalidModulePathError(msg=msg)

    source_path = config[SOURCE]

    if not is_url(source_path):
        relative_path = source_path
        module_config[SOURCE] = os.path.join(base_path, relative_path)
        module_config[SOURCE] = os.path.normpath(module_config[SOURCE])
    else:
        module_config[SOURCE] = source_path

    if module_config[SOURCE] == parent_path:
        msg = f"Module refers to itself: {parent_path}"
        raise exceptions.InvalidModuleError(msg=msg)
    if PROPERTIES in config:
        module_config[PROPERTIES] = config[PROPERTIES]
    if OVERRIDES in config:
        module_config[OVERRIDES] = config[OVERRIDES]
    if ORIGINAL in config:
        module_config[ORIGINAL] = config[ORIGINAL]
    module_config[NO_SOURCE_MAP] = no_source_map
    return Module(template, module_config, parent_module)


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


# pylint:disable=too-many-arguments,too-many-positional-arguments
def process_module_section(
    template, base_path, parent_path, parent_module, no_metrics, no_source_map
):
    "Recursively process the Modules section of a template"

    if MODULES not in template:
        if parent_module is None:
            # This is a template with no modules.
            # Process template constants and new intrinsics.
            constants = process_constants(template)
            if constants is not None:
                replace_constants(constants, template)
            fn_select(template)
            fn_merge(template)
            fn_insertfile(template, base_path)
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
    mapped = process_module_maps(template, parent_module)
    parent_module.mapped = mapped

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
        )
        template = module.process()

    # Look for getatts to a mapped list like !GetAtt Content[].Arn
    # This should be converted to an array like
    # - !GetAtt ContentBucket0.Arn
    # - !GetAtt ContentBucket1.Arn
    # - !GetAtt ContentBucket2.Arn
    #
    # As we process module outputs, we need to remember these and
    # apply them here, since each module is processed separately
    # and it can't replace the entire 'Content[]'
    resolve_mapped_lists(template, mapped)

    # Special handling for intrinsic functions
    fn_select(template)

    fn_merge(template)

    fn_insertfile(template, base_path)

    # Remove the Modules section from the template
    del template[MODULES]

    # Lift the created resources up to the parent
    for k, v in template[RESOURCES].items():
        parent_module.template[RESOURCES][parent_module.name + k] = v

    # We only do this for resources, but in the future we might create
    # a way to lift other sections up to the parent as well.

    return template


class Module:
    """
    Process client-side modules.

    """

    def __init__(self, template, module_config, parent_module):
        """
        Initialize the module with values from the parent template

        :param template The parent template dictionary
        :param module_config The configuration from the parent Modules section
        """

        # The parent template dictionary
        self.template = template
        self.parent_module = parent_module

        if RESOURCES not in self.template:
            # The parent might only have Modules
            self.template[RESOURCES] = {}

        # The name of the module, which is used as a logical id prefix
        self.name = module_config[NAME]

        # Only set when we copy a module with a Map attribute
        self.original_map_name = None
        if ORIGINAL in module_config:
            self.original_map_name = module_config[ORIGINAL]

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

        # Line numbers for resources
        self.lines = {}
        self.no_source_map = False
        if module_config.get(NO_SOURCE_MAP, False):
            self.no_source_map = True

        # A dictionary of mapped modules created by this module
        # If this module contains any sub-modules that are mapped,
        # The dictionary will have the name as the key and length as the value.
        # {"Name": Length}
        self.mapped = {}

    def __str__(self):
        "Print out a string with module details for logs"
        return (
            f"module name: {self.name}, "
            + f"source: {self.source}, props: {self.props}"
        )

    # pylint: disable=too-many-branches
    def process(self):
        """
        Read the module source and process it.

        :return: The modified parent template dictionary
        """

        content, lines = read_source(self.source)
        self.lines = lines

        module_dict = yamlhelper.yaml_parse(content)

        # Process constants
        constants = process_constants(module_dict)
        if constants is not None:
            replace_constants(constants, module_dict)

        if RESOURCES not in module_dict:
            # The module may only have sub modules in the Modules section
            self.resources = {}
        else:
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
                    msg = f"Output should have Value. {self.source}: {k}: {v}"
                    raise exceptions.InvalidModuleError(msg=msg)

        # Read the Conditions section and store it as a dict of string:boolean
        if CONDITIONS in module_dict:
            cs = module_dict[CONDITIONS]

            def find_ref(v):
                return self.find_ref(v)

            try:
                self.conditions = parse_conditions(cs, find_ref)
            except Exception as e:
                msg = f"Failed to process conditions in {self.source}: {e}"
                LOG.exception(msg)
                raise exceptions.InvalidModuleError(msg=msg)

            # Check each resource to see if a Condition omits it
            for logical_id, resource in self.resources.copy().items():
                if CONDITION in resource:
                    if resource[CONDITION] in self.conditions:
                        if self.conditions[resource[CONDITION]] is False:
                            del self.resources[logical_id]
                        else:
                            del self.resources[logical_id][CONDITION]

            # Do the same for modules in the Modules section
            if MODULES in module_dict:
                for k, v in module_dict[MODULES].copy().items():
                    if CONDITION in v:
                        if v[CONDITION] in self.conditions:
                            if self.conditions[v[CONDITION]] is False:
                                del module_dict[MODULES][k]

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

        # Make sure that overrides exist
        self.validate_overrides()

        # Process resources and put them into the parent template
        for logical_id, resource in self.resources.items():
            self.process_resource(logical_id, resource)

        # Process the module's outputs by modifying the parent
        self.process_module_outputs()

        return self.template

    def process_module_outputs(self):
        """
        Fix parent template Ref, GetAtt, and Sub that point to module outputs.

        In the parent you can !GetAtt ModuleName.OutputName
        This will be converted so that it's correct in the packaged template.

        The parent can also refer to module Properties as a convenience,
        so !GetAtt ModuleName.PropertyName will simply copy the
        configured property value.

        Recurse over all sections in the parent template looking for
        GetAtts and Subs that reference a module Outputs value.

        This function is running from the module, inspecting everything
        in the partially resolved parent template.
        """
        sections = [RESOURCES, MODULES, OUTPUTS]
        for section in sections:
            if section not in self.template:
                continue
            for k, v in self.template[section].items():
                self.resolve_module_outputs(k, v, self.template, section)

    def resolve_module_outputs(self, k, v, d, n):
        """
        Recursively resolve GetAtts and Subs that reference module outputs.

        :param name The name of the reference
        :param k The name of the node
        :param v The value of the node
        :param d The dict that holds the parent of k
        :param n The name of the node that holds k

        If a reference is found, this function sets the value of d[n]
        """
        if k == SUB:
            self.resolve_output_sub(v, d, n)
        elif k == GETATT:
            self.resolve_output_getatt(v, d, n)
        else:
            if isdict(v):
                for k2, v2 in v.copy().items():
                    self.resolve_module_outputs(k2, v2, d[n], k)
            elif isinstance(v, list):
                idx = -1
                for v2 in v:
                    idx = idx + 1
                    if isdict(v2):
                        for k3, v3 in v2.copy().items():
                            self.resolve_module_outputs(k3, v3, v, idx)

    def resolve_output_sub_getatt(self, w):
        """
        Resolve a reference to a module in a Sub GetAtt word.

        For example, the parent has

        Modules:
          A:
            Properties:
              Name: foo
        Outputs:
          B:
            Value: !Sub ${A.MyName}
          C:
            Value: !Sub ${A.Name}

        The module has:

          Parameters:
            Name:
              Type: String
          Resources:
            X:
              Properties:
                Y: !Ref Name
          Outputs:
            MyName: !GetAtt Y.Name

        The resulting output:
          B: !Sub ${AX.Name}
          C: foo

        """

        resolved = "${" + w + "}"
        tokens = w.split(".", 1)
        if len(tokens) < 2:
            msg = f"GetAtt {w} has unexpected number of tokens"
            raise exceptions.InvalidModuleError(msg=msg)

        # !Sub ${Content.BucketArn} -> !Sub ${ContentBucket.Arn}

        r = None
        if tokens[0] == self.name:
            if tokens[1] in self.module_outputs:
                # We're referring to the module's Outputs
                r = self.module_outputs[tokens[1]]
            elif tokens[1] in self.props:
                # We're referring to parent Module Properties
                r = self.props[tokens[1]]
            if r is not None:
                if GETATT in r:
                    getatt = r[GETATT]
                    resolved = "${" + self.name + ".".join(getatt) + "}"
                elif SUB in r:
                    resolved = "${" + self.name + r[SUB] + "}"
                elif REF in r:
                    resolved = "${" + self.name + r[REF] + "}"
                else:
                    # Handle scalar properties
                    resolved = r

        return resolved

    def resolve_output_sub(self, v, d, n):
        "Resolve a Sub that refers to a module reference or property"
        words = parse_sub(v, True)
        sub = ""
        for word in words:
            if word.t == WordType.STR:
                sub += word.w
            elif word.t == WordType.AWS:
                sub += "${AWS::" + word.w + "}"
            elif word.t == WordType.REF:
                # A ref to a module reference has to be a getatt
                resolved = "${" + word.w + "}"
                sub += resolved
            elif word.t == WordType.GETATT:
                sub += self.resolve_output_sub_getatt(word.w)

        if is_sub_needed(sub):
            d[n] = {SUB: sub}
        else:
            d[n] = sub

    # pylint:disable=too-many-branches,too-many-locals,too-many-statements
    def resolve_output_getatt(self, v, d, n):
        """
        Resolve a GetAtt that refers to a module Output.

        :param v The value
        :param d The dictionary
        :param n The name of the node

        This function sets d[n] and returns True if it resolved.
        """

        if not isinstance(v, list) or len(v) < 2:
            msg = f"GetAtt {v} invalid"
            raise exceptions.InvalidModuleError(msg=msg)

        # print("")
        # print("resolve_output_getatt")
        # print("  v:", v)
        # print("  d:", d)
        # print("  n:", n)

        # For example, Content.Arn or Content[0].Arn

        mapped = self.parent_module.mapped
        name = v[0]
        prop_name = v[1]

        index = -1
        if "[" in name:
            tokens = name.split("[")
            name = tokens[0]
            if tokens[1] != "]":
                num = tokens[1].replace("]", "")
                if num.isdigit():
                    index = int(num)
                else:
                    msg = f"Invalid index in {v}"
                    raise exceptions.InvalidModuleError(msg=msg)
            else:
                # This is a reference to all of the mapped values
                # For example, Content[].Arn
                if name in mapped:
                    self.resolve_output_getatt_map(mapped, name, prop_name)
                return False

        if index > -1:
            name = f"{name}{index}"

        reffed_prop = None
        if name == self.name:
            if prop_name in self.module_outputs:
                reffed_prop = self.module_outputs[prop_name]
            elif prop_name in self.props:
                reffed_prop = self.props[prop_name]

        if reffed_prop is None:
            # print("  reffed_prop is None")
            # print("")
            return False

        # print("  reffed_prop:", reffed_prop)

        if isinstance(reffed_prop, list):
            for i, r in enumerate(reffed_prop):
                self.replace_reffed_prop(r, reffed_prop, i)
                d[n] = reffed_prop
        else:
            self.replace_reffed_prop(reffed_prop, d, n)

        return True

    def replace_reffed_prop(self, r, d, n):
        """
        Replace a reffed prop in an output getatt.

        Sets d[n].
        """

        if REF in r:
            ref = r[REF]
            d[n] = {REF: self.name + ref}
        elif GETATT in r:
            getatt = r[GETATT]
            if len(getatt) < 2:
                msg = f"GetAtt {getatt} in {self.name} is invalid"
                raise exceptions.InvalidModuleError(msg=msg)
            s = getatt_map_list(getatt)
            if s is not None and s in self.mapped:
                # Special handling for Overrides that GetAtt a module
                # property, when that module has a Map attribute
                if isinstance(self.mapped[s], list):
                    # print("")
                    # print("self.name", self.name)
                    # print("r:", r)
                    # print("d:", d)
                    # print("n:", n)
                    # print("s:", s)
                    # print("self.mapped[s]", self.mapped[s])
                    # print("")
                    d[n] = copy.deepcopy(self.mapped[s])
                    for item in d[n]:
                        if GETATT in item and len(item[GETATT]) > 0:
                            item[GETATT][0] = self.name + item[GETATT][0]
            else:
                d[n] = {GETATT: [self.name + getatt[0], getatt[1]]}
        elif SUB in r:
            # Parse the Sub in the module reference
            words = parse_sub(r[SUB], True)
            sub = ""
            for word in words:
                if word.t == WordType.STR:
                    sub += word.w
                elif word.t == WordType.AWS:
                    sub += "${AWS::" + word.w + "}"
                elif word.t == WordType.REF:
                    # This is a ref to a param or resource
                    # If it's a resource, concatenante the name
                    resolved = "${" + word.w + "}"
                    if word.w in self.resources:
                        resolved = "${" + self.name + word.w + "}"
                    sub += resolved
                elif word.t == WordType.GETATT:
                    resolved = "${" + word.w + "}"
                    tokens = word.w.split(".", 1)
                    if len(tokens) < 2:
                        msg = f"GetAtt {word.w} unexpected length"
                        raise exceptions.InvalidModuleError(msg=msg)
                    if tokens[0] in self.resources:
                        resolved = "${" + self.name + word.w + "}"
                    sub += resolved
            d[n] = {SUB: sub}
        else:
            # Handle scalars in Properties
            d[n] = r

    def resolve_output_getatt_map(self, mapped, name, prop_name):
        "Resolve GetAtts that reference all Outputs from a mapped module"
        num_items = mapped[name]
        dd = [None] * num_items
        for i in range(num_items):
            # Resolve the item as if it was a normal getatt
            vv = [f"{name}{i}", prop_name]
            resolved = self.resolve_output_getatt(vv, dd, i)
            if resolved:
                # Don't set anything here, just remember it so
                # we can go back and fix the entire getatt later
                item_val = dd[i]
                # Use a key like "Content.Arn"
                key = name + "[]." + prop_name
                if key not in mapped:
                    mapped[key] = []
                if item_val not in mapped[key]:
                    print("resolve_output_getatt_map")
                    print("key:", key)
                    print("item_val:", item_val)
                    # Don't double add. We already replaced refs in
                    # modules, so it shows up twice.
                    mapped[key].append(item_val)

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

        process_resource_conditions(
            self.name, self.conditions, self.resources, self.module_outputs
        )

        # Resolve refs, subs, and getatts
        #    (Process module Parameters and parent Properties)
        container = {}
        # We need the container for the first iteration of the recursion
        container[RESOURCES] = self.resources
        self.resolve(logical_id, resource, container, RESOURCES)
        self.template[RESOURCES][self.name + logical_id] = resource

        # DependsOn needs special handling, since it refers directly to
        # logical ids and does not use a !Ref to do so
        self.depends_on(logical_id, resource)

        # Add the source map to Metadata
        if not self.no_source_map:
            if METADATA not in resource:
                resource[METADATA] = {}
            metadata = resource[METADATA]
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
            resource[DEPENDSON] = replace_ds

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

    def resolve(self, k, v, d, n):
        """
        Resolve Refs, Subs, and GetAtts recursively.

        :param k The name of the node
        :param v The value of the node
        :param d The dict that is the parent of the dict that holds k, v
        :param n The name of the dict that holds k, v

        Example

        Resources:
          Bucket:
            Type: AWS::S3::Bucket
            Properties:
              BucketName: !Ref Name

        In the above example,
            k = !Ref, v = Name, d = Properties{}, n = BucketName

        So we can set d[n] = resolved_value (which replaces {k,v})

        In the prior iteration,
            k = BucketName, v = {!Ref, Name}, d = Bucket{}, n = Properties
        """

        if k == REF:
            self.resolve_ref(v, d, n)
        elif k == SUB:
            self.resolve_sub(v, d, n)
        elif k == GETATT:
            self.resolve_getatt(v, d, n)
        else:
            if isdict(v):
                vc = v.copy()
                for k2, v2 in vc.items():
                    self.resolve(k2, v2, d[n], k)
            elif isinstance(v, list):
                idx = -1
                for v2 in v:
                    idx = idx + 1
                    if isdict(v2):
                        v2c = v2.copy()
                        for k3, v3 in v2c.items():
                            self.resolve(k3, v3, v, idx)

    def resolve_ref(self, v, d, n):
        """
        Look for the Ref in the parent template Properties if it matches
        a module Parameter name. If it's not there, use the default if
        there is one. If not, raise an error.

        If there is no matching Parameter, look for a resource with that
        name in this module and fix the logical id so it has the prefix.

        Otherwise raise an exception.
        """
        if not isinstance(v, str):
            msg = f"Ref should be a string: {v}"
            raise exceptions.InvalidModuleError(msg=msg)

        found = self.find_ref(v)
        if found is not None:
            d[n] = found
        else:
            if isinstance(v, str) and v.startswith("AWS::"):
                pass  # return
            # msg = (
            #    f"Not found in {self.source}: {n}: {v}"
            # )
            # raise exceptions.InvalidModuleError(msg=msg)
            #
            # Ideally we would raise an exception here. But in the case
            # of a sub-module referring to another sub-module in
            # the Overrides section, the name has already been fixed,
            # so we won't find it in this template or in parameters.
            # This is identical to the possiblity that a module author
            # might refer to something directly in the parent, without
            # an input. The tradeoff is that we can't detect legit typos.
            # We have to depend on cfn-lint on the final template.

    def resolve_sub_ref(self, w):
        "Resolve a ref inside of a Sub string"
        resolved = "${" + w + "}"
        found = self.find_ref(w)
        if found is not None:
            if isinstance(found, str):
                resolved = found
            else:
                if REF in found:
                    resolved = "${" + found[REF] + "}"
                elif SUB in found:
                    resolved = found[SUB]
                elif GETATT in found:
                    tokens = found[GETATT]
                    if len(tokens) < 2:
                        msg = (
                            "Invalid Sub referencing a GetAtt. "
                            + f"{w}: {found}"
                        )
                        raise exceptions.InvalidModuleError(msg=msg)

                    resolved = "${" + ".".join(tokens) + "}"
        return resolved

    def resolve_sub_getatt(self, w):
        "Resolve a GetAtt ('A.B') inside a Sub string"
        resolved = "${" + w + "}"
        tokens = w.split(".", 1)
        if len(tokens) < 2:
            msg = f"GetAtt {w} has unexpected number of tokens"
            raise exceptions.InvalidModuleError(msg=msg)
        if tokens[0] in self.resources:
            tokens[0] = self.name + tokens[0]
        resolved = "${" + tokens[0] + "." + tokens[1] + "}"
        return resolved

    # pylint: disable=too-many-branches,unused-argument
    def resolve_sub(self, v, d, n):
        """
        Parse the Sub string and break it into tokens.

        If we can fully resolve it, we can replace it with a string.

        Use the same logic as with resolve_ref.
        """
        words = parse_sub(v, True)
        sub = ""
        for word in words:
            if word.t == WordType.STR:
                sub += word.w
            elif word.t == WordType.AWS:
                sub += "${AWS::" + word.w + "}"
            elif word.t == WordType.REF:
                sub += self.resolve_sub_ref(word.w)
            elif word.t == WordType.GETATT:
                sub += self.resolve_sub_getatt(word.w)

        need_sub = is_sub_needed(sub)
        if need_sub:
            d[n] = {SUB: sub}
        else:
            d[n] = sub

    def resolve_getatt(self, v, d, n):
        """
        Resolve a GetAtt. All we do here is add the prefix.

        !GetAtt Foo.Bar becomes !GetAtt ModuleNameFoo.Bar
        """
        if not isinstance(v, list):
            msg = f"GetAtt {v} is not a list"
            raise exceptions.InvalidModuleError(msg=msg)

        # Make sure the logical id exists
        exists = False
        for resource in self.resources:
            if resource == v[0]:
                exists = True
                break
        if exists:
            logical_id = self.name + v[0]
            d[n] = {GETATT: [logical_id, v[1]]}

    def find_ref(self, name):
        """
        Find a Ref.

        A Ref might be to a module Parameter with a matching parent
        template Property, or a Parameter Default. It could also
        be a reference to another resource in this module.

        :param name The name to search for
        :return The referenced element or None
        """
        if name in self.props:
            if name not in self.module_parameters:
                # The parent tried to set a property that doesn't exist
                # in the Parameters section of this module
                msg = f"{name} not found in module Parameters: {self.source}"
                raise exceptions.InvalidModuleError(msg=msg)
            return self.props[name]

        if name in self.module_parameters:
            param = self.module_parameters[name]
            if DEFAULT in param:
                # Use the default value of the Parameter
                return param[DEFAULT]
            msg = f"{name} does not have a Default and is not a Property"
            raise exceptions.InvalidModuleError(msg=msg)

        for logical_id in self.resources:
            if name == logical_id:
                # Simply rename local references to include the module name
                return {REF: self.name + logical_id}

        return None
