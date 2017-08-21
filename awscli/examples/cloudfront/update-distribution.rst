The following command updates the Default Root Object to "index.html"
for a CloudFront distribution with the ID ``S11A16G5KZMEQD``::

  aws cloudfront update-distribution --id S11A16G5KZMEQD \
    --default-root-object index.html

The following command disables a CloudFront distribution with the ID ``S11A16G5KZMEQD``::

  aws cloudfront update-distribution --id S11A16G5KZMEQD --distribution-config file://distconfig-disabled.json --if-match E37HOT42DHPVYH

The distribution ID is available in the output of ``create-distribution`` and ``list-distributions``. The ETag value ``E37HOT42DHPVYH`` for the ``if-match`` parameter is available in the output of ``create-distribution``, ``get-distribution`` or ``get-distribution-config``.

The file ``distconfig-disabled.json`` is a JSON document in the current folder that modifies the existing distribution config for ``S11A16G5KZMEQD`` to disable the distribution. This file was created by taking the existing config from the ``DistributionConfig`` key in the output of ``get-distribution-config`` and changing the ``Enabled`` key's value to ``false``::

  {
    "Comment": "",
    "CacheBehaviors": {
        "Quantity": 0
    },
    "Logging": {
        "Bucket": "",
        "Prefix": "",
        "Enabled": false,
        "IncludeCookies": false
    },
    "Origins": {
        "Items": [
            {
                "OriginPath": "",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                },
                "Id": "my-origin",
                "DomainName": "my-bucket.s3.amazonaws.com"
            }
        ],
        "Quantity": 1
    },
    "DefaultRootObject": "",
    "PriceClass": "PriceClass_All",
    "Enabled": false,
    "DefaultCacheBehavior": {
        "TrustedSigners": {
            "Enabled": false,
            "Quantity": 0
        },
        "TargetOriginId": "my-origin",
        "ViewerProtocolPolicy": "allow-all",
        "ForwardedValues": {
            "Headers": {
                "Quantity": 0
            },
            "Cookies": {
                "Forward": "none"
            },
            "QueryString": true
        },
        "MaxTTL": 31536000,
        "SmoothStreaming": false,
        "DefaultTTL": 86400,
        "AllowedMethods": {
            "Items": [
                "HEAD",
                "GET"
            ],
            "CachedMethods": {
                "Items": [
                    "HEAD",
                    "GET"
                ],
                "Quantity": 2
            },
            "Quantity": 2
        },
        "MinTTL": 3600
    },
    "CallerReference": "my-distribution-2015-09-01",
    "ViewerCertificate": {
        "CloudFrontDefaultCertificate": true,
        "MinimumProtocolVersion": "SSLv3"
    },
    "CustomErrorResponses": {
        "Quantity": 0
    },
    "Restrictions": {
        "GeoRestriction": {
            "RestrictionType": "none",
            "Quantity": 0
        }
    },
    "Aliases": {
        "Quantity": 0
    }
  }

After disabling a CloudFront distribution you can delete it with ``delete-distribution``.

The output includes the updated distribution config. Note that the ``ETag`` value has also changed::

  {
      "Distribution": {
          "Status": "InProgress",
          "DomainName": "d2wkuj2w9l34gt.cloudfront.net",
          "InProgressInvalidationBatches": 0,
          "DistributionConfig": {
              "Comment": "",
              "CacheBehaviors": {
                  "Quantity": 0
              },
              "Logging": {
                  "Bucket": "",
                  "Prefix": "",
                  "Enabled": false,
                  "IncludeCookies": false
              },
              "Origins": {
                  "Items": [
                      {
                          "OriginPath": "",
                          "S3OriginConfig": {
                              "OriginAccessIdentity": ""
                          },
                          "Id": "my-origin",
                          "DomainName": "my-bucket.s3.amazonaws.com"
                      }
                  ],
                  "Quantity": 1
              },
              "DefaultRootObject": "",
              "PriceClass": "PriceClass_All",
              "Enabled": false,
              "DefaultCacheBehavior": {
                  "TrustedSigners": {
                      "Enabled": false,
                      "Quantity": 0
                  },
                  "TargetOriginId": "my-origin",
                  "ViewerProtocolPolicy": "allow-all",
                  "ForwardedValues": {
                      "Headers": {
                          "Quantity": 0
                      },
                      "Cookies": {
                          "Forward": "none"
                      },
                      "QueryString": true
                  },
                  "MaxTTL": 31536000,
                  "SmoothStreaming": false,
                  "DefaultTTL": 86400,
                  "AllowedMethods": {
                      "Items": [
                          "HEAD",
                          "GET"
                      ],
                      "CachedMethods": {
                          "Items": [
                              "HEAD",
                              "GET"
                          ],
                          "Quantity": 2
                      },
                      "Quantity": 2
                  },
                  "MinTTL": 3600
              },
              "CallerReference": "my-distribution-2015-09-01",
              "ViewerCertificate": {
                  "CloudFrontDefaultCertificate": true,
                  "MinimumProtocolVersion": "SSLv3"
              },
              "CustomErrorResponses": {
                  "Quantity": 0
              },
              "Restrictions": {
                  "GeoRestriction": {
                      "RestrictionType": "none",
                      "Quantity": 0
                  }
              },
              "Aliases": {
                  "Quantity": 0
              }
          },
          "ActiveTrustedSigners": {
              "Enabled": false,
              "Quantity": 0
          },
          "LastModifiedTime": "2015-09-01T17:54:11.453Z",
          "Id": "S11A16G5KZMEQD"
      },
      "ETag": "8UBQECEJX24ST"
  }
