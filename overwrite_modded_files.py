import os
import shutil

cwd = os.getcwd()

modified_files = {
	'mozharness\\mozharness\\mozilla\\testing': 'raptor.py',
	'mozharness\\mozharness\\mozilla\\testing': 'windows_powerusage.py'
}

for key, val in modified_files.items():
	shutil.copyfile(
		os.path.join(cwd, val),
		os.path.join(cwd, key, val)
	)
