**Example 1: To retrieve a list of all control mapping types**

The following ``list-control-mappings`` example retrieves a list of all control mapping types. ::

    aws controlcatalog list-control-mappings

Output::

    {
        "ControlMappings": [
            {
                "ControlArn": "arn:aws:controlcatalog:::control/ckrg5g06x08c6pem7eEXAMPLE",
                "MappingType": "FRAMEWORK",
                "Mapping": {
                    "Framework": {
                        "Name": "SSAE-18-SOC-2-Oct-2023",
                        "Item": "CC6.1"
                    }
                }
            },
            {
                "ControlArn": "arn:aws:controlcatalog:::control/5lwgwp498974xwygyEXAMPLE",
                "MappingType": "FRAMEWORK",
                "Mapping": {
                    "Framework": {
                        "Name": "CIS-v8.0",
                        "Item": "14.6"
                    }
                }
            },
            {
                "ControlArn": "arn:aws:controlcatalog:::control/6s095tcdtgab75dd02EXAMPLE",
                "MappingType": "COMMON_CONTROL",
                "Mapping": {
                    "CommonControl": {
                        "CommonControlArn": "arn:aws:controlcatalog:::common-control/c0kq7ddgbp8ivhicnlEXAMPLE"
                    }
                }
            }
        ]
    }
    
For more information, see `Ontology overview <https://docs.aws.amazon.com/controlcatalog/latest/userguide/ontology-overview.html>`__ in the *AWS Control Catalog User Guide*.

**Example 2: To retrieve a list of control mappings of a specific control mapping type**

The following ``list-control-mappings`` example retrieves a list of control mappings of a specific control mapping type. ::

    aws controlcatalog list-control-mappings \
        --filter MappingTypes=FRAMEWORK

Output::

    {
        "ControlMappings": [
            {
                "ControlArn": "arn:aws:controlcatalog:::control/ckrg5g06x08c6pem7eEXAMPLE",
                "MappingType": "FRAMEWORK",
                "Mapping": {
                    "Framework": {
                        "Name": "SSAE-18-SOC-2-Oct-2023",
                        "Item": "CC6.1"
                    }
                }
            },
            {
                "ControlArn": "arn:aws:controlcatalog:::control/5lwgwp498974xwygy5EXAMPLE",
                "MappingType": "FRAMEWORK",
                "Mapping": {
                    "Framework": {
                        "Name": "CIS-v8.0",
                        "Item": "14.6"
                    }
                }
            }
        ]
    }

For more information, see `Ontology overview <https://docs.aws.amazon.com/controlcatalog/latest/userguide/ontology-overview.html>`__ in the *AWS Control Catalog User Guide*.
