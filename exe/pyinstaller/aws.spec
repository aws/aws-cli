# -*- mode: python -*-

block_cipher = None
exe_name = 'aws'

aws_a = Analysis(['../../bin/aws'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['cmd', 'code', 'pdb'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

# Replace the Python.framework directory with a top-level Python executable
# This is easier for our internal signing and notarization code,
# since we're not signing via PyInstaller
updated_binaries = []
for dest, src, typecode in aws_a.binaries:
    if dest.startswith('Python.framework/') and dest.endswith('/Python'):
        dest = 'Python'
    updated_binaries.append((dest, src, typecode))
aws_a.binaries = updated_binaries

# Remove the symlinks and the Info.plist related to Python.framework
# since we're using the top-level executable above
updated_datas = []
for dest, src, typecode in aws_a.datas:
    if (dest.startswith('Python.framework/') or (dest == 'Python' and typecode == 'SYMLINK')):
        continue
    updated_datas.append((dest, src, typecode))
aws_a.datas = updated_datas

# Verify that there are no remaining symlinks
for dest, src, typecode in aws_a.datas:
    if typecode == 'SYMLINK':
        raise ValueError((f'Symlink ({dest} -> {src}) found in table of contents. '
            'Our downstream packaging and signing code does not support symlinks, '
            'so this requires investigation.'))

aws_pyz = PYZ(aws_a.pure, aws_a.zipped_data, cipher=block_cipher)
aws_exe = EXE(aws_pyz,
          aws_a.scripts,
          [],
          exclude_binaries=True,
          name=exe_name,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          contents_directory='.')
coll = COLLECT(aws_exe,
               aws_a.binaries,
               aws_a.zipfiles,
               aws_a.datas,
               strip=False,
               upx=True,
               name='aws')

