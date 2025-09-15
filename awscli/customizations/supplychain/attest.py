# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import json
import sys
import base64
from datetime import datetime

from awscli.customizations.commands import BasicCommand
from awscli.customizations.supplychain.utils import (
    get_signer_client, get_kms_client, validate_resource_arn,
    create_kms_signing_key, sign_with_kms, sign_with_x509,
    create_jws_envelope, create_dsse_envelope
)


class AttestCommand(BasicCommand):
    NAME = 'attest'

    DESCRIPTION = (
        "Create and manage cryptographic attestations for software artifacts. "
        "This command supports signing with AWS KMS, X.509 certificates, or "
        "creating unsigned attestations. Attestations follow the in-toto "
        "specification and can be output in multiple formats including JWS and DSSE."
    )

    ARG_TABLE = [
        {
            'name': 'resource-arn',
            'help_text': "The ARN of the resource to create an attestation for",
            'required': True
        },
        {
            'name': 'predicate-type',
            'help_text': "The type of attestation predicate",
            'required': True,
            'choices': ['slsa-provenance', 'vulnerability-scan', 'sbom', 'custom']
        },
        {
            'name': 'predicate-file',
            'help_text': "Path to a file containing the predicate data",
            'required': False
        },

        # Signing Options
        {
            'name': 'sign',
            'action': 'store_true',
            'help_text': "Sign the attestation (requires --kms-key-id or --x509-cert)"
        },

        # KMS Signing Options
        {
            'name': 'kms-key-id',
            'help_text': (
                "KMS key ID or ARN for signing. Use 'generate' to create a new key"
            ),
            'required': False
        },
        {
            'name': 'kms-key-alias',
            'help_text': (
                "Alias for newly generated KMS key (used with --kms-key-id generate)"
            ),
            'required': False
        },
        {
            'name': 'signing-algorithm',
            'help_text': "KMS signing algorithm",
            'default': 'RSASSA_PSS_SHA_256',
            'choices': [
                'RSASSA_PSS_SHA_256', 'RSASSA_PSS_SHA_384', 'RSASSA_PSS_SHA_512',
                'RSASSA_PKCS1_V1_5_SHA_256', 'RSASSA_PKCS1_V1_5_SHA_384',
                'RSASSA_PKCS1_V1_5_SHA_512', 'ECDSA_SHA_256', 'ECDSA_SHA_384'
            ]
        },

        # X.509 Certificate Signing Options
        {
            'name': 'x509-cert',
            'help_text': "Path to X.509 certificate file (PEM format) for signing",
            'required': False
        },
        {
            'name': 'x509-key',
            'help_text': "Path to private key file (PEM format) for X.509 signing",
            'required': False
        },
        {
            'name': 'x509-key-password',
            'help_text': "Password for encrypted private key file",
            'required': False
        },

        # Legacy AWS Signer support (optional)
        {
            'name': 'signing-profile',
            'help_text': "The AWS Signer profile to use for signing",
            'required': False
        },

        # Output Options
        {
            'name': 'output',
            'help_text': "Output file for the attestation",
            'required': False
        },
        {
            'name': 'output-signature',
            'help_text': "Separate file to save the signature",
            'required': False
        },
        {
            'name': 'output-format',
            'help_text': "Output format for signed attestation",
            'default': 'json',
            'choices': ['json', 'jws', 'dsse']
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        try:
            # Create attestation structure
            attestation = {
                "_type": "https://in-toto.io/Statement/v0.1",
                "predicateType": f"https://slsa.dev/{parsed_args.predicate_type}/v0.1",
                "subject": [{
                    "name": parsed_args.resource_arn,
                    "digest": {"sha256": "placeholder"}  # In production, compute actual digest
                }],
                "predicate": {}
            }

            # Load predicate data if provided
            if parsed_args.predicate_file:
                with open(parsed_args.predicate_file, 'r') as f:
                    attestation['predicate'] = json.load(f)
            else:
                # Create basic predicate
                attestation['predicate'] = self._create_default_predicate(parsed_args)

            # Convert to JSON string for signing (canonical JSON)
            attestation_json = json.dumps(attestation, indent=2, sort_keys=True)

            # Handle signing if requested
            signature = None
            signing_info = {}

            if parsed_args.sign:
                if parsed_args.kms_key_id:
                    signature, signing_info = self._sign_with_kms(
                        attestation_json, parsed_args, parsed_globals
                    )
                elif parsed_args.x509_cert:
                    if not parsed_args.x509_key:
                        sys.stderr.write(
                            "Error: --x509-cert requires --x509-key\n"
                        )
                        return 1
                    signature, signing_info = self._sign_with_x509(
                        attestation_json, parsed_args
                    )
                elif parsed_args.signing_profile:
                    # Legacy AWS Signer support (future enhancement)
                    sys.stderr.write(
                        "AWS Signer profiles not yet implemented. "
                        "Use --kms-key-id or --x509-cert\n"
                    )
                    return 1
                else:
                    sys.stderr.write(
                        "Error: --sign requires either --kms-key-id or --x509-cert\n"
                    )
                    return 1

            # Format output based on requested format
            if parsed_args.output_format == 'jws' and signature:
                output = json.dumps(create_jws_envelope(
                    attestation_json,
                    signature,
                    cert_chain=signing_info.get('cert_chain'),
                    key_id=signing_info.get('key_id')
                ), indent=2)
            elif parsed_args.output_format == 'dsse' and signature:
                output = json.dumps(create_dsse_envelope(
                    "application/vnd.in-toto+json",
                    attestation_json,
                    [{
                        "sig": signature,
                        "keyid": signing_info.get('key_id', '')
                    }]
                ), indent=2)
            else:
                # Standard JSON format
                if signature:
                    attestation['signatures'] = [{
                        'keyid': signing_info.get('key_id', ''),
                        'sig': signature,
                        'algorithm': signing_info.get('algorithm', '')
                    }]
                output = json.dumps(attestation, indent=2)

            # Save signature separately if requested
            if parsed_args.output_signature and signature:
                with open(parsed_args.output_signature, 'w') as f:
                    f.write(signature)
                sys.stdout.write(
                    f"Signature written to {parsed_args.output_signature}\n"
                )

            # Output attestation
            if parsed_args.output:
                with open(parsed_args.output, 'w') as f:
                    f.write(output)
                sys.stdout.write(f"Attestation written to {parsed_args.output}\n")
            else:
                sys.stdout.write(output)
                sys.stdout.write("\n")

            return 0

        except Exception as e:
            sys.stderr.write(f"Error creating attestation: {str(e)}\n")
            return 1

    def _create_default_predicate(self, parsed_args):
        """Create a default predicate based on type"""
        return {
            "buildType": "aws-cli-supplychain",
            "builder": {"id": "aws-cli"},
            "invocation": {
                "configSource": {"uri": parsed_args.resource_arn},
                "parameters": {},
                "environment": {}
            },
            "metadata": {
                "buildStartedOn": datetime.utcnow().isoformat() + 'Z',
                "buildFinishedOn": datetime.utcnow().isoformat() + 'Z',
                "completeness": {"parameters": True, "environment": False},
                "reproducible": False
            }
        }

    def _sign_with_kms(self, message, parsed_args, parsed_globals):
        """Sign attestation using AWS KMS"""
        kms_client = get_kms_client(self._session, parsed_globals)

        # Generate new key if requested
        if parsed_args.kms_key_id == 'generate':
            sys.stdout.write("Generating new KMS signing key...\n")
            key_id = create_kms_signing_key(
                kms_client,
                alias=parsed_args.kms_key_alias,
                description=f"Supply Chain Attestation Key for {parsed_args.resource_arn}"
            )
            sys.stdout.write(f"Created KMS key: {key_id}\n")
            if parsed_args.kms_key_alias:
                alias = parsed_args.kms_key_alias
                if not alias.startswith('alias/'):
                    alias = f'alias/{alias}'
                sys.stdout.write(f"Created alias: {alias}\n")
        else:
            key_id = parsed_args.kms_key_id

        # Sign the attestation
        signature = sign_with_kms(
            kms_client,
            key_id,
            message,
            parsed_args.signing_algorithm
        )

        return signature, {
            'key_id': key_id,
            'algorithm': parsed_args.signing_algorithm,
            'type': 'kms'
        }

    def _sign_with_x509(self, message, parsed_args):
        """Sign attestation using X.509 certificate"""
        signature = sign_with_x509(
            parsed_args.x509_cert,
            parsed_args.x509_key,
            message,
            parsed_args.x509_key_password
        )

        # Read certificate for metadata
        with open(parsed_args.x509_cert, 'r') as f:
            cert_content = f.read()
            # Remove PEM headers for cert chain
            cert_lines = cert_content.split('\n')
            cert_body = ''.join([
                line for line in cert_lines
                if not line.startswith('-----')
            ])

        return signature, {
            'cert_chain': [cert_body],
            'type': 'x509',
            'algorithm': 'RS256'
        }