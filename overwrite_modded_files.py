import os
import shutil

cwd = os.getcwd()

modified_files = [
	'mozharness\\mozharness\\mozilla\\testing\\raptor.py',
	'mozharness\\mozharness\\mozilla\\testing\\windows_powerusage.py'
]

for key in modified_files:
	print(key)
	parts = key.split('\\')
	file = parts[-1]
	root = '\\'.join(parts[:-1])
	print(parts, file, root)

	shutil.copyfile(
		os.path.join(cwd, file),
		os.path.join(cwd, root, file)
	)
