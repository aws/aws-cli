The following command retrieves a list of distributions::

  aws cloudfront list-distributions

Output::

  {
      "DistributionList": {
          "Marker": "",
          "Items": [
              {
                  "Status": "Deployed",
                  "ARN": "arn:aws:cloudfront::123456789012:distribution/EDFDVBD632BHDS5",
                  "CacheBehaviors": {
                      "Quantity": 0
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
                  "DomainName": "d2wkuj2w9l34gt.cloudfront.net",
                  "PriceClass": "PriceClass_All",
                  "Enabled": true,
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
                  "Comment": "",
                  "ViewerCertificate": {
                      "CloudFrontDefaultCertificate": true,
                      "MinimumProtocolVersion": "SSLv3"
                  },
                  "CustomErrorResponses": {
                      "Quantity": 0
                  },
                  "LastModifiedTime": "2015-08-31T21:11:29.093Z",
                  "Id": "S11A16G5KZMEQD",
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
          ],
          "IsTruncated": false,
          "MaxItems": 100,
          "Quantity": 1
      }
  }