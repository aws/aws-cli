# Copyright 2012-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


TAGS = "Tags to associate with the new product."

BUCKET_NAME = ("Name of the S3 bucket name where the CloudFormation "
               "template will be uploaded to")

SUPPORT_DESCRIPTION = "Support information about the product"

SUPPORT_EMAIL = "Contact email for product support"

PA_NAME = "The name assigned to the provisioning artifact"

PA_DESCRIPTION = "The text description of the provisioning artifact"

PA_TYPE = "The type of the provisioning artifact"

DISTRIBUTOR = "The distributor of the product"

PRODUCT_ID = "The product identifier"

PRODUCT_NAME = "The name of the product"

OWNER = "The owner of the product"

PRODUCT_TYPE = "The type of the product to create"

PRODUCT_DESCRIPTION = "The text description of the product"

PRODUCT_COMMAND_DESCRIPTION = ("Create a new product using a CloudFormation "
                               "template specified as a local file path")

PA_COMMAND_DESCRIPTION = ("Create a new provisioning artifact for the "
                          "specified product using a CloudFormation template "
                          "specified as a local file path")

GENERATE_COMMAND = ("Generate a Service Catalog product or provisioning "
                    "artifact using a CloudFormation template specified "
                    "as a local file path")

FILE_PATH = "A local file path that references the CloudFormation template"
