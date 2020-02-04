# -*- mode: python -*-

block_cipher = None
exe_name = "aws_completer"


completer_a = Analysis(['../../bin/aws_completer'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['cmd', 'code', 'pdb'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
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
          console=True)
coll = COLLECT(completer_exe,
               completer_a.binaries,
               completer_a.zipfiles,
               completer_a.datas,
               strip=False,
               upx=True,
               name='aws_completer')
