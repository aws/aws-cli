# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""
Modify an existing option.

This one changes the behavior of the ``--bucket`` option to create the
specified bucket if it does not already exist.

TODO
In this case we are adding to the existing documentation.  But what if
we wanted to replace it entirely?  Or modify what was already provided?
We don't have a way to handle that right now.

One option would be to try to handle it at the event level so that we
could somehow specify when registering the handler that this handler
should be fired instead of any other registered handlers.

Another option would be to somehow pass the content generated for a
particular event through all handlers registered for that event.  A
handler could then remove previously generated content or modify it
although the modification would be tedious since it would have to
search through the current text and make changes.  This could break
easily when the doc strings in the JSON model change.
"""

def awscli_initialize(cli):
    cli.register('before-call.elastictranscoder.create-pipeline',
                 handler=create_bucket)
    cli.register('doc-option.Operation.create-pipeline.output-bucket',
                 handler=doc_handler)

def create_bucket(session, **kwargs):
    # We need the S3 service object
    s3 = session.get_service('s3')
    # And we need an endpoint.  We arent' specifying a region so
    # we will get the user's default region for this profile.
    endpoint = s3.get_endpoint()
    # And finally, we need the list-objects operation.
    operation = s3.get_operation('list-objects')
    http_response, data = operation.call(endpoint, bucket=opts.output_bucket,
                                         maxkeys=0)
    if http_response.status_code == 404:
        # The bucket does not exist, try to create it.
        operation = s3.get_operation('create-bucket')
        http_response, data = operation.call(endpoint,
                                             bucket=opts.output_bucket)
        if http_response.status_code != 200:
            # TODO - what should we do in the case of errors?
            pass


def doc_handler(arg_name, help_command, **kwargs):
    """
    This handler will get called when we are documenting the
    ``output-bucket`` option of the ``create-pipeline`` command.

    The handler is passed a ``help_command`` object which contains
    state that was passed from the CLI to this handler.  In the
    `help_command``, you will find a ``doc`` attribute which contains
    the actual document object that is being used to collect the
    documentation.

    For now, this ``document`` object will always be a ``ReSTDocument``
    but other formats are possible.  How would this code handle that?
    We could query the format of the document we are passed and try to
    change what we output to match that format but hopefully the doc
    object will have the right abstractions available so we can just
    do things like ``start_note`` and the right thing will happen for
    that type of document.
    """
    doc = help_command.doc
    doc.style.new_paragraph()
    doc.style.start_note()
    doc.writeln('If the bucket does not exist, it will be created')
    doc.style.end_note()
