# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation import yamlhelper
import os

RESOURCES = "Resources"
METADATA = "Metadata"
OVERRIDES = "Overrides"
DEPENDSON = "DependsOn"
PROPERTIES = "Properties"
CREATIONPOLICY = "CreationPolicy"
UPDATEPOLICY = "UpdatePolicy"
DELETIONPOLICY = "DeletionPolicy"
UPDATEREPLACEPOLICY = "UpdateReplacePolicy"
CONDITION = "Condition"
DEFAULT = "Default"
NAME = "Name"
SOURCE = "Source"


def read_source(source):
    "Read the source file and return the content as a string"

    if not isinstance(source, str) or not os.path.isfile(source):
        raise exceptions.InvalidModulePathError(source=source)

    with open(source, "r") as s:
        return s.read()


class Module:
    """
    Process client-side modules.

    See tests/unit/customizations/cloudformation/modules for examples of what
    the Modules section of a template looks like.

    A module is itself basically a CloudFormation template, with a Parameters
    section and Resources that are injected into the parent template. The
    Properties defined in the Modules section correspond to the Parameters in
    the module. These modules operate in a similar way to registry modules.

    The name of the module in the Modules section is used as a prefix to
    logical ids that are defined in the module.

    In addition to the parent setting Properties, all attributes of the module
    can be overridden with Overrides, which require the consumer to know how
    the module is structured. This "escape hatch" is considered a first class
    citizen in the design, to avoid excessive Parameter definitions to cover
    every possible use case.

    Module Parameters (set by Properties in the parent) are handled with
    Refs, Subs, and GetAtts in the module. These are handled in a way that
    fixes references to match module prefixes, fully resolving values
    that are actually strings and leaving others to be resolved at deploy time.

    Modules can contain other modules, with no limit to the levels of nesting.
    """

    def __init__(self, template, module_config):
        """
        Initialize the module with values from the parent template

        :param template The parent template dictionary
        :param module_config The configuration from the parent Modules section
        """

        # The parent template dictionary
        self.template = template

        # The name of the module, which is used as a logical id prefix
        self.name = module_config[NAME]

        # The location of the source for the module, a URI string
        self.source = module_config[SOURCE]

        # The Properties from the parent template
        self.props = module_config[PROPERTIES]

        # The Overrides from the parent template
        self.overrides = module_config[OVERRIDES]

        # Resources defined in the module
        self.resources = {}

        # Parameters defined in the module
        self.params = {}

    def __str__(self):
        "Print out a string with module details for logs"
        return (
            f"module name: {self.name}, "
            + f"source: {self.source}, props: {self.props}"
        )

    def process(self):
        """
        Read the module source and return a dictionary that looks like a
        template, with keys such as 'Resources' that have the processed
        elements to be injected into the parent.

        :return: The modified parent template dictionary
        """

        content = read_source(self.source)

        module_dict = yamlhelper.yaml_parse(content)
        if RESOURCES not in module_dict:
            msg = "Modules must have a Resources section"
            raise exceptions.InvalidModuleError(msg=msg)

        self.validate_overrides()

        # TODO - For each resource in the module:
        for logical_id, resource in module_dict[RESOURCES].items():
            self.process_resource(logical_id, resource)

        return self.template

    def validate_overrides(self):
        "Make sure resources referenced by overrides actually exist"
        pass  # TODO

    def process_resource(self, logical_id, resource):
        "Process a single resource"

        # TODO - For each property (and property-like attribute),
        #        replace the value if it appears in parent overrides.
        # (Properties, CreationPolicy, Metadata, UpdatePolicy)

        # TODO - Replace scalar attributes with overrides
        # (DeletionPolicy, UpdateReplacePolicy, Condition)

        # TODO - Replace DependsOn with overrides

        # TODO - Resolve refs, subs, and getatts
        #        (Process module Parameters and parent Properties)

        self.template[RESOURCES]["Prefix?" + logical_id] = resource
