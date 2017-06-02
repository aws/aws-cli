import hashlib
import os


def hash_file(filepath):
    """Create MD5 hash filename and contents"""
    md5 = hashlib.md5()

    # Hash filename
    filename = os.path.basename(filepath)
    md5.update(filename)

    # md5 file 4096 bytes at a time
    with open(filepath, "rb") as f:
        curpos = f.tell()
        f.seek(0)
        while True:
            buff = f.read(4096)
            if len(buff) == 0:
                break
            md5.update(buff)
        f.seek(curpos)
    return md5.hexdigest()


def hash_dir(base_dirpath):
    """Create MD5 hash of dirname and contents"""
    if not os.path.isdir(base_dirpath):
        raise AttributeError(
            "dirpath: {0} is not a directory".format(base_dirpath))
    md5 = hashlib.md5()

    # hash name of directory
    dirname = os.path.basename(base_dirpath)
    md5.update(dirname)

    # hash directory contents
    for root, dirs, files in os.walk(base_dirpath):
        # hash all nested directories
        for nested_dir in sorted(dirs):
            dirpath = os.path.join(root, nested_dir)
            dirhash = hash_dir(dirpath)
            md5.update(dirhash)

        # hash all files in the root directory
        for nested_file in sorted(files):
            filepath = os.path.join(root, nested_file)
            filehash = hash_file(filepath)
            md5.update(filehash)

    return md5.hexdigest()
