**To delete imported key material from a KMS key**

The following ``delete-imported-key-material`` example deletes key material that had been imported into a KMS key. ::

    aws kms delete-imported-key-material \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111


Output::

    {
        "KeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "KeyMaterialId": "0b7fd7ddbac6eef27907413567cad8c810e2883dc8a7534067a82ee1142fc1e6"
    }

For more information, see `Deleting imported key material <https://docs.aws.amazon.com/kms/latest/developerguide/importing-keys-delete-key-material.html>`__ in the *AWS Key Management Service Developer Guide*.