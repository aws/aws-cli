# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging

from prompt_toolkit.document import Document
from prompt_toolkit.application import get_app


class PromptToolkitHandler(logging.StreamHandler):

    def emit(self, record):
        try:
            app = get_app()
            if app.is_running and getattr(app, 'debug', False):
                msg = self.format(record)
                debug_buffer = app.layout.get_buffer_by_name('debug_buffer')
                current_document = debug_buffer.document.text
                if current_document:
                    msg = '\n'.join([current_document, msg])
                debug_buffer.set_document(
                    Document(text=msg), bypass_readonly=True
                )
            else:
                super().emit(record)
        except:
            self.handleError(record)
