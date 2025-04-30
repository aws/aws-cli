"""Tests for Ref resolution in Fn::Flatten"""

from awscli.testutils import unittest
from awscli.customizations.cloudformation.modules.flatten import (
    _process_flatten,
    fn_flatten,
    FLATTEN,
)
from awscli.customizations.cloudformation.modules.process import Module
from awscli.customizations.cloudformation.modules.names import (
    NAME,
    SOURCE,
    PARAMETERS,
    REF,
    RESOURCES,
    PROPERTIES,
    MODULES,
)


class TestFlattenRefResolution(unittest.TestCase):
    """Test reference resolution in Fn::Flatten"""

    def test_flatten_with_module_resolution(self):
        """Test Fn::Flatten with proper Module reference resolution"""

        # Create a template with Fn::Flatten using a reference
        template = {
            PARAMETERS: {
                "ServiceConfig": {
                    "Type": "Map",
                    "Default": {
                        "services": [
                            {"name": "api", "environments": ["dev", "prod"]},
                            {
                                "name": "worker",
                                "environments": ["dev", "prod"],
                            },
                        ]
                    },
                }
            },
            RESOURCES: {
                "TestResource": {
                    "Type": "AWS::Test::Resource",
                    PROPERTIES: {
                        "Items": {
                            FLATTEN: {
                                "Source": {REF: "ServiceConfig"},
                                "Transform": {
                                    "Template": {
                                        "Name": "$item.name",
                                        "Environment": "$env",
                                    },
                                    "Variables": {
                                        "env": "$item.environments[*]"
                                    },
                                },
                            }
                        }
                    },
                }
            },
        }

        # Create a Module instance with proper configuration
        module_config = {
            NAME: "",  # Empty name for root module
            SOURCE: "",  # Empty source for root module
        }
        module = Module(template, module_config, None)

        # Set module parameters
        module.module_parameters = template[PARAMETERS]

        # Use the module's resolve function to resolve references
        resource = template[RESOURCES]["TestResource"]
        module.resolve(resource)

        # Now process the Fn::Flatten with resolved references
        fn_flatten(template)

        # Verify the result
        items = template[RESOURCES]["TestResource"][PROPERTIES]["Items"]
        self.assertEqual(len(items), 4, "Expected 4 items after flattening")

        # Check that all combinations are present
        names = [item["Name"] for item in items]
        environments = [item["Environment"] for item in items]

        self.assertEqual(
            names.count("api"), 2, "Expected 'api' to appear twice"
        )
        self.assertEqual(
            names.count("worker"), 2, "Expected 'worker' to appear twice"
        )
        self.assertEqual(
            environments.count("dev"), 2, "Expected 'dev' to appear twice"
        )
        self.assertEqual(
            environments.count("prod"), 2, "Expected 'prod' to appear twice"
        )

    def test_flatten_foreach_integration(self):
        """Test that Fn::Flatten works correctly when used inside ForEach"""

        # Create a template similar to the flatten-foreach-template.yaml
        template = {
            PARAMETERS: {
                "ServiceConfig": {
                    "Type": "Map",
                    "Default": {
                        "services": [
                            {"name": "api", "environments": ["dev", "prod"]},
                            {
                                "name": "worker",
                                "environments": ["dev", "prod"],
                            },
                            {"name": "scheduler", "environments": ["prod"]},
                        ]
                    },
                }
            },
            MODULES: {
                "Service": {
                    SOURCE: "./dummy-module.yaml",
                    "ForEach": {
                        FLATTEN: {
                            "Source": {REF: "ServiceConfig"},
                            "Transform": {
                                "Template": {
                                    "Identifier": "$item.name-$env",
                                    "ServiceName": "$item.name",
                                    "Environment": "$env",
                                    "Type": "service",
                                },
                                "Variables": {"env": "$item.environments[*]"},
                            },
                        }
                    },
                    PROPERTIES: {
                        "Name": {"Fn::Sub": "${Identifier}"},
                        "ServiceName": {"Fn::Sub": "${Value.ServiceName}"},
                        "Environment": {"Fn::Sub": "${Value.Environment}"},
                    },
                }
            },
        }

        # Create a Module instance with proper configuration
        module_config = {
            NAME: "",  # Empty name for root module
            SOURCE: "",  # Empty source for root module
        }
        module = Module(template, module_config, None)

        # Set module parameters
        module.module_parameters = template[PARAMETERS]

        # Use the module's resolve function to resolve
        # references in the ForEach
        foreach_config = template[MODULES]["Service"]["ForEach"]
        module.resolve(foreach_config)

        # Now process the Fn::Flatten with resolved references
        result = _process_flatten(foreach_config[FLATTEN])

        # Verify the result
        self.assertEqual(len(result), 5, "Expected 5 items after flattening")

        # Check that all expected combinations are present
        identifiers = [item["Identifier"] for item in result]
        self.assertIn("api-dev", identifiers)
        self.assertIn("api-prod", identifiers)
        self.assertIn("worker-dev", identifiers)
        self.assertIn("worker-prod", identifiers)
        self.assertIn("scheduler-prod", identifiers)
