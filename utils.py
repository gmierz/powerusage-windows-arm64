import os


def pattern_find(srcf_to_find, sources):
	if sources is None:
		return True

	for srcf in sources:
		if srcf in srcf_to_find:
			return srcf
	return None


def get_paths_from_dir(source_dir, file_matchers=None):
	paths = []
	for root, _, files in os.walk(source_dir):
		for file in files:
			if pattern_find(file, file_matchers):
				paths.append(os.path.join(root, file))
	return paths


def millijoules_to_joules(val):
	return val/1000


def joules_to_milliwatts(energy_consumed, time_in_seconds):
	return energy_consumed/time_in_seconds


def joules_to_milliwatthours(energy_in_joules):
	return energy_in_joules/3.6
