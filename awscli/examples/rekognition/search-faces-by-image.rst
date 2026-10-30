**To search for faces in a collection that match the largest face in an image.**

The following ``search-faces-by-image`` example searches for faces in a collection that match the largest face in the specified image. ::

    aws rekognition search-faces-by-image \
        --image '{"S3Object":{"Bucket":"amzn-s3-demo-bucket","Name":"ExamplePerson.jpg"}}' \
        --collection-id MyFaceImageCollection

Output::

    {
        "SearchedFaceBoundingBox": {
            "Width": 0.18562500178813934, 
            "Top": 0.1618015021085739, 
            "Left": 0.5575000047683716, 
            "Height": 0.24770642817020416
        }, 
        "SearchedFaceConfidence": 99.993408203125, 
        "FaceMatches": [
            {
                "Face": {
                    "BoundingBox": {
                        "Width": 0.18562500178813934, 
                        "Top": 0.1618019938468933, 
                        "Left": 0.5575000047683716, 
                        "Height": 0.24770599603652954
                    }, 
                    "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                    "ExternalImageId": "example-image.jpg", 
                    "Confidence": 99.99340057373047, 
                    "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
                }, 
                "Similarity": 99.97913360595703
            }, 
            {
                "Face": {
                    "BoundingBox": {
                        "Width": 0.18562500178813934, 
                        "Top": 0.1618019938468933, 
                        "Left": 0.5575000047683716, 
                        "Height": 0.24770599603652954
                    }, 
                    "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333", 
                    "ExternalImageId": "image3.jpg", 
                    "Confidence": 99.99340057373047, 
                    "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
                }, 
                "Similarity": 99.97913360595703
            }, 
            {
                "Face": {
                    "BoundingBox": {
                        "Width": 0.41499999165534973, 
                        "Top": 0.09187500178813934, 
                        "Left": 0.28083300590515137, 
                        "Height": 0.3112500011920929
                    }, 
                    "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555", 
                    "ExternalImageId": "image2.jpg", 
                    "Confidence": 99.99769592285156, 
                    "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
                }, 
                "Similarity": 99.18069458007812
            }, 
            {
                "Face": {
                    "BoundingBox": {
                        "Width": 0.48166701197624207, 
                        "Top": 0.20999999344348907, 
                        "Left": 0.21250000596046448, 
                        "Height": 0.36125001311302185
                    }, 
                    "FaceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777", 
                    "ExternalImageId": "image1.jpg", 
                    "Confidence": 99.99949645996094, 
                    "ImageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE88888"
                }, 
                "Similarity": 98.66607666015625
            }
        ], 
        "FaceModelVersion": "3.0"
    }

For more information, see `Searching for a Face Using an Image <https://docs.aws.amazon.com/rekognition/latest/dg/search-face-with-image-procedure.html>`__ in the *Amazon Rekognition Developer Guide*.
