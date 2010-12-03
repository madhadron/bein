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

@program
def sort_bam(bamfile):
    filename = unique_filename_in()
    return {'arguments': ['samtools','sort',bamfile,filename],
            'return_value': filename + '.bam'}

@program
def index_bam(bamfile):
    return {'arguments': ['samtools','index',bamfile],
            'return_value': bamfile + '.bai'}

def add_and_index_bam(ex, bamfile, description=""):
    sort = sort_bam(ex, bamfile)
    index = index_bam(ex, sort)
    fileid = ex.add(sort, description=description)
    ex.add(index, description=description + " (BAM index)",
           associate_to_filename=sort, template='%s.bai')
    return fileid

@program
def merge_bamfiles(files):
    filename = unique_filename_in()
    args = ['samtools','merge',filename]
    args.extend(files)
    return {'arguments': args,
            'return_value': filename}

@program
def bowtie_build(files, index = None):
    if index == None:
        index = unique_filename_in()
    if isinstance(files,list):
        files = ",".join(files)
    return {'arguments': ['bowtie-build', '-f', files, index],
            'return_value': index}

def add_bowtie_index(ex, files, description="", alias=None, index=None):
    index = bowtie_build(ex, files, index=index)
    touch(ex, index)
    ex.add(index, description=description, alias=alias)
    ex.add(index + ".1.ebwt", associate_to_filename=index, template='%s.1.ebwt')
    ex.add(index + ".2.ebwt", associate_to_filename=index, template='%s.2.ebwt')
    ex.add(index + ".3.ebwt", associate_to_filename=index, template='%s.3.ebwt')
    ex.add(index + ".4.ebwt", associate_to_filename=index, template='%s.4.ebwt')
    ex.add(index + ".rev.1.ebwt", associate_to_filename=index, template='%s.rev.1.ebwt')
    ex.add(index + ".rev.2.ebwt", associate_to_filename=index, template='%s.rev.2.ebwt')
    return index
