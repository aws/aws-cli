# -*- mode: python -*-

block_cipher = None


aws_a = Analysis(['../bin/aws'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
aws_pyz = PYZ(aws_a.pure, aws_a.zipped_data, cipher=block_cipher)
aws_exe = EXE(aws_pyz,
          aws_a.scripts,
          [],
          exclude_binaries=True,
          name='aws',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(aws_exe,
               aws_a.binaries,
               aws_a.zipfiles,
               aws_a.datas,
               strip=False,
               upx=True,
               name='aws')
