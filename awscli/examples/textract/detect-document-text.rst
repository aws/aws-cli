**To detect text in a document**

The following ``detect-document-text`` example shows how to detect text in a document.

For Linux and macOS, use the following command. ::

    aws textract detect-document-text \
        --document '{"S3Object":{"Bucket":"amzn-s3-demo-bucket","Name":"document"}}'

For Windows, use the following command. ::

    aws textract detect-document-text \
        --document "{\"S3Object\":{\"Bucket\":\"amzn-s3-demo-bucket\",\"Name\":\"document\"}}"

Output::

    {
        "Blocks": [
            {
                "Geometry": {
                    "BoundingBox": {
                        "Width": 1.0, 
                        "Top": 0.0, 
                        "Left": 0.0, 
                        "Height": 1.0
                    }, 
                    "Polygon": [
                        {
                            "Y": 0.0, 
                            "X": 0.0
                        }, 
                        {
                            "Y": 0.0, 
                            "X": 1.0
                        }, 
                        {
                            "Y": 1.0, 
                            "X": 1.0
                        }, 
                        {
                            "Y": 1.0, 
                            "X": 0.0
                        }
                    ]
                }, 
                "Relationships": [
                    {
                        "Type": "CHILD", 
                        "Ids": [
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
                        ]
                    } 
                ], 
                "BlockType": "PAGE", 
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            }, 
            {
                "Relationships": [
                    {
                        "Type": "CHILD", 
                        "Ids": [
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555", 
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
                        ]
                    }
                ], 
                "Confidence": 89.11581420898438, 
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.33642634749412537, 
                        "Top": 0.17169663310050964, 
                        "Left": 0.13885067403316498, 
                        "Height": 0.49159330129623413
                    }, 
                    "Polygon": [
                        {
                            "Y": 0.17169663310050964, 
                            "X": 0.13885067403316498
                        }, 
                        {
                            "Y": 0.17169663310050964, 
                            "X": 0.47527703642845154
                        }, 
                        {
                            "Y": 0.6632899641990662, 
                            "X": 0.47527703642845154
                        }, 
                        {
                            "Y": 0.6632899641990662, 
                            "X": 0.13885067403316498
                        }
                    ]
                }, 
                "Text": "He llo,", 
                "BlockType": "LINE", 
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }, 
            {
                "Relationships": [
                    {
                        "Type": "CHILD", 
                        "Ids": [
                            "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777"
                        ]
                    }
                ], 
                "Confidence": 85.5694351196289, 
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.33182239532470703, 
                        "Top": 0.23131252825260162, 
                        "Left": 0.5091826915740967, 
                        "Height": 0.3766750991344452
                    }, 
                    "Polygon": [
                        {
                            "Y": 0.23131252825260162, 
                            "X": 0.5091826915740967
                        }, 
                        {
                            "Y": 0.23131252825260162, 
                            "X": 0.8410050868988037
                        }, 
                        {
                            "Y": 0.607987642288208, 
                            "X": 0.8410050868988037
                        }, 
                        {
                            "Y": 0.607987642288208, 
                            "X": 0.5091826915740967
                        }
                    ]
                }, 
                "Text": "worlc", 
                "BlockType": "LINE", 
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ], 
        "DocumentMetadata": {
            "Pages": 1
        }
    }

For more information, see `Detecting Document Text with Amazon Textract <https://docs.aws.amazon.com/textract/latest/dg/detecting-document-text.html>`__ in the *Amazon Textract Developer Guide*.
