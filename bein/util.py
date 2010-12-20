# bein/util.py
# Copyright 2010, Frederick Ross

# This file is part of bein.

# Bein is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your
# option) any later version.

# Bein is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# You should have received a copy of the GNU General Public License
# along with bein.  If not, see <http://www.gnu.org/licenses/>.
"""
:mod:`bein.util` -- Library of functions for bein
=================================================

.. module:: bein.util
   :platform: Unix
   :synopsis: Useful programs and utilities for bein
.. moduleauthor:: Fred Ross <madhadron at gmail dot com>

This module is a repository of assorted robust functions that have
been developed for bein in day to day use.  Much of it is focused on
analysis of high throughput sequencing data, but if you have useful
functions for a different domain, please contribute them.
"""

from contextlib import contextmanager
import pickle
import pylab
import re
import sys
import os
from bein import *
import pysam

# Basic utilities


def pause():
    """Pause until the user hits Return."""
    sys.stdin.readline()
    return None


@program
def touch(filename = None):
    """Equivalent to shell: ``touch filename``

    Returns *filename*.  If filename is ``None``, *filename* is set to
    a unique, random name.
    """
    if filename == None:
        filename = unique_filename_in()
    return {"arguments": ["touch",filename],
            "return_value": filename}


@program
def sleep(n):
    """Sleep for *n* seconds.  Returns *n*."""
    return {"arguments": ["sleep", str(n)],
            "return_value": n}


@program
def count_lines(filename):
    """Count the number of lines in *filename* (equivalent to ``wc -l``)."""
    def parse_output(p):
        m = re.search(r'^\s*(\d+)\s+' + filename + r'\s*$',
                      ''.join(p.stdout))
        return int(m.groups()[-1]) # in case of a weird line in LSF
    return {"arguments": ["wc","-l",filename],
            "return_value": parse_output}


@program
def split_file(filename, n_lines = 1000, prefix = None, suffix_length = 3):
    """Equivalent to Unix command ``split``.

    *filename* is the file to split.  Returns a list of the names of
    the new files created.  *n_lines* is the number of lines to put in
    each file, *prefix* is the file prefix to use (which is set to a
    unique, randomly chosen string if not specified), and
    *suffix_length* is the number of positions to use after the prefix
    to label the files.
    """
    if prefix == None:
        prefix = unique_filename_in()
    def extract_filenames(p):
        return [re.search(r"creating file .(.+)'", x).groups()[0]
                for x in p.stdout]
    return {"arguments": ["split", "--verbose", "-a", str(suffix_length),
                          "-l", str(n_lines), filename, prefix],
            "return_value": extract_filenames}


########
# Bowtie
########

@program
def bowtie(index, reads, args="-Sra"):
    """Run bowtie with *args* to map *reads* against *index*.

    Returns the filename of bowtie's output file.  *args* gives the
    command line arguments to bowtie, and may be either a string or a
    list of strings.
    """
    sam_filename = unique_filename_in()
    if isinstance(args, list):
        options = args
    elif isinstance(args, str):
        options = [args]
    else:
        raise ValueError("bowtie's args keyword argument requires a string or a " + \
                         "list of strings.  Received: " + str(args))
    if isinstance(reads, list):
        reads = ",".join(reads)
    return {"arguments": ["bowtie"] + options + [index, reads, sam_filename],
            "return_value": sam_filename}


@program
def bowtie_build(files, index = None):
    """Created a bowtie index from *files*.

    *files* can be a string giving the name of a FASTA file, or a list
    of strings giving the names of several FASTA files.  The prefix of
    the resulting bowtie index is returned.
    """
    if index == None:
        index = unique_filename_in()
    if isinstance(files,list):
        files = ",".join(files)
    return {'arguments': ['bowtie-build', '-f', files, index],
            'return_value': index}


def parallel_bowtie(ex, index, reads, n_lines = 1000000, bowtie_args="-Sra", add_nh_flags=False):
    """Run bowtie in parallel on pieces of *reads*.

    Splits *reads* into chunks *n_lines* long, then runs bowtie with
    arguments *bowtie_args* to map each chunk against *index*.  One of
    the arguments needs to be -S so the output takes the form of SAM
    files, because the results are converted to BAM and merged.  The
    filename of the single, merged BAM file is returned.

    Bowtie does not set the NH flag on its SAM file output.  If the
    *add_nh_flags* argument is ``True``, this function calculates
    and adds the flag before merging the BAM files.
    """
    subfiles = split_file(ex, reads, n_lines = n_lines)
    futures = [bowtie.nonblocking(ex, index, sf, args = bowtie_args) for sf in subfiles]
    samfiles = [f.wait() for f in futures]
    if add_nh_flags:
        bamfiles = [add_nh_flag(sf) for sf in samfiles]
    else:
        futures = [sam_to_bam.nonblocking(ex, sf) for sf in samfiles]
        bamfiles = [f.wait() for f in futures]
    return merge_bam.nonblocking(ex, bamfiles).wait()

def parallel_bowtie_lsf(ex, index, reads, n_lines = 1000000, bowtie_args="-Sra", add_nh_flags=False):
    """Identical to parallel_bowtie, but runs programs via LSF."""
    subfiles = split_file(ex, reads, n_lines = n_lines)
    futures = [bowtie.lsf(ex, index, sf, args = bowtie_args) for sf in subfiles]
    samfiles = [f.wait() for f in futures]
    if add_nh_flags:
        bamfiles = [add_nh_flag(sf) for sf in samfiles]
    else:
        futures = [sam_to_bam.lsf(ex, sf) for sf in samfiles]
        bamfiles = [f.wait() for f in futures]
    return merge_bam.lsf(ex, bamfiles).wait()

###############
# BAM/SAM files
###############
@program
def sam_to_bam(sam_filename):
    """Convert *sam_filename* to a BAM file.

    *sam_filename* must obviously be the filename of a SAM file.
    Returns the filename of the created BAM file.

    Equivalent: ``samtools view -b -S -o ...``
    """
    bam_filename = unique_filename_in()
    return {"arguments": ["samtools","view","-b","-S","-o",
                          bam_filename,sam_filename],
            "return_value": bam_filename}

@program
def sort_bam(bamfile):
    """Sort a BAM file *bamfile*.

    Returns the filename of the newly created, sorted BAM file.

    Equivalent: ``samtools sort ...``
    """
    filename = unique_filename_in()
    return {'arguments': ['samtools','sort',bamfile,filename],
            'return_value': filename + '.bam'}


@program
def index_bam(bamfile):
    """Index a sorted BAM file.

    Returns the filename in *bamfile* with ``.bai`` appended, that is,
    the filename of the newly created index.  *bamfile* must be sorted
    for this to work.

    Equivalent: ``samtools index ...``
    """
    return {'arguments': ['samtools','index',bamfile],
            'return_value': bamfile + '.bai'}


@program
def merge_bam(files):
    """Merge a list of BAM files.

    *files* should be a list of filenames of BAM files.  They are
    merged into a single BAM file, and the filename of that new file
    is returned.
    """
    filename = unique_filename_in()
    return {'arguments': ['samtools','merge',filename] + files,
            'return_value': filename}

def split_by_readname(samfile):
    """Return an iterator over the reads in *samfile* grouped by read name.

    The SAM file produced by bowtie is sorted by read name.  Often we
    want to work with all of the alignments of a particular read at
    once.  This function turns the flat list of reads into a list of
    lists of reads, where each sublist has the same read name.
    """
    last_read = None
    for r in samfile:
        if r.qname != last_read:
            if last_read != None:
                yield accum
            accum = [r]
            last_read = r.qname
        else:
            accum.append(r)
    if last_read != None:
        # We have to check, since if samfile
        # has no alignments, accum is never defined.
        yield accum

def add_nh_flag(samfile):
    """Adds NH (Number of Hits) flag to each read alignment in *samfile*.
    
    Scans a TAM file ordered by read name, counts the number of
    alternative alignments reported and writes them to a BAM file
    with the NH tag added.
    """
    infile = pysam.Samfile(samfile, "r")
    outname = unique_filename_in()
    outfile = pysam.Samfile(outname, "wb", template=infile)
    for readset in split_by_readname(infile):
        nh = len(readset)
        for read in readset:
            if (read.is_unmapped):
                nh = 0
            read.tags = read.tags+[("NH",nh)]
            outfile.write(read)
    infile.close()
    outfile.close()
    return outname

# Adding special file types


def add_pickle(execution, val, description="", alias=None):
    """Pickle *val*, and add it to the repository.

    add_pickle lets you dump almost any Python value to a file in the
    MiniLIMS repository.  It is useful to keep track of intermediate
    calculations.  *description* will be set as the pickle file's
    description.
    """
    filename = unique_filename_in()
    with open(filename, 'wb') as f:
        pickle.dump(val, f)
    execution.add(filename, description=description, alias=None)
    return filename


@contextmanager
def add_figure(ex, figure_type='eps', description="", alias=None, figure_size=None):
    """Create a matplotlib figure and write it to the repository.

    Use this as a with statement, for instance::

        with add_figure(ex, 'eps') as fig:
            hist(a)
            xlabel('Random things I found')

    This will plot a histogram of a with the x axis label set, and
    write the plot to the repository as an EPS file.
    """
    f = pylab.figure(figsize=figure_size)
    yield f
    filename = unique_filename_in() + '.' + figure_type
    f.savefig(filename)
    ex.add(filename, description=description, alias=alias)


def add_and_index_bam(ex, bamfile, description="", alias=None):
    """Indexes *bamfile* and adds it to the repository.

    The index created is properly associated to *bamfile* in the
    repository, so when you use the BAM file later, the index will
    also be copied into place with the correct name.
    """
    sort = sort_bam(ex, bamfile)
    index = index_bam(ex, sort)
    ex.add(sort, description=description, alias=alias)
    ex.add(index, description=description + " (BAM index)",
           associate_to_filename=sort, template='%s.bai')
    return sort


def add_bowtie_index(execution, files, description="", alias=None, index=None):
    """Adds an index of a list of FASTA files to the repository.

    *files* is a list of filenames of FASTA files.  The files are
    indexed with bowtie-build, then a placeholder is written to the
    repository, and the six files of the bowtie index are associated
    to it.  Using the placeholder in an execution will properly set up
    the whole index.

    *alias* is an optional alias to give to the whole index so it may
    be referred to by name in future.  *index* lets you set the actual
    name of the index created.
    """
    index = bowtie_build(execution, files, index=index)
    touch(execution, index)
    execution.add(index, description=description, alias=alias)
    execution.add(index + ".1.ebwt", associate_to_filename=index, template='%s.1.ebwt')
    execution.add(index + ".2.ebwt", associate_to_filename=index, template='%s.2.ebwt')
    execution.add(index + ".3.ebwt", associate_to_filename=index, template='%s.3.ebwt')
    execution.add(index + ".4.ebwt", associate_to_filename=index, template='%s.4.ebwt')
    execution.add(index + ".rev.1.ebwt", associate_to_filename=index, template='%s.rev.1.ebwt')
    execution.add(index + ".rev.2.ebwt", associate_to_filename=index, template='%s.rev.2.ebwt')
    return index
