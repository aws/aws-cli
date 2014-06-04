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


from awscli.arguments import CustomArgument
from awscli.customizations.emr import helptext
from awscli.customizations.emr import emrutils


def modify_tags_argument(argument_table, **kwargs):
    argument_table['tags'] = TagsArgument('tags', required=True,
                                          help_text=helptext.TAGS, nargs='+')


class TagsArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        parameters['Tags'] = emrutils.parse_tags(value)