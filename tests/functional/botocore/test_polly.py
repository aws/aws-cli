# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tests import BaseSessionTest


class TestPolly(BaseSessionTest):
    def test_start_speech_synthesis_stream(self):
        """StartSpeechSynthesisStream operation removed due to h2 requirement"""
        polly_client = self.session.create_client('polly', 'us-west-2')
        try:
            polly_client.start_speech_synthesis_stream
        except AttributeError:
            pass
        else:
            self.fail(
                'start_speech_synthesis_stream shouldn\'t be available on the '
                'polly client.'
            )
