**To delete faces from a collection**

The following ``delete-faces`` example deletes the specified face from a collection. ::

    aws rekognition delete-faces \
        --collection-id MyCollection \
        --face-ids '["a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"]'

Output::

    {
        "DeletedFaces": [
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        ]
    }

For more information, see `Deleting Faces from a Collection <https://docs.aws.amazon.com/rekognition/latest/dg/delete-faces-procedure.html>`__ in the *Amazon Rekognition Developer Guide*.
