**To retrieve information about all completed key material rotations**

The following ``list-key-rotations`` example lists information about all completed key material rotations for the specified KMS key. ::

    aws kms list-key-rotations \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Rotations": [
            {
                "KeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "RotationDate": "2024-03-02T10:11:36.564000+00:00",
                "RotationType": "AUTOMATIC"
            },
            {
                "KeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "RotationDate": "2024-04-05T15:14:47.757000+00:00",
                "RotationType": "ON_DEMAND"
            }
        ],
        "Truncated": false
    }

For more information, see `Rotating keys <https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
