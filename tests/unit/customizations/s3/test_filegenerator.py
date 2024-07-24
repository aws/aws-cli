# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import platform
from awscli.testutils import mock, unittest, FileCreator, BaseAWSCommandParamsTest
from awscli.testutils import skip_if_windows
import stat
import tempfile
import shutil
import socket

from botocore.exceptions import ClientError

from awscli.customizations.s3.filegenerator import FileGenerator, \
    FileDecodingError, FileStat, is_special_file, is_readable
from awscli.customizations.s3.utils import get_file_stat, EPOCH_TIME
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files, \
    compare_files


@skip_if_windows('Special files only supported on mac/linux')
class TestIsSpecialFile(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        self.filename = 'foo'

    def tearDown(self):
        self.files.remove_all()

    def test_is_character_device(self):
        file_path = os.path.join(self.files.rootdir, self.filename)
        self.files.create_file(self.filename, contents='')
        with mock.patch('stat.S_ISCHR') as mock_class:
            mock_class.return_value = True
            self.assertTrue(is_special_file(file_path))

    def test_is_block_device(self):
        file_path = os.path.join(self.files.rootdir, self.filename)
        self.files.create_file(self.filename, contents='')
        with mock.patch('stat.S_ISBLK') as mock_class:
            mock_class.return_value = True
            self.assertTrue(is_special_file(file_path))

    def test_is_fifo(self):
        file_path = os.path.join(self.files.rootdir, self.filename)
        mode = 0o600 | stat.S_IFIFO
        os.mknod(file_path, mode)
        self.assertTrue(is_special_file(file_path))

    def test_is_socket(self):
        file_path = os.path.join(self.files.rootdir, self.filename)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(file_path)
        self.assertTrue(is_special_file(file_path))


class TestIsReadable(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        self.filename = 'foo'
        self.full_path = os.path.join(self.files.rootdir, self.filename)

    def tearDown(self):
        self.files.remove_all()

    def test_unreadable_file(self):
        self.files.create_file(self.filename, contents="foo")
        open_function = 'awscli.customizations.s3.filegenerator._open'
        with mock.patch(open_function) as mock_class:
            mock_class.side_effect = OSError()
            self.assertFalse(is_readable(self.full_path))

    def test_unreadable_directory(self):
        os.mkdir(self.full_path)
        with mock.patch('os.listdir') as mock_class:
            mock_class.side_effect = OSError()
            self.assertFalse(is_readable(self.full_path))


class LocalFileGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.client = None
        self.file_creator = FileCreator()
        self.files = make_loc_files(self.file_creator)
        self.local_file = self.files[0]
        self.local_dir = self.files[3] + os.sep

    def tearDown(self):
        clean_loc_files(self.file_creator)

    def test_local_file(self):
        """
        Generate a single local file.
        """
        input_local_file = {'src': {'path': self.local_file,
                                    'type': 'local'},
                            'dest': {'path': 'bucket/text1.txt',
                                     'type': 's3'},
                            'dir_op': False, 'use_src_name': False}
        params = {'region': 'us-east-1'}
        files = FileGenerator(self.client, '').call(input_local_file)
        result_list = []
        for filename in files:
            result_list.append(filename)
        size, last_update = get_file_stat(self.local_file)
        file_stat = FileStat(src=self.local_file, dest='bucket/text1.txt',
                             compare_key='text1.txt', size=size,
                             last_update=last_update, src_type='local',
                             dest_type='s3', operation_name='')
        ref_list = [file_stat]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

    def test_local_directory(self):
        """
        Generate an entire local directory.
        """
        input_local_dir = {'src': {'path': self.local_dir,
                                   'type': 'local'},
                           'dest': {'path': 'bucket/',
                                    'type': 's3'},
                           'dir_op': True, 'use_src_name': True}
        params = {'region': 'us-east-1'}
        files = FileGenerator(self.client, '').call(input_local_dir)
        result_list = []
        for filename in files:
            result_list.append(filename)
        size, last_update = get_file_stat(self.local_file)
        file_stat = FileStat(src=self.local_file, dest='bucket/text1.txt',
                             compare_key='text1.txt', size=size,
                             last_update=last_update, src_type='local',
                             dest_type='s3', operation_name='')
        path = self.local_dir + 'another_directory' + os.sep \
            + 'text2.txt'
        size, last_update = get_file_stat(path)
        file_stat2 = FileStat(src=path,
                              dest='bucket/another_directory/text2.txt',
                              compare_key='another_directory/text2.txt',
                              size=size, last_update=last_update,
                              src_type='local',
                              dest_type='s3', operation_name='')
        ref_list = [file_stat2, file_stat]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])


@skip_if_windows('Symlink tests only supported on mac/linux')
class TestIgnoreFilesLocally(unittest.TestCase):
    """
    This class tests the ability to ignore particular files.  This includes
    skipping symlink when desired.
    """
    def setUp(self):
        self.client = None
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    def test_warning(self):
        path = os.path.join(self.files.rootdir, 'badsymlink')
        os.symlink('non-existent-file', path)
        filegenerator = FileGenerator(self.client, '', True)
        self.assertTrue(filegenerator.should_ignore_file(path))

    def test_skip_symlink(self):
        filename = 'foo.txt'
        self.files.create_file(os.path.join(self.files.rootdir,
                               filename),
                               contents='foo.txt contents')
        sym_path = os.path.join(self.files.rootdir, 'symlink')
        os.symlink(filename, sym_path)
        filegenerator = FileGenerator(self.client, '', False)
        self.assertTrue(filegenerator.should_ignore_file(sym_path))

    def test_no_skip_symlink(self):
        filename = 'foo.txt'
        path = self.files.create_file(os.path.join(self.files.rootdir,
                                                   filename),
                                      contents='foo.txt contents')
        sym_path = os.path.join(self.files.rootdir, 'symlink')
        os.symlink(path, sym_path)
        filegenerator = FileGenerator(self.client, '', True)
        self.assertFalse(filegenerator.should_ignore_file(sym_path))
        self.assertFalse(filegenerator.should_ignore_file(path))

    def test_no_skip_symlink_dir(self):
        filename = 'dir'
        path = os.path.join(self.files.rootdir, 'dir/')
        os.mkdir(path)
        sym_path = os.path.join(self.files.rootdir, 'symlink')
        os.symlink(path, sym_path)
        filegenerator = FileGenerator(self.client, '', True)
        self.assertFalse(filegenerator.should_ignore_file(sym_path))
        self.assertFalse(filegenerator.should_ignore_file(path))


class TestThrowsWarning(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        self.root = self.files.rootdir
        self.client = None

    def tearDown(self):
        self.files.remove_all()

    def test_no_warning(self):
        file_gen = FileGenerator(self.client, '', False)
        self.files.create_file("foo.txt", contents="foo")
        full_path = os.path.join(self.root, "foo.txt")
        return_val = file_gen.triggers_warning(full_path)
        self.assertFalse(return_val)
        self.assertTrue(file_gen.result_queue.empty())

    def test_no_exists(self):
        file_gen = FileGenerator(self.client, '', False)
        filename = os.path.join(self.root, 'file')
        return_val = file_gen.triggers_warning(filename)
        self.assertTrue(return_val)
        warning_message = file_gen.result_queue.get()
        self.assertEqual(warning_message.message,
                         ("warning: Skipping file %s. File does not exist." %
                          filename))

    def test_no_read_access(self):
        file_gen = FileGenerator(self.client, '', False)
        self.files.create_file("foo.txt", contents="foo")
        full_path = os.path.join(self.root, "foo.txt")
        open_function = 'awscli.customizations.s3.filegenerator._open'
        with mock.patch(open_function) as mock_class:
            mock_class.side_effect = OSError()
            return_val = file_gen.triggers_warning(full_path)
            self.assertTrue(return_val)
        warning_message = file_gen.result_queue.get()
        self.assertEqual(warning_message.message,
                         ("warning: Skipping file %s. File/Directory is "
                          "not readable." % full_path))

    @skip_if_windows('Special files only supported on mac/linux')
    def test_is_special_file_warning(self):
        file_gen = FileGenerator(self.client, '', False)
        file_path = os.path.join(self.files.rootdir, 'foo')
        # Use socket for special file.
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(file_path)
        return_val = file_gen.triggers_warning(file_path)
        self.assertTrue(return_val)
        warning_message = file_gen.result_queue.get()
        self.assertEqual(warning_message.message,
                         ("warning: Skipping file %s. File is character "
                          "special device, block special device, FIFO, or "
                          "socket." % file_path))


@skip_if_windows('Symlink tests only supported on mac/linux')
class TestSymlinksIgnoreFiles(unittest.TestCase):
    """
    This class tests the ability to list out the correct local files
    depending on if symlinks are being followed.  Also tests to ensure
    broken symlinks fail.
    """
    def setUp(self):
        self.client = None
        self.files = FileCreator()
        # List of local filenames.
        self.filenames = []
        self.root = self.files.rootdir
        self.bucket = 'bucket/'
        filename_1 = self.files.create_file('foo.txt',
                                            contents='foo.txt contents')
        self.filenames.append(filename_1)
        nested_dir = os.path.join(self.root, 'realfiles')
        os.mkdir(nested_dir)
        filename_2 = self.files.create_file(os.path.join(nested_dir,
                                                         'bar.txt'),
                                            contents='bar.txt contents')
        self.filenames.append(filename_2)
        # Names of symlinks.
        self.symlinks = []
        # Names of files if symlinks are followed.
        self.symlink_files = []
        # Create symlink to file foo.txt.
        symlink_1 = os.path.join(self.root, 'symlink_1')
        os.symlink(filename_1, symlink_1)
        self.symlinks.append(symlink_1)
        self.symlink_files.append(symlink_1)
        # Create a symlink to a file that does not exist.
        symlink_2 = os.path.join(self.root, 'symlink_2')
        os.symlink('non-existent-file', symlink_2)
        self.symlinks.append(symlink_2)
        # Create a symlink to directory realfiles
        symlink_3 = os.path.join(self.root, 'symlink_3')
        os.symlink(nested_dir, symlink_3)
        self.symlinks.append(symlink_3)
        self.symlink_files.append(os.path.join(symlink_3, 'bar.txt'))

    def tearDown(self):
        self.files.remove_all()

    def test_no_follow_symlink(self):
        abs_root = str(os.path.abspath(self.root) + os.sep)
        input_local_dir = {'src': {'path': abs_root,
                                   'type': 'local'},
                           'dest': {'path': self.bucket,
                                    'type': 's3'},
                           'dir_op': True, 'use_src_name': True}
        file_stats = FileGenerator(self.client, '', False).call(input_local_dir)
        self.filenames.sort()
        result_list = []
        for file_stat in file_stats:
            result_list.append(getattr(file_stat, 'src'))
        self.assertEqual(len(result_list), len(self.filenames))
        # Just check to make sure the right local files are generated.
        for i in range(len(result_list)):
            filename = str(os.path.abspath(self.filenames[i]))
            self.assertEqual(result_list[i], filename)

    def test_warn_bad_symlink(self):
        """
        This tests to make sure it fails when following bad symlinks.
        """
        abs_root = str(os.path.abspath(self.root) + os.sep)
        input_local_dir = {'src': {'path': abs_root,
                                   'type': 'local'},
                           'dest': {'path': self.bucket,
                                    'type': 's3'},
                           'dir_op': True, 'use_src_name': True}
        file_stats = FileGenerator(self.client, '', True).call(input_local_dir)
        file_gen = FileGenerator(self.client, '', True)
        file_stats = file_gen.call(input_local_dir)
        all_filenames = self.filenames + self.symlink_files
        all_filenames.sort()
        result_list = []
        for file_stat in file_stats:
            result_list.append(getattr(file_stat, 'src'))
        self.assertEqual(len(result_list), len(all_filenames))
        # Just check to make sure the right local files are generated.
        for i in range(len(result_list)):
            filename = str(os.path.abspath(all_filenames[i]))
            self.assertEqual(result_list[i], filename)
        self.assertFalse(file_gen.result_queue.empty())

    def test_follow_symlink(self):
        # First remove the bad symlink.
        os.remove(os.path.join(self.root, 'symlink_2'))
        abs_root = str(os.path.abspath(self.root) + os.sep)
        input_local_dir = {'src': {'path': abs_root,
                                   'type': 'local'},
                           'dest': {'path': self.bucket,
                                    'type': 's3'},
                           'dir_op': True, 'use_src_name': True}
        file_stats = FileGenerator(self.client, '', True).call(input_local_dir)
        all_filenames = self.filenames + self.symlink_files
        all_filenames.sort()
        result_list = []
        for file_stat in file_stats:
            result_list.append(getattr(file_stat, 'src'))
        self.assertEqual(len(result_list), len(all_filenames))
        # Just check to make sure the right local files are generated.
        for i in range(len(result_list)):
            filename = str(os.path.abspath(all_filenames[i]))
            self.assertEqual(result_list[i], filename)


class TestListFilesLocally(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.directory = str(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.directory)

    @mock.patch('os.listdir')
    def test_error_raised_on_decoding_error(self, listdir_mock):
        # On Python3, sys.getdefaultencoding
        file_generator = FileGenerator(None, None, None)
        # utf-8 encoding for U+2713.
        listdir_mock.return_value = [b'\xe2\x9c\x93']
        list(file_generator.list_files(self.directory, dir_op=True))
        # Ensure the message was added to the result queue and is
        # being skipped.
        self.assertFalse(file_generator.result_queue.empty())
        warning_message = file_generator.result_queue.get()
        self.assertIn("warning: Skipping file ", warning_message.message)
        self.assertIn("Please check your locale settings.",
                      warning_message.message)

    def test_list_files_is_in_sorted_order(self):
        p = os.path.join
        open(p(self.directory, 'test-123.txt'), 'w').close()
        open(p(self.directory, 'test-321.txt'), 'w').close()
        open(p(self.directory, 'test123.txt'), 'w').close()
        open(p(self.directory, 'test321.txt'), 'w').close()
        os.mkdir(p(self.directory, 'test'))
        open(p(self.directory, 'test', 'foo.txt'), 'w').close()

        file_generator = FileGenerator(None, None, None)
        values = list(el[0] for el in file_generator.list_files(
            self.directory, dir_op=True))
        ref_vals = list(sorted(values,
                               key=lambda items: items.replace(os.sep, '/')))
        self.assertEqual(values, ref_vals)

    @mock.patch('awscli.customizations.s3.filegenerator.get_file_stat')
    def test_list_files_with_invalid_timestamp(self, stat_mock):
        stat_mock.return_value = 9, None
        open(os.path.join(self.directory, 'test'), 'w').close()
        file_generator = FileGenerator(None, None, None)
        value = list(file_generator.list_files(self.directory, dir_op=True))[0]
        self.assertIs(value[1]['LastModified'], EPOCH_TIME)

    def test_list_local_files_with_unicode_chars(self):
        p = os.path.join
        open(p(self.directory, u'a'), 'w').close()
        open(p(self.directory, u'a\u0300'), 'w').close()
        open(p(self.directory, u'a\u0300-1'), 'w').close()
        open(p(self.directory, u'a\u03001'), 'w').close()
        open(p(self.directory, u'z'), 'w').close()
        open(p(self.directory, u'\u00e6'), 'w').close()
        os.mkdir(p(self.directory, u'a\u0300a'))
        open(p(self.directory, u'a\u0300a', u'a'), 'w').close()
        open(p(self.directory, u'a\u0300a', u'z'), 'w').close()
        open(p(self.directory, u'a\u0300a', u'\u00e6'), 'w').close()

        file_generator = FileGenerator(None, None, None)
        values = list(el[0] for el in file_generator.list_files(
            self.directory, dir_op=True))
        expected_order = [os.path.join(self.directory, el) for el in [
            u"a",
            u"a\u0300",
            u"a\u0300-1",
            u"a\u03001",
            u"a\u0300a%sa" % os.path.sep,
            u"a\u0300a%sz" % os.path.sep,
            u"a\u0300a%s\u00e6" % os.path.sep,
            u"z",
            u"\u00e6"
        ]]
        self.assertEqual(values, expected_order)


class TestNormalizeSort(unittest.TestCase):
    def test_normalize_sort(self):
        names = ['xyz123456789',
                 'xyz1' + os.path.sep + 'test',
                 'xyz' + os.path.sep + 'test']
        ref_names = [names[2], names[1], names[0]]
        filegenerator = FileGenerator(None, None, None)
        filegenerator.normalize_sort(names, os.path.sep, '/')
        for i in range(len(ref_names)):
            self.assertEqual(ref_names[i], names[i])

    def test_normalize_sort_backslash(self):
        names = ['xyz123456789',
                 'xyz1\\test',
                 'xyz\\test']
        ref_names = [names[2], names[1], names[0]]
        filegenerator = FileGenerator(None, None, None)
        filegenerator.normalize_sort(names, '\\', '/')
        for i in range(len(ref_names)):
            self.assertEqual(ref_names[i], names[i])


class S3FileGeneratorTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(S3FileGeneratorTest, self).setUp()
        self.client = self.driver.session.create_client('s3')
        self.bucket = 'foo'
        self.file1 = self.bucket + '/' + 'text1.txt'
        self.file2 = self.bucket + '/' + 'another_directory/text2.txt'

    def test_s3_file(self):
        """
        Generate a single s3 file
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.file1, 'type': 's3'},
                         'dest': {'path': 'text1.txt', 'type': 'local'},
                         'dir_op': False, 'use_src_name': False}
        params = {'region': 'us-east-1'}
        self.parsed_responses = [{"ETag": "abcd", "ContentLength": 100,
                                  "LastModified": "2014-01-09T20:45:49.000Z"}]
        self.patch_make_request()

        file_gen = FileGenerator(self.client, '')
        files = file_gen.call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)
        file_stat = FileStat(src=self.file1, dest='text1.txt',
                             compare_key='text1.txt',
                             size=result_list[0].size,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation_name='')

        ref_list = [file_stat]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

    def test_s3_single_file_404(self):
        """
        Test the error message for a 404 ClientError for a single file listing
        """
        input_s3_file = {'src': {'path': self.file1, 'type': 's3'},
                         'dest': {'path': 'text1.txt', 'type': 'local'},
                         'dir_op': False, 'use_src_name': False}
        params = {'region': 'us-east-1'}
        self.client = mock.Mock()
        self.client.head_object.side_effect = \
                ClientError(
                    {'Error': {'Code': '404', 'Message': 'Not Found'}},
                    'HeadObject',
                )
        file_gen = FileGenerator(self.client, '')
        files = file_gen.call(input_s3_file)
        # The error should include 404 and should include the key name.
        with self.assertRaisesRegex(ClientError, '404.*text1.txt'):
            list(files)

    def test_s3_single_file_delete(self):
        input_s3_file = {'src': {'path': self.file1, 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': False, 'use_src_name': True}
        self.client = mock.Mock()
        file_gen = FileGenerator(self.client, 'delete')
        result_list = list(file_gen.call(input_s3_file))
        self.assertEqual(len(result_list), 1)
        compare_files(
            self,
            result_list[0],
            FileStat(src=self.file1, dest='text1.txt',
                     compare_key='text1.txt',
                     size=None, last_update=None,
                     src_type='s3', dest_type='local',
                     operation_name='delete')
        )
        self.client.head_object.assert_not_called()

    def test_s3_directory(self):
        """
        Generates s3 files under a common prefix. Also it ensures that
        zero size files are ignored.
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.bucket + '/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        params = {'region': 'us-east-1'}
        files = FileGenerator(self.client, '').call(input_s3_file)

        self.parsed_responses = [{
            "CommonPrefixes": [], "Contents": [
                {"Key": "another_directory/text2.txt", "Size": 100,
                 "LastModified": "2014-01-09T20:45:49.000Z"},
                {"Key": "text1.txt", "Size": 10,
                 "LastModified": "2013-01-09T20:45:49.000Z"}]}]
        self.patch_make_request()
        result_list = []
        for filename in files:
            result_list.append(filename)
        file_stat = FileStat(src=self.file2,
                             dest='another_directory' + os.sep +
                             'text2.txt',
                             compare_key='another_directory/text2.txt',
                             size=result_list[0].size,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation_name='')
        file_stat2 = FileStat(src=self.file1,
                              dest='text1.txt',
                              compare_key='text1.txt',
                              size=result_list[1].size,
                              last_update=result_list[1].last_update,
                              src_type='s3',
                              dest_type='local', operation_name='')

        ref_list = [file_stat, file_stat2]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

    def test_s3_delete_directory(self):
        """
        Generates s3 files under a common prefix. Also it ensures that
        the directory itself is included because it is a delete command
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.bucket + '/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        self.parsed_responses = [{
            "CommonPrefixes": [], "Contents": [
                {"Key": "another_directory/", "Size": 0,
                 "LastModified": "2012-01-09T20:45:49.000Z"},
                {"Key": "another_directory/text2.txt", "Size": 100,
                 "LastModified": "2014-01-09T20:45:49.000Z"},
                {"Key": "text1.txt", "Size": 10,
                 "LastModified": "2013-01-09T20:45:49.000Z"}]}]
        self.patch_make_request()
        files = FileGenerator(self.client, 'delete').call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)

        file_stat1 = FileStat(src=self.bucket + '/another_directory/',
                              dest='another_directory' + os.sep,
                              compare_key='another_directory/',
                              size=result_list[0].size,
                              last_update=result_list[0].last_update,
                              src_type='s3',
                              dest_type='local', operation_name='delete')
        file_stat2 = FileStat(src=self.file2,
                              dest='another_directory' + os.sep + 'text2.txt',
                              compare_key='another_directory/text2.txt',
                              size=result_list[1].size,
                              last_update=result_list[1].last_update,
                              src_type='s3',
                              dest_type='local', operation_name='delete')
        file_stat3 = FileStat(src=self.file1,
                              dest='text1.txt',
                              compare_key='text1.txt',
                              size=result_list[2].size,
                              last_update=result_list[2].last_update,
                              src_type='s3',
                              dest_type='local', operation_name='delete')

        ref_list = [file_stat1, file_stat2, file_stat3]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])


if __name__ == "__main__":
    unittest.main()
