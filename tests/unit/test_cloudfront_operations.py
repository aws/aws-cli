#!/usr/bin/env python
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
from tests import BaseEnvVar
import botocore.session

CREATE_DISTRIBUTION_INPUT = {
   "CallerReference": "example.com2012-04-11-5:09pm",
   "Aliases": {
      "Quantity": 1,
      "Items": [
         "www.example.com"
      ]
   },
   "DefaultRootObject": "index.html",
   "Origins": {
      "Quantity": 2,
      "Items": [
         {
           "Id": "example-Amazon S3-origin",
           "DomainName": "myawsbucket.s3.amazonaws.com",
           "S3OriginConfig": {
             "OriginAccessIdentity": "origin-access-identity/cloudfront/E74FTE3AEXAMPLE"
            }
         },
         {
           "Id": "example-custom-origin",
           "DomainName": "example.com",
           "CustomOriginConfig": {
              "HTTPPort": 80,
              "HTTPSPort": 443,
              "OriginProtocolPolicy": "match-viewer"
            }
         }
      ]
   },
   "DefaultCacheBehavior": {
      "TargetOriginId": "example-Amazon S3-origin",
      "ForwardedValues": {
         "QueryString": True,
         "Cookies": {
            "Forward": "whitelist",
            "WhitelistedNames": {
               "Quantity": 1,
               "Items": [
                  "example-cookie"
               ]
            }
         }
      },
      "TrustedSigners": {
         "Enabled": True,
         "Quantity": 3,
         "Items": [
            "self", "111122223333", "444455556666"
         ]
      },
      "ViewerProtocolPolicy": "https-only",
      "MinTTL": 0
   },
   "CacheBehaviors": {
      "Quantity": 1,
      "Items": [
         {
            "PathPattern": "*.jpg",
            "TargetOriginId": "example-custom-origin",
            "ForwardedValues": {
               "QueryString": False,
               "Cookies": {
                  "Forward": "all"
               }
            },
            "TrustedSigners": {
               "Enabled": True,
               "Quantity": 2,
               "Items": ["self", "111122223333"]
            },
            "ViewerProtocolPolicy": "allow-all",
            "MinTTL": 86400
         }
      ]
   },
   "Comment": "example comment",
   "Logging": {
      "Enabled": True,
      "IncludeCookies": True,
      "Bucket": "myawslogbucket.s3.amazonaws.com",
      "Prefix": "example.com"
   },
   "ViewerCertificate": {
      "IAMCertificateId": "AS1A2M3P4L5E67SIIXR3J"
   },
   "PriceClass": "PriceClass_All",
   "Enabled": True
}

CREATE_DISTRIBUTION_PAYLOAD="""
<DistributionConfig>
   <CallerReference>example.com2012-04-11-5:09pm</CallerReference>
   <Aliases>
      <Quantity>1</Quantity>
      <Items>
         <CNAME>www.example.com</CNAME>
      </Items>
   </Aliases>
   <DefaultRootObject>index.html</DefaultRootObject>
   <Origins>
      <Quantity>2</Quantity>
      <Items>
         <Origin>
            <Id>example-Amazon S3-origin</Id>
            <DomainName>myawsbucket.s3.amazonaws.com</DomainName>
            <S3OriginConfig>
               <OriginAccessIdentity>origin-access-identity/cloudfront/E74FTE3AEXAMPLE</OriginAccessIdentity>
            </S3OriginConfig>
         </Origin>
         <Origin>
            <Id>example-custom-origin</Id>
            <DomainName>example.com</DomainName>
            <CustomOriginConfig>
               <HTTPPort>80</HTTPPort>
               <HTTPSPort>443</HTTPSPort>
               <OriginProtocolPolicy>match-viewer</OriginProtocolPolicy>
            </CustomOriginConfig>
         </Origin>
      </Items>
   </Origins>
   <DefaultCacheBehavior>
      <TargetOriginId>example-Amazon S3-origin</TargetOriginId>
      <ForwardedValues>
         <QueryString>true</QueryString>
         <Cookies>
            <Forward>whitelist</Forward>
            <WhitelistedNames>
               <Quantity>1</Quantity>
               <Items>
                  <Name>example-cookie</Name>
               </Items>
            </WhitelistedNames>
         </Cookies>
      </ForwardedValues>
      <TrustedSigners>
         <Enabled>true</Enabled>
         <Quantity>3</Quantity>
         <Items>
            <AwsAccountNumber>self</AwsAccountNumber>
            <AwsAccountNumber>111122223333</AwsAccountNumber>
            <AwsAccountNumber>444455556666</AwsAccountNumber>
         </Items>
      </TrustedSigners>
      <ViewerProtocolPolicy>https-only</ViewerProtocolPolicy>
      <MinTTL>0</MinTTL>
   </DefaultCacheBehavior>
   <CacheBehaviors>
      <Quantity>1</Quantity>
      <Items>
         <CacheBehavior>
            <PathPattern>*.jpg</PathPattern>
            <TargetOriginId>example-custom-origin</TargetOriginId>
            <ForwardedValues>
               <QueryString>false</QueryString>
               <Cookies>
                  <Forward>all</Forward>
               </Cookies>
            </ForwardedValues>
            <TrustedSigners>
               <Enabled>true</Enabled>
               <Quantity>2</Quantity>
               <Items>
                  <AwsAccountNumber>self</AwsAccountNumber>
                  <AwsAccountNumber>111122223333</AwsAccountNumber>
               </Items>
            </TrustedSigners>
            <ViewerProtocolPolicy>allow-all</ViewerProtocolPolicy>
            <MinTTL>86400</MinTTL>
         </CacheBehavior>
      </Items>
   </CacheBehaviors>
   <Comment>example comment</Comment>
   <Logging>
      <Enabled>true</Enabled>
      <IncludeCookies>true</IncludeCookies>
      <Bucket>myawslogbucket.s3.amazonaws.com</Bucket>
      <Prefix>example.com</Prefix>
   </Logging>
   <PriceClass>PriceClass_All</PriceClass>
   <Enabled>true</Enabled>
   <ViewerCertificate>
      <IAMCertificateId>AS1A2M3P4L5E67SIIXR3J</IAMCertificateId>
   </ViewerCertificate>
</DistributionConfig>
"""

CREATE_ORIGIN_ACCESS_IDENTITY_INPUT = {
   "CallerReference": "20120229090000",
   "Comment": "My comments"
   }

CREATE_ORIGIN_ACCESS_IDENTITY_PAYLOAD = """
<CloudFrontOriginAccessIdentityConfig>  
   <CallerReference>20120229090000</CallerReference>
   <Comment>My comments</Comment>
</CloudFrontOriginAccessIdentityConfig>"""

CREATE_INVALIDATION_INPUT = {
   "Paths": {
      "Quantity": 3,
      "Items": [
         "/image1.jpg",
         "/image2.jpg",
         "/videos/movie.flv"
      ]
   },
   "CallerReference": "20120301090001"
}

CREATE_INVALIDATION_PAYLOAD = """
<InvalidationBatch>
   <Paths>
      <Quantity>3</Quantity>
      <Items>
         <Path>/image1.jpg</Path>
         <Path>/image2.jpg</Path>
         <Path>/videos/movie.flv</Path>
      </Items>
   </Paths>
   <CallerReference>20120301090001</CallerReference>
</InvalidationBatch>"""


class TestCloudFrontOperations(BaseEnvVar):

    def setUp(self):
        super(TestCloudFrontOperations, self).setUp()
        self.environ['AWS_ACCESS_KEY_ID'] = 'foo'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'bar'
        self.session = botocore.session.get_session()
        self.cloudfront = self.session.get_service('cloudfront')
        self.endpoint = self.cloudfront.get_endpoint('us-east-1')

    def test_create_distribution(self):
        op = self.cloudfront.get_operation('CreateDistribution2013_05_12')
        params = op.build_parameters(distribution_config=CREATE_DISTRIBUTION_INPUT)
        self.maxDiff = None
        payload = ''.join([s.strip() for s in CREATE_DISTRIBUTION_PAYLOAD.split('\n')])
        self.assertEqual(params['payload'].getvalue(), payload)

    def test_delete_distribution(self):
        op = self.cloudfront.get_operation('DeleteDistribution2013_05_12')
        params = op.build_parameters(id='IDFDVBD632BHDS5',
                                     if_match='2QWRUHAPOMQZL')
        self.assertIn('Id', params['uri_params'])
        self.assertEqual(params['uri_params']['Id'], 'IDFDVBD632BHDS5')
        self.assertIn('If-Match', params['headers'])
        self.assertEqual(params['headers']['If-Match'], '2QWRUHAPOMQZL')

    def test_create_origin_access_identity_distribution(self):
        op = self.cloudfront.get_operation('CreateCloudFrontOriginAccessIdentity2013_05_12')
        params = op.build_parameters(cloud_front_origin_access_identity_config=CREATE_ORIGIN_ACCESS_IDENTITY_INPUT)
        self.maxDiff = None
        payload = ''.join([s.strip() for s in CREATE_ORIGIN_ACCESS_IDENTITY_PAYLOAD.split('\n')])
        self.assertEqual(params['payload'].getvalue(), payload)

    def test_delete_origin_access_identity(self):
        op = self.cloudfront.get_operation('DeleteCloudFrontOriginAccessIdentity2013_05_12')
        params = op.build_parameters(id='IDFDVBD632BHDS5',
                                     if_match='2QWRUHAPOMQZL')
        self.assertIn('Id', params['uri_params'])
        self.assertEqual(params['uri_params']['Id'], 'IDFDVBD632BHDS5')
        self.assertIn('If-Match', params['headers'])
        self.assertEqual(params['headers']['If-Match'], '2QWRUHAPOMQZL')

    def test_create_invalidation(self):
        op = self.cloudfront.get_operation('CreateInvalidation2013_05_12')
        params = op.build_parameters(distribution_id='IDFDVBD632BHDS5',
                                     invalidation_batch=CREATE_INVALIDATION_INPUT)
        self.maxDiff = None
        payload = ''.join([s.strip() for s in CREATE_INVALIDATION_PAYLOAD.split('\n')])
        self.assertEqual(params['payload'].getvalue(), payload)
        self.assertEqual(params['uri_params'],
                         {'DistributionId': 'IDFDVBD632BHDS5'})


if __name__ == "__main__":
    unittest.main()
