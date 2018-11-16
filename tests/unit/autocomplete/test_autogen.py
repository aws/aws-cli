# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest
from copy import deepcopy
from awscli.autocomplete.autogen import ServerCompletionHeuristic
from botocore.model import ServiceModel


# To make these tests more realistic, a stripped down version of the ACM
# service is included as part of these tests.  There are a few extra
# shapes/operations that are added to exercise more of the code, but
# overall the model still reflects something that you'd actually see
# in a real service model.
BASIC_MODEL = {
    "version": "2.0",
    "metadata": {
        "apiVersion": "2015-12-08",
        "endpointPrefix": "acm",
        "jsonVersion": "1.1",
        "protocol": "json",
        "serviceAbbreviation": "ACM",
        "serviceFullName": "AWS Certificate Manager",
        "serviceId": "ACM",
        "signatureVersion": "v4",
        "targetPrefix": "CertificateManager",
        "uid": "acm-2015-12-08",
    },
    "operations": {
        "CreateCertificate": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "CreateCertificateRequest"},
            "name": "DeleteCertificate",
        },
        "DeleteCertificate": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "DeleteCertificateRequest"},
            "name": "DeleteCertificate",
        },
        "DescribeCertificate": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "DescribeCertificateRequest"},
            "name": "DescribeCertificate",
            "output": {"shape": "DescribeCertificateResponse"},
        },
        "ExportCertificate": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "ExportCertificateRequest"},
            "name": "ExportCertificate",
            "output": {"shape": "ExportCertificateResponse"},
        },
        "GetCertificate": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "GetCertificateRequest"},
            "name": "GetCertificate",
            "output": {"shape": "GetCertificateResponse"},
        },
        "ImportCertificate": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "ImportCertificateRequest"},
            "name": "ImportCertificate",
            "output": {"shape": "ImportCertificateResponse"},
        },
        "ListCertificates": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "ListCertificatesRequest"},
            "name": "ListCertificates",
            "output": {"shape": "ListCertificatesResponse"},
        },
    },
    "shapes": {
        "Arn": {"max": 2048, "min": 20, "type": "string"},
        "CertificateBody": {"max": 32768, "min": 1, "type": "string"},
        "CertificateBodyBlob": {"max": 32768, "min": 1, "type": "blob"},
        "CertificateChain": {"max": 2097152, "min": 1, "type": "string"},
        "CertificateChainBlob": {"max": 2097152, "min": 1, "type": "blob"},
        "CertificateDetail": {
            "members": {
                "CertificateArn": {"shape": "Arn"},
                "CertificateAuthorityArn": {"shape": "Arn"},
                "Options": {"shape": "CertificateOptions"},
                "SubjectAlternativeNames": {"shape": "DomainList"},
                "Type": {"shape": "CertificateType"},
            },
            "type": "structure",
        },
        "CertificateOptions": {
            "members": {},
            "type": "structure",
        },
        "CertificateStatus": {"type": "string"},
        "CertificateStatuses": {
            "member": {"shape": "CertificateStatus"},
            "type": "list",
        },
        "CertificateSummary": {
            "members": {
                "CertificateArn": {"shape": "Arn"},
                "DomainName": {"shape": "DomainNameString"},
            },
            "type": "structure",
        },
        "CertificateSummaryList": {
            "member": {"shape": "CertificateSummary"},
            "type": "list",
        },
        "CertificateType": {"type": "string"},
        "CreateCertificateRequest": {
            "members": {"CertificateArn": {"shape": "Arn"}},
            "required": ["CertificateArn"],
            "type": "structure",
        },
        "DeleteCertificateRequest": {
            "members": {"CertificateArn": {"shape": "Arn"}},
            "required": ["CertificateArn"],
            "type": "structure",
        },
        "DescribeCertificateRequest": {
            "members": {"CertificateArn": {"shape": "Arn"}},
            "required": ["CertificateArn"],
            "type": "structure",
        },
        "DescribeCertificateResponse": {
            "members": {"Certificate": {"shape": "CertificateDetail"}},
            "type": "structure",
        },
        "DomainList": {
            "max": 100,
            "member": {"shape": "DomainNameString"},
            "min": 1,
            "type": "list",
        },
        "DomainNameString": {"max": 253, "min": 1, "type": "string"},
        "DomainStatus": {"type": "string"},
        "DomainValidation": {
            "members": {
                "DomainName": {"shape": "DomainNameString"},
                "ResourceRecord": {"shape": "ResourceRecord"},
                "ValidationDomain": {"shape": "DomainNameString"},
                "ValidationEmails": {"shape": "ValidationEmailList"},
                "ValidationMethod": {"shape": "ValidationMethod"},
                "ValidationStatus": {"shape": "DomainStatus"},
            },
            "required": ["DomainName"],
            "type": "structure",
        },
        "DomainValidationList": {
            "max": 1000,
            "member": {"shape": "DomainValidation"},
            "min": 1,
            "type": "list",
        },
        "ExportCertificateRequest": {
            "members": {
                "CertificateArn": {"shape": "Arn"},
                "Passphrase": {"shape": "PassphraseBlob"},
            },
            "required": ["CertificateArn", "Passphrase"],
            "type": "structure",
        },
        "ExportCertificateResponse": {
            "members": {
                "Certificate": {"shape": "CertificateBody"},
                "CertificateChain": {"shape": "CertificateChain"},
                "PrivateKey": {"shape": "PrivateKey"},
            },
            "type": "structure",
        },
        "ExtendedKeyUsage": {
            "members": {
                "Name": {"shape": "ExtendedKeyUsageName"},
                "OID": {"shape": "String"},
            },
            "type": "structure",
        },
        "ExtendedKeyUsageFilterList": {
            "member": {"shape": "ExtendedKeyUsageName"},
            "type": "list",
        },
        "ExtendedKeyUsageList": {
            "member": {"shape": "ExtendedKeyUsage"},
            "type": "list",
        },
        "ExtendedKeyUsageName": {"type": "string"},
        "FailureReason": {"type": "string"},
        "Filters": {
            "members": {
                "extendedKeyUsage": {"shape": "ExtendedKeyUsageFilterList"},
                "keyTypes": {"shape": "KeyAlgorithmList"},
                "keyUsage": {"shape": "KeyUsageFilterList"},
            },
            "type": "structure",
        },
        "GetCertificateRequest": {
            "members": {"CertificateArn": {"shape": "Arn"}},
            "required": ["CertificateArn"],
            "type": "structure",
        },
        "GetCertificateResponse": {
            "members": {
                "Certificate": {"shape": "CertificateBody"},
                "CertificateChain": {"shape": "CertificateChain"},
            },
            "type": "structure",
        },
        "ImportCertificateRequest": {
            "members": {
                "Certificate": {"shape": "CertificateBodyBlob"},
                "CertificateArn": {"shape": "Arn"},
                "CertificateChain": {"shape": "CertificateChainBlob"},
                "PrivateKey": {"shape": "PrivateKeyBlob"},
            },
            "required": ["Certificate", "PrivateKey"],
            "type": "structure",
        },
        "ImportCertificateResponse": {
            "members": {"CertificateArn": {"shape": "Arn"}},
            "type": "structure",
        },
        "InUseList": {"member": {"shape": "String"}, "type": "list"},
        "KeyAlgorithm": {"type": "string"},
        "KeyAlgorithmList": {
            "member": {"shape": "KeyAlgorithm"},
            "type": "list",
        },
        "KeyUsage": {
            "members": {"Name": {"shape": "KeyUsageName"}},
            "type": "structure",
        },
        "KeyUsageFilterList": {
            "member": {"shape": "KeyUsageName"},
            "type": "list",
        },
        "KeyUsageList": {"member": {"shape": "KeyUsage"}, "type": "list"},
        "KeyUsageName": {"type": "string"},
        "ListCertificatesRequest": {
            "members": {
                "CertificateStatuses": {"shape": "CertificateStatuses"},
                "Includes": {"shape": "Filters"},
                "MaxItems": {"shape": "MaxItems"},
                "NextToken": {"shape": "NextToken"},
            },
            "type": "structure",
        },
        "ListCertificatesResponse": {
            "members": {
                "CertificateSummaryList": {"shape": "CertificateSummaryList"},
                "NextToken": {"shape": "NextToken"},
            },
            "type": "structure",
        },
        "MaxItems": {"max": 1000, "min": 1, "type": "integer"},
        "NextToken": {"max": 320, "min": 1, "type": "string"},
        "PassphraseBlob": {
            "type": "blob",
        },
        "PrivateKey": {
            "type": "string",
        },
        "PrivateKeyBlob": {
            "type": "blob",
        },
        "RecordType": {"type": "string"},
        "RenewalEligibility": {"type": "string"},
        "RenewalStatus": {"type": "string"},
        "RenewalSummary": {
            "members": {
                "DomainValidationOptions": {"shape": "DomainValidationList"},
                "RenewalStatus": {"shape": "RenewalStatus"},
            },
            "required": ["RenewalStatus", "DomainValidationOptions"],
            "type": "structure",
        },
        "ResourceRecord": {
            "members": {
                "Name": {"shape": "String"},
                "Type": {"shape": "RecordType"},
                "Value": {"shape": "String"},
            },
            "required": ["Name", "Type", "Value"],
            "type": "structure",
        },
        "RevocationReason": {"type": "string"},
        "String": {"type": "string"},
        "TStamp": {"type": "timestamp"},
        "ValidationEmailList": {"member": {"shape": "String"}, "type": "list"},
        "ValidationMethod": {"type": "string"},
    },
}


# This is a stripped down version from athena.
MODEL_WITH_STRING_LIST = {
    "version": "2.0",
    "metadata": {},
    "operations": {
        "CreateNamedQuery": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "CreateNamedQueryInput"},
            "name": "CreateNamedQuery",
            "output": {"shape": "CreateNamedQueryOutput"},
        },
        "DeleteNamedQuery": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "DeleteNamedQueryInput"},
            "name": "DeleteNamedQuery",
            "output": {"shape": "DeleteNamedQueryOutput"},
        },
        "GetNamedQuery": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "GetNamedQueryInput"},
            "name": "GetNamedQuery",
            "output": {"shape": "GetNamedQueryOutput"},
        },
        "ListNamedQueries": {
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "ListNamedQueriesInput"},
            "name": "ListNamedQueries",
            "output": {"shape": "ListNamedQueriesOutput"},
        },
    },
    "shapes": {
        "CreateNamedQueryInput": {
            "members": {
                "ClientRequestToken": {
                    "idempotencyToken": True,
                    "shape": "IdempotencyToken",
                },
                "Database": {"shape": "DatabaseString"},
                "Description": {"shape": "DescriptionString"},
                "Name": {"shape": "NameString"},
                "QueryString": {"shape": "QueryString"},
            },
            "required": ["Name", "Database", "QueryString"],
            "type": "structure",
        },
        "CreateNamedQueryOutput": {
            "members": {"NamedQueryId": {"shape": "NamedQueryId"}},
            "type": "structure",
        },
        "DatabaseString": {"type": "string"},
        "DeleteNamedQueryInput": {
            "members": {
                "NamedQueryId": {
                    "idempotencyToken": True,
                    "shape": "NamedQueryId",
                }
            },
            "required": ["NamedQueryId"],
            "type": "structure",
        },
        "DeleteNamedQueryOutput": {"members": {}, "type": "structure"},
        "DescriptionString": {"type": "string"},
        "GetNamedQueryInput": {
            "members": {"NamedQueryId": {"shape": "NamedQueryId"}},
            "required": ["NamedQueryId"],
            "type": "structure",
        },
        "GetNamedQueryOutput": {
            "members": {"NamedQuery": {"shape": "NamedQuery"}},
            "type": "structure",
        },
        "IdempotencyToken": {"type": "string"},
        "ListNamedQueriesInput": {
            "members": {
                "MaxResults": {"shape": "MaxNamedQueriesCount"},
                "NextToken": {"shape": "Token"},
            },
            "type": "structure",
        },
        "ListNamedQueriesOutput": {
            "members": {
                "NamedQueryIds": {"shape": "NamedQueryIdList"},
                "NextToken": {"shape": "Token"},
            },
            "type": "structure",
        },
        "MaxNamedQueriesCount": {"type": "integer"},
        "NameString": {"type": "string"},
        "NamedQuery": {
            "members": {
                "Database": {"shape": "DatabaseString"},
                "Description": {"shape": "DescriptionString"},
                "Name": {"shape": "NameString"},
                "NamedQueryId": {"shape": "NamedQueryId"},
                "QueryString": {"shape": "QueryString"},
            },
            "required": ["Name", "Database", "QueryString"],
            "type": "structure",
        },
        "NamedQueryId": {"type": "string"},
        "NamedQueryIdList": {
            "member": {"shape": "NamedQueryId"},
            "type": "list",
        },
        "QueryString": {"type": "string"},
        "Token": {"type": "string"},
    },
}


class TestCanGenerateCompletions(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        self.service_model = ServiceModel(BASIC_MODEL)
        self.heuristic = ServerCompletionHeuristic()

    def test_can_generate_resource_descriptions(self):
        resources = self.heuristic.generate_completion_descriptions(
            self.service_model)['resources']
        self.assertEqual(
            resources, {
                'Certificate': {
                    'operation': 'ListCertificates',
                    'resourceIdentifier': {
                        'CertificateArn': (
                            'CertificateSummaryList[].CertificateArn')
                    }
                }
             }
        )

    def test_can_generate_operations(self):
        # This model is chosen specifically because there's only
        # one resource we generate.  This makes the assertions easier.
        operations = self.heuristic.generate_completion_descriptions(
            self.service_model)['operations']
        completion_param = {
            'CertificateArn': {
                'completions': [
                    {'parameters': {},
                     'resourceIdentifier': 'CertificateArn',
                     'resourceName': 'Certificate'}
                ]
            }
        }
        self.assertEqual(
            list(sorted(operations)),
            ['DeleteCertificate', 'DescribeCertificate', 'ExportCertificate',
             'GetCertificate', 'ImportCertificate'])
        for op in operations.values():
            self.assertEqual(op, completion_param)

    def test_can_generate_operation_with_describe_prefix(self):
        model = deepcopy(BASIC_MODEL)
        # Swap ListCertificates for DescribeCertificates.
        # We should still be able to generate auto-completion data.
        model['operations']['DescribeCertificates'] = model['operations'].pop(
            'ListCertificates')
        service_model = ServiceModel(model)
        completion_data = self.heuristic.generate_completion_descriptions(
            service_model)
        # Ensure we're using the swapped 'DescribeCertificates' operation.
        self.assertEqual(
             completion_data['resources']['Certificate']['operation'],
            'DescribeCertificates'
        )
        self.assertEqual(
            list(sorted(completion_data['operations'])),
            ['DeleteCertificate', 'DescribeCertificate', 'ExportCertificate',
             'GetCertificate', 'ImportCertificate'])

    def test_can_generate_string_list_completions(self):
        service_model = ServiceModel(MODEL_WITH_STRING_LIST)
        completion_data = self.heuristic.generate_completion_descriptions(
            service_model)
        expected = {
            'version': '1.0',
            'operations': {
                'DeleteNamedQuery': {
                    'NamedQueryId': {
                        'completions': [{'parameters': {},
                                         'resourceIdentifier': 'NamedQueryId',
                                         'resourceName': 'NamedQuery'}]}},
                'GetNamedQuery': {
                    'NamedQueryId': {
                        'completions': [{'parameters': {},
                                         'resourceIdentifier': 'NamedQueryId',
                                         'resourceName': 'NamedQuery'}]}}
            },
            'resources': {
                'NamedQuery': {'operation': 'ListNamedQueries',
                               'resourceIdentifier': {
                                   'NamedQueryId': 'NamedQueryIds[]'}}}
        }
        self.assertEqual(completion_data, expected)

    def test_resources_map_input_params_for_required_inputs(self):
        model_dict = deepcopy(BASIC_MODEL)
        # We're going to mark an input param of ListCertificates as required.
        model_dict['shapes']['ListCertificatesRequest']['required'] = [
            'CertificateStatuses']
        # We also have to have an operation reference this
        service_model = ServiceModel(model_dict)
        completion_data = self.heuristic.generate_completion_descriptions(
            service_model, prune_completions=False)
        resources = completion_data['resources']
        self.assertEqual(
            resources, {
                'Certificate': {
                    'operation': 'ListCertificates',
                    'inputParameters': ['CertificateStatuses'],
                    'resourceIdentifier': {
                        'CertificateArn': (
                            'CertificateSummaryList[].CertificateArn'),
                        'DomainName': (
                            'CertificateSummaryList[].DomainName'
                        )
                    }
                }
             }
        )

    def test_remove_operations_with_required_params(self):
        # We can remove this test once we implement this functionality.
        custom_model = {
            'metadata': {},
            'operations': {
                'ListFooBarThings': {
                    'input': {'shape': 'ListFooBarThingsRequest'},
                    'output': {'shape': 'ListFooBarThingsResponse'},
                },
                'DeleteFooBarThing': {
                    'input': {'shape': 'DeleteFooBarThingRequest'},
                }
            },
            'shapes': {
                'DeleteFooBarThingRequest': {
                    'type': 'structure',
                    'members': {
                        'RequiredParam': {'shape': 'String'},
                        'FooBarThing': {'shape': 'String'},
                    }
                },
                'ListFooBarThingsRequest': {
                    'members': {
                        'RequiredParam': {'shape': 'String'},
                    },
                    'type': 'structure',
                    'required': ['RequiredParam'],
                },
                'ListFooBarThingsResponse': {
                    'type': 'structure',
                    'members': {
                        'FooBarThings': {'shape': 'FooBarThingList'},
                    }
                },
                'FooBarThingList': {
                    'type': 'list',
                    'member': {'shape': 'String'}
                },
                'String': {'type': 'string'},
            }
        }
        service_model = ServiceModel(custom_model)
        completion_data = self.heuristic.generate_completion_descriptions(
            service_model)
        # The operations dict should be empty because the FooBarThing has
        # a required parameter and we don't support that yet.
        self.assertEqual(completion_data['operations'], {})

    def test_can_reference_multiple_identifiers_if_used(self):
        custom_model = {
            'metadata': {},
            'operations': {
                'ListFooBarThings': {
                    'output': {'shape': 'ListFooBarThingsResponse'},
                },
                'DeleteFooBarThing': {
                    'input': {'shape': 'DeleteFooBarThingRequest'},
                }
            },
            'shapes': {
                'DeleteFooBarThingRequest': {
                    'type': 'structure',
                    'members': {
                        'FooBarThingId': {'shape': 'String'},
                        'FooBarThingArn': {'shape': 'String'},
                    }
                },
                'ListFooBarThingsResponse': {
                    'type': 'structure',
                    'members': {
                        'FooBarThings': {'shape': 'FooBarThingList'},
                    }
                },
                'FooBarThingList': {
                    'type': 'list',
                    'member': {'shape': 'FooBarThingType'},
                },
                'FooBarThingType': {
                    'type': 'structure',
                    'members': {
                        # The DeleteFooBarThing accepts either an Id
                        # or an Arn.
                        'FooBarThingId': {'shape': 'String'},
                        'FooBarThingArn': {'shape': 'String'},
                        # However it doesn't accept a "Name", so this
                        # identifier will be pruned from the response.
                        'FooBarThingPruneId': {'shape': 'String'},
                    }
                },
                'String': {'type': 'string'},
            }
        }
        service_model = ServiceModel(custom_model)
        completion_data = self.heuristic.generate_completion_descriptions(
            service_model)
        self.assertEqual(
            completion_data['resources'],
             {'FooBarThing': {
                 'operation': 'ListFooBarThings',
                 'resourceIdentifier': {
                     'FooBarThingArn': 'FooBarThings[].FooBarThingArn',
                     'FooBarThingId': 'FooBarThings[].FooBarThingId'
                 }}
             }
        )
