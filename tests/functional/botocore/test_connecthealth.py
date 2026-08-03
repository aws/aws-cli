# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pytest

from botocore.session import get_session


def test_start_medical_scribe_listening_session_removal():
    """start_medical_scribe_listening_session operation removed due to h2 requirement"""
    session = get_session()
    connecthealth = session.create_client('connecthealth', 'us-west-2')
    with pytest.raises(AttributeError):
        connecthealth.start_medical_scribe_listening_session
