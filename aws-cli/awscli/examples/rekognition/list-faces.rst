**To list the faces in a collection**

The following ``list-faces`` example lists the faces in the specified collection. ::

    aws rekognition list-faces \
        --collection-id MyCollection

Output::

    {
        "FaceModelVersion": "3.0", 
        "Faces": [
            {
                "BoundingBox": {
                    "Width": 0.5216310024261475, 
                    "Top": 0.3256250023841858, 
                    "Left": 0.13394300639629364, 
                    "Height": 0.3918749988079071
                }, 
                "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "ExternalImageId": "image1.jpg", 
                "Confidence": 100.0, 
                "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }, 
            {
                "BoundingBox": {
                    "Width": 0.5074880123138428, 
                    "Top": 0.3774999976158142, 
                    "Left": 0.18302799761295319, 
                    "Height": 0.3812499940395355
                }, 
                "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333", 
                "ExternalImageId": "image2.jpg", 
                "Confidence": 99.99930572509766, 
                "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            }, 
            {
                "BoundingBox": {
                    "Width": 0.5574039816856384, 
                    "Top": 0.37187498807907104, 
                    "Left": 0.14559100568294525, 
                    "Height": 0.4181250035762787
                }, 
                "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555", 
                "ExternalImageId": "image3.jpg", 
                "Confidence": 99.99960327148438, 
                "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
            }, 
            {
                "BoundingBox": {
                    "Width": 0.18562500178813934, 
                    "Top": 0.1618019938468933, 
                    "Left": 0.5575000047683716, 
                    "Height": 0.24770599603652954
                }, 
                "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777", 
                "ExternalImageId": "image4.jpg", 
                "Confidence": 99.99340057373047, 
                "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE88888"
            }
        ]
    }

For more information, see `Listing Faces in a Collection <https://docs.aws.amazon.com/rekognition/latest/dg/list-faces-in-collection-procedure.html>`__ in the *Amazon Rekognition Developer Guide*.
