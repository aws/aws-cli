# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestUpdateCustomVerificationEmailTemplate(BaseAWSCommandParamsTest):
    prefix = 'sesv2 update-custom-verification-email-template'
    template_name = 'test-template-name'
    from_email_address = 'from@example.com'
    template_subject = 'template-subject'
    template_content = 'template-content'
    success_redirection_url = 'https://aws.amazon.com/ses/verifysuccess'
    failure_redirection_url = 'https://aws.amazon.com/ses/verifyfailure'

    def test_update_custom_verification_email_template(self):
        cmdline = self.prefix
        cmdline += ' --template-name ' + self.template_name
        cmdline += ' --from-email-address ' + self.from_email_address
        cmdline += ' --template-subject ' + self.template_subject
        cmdline += ' --template-content ' + self.template_content
        cmdline += ' --success-redirection-url ' + self.success_redirection_url
        cmdline += ' --failure-redirection-url ' + self.failure_redirection_url

        result = {
            'TemplateName': self.template_name,
            'FromEmailAddress': self.from_email_address,
            'TemplateSubject': self.template_subject,
            'TemplateContent': self.template_content,
            'SuccessRedirectionURL': self.success_redirection_url,
            'FailureRedirectionURL': self.failure_redirection_url
        }
        self.assert_params_for_cmd(cmdline, result)
