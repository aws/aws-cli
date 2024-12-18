# Local CloudFormation Modules

See tests/unit/customizations/cloudformation/modules for examples of what the
Modules section of a template looks like.

Modules can be referenced in a new Modules section in the template, or they can
be referenced as Resources with the Type LocalModule.  Modules have a Source
attribute pointing to a local file, a Properties attribute that corresponds to
Parameters in the modules, and an Overrides attribute that can override module
output.

A module is itself basically a CloudFormation template, with a Parameters
section and Resources that are injected into the parent template. The
Properties defined in the Modules section correspond to the Parameters in the
module. These modules operate in a similar way to registry modules.

The name of the module in the Modules section is used as a prefix to logical
ids that are defined in the module. Or if the module is referenced in the Type
attribute of a Resource, the logical id of the resource is used as the prefix.

In addition to the parent setting Properties, all attributes of the module can
be overridden with Overrides, which require the consumer to know how the module
is structured. This "escape hatch" is considered a first class citizen in the
design, to avoid excessive Parameter definitions to cover every possible use
case.

Module Parameters (set by Properties in the parent) are handled with Refs,
Subs, and GetAtts in the module. These are handled in a way that fixes
references to match module prefixes, fully resolving values that are actually
strings and leaving others to be resolved at deploy time.

Modules can contain other modules, with no limit to the levels of nesting.

Modules can define Outputs, which are key-value pairs that can be referenced by
the parent.

When using modules, you can use a comma-delimited list to create a number of
similar resources. This is simpler than using `Fn::ForEach` but has the
limitation of requiring the list to be resolved at build time.
See tests/unit/customizations/cloudformation/modules/vpc-module.yaml.


