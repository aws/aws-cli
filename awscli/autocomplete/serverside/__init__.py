# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

# NOTE: This file is imported whenever a user hits TAB.  There should not
# be any expensive imports in this file.  If necessary, use lazy imports
# to ensure we only import heavyweight modules when we know we need them.
from awscli.autocomplete.serverside import servercomp
from awscli.autocomplete.serverside import model
from awscli.autocomplete import db


def create_server_side_completer(index_filename):
    return servercomp.ServerSideCompleter(
        model.DBCompletionLookup(
            db.DatabaseConnection(index_filename)
        ),
        servercomp.LazyClientCreator())
