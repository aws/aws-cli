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

from awscli.customizations.arguments import NestedBlobArgumentHoister

_ASSET_BUNDLE_FILE_DOCSTRING = (
    '<p>The content of the asset bundle to be uploaded. '
    'To specify the content of a local file use the '
    'fileb:// prefix. Example: fileb://asset-bundle.zip</p>')

_ASSET_BUNDLE_DOCSTRING_ADDENDUM = (
    '<p>To specify a local file use '
    '<code>--asset-bundle-import-source-bytes</code> instead.</p>')


def register_quicksight_asset_bundle_customizations(cli):
    cli.register(
        'building-argument-table.quicksight.start-asset-bundle-import-job',
        NestedBlobArgumentHoister(
            source_arg='asset-bundle-import-source',
            source_arg_blob_member='Body',
            new_arg='asset-bundle-import-source-bytes',
            new_arg_doc_string=_ASSET_BUNDLE_FILE_DOCSTRING,
            doc_string_addendum=_ASSET_BUNDLE_DOCSTRING_ADDENDUM))
