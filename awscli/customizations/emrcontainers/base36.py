# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class Base36(object):
    def str_to_int(self, request):
        """Method to convert given string into decimal representation"""
        result = 0
        for char in request:
            result = result * 256 + ord(char)

        return result

    def encode(self, request):
        """Method to return base36 encoded form of the input string"""
        decimal_number = self.str_to_int(str(request))
        alphabet, base36 = ['0123456789abcdefghijklmnopqrstuvwxyz', '']

        while decimal_number:
            decimal_number, i = divmod(decimal_number, 36)
            base36 = alphabet[i] + base36

        return base36 or alphabet[0]
