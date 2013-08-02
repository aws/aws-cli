import os
import unittest

from awscli.customizations.s3.filegenerator import FileInfo
from awscli.customizations.s3.filters import Filter


class FiltersTest(unittest.TestCase):
    def setUp(self):
        self.local_files = []
        self.loc_file1 = FileInfo(src=os.path.abspath('test.txt'), dest='',
                                  compare_key='', size=10,
                                  last_update=0, src_type='local',
                                  dest_type='s3', operation='')
        self.loc_file2 = FileInfo(src=os.path.abspath('test.jpg'), dest='',
                                  compare_key='', size=10,
                                  last_update=0, src_type='local',
                                  dest_type='s3', operation='')
        path = 'directory' + os.sep + 'test.jpg'
        self.loc_file3 = FileInfo(src=os.path.abspath(path), dest='',
                                  compare_key='', size=10,
                                  last_update=0, src_type='local',
                                  dest_type='s3', operation='')
        self.local_files.append(self.loc_file1)
        self.local_files.append(self.loc_file2)
        self.local_files.append(self.loc_file3)

        self.s3_files = []
        self.s3_file1 = FileInfo('bucket/test.txt', dest='',
                                 compare_key='', size=10,
                                 last_update=0, src_type='s3',
                                 dest_type='s3', operation='')
        self.s3_file2 = FileInfo('bucket/test.jpg', dest='',
                                 compare_key='', size=10,
                                 last_update=0, src_type='s3',
                                 dest_type='s3', operation='')
        self.s3_file3 = FileInfo('bucket/key/test.jpg', dest='',
                                 compare_key='', size=10,
                                 last_update=0, src_type='s3',
                                 dest_type='s3', operation='')
        self.s3_files.append(self.s3_file1)
        self.s3_files.append(self.s3_file2)
        self.s3_files.append(self.s3_file3)

    def test_no_filter(self):
        """
        No filters
        """
        patterns = []
        exc_inc_filter = Filter({})
        files = exc_inc_filter.call(iter(self.local_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, self.local_files)

        files = exc_inc_filter.call(iter(self.s3_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, self.s3_files)

    def test_include(self):
        """
        Only an include file
        """
        patterns = [['--include', '*.txt']]
        exc_inc_filter = Filter({'filters': patterns})
        files = exc_inc_filter.call(iter(self.local_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, self.local_files)

        files = exc_inc_filter.call(iter(self.s3_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, self.s3_files)

    def test_exclude(self):
        """
        Only an exclude filter
        """
        patterns = [['--exclude', '*']]
        exc_inc_filter = Filter({'filters': patterns})
        files = exc_inc_filter.call(iter(self.local_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, [])

        files = exc_inc_filter.call(iter(self.s3_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, [])

    def test_exclude_include(self):
        """
        Exclude everything and then include all .txt files
        """
        patterns = [['--exclude', '*'], ['--include', '*.txt']]
        exc_inc_filter = Filter({'filters': patterns})
        files = exc_inc_filter.call(iter(self.local_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, [self.loc_file1])

        files = exc_inc_filter.call(iter(self.s3_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, [self.s3_file1])

    def test_include_exclude(self):
        """
        Include all .txt files then exclude everything
        """
        patterns = [['--include', '*.txt'], ['--exclude', '*']]
        exc_inc_filter = Filter({'filters': patterns})
        files = exc_inc_filter.call(iter(self.local_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, [])

        files = exc_inc_filter.call(iter(self.s3_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, [])

if __name__ == "__main__":
    unittest.main()
