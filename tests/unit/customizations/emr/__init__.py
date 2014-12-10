# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.customizations.preview import mark_as_preview


class EMRBaseAWSCommandParamsTest(BaseAWSCommandParamsTest):
    """EMR specific test class.

    This class will take EMR out of preview mode before running tests.
    This class won't be necessary when EMR is taken out of preview mode.

    """
    def setUp(self):
        super(EMRBaseAWSCommandParamsTest, self).setUp()
        # We actually will just disable preview mode completely.
        self.driver.session.unregister('building-command-table.main',
                                       mark_as_preview)
