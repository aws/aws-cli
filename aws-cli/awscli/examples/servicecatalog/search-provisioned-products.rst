**To search provisioned products**

The following ``search-provisioned-products`` example searches for provisioned products matching the specified product ID, using a JSON file to pass parameters. ::

    aws servicecatalog search-provisioned-products \
        --cli-input-json file://search-provisioned-products-input.json

Contents of ``search-provisioned-products-input.json``::

    {
        "Filters": {
            "SearchQuery": [
                "prod-tcjvfz3syn2rg"
            ]
        }
    }

Output::

    {
        "ProvisionedProducts": [
            {
                "ProvisioningArtifactId": "pa-pcz347abcdcfm",
                "Name": "mytestppname3",
                "CreatedTime": 1577222793.358,
                "Id": "pp-abcd27bm4mldq",
                "Status": "ERROR",
                "UserArn": "arn:aws:iam::123456789012:user/cliuser",
                "StatusMessage": "AmazonCloudFormationException  Parameters: [KeyName] must have values (Service: AmazonCloudFormation; Status Code: 400; Error Code: ValidationError; Request ID: a1b2c3d4-5678-90ab-cdef-EXAMPLE11111)",
                "Arn": "arn:aws:servicecatalog:us-west-2:123456789012:stack/mytestppname3/pp-abcd27bm4mldq",
                "Tags": [
                    {
                        "Value": "arn:aws:catalog:us-west-2:123456789012:product/prod-abcdfz3syn2rg",
                        "Key": "aws:servicecatalog:productArn"
                    },
                    {
                        "Value": "arn:aws:iam::123456789012:user/cliuser",
                        "Key": "aws:servicecatalog:provisioningPrincipalArn"
                    },
                    {
                        "Value": "value-3",
                        "Key": "1234"
                    },
                    {
                        "Value": "pa-pcz347abcdcfm",
                        "Key": "aws:servicecatalog:provisioningArtifactIdentifier"
                    },
                    {
                        "Value": "arn:aws:catalog:us-west-2:123456789012:portfolio/port-2s6abcdq5wdh4",
                        "Key": "aws:servicecatalog:portfolioArn"
                    },
                    {
                        "Value": "arn:aws:servicecatalog:us-west-2:123456789012:stack/mytestppname3/pp-abcd27bm4mldq",
                        "Key": "aws:servicecatalog:provisionedProductArn"
                    }
                ],
                "IdempotencyToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "UserArnSession": "arn:aws:iam::123456789012:user/cliuser",
                "Type": "CFN_STACK",
                "LastRecordId": "rec-tfuawdabcdxge",
                "ProductId": "prod-abcdfz3syn2rg"
            }
        ],
        "TotalResultsCount": 1
    }

For more information, see `Managing Provisioned Products <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/provisioned-products.html>`__ in the *AWS Service Catalog Administrator Guide*.
