**To derive a shared secret**

The following ``derive-shared-secret`` example derives a shared secret using a key agreement algorithm.

You must use an asymmetric NIST-recommended elliptic curve (ECC) or SM2 (China Regions only) KMS key pair with a ``KeyUsage`` value of ``KEY_AGREEMENT`` to call DeriveSharedSecret. ::

    aws kms derive-shared-secret \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --key-agreement-algorithm ECDH \
        --public-key "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvH3Yj0wbkLEpUl95Cv1cJVjsVNSjwGq3tCLnzXfhVwVvmzGN8pYj3U8nKwgouaHbBWNJYjP5VutbbkKS4Kv4GojwZBJyHN17kmxo8yTjRmjR15SKIQ8cqRA2uaERMLnpztIXdZp232PQPbWGxDyXYJ0aJ5EFSag"

Output::

    {
        "KeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "SharedSecret": "MEYCIQCKZLWyTk5runarx6XiAkU9gv3lbwPO/pHa+DXFehzdDwIhANwpsIV2g/9SPWLLsF6p/hiSskuIXMTRwqrMdVKWTMHG",
        "KeyAgreementAlgorithm": "ECDH",
        "KeyOrigin": "AWS_KMS"
    }

For more information, see `AWS KMS cryptography essentials <https://docs.aws.amazon.com/kms/latest/developerguide/kms-cryptography.html#asymmetric-key-ops>`__ in the *AWS Key Management Service Developer Guide*.