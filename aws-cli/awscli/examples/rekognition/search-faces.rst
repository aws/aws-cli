**To search for faces in a collection that match a face ID.**

The following ``search-faces`` example searches for faces in a collection that match the specified face ID. ::

    aws rekognition search-faces \
        --face-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --collection-id MyCollection

Output::

    {
        "SearchedFaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "FaceModelVersion": "3.0", 
        "FaceMatches": [
            {
                "Face": {
                    "BoundingBox": {
                        "Width": 0.48166701197624207, 
                        "Top": 0.20999999344348907, 
                        "Left": 0.21250000596046448, 
                        "Height": 0.36125001311302185
                    }, 
                    "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
                    "ExternalImageId": "image1.jpg", 
                    "Confidence": 99.99949645996094, 
                    "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
                }, 
                "Similarity": 99.30997467041016
            }, 
            {
                "Face": {
                    "BoundingBox": {
                        "Width": 0.18562500178813934, 
                        "Top": 0.1618019938468933, 
                        "Left": 0.5575000047683716, 
                        "Height": 0.24770599603652954
                    }, 
                    "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444", 
                    "ExternalImageId": "example-image.jpg", 
                    "Confidence": 99.99340057373047, 
                    "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555"
                }, 
                "Similarity": 99.24862670898438
            }, 
            {
                "Face": {
                    "BoundingBox": {
                        "Width": 0.18562500178813934, 
                        "Top": 0.1618019938468933, 
                        "Left": 0.5575000047683716, 
                        "Height": 0.24770599603652954
                    }, 
                    "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666", 
                    "ExternalImageId": "image3.jpg", 
                    "Confidence": 99.99340057373047, 
                    "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777"
                }, 
                "Similarity": 99.24862670898438
            }, 
            {
                "Face": {
                    "BoundingBox": {
                        "Width": 0.5349419713020325, 
                        "Top": 0.29124999046325684, 
                        "Left": 0.16389399766921997, 
                        "Height": 0.40187498927116394
                    }, 
                    "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE88888", 
                    "ExternalImageId": "image9.jpg", 
                    "Confidence": 99.99979400634766, 
                    "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE99999"
                }, 
                "Similarity": 96.73158264160156
            }
        ]
    }

For more information, see `Searching for a Face Using Its Face ID <https://docs.aws.amazon.com/rekognition/latest/dg/search-face-with-id-procedure.html>`__ in the *Amazon Rekognition Developer Guide*.
