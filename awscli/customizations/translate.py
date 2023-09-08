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
import copy

from awscli.arguments import CustomArgument, CLIArgument
from awscli.customizations.binaryhoist import (
    BinaryBlobArgumentHoister,
    ArgumentParameters,
)

FILE_DOCSTRING = (
    "<p>The path to the file of the code you are uploading. "
    "Example: fileb://data.csv</p>"
)
FILE_ERRORSTRING = (
    "File cannot be provided as part of the "
    "'--terminology-data' argument. Please use the "
    "'--data-file' option instead to specify a "
    "file."
)

DOCUMENT_DOCSTRING = (
    "<p>The path to a file of the content you are uploading "
    "Example: fileb://data.txt</p>"
)
DOCUMENT_ERRORSTRING = (
    "Content cannot be provided as a part of the "
    "'--document' argument. Please use the '--document-content' option instead "
    "to specify a file."
)


def register_translate_import_terminology(cli):
    cli.register(
        "building-argument-table.translate.import-terminology",
        BinaryBlobArgumentHoister(
            new_argument=ArgumentParameters(
                name="data-file",
                help_text=FILE_DOCSTRING,
                required=True,
            ),
            original_argument=ArgumentParameters(
                name="terminology-data",
                member="File",
                required=False,
            ),
            error_if_original_used=FILE_ERRORSTRING,
        ),
    ),

    cli.register(
        "building-argument-table.translate.translate-document",
        BinaryBlobArgumentHoister(
            new_argument=ArgumentParameters(
                name="document-content",
                help_text=DOCUMENT_DOCSTRING,
                required=True,
            ),
            original_argument=ArgumentParameters(
                name="document",
                member="Content",
                required=True,
            ),
            error_if_original_used=DOCUMENT_ERRORSTRING,
        ),
    )
