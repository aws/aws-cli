# -*- mode: python -*-
import platform

block_cipher = None
exe_name = "aws_completer"


completer_a = Analysis(['../../bin/aws_completer'],
             binaries=[],
             datas=[('../../awscli/data/metadata.json', 'awscli/data')],
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
if platform.system() == "Darwin":
    updated_binaries = []
    for dest, src, typecode in completer_a.binaries:
        # Look for the actual Python executable, regardless of the version
        if dest.startswith('Python.framework/Versions/') and dest.endswith('/Python'):
            # and move it to the top
            dest = 'Python'
        elif dest.startswith('Python3.framework/Versions/') and dest.endswith('/Python3'):
            # and move it to the top
            dest = 'Python3'
        updated_binaries.append((dest, src, typecode))
    completer_a.binaries = updated_binaries

    # Remove the symlinks and the Info.plist related to Python.framework
    # since we're using the top-level executable above
    updated_datas = []
    for dest, src, typecode in completer_a.datas:
        if (dest.startswith('Python.framework/') or (dest == 'Python' and typecode == 'SYMLINK')):
            continue
        elif (dest.startswith('Python3.framework/') or (dest == 'Python3' and typecode == 'SYMLINK')):
            continue
        updated_datas.append((dest, src, typecode))
    completer_a.datas = updated_datas

completer_pyz = PYZ(completer_a.pure, completer_a.zipped_data, cipher=block_cipher)
completer_exe = EXE(completer_pyz,
          completer_a.scripts,
          [],
          exclude_binaries=True,
          name=exe_name,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          contents_directory='.')
coll = COLLECT(completer_exe,
               completer_a.binaries,
               completer_a.zipfiles,
               completer_a.datas,
               strip=False,
               upx=True,
               name='aws_completer')
