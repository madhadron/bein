"""Store commands for memoize"""
import os
import shutil
import cPickle

from bein import unique_filename_in

class value(object):
    @classmethod
    def serialize(self, ex, value):
        pickle_filename = unique_filename_in(ex.lims.memopad_path)
        with open(os.path.join(ex.lims.memopad_path, pickle_filename), 'w') as pickle_file:
            cPickle.dump(value, pickle_file)
        return pickle_filename

    @classmethod
    def restore(self, ex, filename):
        with open(filename) as f:
            v = cPickle.load(f)
        return v


class file(object):
    @classmethod
    def serialize(self, ex, value):
        file_to_copy = os.path.join(ex.working_directory, value)
        target_filename = unique_filename_in(ex.lims.memopad_path)
        shutil.copyfile(file_to_copy, os.path.join(ex.lims.memopad_path, target_filename))
        return target_filename

    @classmethod
    def restore(self, ex, filename):
        target_filename = unique_filename_in(ex.working_directory)
        shutil.copyfile(os.path.join(ex.lims.memopad_path, filename),
                        os.path.join(ex.working_directory, target_filename))
        return target_filename
