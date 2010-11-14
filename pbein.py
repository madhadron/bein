import subprocess
import random
import string
import os
import sqlite3
import time
import shutil
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
    return (["bowtie", "-Sra", index, reads,sam_filename], 4)

@program
def sam_to_bam(sam_filename):
    bam_filename = unique_filename_in(os.getcwd())
    return (["samtools","view","-b","-S","-o",bam_filename,sam_filename], 5)

@program
def touch():
    filename = unique_filename_in(os.getcwd())
    return (["touch",filename],1)

class Execution(object):
    def __init__(self, lims, exwd):
        self.lims = lims
        self.exwd = exwd
        self.programs = []
        self.files = []
        self.started_at = int(time.time())
        self.finished_at = None
    def report(self, program):
        self.programs.append(program)
    def add(self, file_name, description=""):
        self.files.append((file_name,description))
    def finish(self):
        self.finished_at = int(time.time())
    def use(self, fileid):
        return [x for (x,) in self.lims.db.execute("select exportfile(?,?)", (fileid, self.exwd))][0]
        

@contextmanager
def execution(lims = None):
    execution_dir = unique_filename_in(os.getcwd())
    os.mkdir(os.path.join(os.getcwd(), execution_dir))
    ex = Execution(lims,os.path.join(os.getcwd(), execution_dir))
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
        self.db.create_function("importfile",1,self.copy_file_to_repository)
        self.db.create_function("deletefile",1,self.delete_repository_file)
        self.db.create_function("exportfile",2,self.export_file_from_repository)

    def initialize_database(self, db):
        self.db.execute("""
        CREATE TABLE execution ( 
             id integer primary key, 
             started_at integer not null, 
             finished_at integer default null,
             working_directory text not null, 
             description text not null default '' 
        )""")
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
        )""")
        self.db.execute("""
        CREATE TABLE argument (
               pos integer,
               program integer references program(pos),
               execution integer references program(execution),
               argument text not null,
               primary key (pos,program,execution)
        )""")
        self.db.execute("""
        CREATE TABLE file ( 
               id integer primary key autoincrement, 
               external_name text, 
               repository_name text,
               created timestamp default current_timestamp, 
               description text not null default '',
               origin text not null default 'execution', 
               origin_value integer default null
        )""")

        self.db.commit()
        self.db.execute("""
        CREATE TRIGGER prevent_repository_name_change BEFORE UPDATE ON file
        FOR EACH ROW WHEN (OLD.repository_name != NEW.repository_name) BEGIN
             SELECT RAISE(FAIL, 'Cannot change the repository name of a file.');
        END""")

    def copy_file_to_repository(self,src):
        filename = unique_filename_in(self.file_path)
        shutil.copyfile(src,os.path.abspath(os.path.join(self.file_path,filename)))
        return filename

    def delete_repository_file(self,filename):
        os.remove(os.path.join(self.file_path,filename))
        return None

    def export_file_from_repository(self,fileid,dst):
        filename = unique_filename_in(dst)
        try:
            [repository_filename] = [x for (x,) in self.db.execute("select repository_name from file where id=?", 
                                                                   (fileid,))]
            shutil.copyfile(os.path.abspath(os.path.join(self.file_path,repository_filename)),
                            os.path.abspath(os.path.join(dst, filename)))
            return filename
        except ValueError, v:
            return None

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
        for (filename,description) in ex.files:
            self.db.execute("""insert into file(external_name,repository_name,description,origin,origin_value) values (?,importfile(?),?,?,?)""",
                            (filename,os.path.abspath(os.path.join(ex.exwd,filename)),
                             description,'execution',exid))
        self.db.commit()
        return exid

m = MiniLims("test")
with execution(m) as ex:
#    f = bowtie(ex, index = '../test_data/selected_transcripts', reads = '../test_data/reads-1-1')
    f = touch(ex)
    ex.add(f, "Testing")
with execution(m) as ex:
    print ex.use(1)
    print ex.exwd
        

