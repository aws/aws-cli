**Example 1: To download the public key of an asymmetric KMS key**

The following ``get-public-key`` example downloads the public key of an asymmetric KMS key. 

In addition to returning the public key, the output includes information that you need to use the public key safely outside of AWS KMS, including the key usage and supported encryption algorithms. ::

    aws kms get-public-key \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "KeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "PublicKey": "jANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAl5epvg1/QtJhxSi2g9SDEVg8QV/...",
        "CustomerMasterKeySpec": "RSA_4096",
        "KeyUsage": "ENCRYPT_DECRYPT",
        "EncryptionAlgorithms": [
            "RSAES_OAEP_SHA_1",
            "RSAES_OAEP_SHA_256"
        ]
    }

For more information about using asymmetric KMS keys in AWS KMS, see `Asymmetric keys in AWS KMS <https://docs.aws.amazon.com/kms/latest/developerguide/symmetric-asymmetric.html>`__ in the *AWS Key Management Service Developer Guide*.
**Example 2: To convert a public key to DER format (Linux and macOS)**

The following ``get-public-key`` example downloads the public key of an asymmetric KMS key and saves it in a DER file.

When you use the ``get-public-key`` command in the AWS CLI, it returns a DER-encoded X.509 public key that is Base64-encoded. This example gets the value of the ``PublicKey`` property as text. It Base64-decodes the ``PublicKey`` and saves it in the ``public_key.der`` file. The ``output`` parameter returns the output as text, instead of JSON. The ``--query`` parameter gets only the ``PublicKey`` property, not the properties that you need to use the public key safely outside of AWS KMS. 

Before running this command, replace the example key ID with a valid key ID from your AWS account. ::

    aws kms get-public-key \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --output text \
        --query PublicKey | base64 --decode > public_key.der

This command produces no output.

For more information about using asymmetric KMS keys in AWS KMS, see `Asymmetric keys in AWS KMS <https://docs.aws.amazon.com/kms/latest/developerguide/symmetric-asymmetric.html>`__ in the *AWS Key Management Service Developer Guide*.