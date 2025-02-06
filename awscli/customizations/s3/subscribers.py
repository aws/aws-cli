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
import errno
import logging
import os
import time

from botocore.utils import percent_encode_sequence
from s3transfer.subscribers import BaseSubscriber

from awscli.customizations.s3 import utils


LOGGER = logging.getLogger(__name__)


class CreateDirectoryError(Exception):
    pass


# TODO: Eventually port this down to the BaseSubscriber or a new subscriber
# class in s3transfer. The functionality is very convenient but may need
# some further design decisions to make it a feature in s3transfer.
class OnDoneFilteredSubscriber(BaseSubscriber):
    """Subscriber that differentiates between successes and failures

    It is really a convenience class so developers do not have to have
    to constantly remember to have a general try/except around future.result()
    """
    def on_done(self, future, **kwargs):
        future_exception = None
        try:

            future.result()
        except Exception as e:
            future_exception = e
        # If the result propogates an error, call the on_failure
        # method instead.
        if future_exception:
            self._on_failure(future, future_exception)
        else:
            self._on_success(future)

    def _on_success(self, future):
        pass

    def _on_failure(self, future, e):
        pass


class ProvideSizeSubscriber(BaseSubscriber):
    """
    A subscriber which provides the transfer size before it's queued.
    """
    def __init__(self, size):
        self.size = size

    def on_queued(self, future, **kwargs):
        # The CRT transfer client does not support providing an expected
        # size for the transfer. So only provide it if it is available.
        if hasattr(future.meta, 'provide_transfer_size'):
            future.meta.provide_transfer_size(self.size)
        else:
            LOGGER.debug(
                'Not providing transfer size. Future: %s does not offer'
                'the capability to notify the size of a transfer', future
            )


class DeleteSourceSubscriber(OnDoneFilteredSubscriber):
    """A subscriber which deletes the source of the transfer."""
    def _on_success(self, future):
        try:
            self._delete_source(future)
        except Exception as e:
            future.set_exception(e)

    def _delete_source(self, future):
        raise NotImplementedError('_delete_source()')


class DeleteSourceObjectSubscriber(DeleteSourceSubscriber):
    """A subscriber which deletes an object."""
    def __init__(self, client):
        self._client = client

    def _get_bucket(self, call_args):
        return call_args.bucket

    def _get_key(self, call_args):
        return call_args.key

    def _delete_source(self, future):
        call_args = future.meta.call_args
        delete_object_kwargs = {
            'Bucket': self._get_bucket(call_args),
            'Key': self._get_key(call_args)
        }
        if call_args.extra_args.get('RequestPayer'):
            delete_object_kwargs['RequestPayer'] = call_args.extra_args[
                'RequestPayer']
        self._client.delete_object(**delete_object_kwargs)


class DeleteCopySourceObjectSubscriber(DeleteSourceObjectSubscriber):
    """A subscriber which deletes the copy source."""
    def _get_bucket(self, call_args):
        return call_args.copy_source['Bucket']

    def _get_key(self, call_args):
        return call_args.copy_source['Key']


class DeleteSourceFileSubscriber(DeleteSourceSubscriber):
    """A subscriber which deletes a file."""
    def _delete_source(self, future):
        os.remove(future.meta.call_args.fileobj)


class BaseProvideContentTypeSubscriber(BaseSubscriber):
    """A subscriber that provides content type when creating s3 objects"""

    def on_queued(self, future, **kwargs):
        guessed_type = utils.guess_content_type(self._get_filename(future))
        if guessed_type is not None:
            future.meta.call_args.extra_args['ContentType'] = guessed_type

    def _get_filename(self, future):
        raise NotImplementedError('_get_filename()')


class ProvideUploadContentTypeSubscriber(BaseProvideContentTypeSubscriber):
    def _get_filename(self, future):
        return future.meta.call_args.fileobj


class ProvideLastModifiedTimeSubscriber(OnDoneFilteredSubscriber):
    """Sets utime for a downloaded file"""
    def __init__(self, last_modified_time, result_queue):
        self._last_modified_time = last_modified_time
        self._result_queue = result_queue

    def _on_success(self, future, **kwargs):
        filename = future.meta.call_args.fileobj
        try:
            last_update_tuple = self._last_modified_time.timetuple()
            mod_timestamp = time.mktime(last_update_tuple)
            utils.set_file_utime(filename, int(mod_timestamp))
        except Exception as e:
            warning_message = (
                'Successfully Downloaded %s but was unable to update the '
                'last modified time. %s' % (filename, e))
            self._result_queue.put(
                utils.create_warning(filename, warning_message))


class DirectoryCreatorSubscriber(BaseSubscriber):
    """Creates a directory to download if it does not exist"""
    def on_queued(self, future, **kwargs):
        d = os.path.dirname(future.meta.call_args.fileobj)
        try:
            if not os.path.exists(d):
                os.makedirs(d)
        except OSError as e:
            if not e.errno == errno.EEXIST:
                raise CreateDirectoryError(
                    "Could not create directory %s: %s" % (d, e))


class CopyPropsSubscriberFactory(object):
    def __init__(self, client, transfer_config, cli_params):
        self._client = client
        self._transfer_config = transfer_config
        self._cli_params = cli_params

    def get_subscribers(self, fileinfo):
        copy_props = self._cli_params.get(
            'copy_props', 'default').replace('-', '_')
        return getattr(self, '_get_%s_subscribers' % copy_props)(fileinfo)

    def _get_none_subscribers(self, fileinfo):
        return [
            ReplaceMetadataDirectiveSubscriber(),
            ReplaceTaggingDirectiveSubscriber(),
        ]

    def _get_metadata_directive_subscribers(self, fileinfo):
        return [
            self._create_metadata_directive_props_subscriber(fileinfo),
            ReplaceTaggingDirectiveSubscriber()
        ]

    def _get_default_subscribers(self, fileinfo):
        return [
            self._create_metadata_directive_props_subscriber(fileinfo),
            SetTagsSubscriber(
                self._client, self._transfer_config, self._cli_params,
                source_client=fileinfo.source_client,
            )
        ]

    def _create_metadata_directive_props_subscriber(self, fileinfo):
        subscriber_kwargs = {
            'client': fileinfo.source_client,
            'transfer_config': self._transfer_config,
            'cli_params': self._cli_params,
        }
        if not self._cli_params.get('dir_op'):
            subscriber_kwargs[
                'head_object_response'] = fileinfo.associated_response_data
        return SetMetadataDirectivePropsSubscriber(**subscriber_kwargs)


class ReplaceDirectiveSubscriber(BaseSubscriber):
    _DIRECTIVE_PARAM = ''

    def on_queued(self, future, **kwargs):
        future.meta.call_args.extra_args[self._DIRECTIVE_PARAM] = 'REPLACE'


class ReplaceMetadataDirectiveSubscriber(ReplaceDirectiveSubscriber):
    _DIRECTIVE_PARAM = 'MetadataDirective'


class ReplaceTaggingDirectiveSubscriber(ReplaceDirectiveSubscriber):
    _DIRECTIVE_PARAM = 'TaggingDirective'


class SetMetadataDirectivePropsSubscriber(BaseSubscriber):
    _ALL_METADATA_DIRECTIVE_PROPERTIES = [
        'CacheControl',
        'ContentDisposition',
        'ContentEncoding',
        'ContentLanguage',
        'ContentType',
        'Expires',
        'Metadata',
    ]

    def __init__(self, client, transfer_config, cli_params,
                 head_object_response=None):
        self._client = client
        self._transfer_config = transfer_config
        self._cli_params = cli_params
        self._head_object_response = head_object_response

    def on_queued(self, future, **kwargs):
        should_inject_metadata = False
        if self._is_multipart_copy(future):
            should_inject_metadata = True
        elif self._has_explict_metadata_request_params(future):
            should_inject_metadata = True
            future.meta.call_args.extra_args['MetadataDirective'] = 'REPLACE'
        if should_inject_metadata:
            head_object_response = self._get_head_object_response(future)
            self._inject_metadata_props(future, head_object_response)

    def _has_explict_metadata_request_params(self, future):
        for param in future.meta.call_args.extra_args:
            if param in self._ALL_METADATA_DIRECTIVE_PROPERTIES:
                return True
        return False

    def _get_head_object_response(self, future):
        if self._head_object_response is not None:
            return self._head_object_response
        copy_source = future.meta.call_args.copy_source
        head_object_params = {
            'Bucket': copy_source['Bucket'],
            'Key': copy_source['Key'],
        }
        utils.RequestParamsMapper.map_head_object_params_with_copy_source_sse(
            head_object_params, self._cli_params)
        return self._client.head_object(**head_object_params)

    def _inject_metadata_props(self, future, head_object_response):
        request_args = future.meta.call_args.extra_args
        for param in self._ALL_METADATA_DIRECTIVE_PROPERTIES:
            if param not in request_args and param in head_object_response:
                request_args[param] = head_object_response[param]

    def _is_multipart_copy(self, future):
        return future.meta.size >= self._transfer_config.multipart_threshold


class SetTagsSubscriber(OnDoneFilteredSubscriber):
    _MAX_TAGGING_HEADER_SIZE = 2 * 1024

    def __init__(self, client, transfer_config, cli_params, source_client):
        self._client = client
        self._transfer_config = transfer_config
        self._cli_params = cli_params
        self._source_client = source_client

    def on_queued(self, future, **kwargs):
        # Tags only need to be set if the operation is a multipart copy
        if not self._is_multipart_copy(future):
            return
        bucket, key = self._get_bucket_key_from_copy_source(future)
        tags = self._get_tags(bucket, key)
        if not tags:
            return
        header_value = self._serialize_to_header_value(tags)
        if self._fits_in_tagging_header(header_value):
            future.meta.call_args.extra_args['Tagging'] = header_value
        else:
            future.meta.user_context['TagSet'] = tags

    def _on_success(self, future):
        if 'TagSet' in future.meta.user_context:
            bucket = future.meta.call_args.bucket
            key = future.meta.call_args.key
            tag_set = future.meta.user_context['TagSet']
            try:
                self._put_object_tagging(bucket, key, tag_set)
            except Exception as e:
                self._delete_object(bucket, key)
                future.set_exception(e)

    def _put_object_tagging(self, bucket, key, tag_set):
        extra_args = {}
        utils.RequestParamsMapper.map_put_object_tagging_params(
            extra_args, self._cli_params
        )
        self._client.put_object_tagging(
            Bucket=bucket,
            Key=key,
            Tagging={'TagSet': tag_set},
            **extra_args
        )

    def _delete_object(self, bucket, key):
        params = {
            'Bucket': bucket,
            'Key': key
        }
        utils.RequestParamsMapper.map_delete_object_params(
            params, self._cli_params)
        self._client.delete_object(**params)

    def _get_bucket_key_from_copy_source(self, future):
        copy_source = future.meta.call_args.copy_source
        return copy_source['Bucket'], copy_source['Key']

    def _get_tags(self, bucket, key):
        extra_args = {}
        utils.RequestParamsMapper.map_get_object_tagging_params(
            extra_args, self._cli_params
        )
        get_tags_response = self._source_client.get_object_tagging(
            Bucket=bucket, Key=key, **extra_args)
        return get_tags_response['TagSet']

    def _fits_in_tagging_header(self, tagging_header):
        return len(
            tagging_header.encode('utf-8')) <= self._MAX_TAGGING_HEADER_SIZE

    def _serialize_to_header_value(self, tags):
        return percent_encode_sequence(
            [(tag['Key'], tag['Value']) for tag in tags])

    def _is_multipart_copy(self, future):
        return future.meta.size >= self._transfer_config.multipart_threshold
