# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/

# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import sys
import six

if six.PY3:
    def get_stdout_text_writer():
        return sys.stdout
else:
    import codecs
    import locale
    def get_stdout_text_writer():
        # In python3, all the sys.stdout/sys.stderr streams are in text
        # mode.  This means they expect unicode, and will encode the
        # unicode automatically before actually writing to stdout/stderr.
        # In python2, that's not the case.  In order to provide a consistent
        # interface, we can create a wrapper around sys.stdout that will take
        # unicode, and automatically encode it to the preferred encoding.
        # That way consumers can just call get_stdout_text_writer() and write
        # unicode to the returned stream.  Note that get_stdout_text_writer
        # just returns sys.stdout in the PY3 section above because python3
        # handles this.
        return codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
