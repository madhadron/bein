import subprocess
import random
import string
import os
import sqlite3
import time
from contextlib import contextmanager

class program(object):
    def __init__(self, gen_args):
        self.gen_args = gen_args
    def __call__(self, ex, *args):
        (cmds,n) = self.gen_args(*args)
        sp = subprocess.Popen(cmds, bufsize=-1, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd = ex.exwd)
        return_code = sp.wait()
        ex.report(ProgramOutput(return_code, sp.pid,
                                cmds, 
                                sp.stdout.readlines(), 
                                sp.stderr.readlines()))
        if return_code == 0:
            return cmds[n]
        else: 
            raise ProgramFailed(ProgramOutput(return_code, cmds, 
                                              sp.stdout.readlines(), 
                                              sp.stderr.readlines()))
    def __lsf__(self, ex, *args):
        pass

class ProgramOutput(object):
    def __init__(self, return_code, pid, arguments, stdout, stderr):
        self.return_code = return_code
        self.pid = pid
        self.arguments = arguments
        self.stdout = stdout
        self.stderr = stderr

class ProgramFailed(Exception):
    def __init__(self, output):
        self.output = output

def unique_filename_in(path):
    def random_string():
        return "".join([random.choice(string.letters + string.digits) 
                        for x in range(20)])
    filename = random_string()
    while os.path.exists(os.path.join(path,filename)):
        filename = random_string()
    return filename

@program
def bowtie(index, reads):
    sam_filename = unique_filename_in(os.getcwd())
    return (["bowtie", "-Sra", index, reads,sam_filename], 2)

@program
def sam_to_bam(sam_filename):
    bam_filename = unique_filename_in(os.getcwd())
    return (["samtools","view","-b","-S","-o",bam_filename,sam_filename], 5)

class Execution(object):
    def __init__(self, exwd):
        self.exwd = exwd
        self.programs = []
        self.started_at = int(time.time())
        self.finished_at = None
    def report(self, program):
        self.programs.append(program)
    def finish(self):
        self.finished_at = int(time.time())
        

@contextmanager
def execution(lims = None):
    execution_dir = unique_filename_in(os.getcwd())
    os.mkdir(os.path.join(os.getcwd(), execution_dir))
    ex = Execution(os.path.join(os.getcwd(), execution_dir))
    yield ex
    ex.finish()
    if lims != None:
        lims.write(ex)

class MiniLims:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.file_path = path +".files"
        if not(os.path.exists(self.file_path)):
            self.initialize_database(self.db)
            os.mkdir(self.file_path)

    def initialize_database(self, db):
        self.db.execute("""
        CREATE TABLE execution ( 
             id integer primary key, 
             started_at integer not null, 
             finished_at integer default null,
             working_directory text not null, 
             description text not null default '' 
        );""")
        self.db.execute("""
        CREATE TABLE program (
               pos integer,
               execution integer references execution(id),
               pid integer not null,
               stdin text default null,
               return_code integer not null,
               stdout text default null,
               stderr text default null,
               primary key (pos,execution)
        );""")
        self.db.execute("""
        CREATE TABLE argument (
               pos integer,
               program integer references program(pos),
               execution integer references program(execution),
               argument text not null,
               primary key (pos,program,execution)
        );""")

    def write(self, ex, description = ""):
        """Write an execution to the miniLims"""
        self.db.execute("""
                        insert into execution(started_at,finished_at,
                                              working_directory,description) 
                        values (?,?,?,?)""",
                        (ex.started_at, ex.finished_at, ex.exwd, description))
        [exid] = [x for (x,) in self.db.execute("select last_insert_rowid()")]
        for i,p in enumerate(ex.programs):
            self.db.execute("""insert into program(pos,execution,pid,return_code,stdout,stderr) values (?,?,?,?,?,?)""",
                            (i, exid, p.pid, p.return_code,
                             "".join(p.stdout), "".join(p.stderr)))
            [prid] = [x for (x,) in self.db.execute("select last_insert_rowid()")]
            for j,a in enumerate(p.arguments):
                self.db.execute("""insert into argument(pos,program,execution,argument) values (?,?,?,?)""",
                                (j,prid,exid,a))
        self.db.commit()
        return exid

m = MiniLims("test")
with execution(m) as ex:
    print(bowtie(ex,'../test_data/selected_transcripts','../test_data/reads-1-1'))

        

