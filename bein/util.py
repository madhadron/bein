from contextlib import contextmanager
import pickle
from pylab import *
import re
import sys
import os
from bein import *

@program
def bowtie(index, reads, args="-Sra"):
    sam_filename = unique_filename_in()
    return {"arguments": ["bowtie", args, index, reads,sam_filename],
            "return_value": sam_filename}

@program
def sam_to_bam(sam_filename):
    bam_filename = unique_filename_in()
    return {"arguments": ["samtools","view","-b","-S","-o",
                          bam_filename,sam_filename],
            "return_value": bam_filename}

def pause():
    sys.stdin.readline()
    return None

@program
def touch(filename = None):
    if filename == None:
        filename = unique_filename_in()
    return {"arguments": ["touch",filename],
            "return_value": filename}

@program
def sleep(n):
    return {"arguments": ["sleep", str(n)],
            "return_value": lambda q: n}

@program
def count_lines(filename):
    def parse_output(p):
        m = re.search(r'^\s+(\d+)\s+' + filename,
                      ''.join(p.stdout))
        return int(m.groups()[0])
    return {"arguments": ["wc","-l",filename],
            "return_value": parse_output}

@program
def split_file(filename, n_lines = 1000, prefix = None, suffix_length = 3):
    if prefix == None:
        prefix = unique_filename_in()
        def extract_filenames(p):
            return [re.search(r"creating file .(.+)'", x).groups()[0]
                    for x in p.stdout]
        return {"arguments": ["split", "--verbose", "-a", str(suffix_length),
                              "-l", str(n_lines), filename, prefix],
                "return_value": extract_filenames}

@program
def merge_samfiles(*files):
    filename = unique_filename_in()
    return {'arguments': ['samtools','merge',filename] + files,
            'return_value': filename}

def parallel_bowtie(ex, index, reads, args="-Sra"):
    subfiles = split_file(ex, reads)
    futures = [bowtie.nonblocking(ex, index, sf, args) for sf in subfiles]
    samfiles = [f.wait() for f in futures]
    return merge_samfiles(ex, samfiles)
    

def add_pickle(ex, val, description=""):
    filename = unique_filename_in()
    with open(filename, 'wb') as f:
        pickle.dump(val, f)
    ex.add(filename, description)

@contextmanager
def add_figure(ex, figure_type='eps', description=""):
    f = figure()
    yield f
    filename = unique_filename_in() + '.' + figure_type
    f.savefig(filename)
    ex.add(filename, description)
