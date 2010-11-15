"""bein - LIMS and workflow manager for bioinformatics
by Frederick Ross <madhadron@gmail.com>

Bein contains a miniature LIMS (Laboratory Information Management System) and a workflow manager.  It was written for the Bioinformatics and Biostatistics Core Facility of the Ecole Polytechnique Federale de Lausanne.  It is aimed at processes just complicated enough where the Unix shell becomes problematic, but not so large as to justify all the machinery of big workflow managers like KNIME or Galaxy.

There are three core classes you need to understand:

program
-------
Programs are functions which are turned into callable objects by the @program decorator.  They provide a very clean way of binding programs into bein so that all the machinery of workflow management and LIMS functions properly.

execution
---------
The actual class is Execution, but it is generally created with the execution contextmanager.  An execution tracks all the information about a run of a given set of programs.  It corresponds roughly to a script in shell.

Executions are run in a temporary directory.  The execution provides methods to pull in files from the LIMS for use, write files back to the LIMS, and tracks all arguments, pids, outputs, and exit codes of programs run during the execution.

MiniLIMS
* Database and file directory object.  Never edit a MiniLIMS repository by hand.
"""
import subprocess
import random
import string
import os
import sqlite3
import time
import shutil
import threading
from contextlib import contextmanager

# miscellaneous types

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


# programs

class program(object):
    """Decorator to wrap make programs for use by bein.

    * One paragraph overview of what's going on
    * How to wrap a function
    * How to call a wrapped function

    The decorated function should return a two element tuple.  The
    first element is a list of strings giving the command and
    arguments to run.  The second is the position in that tuple that
    should be returned if the program exits with return code 0.

    An extra argument is inserted before the argument list of the
    generated function, which takes an execution.

    For example,
    @program
    def touch(filename):
        return (["touch",filename], 1)
    """
    def __init__(self, gen_args):
        self.gen_args = gen_args

    def __call__(self, ex, *args):
        """Run a program locally, and block until it completes.

        In addition to the arguments to the decorated function, the
        program object created by a decorator takes an Execution
        object as an extra argument at the beginning of the argument
        list.

        * Add stuff about recording to execution object.
        """
        (cmds,n) = self.gen_args(*args)
        sp = subprocess.Popen(cmds, bufsize=-1, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd = ex.exwd)
        return_code = sp.wait()
        ex.report(ProgramOutput(return_code, sp.pid,
                                cmds, 
                                sp.stdout.readlines(),   # stdout and stderr
                                sp.stderr.readlines()))  # are lists of strings ending with newlines
        if return_code == 0:
            return cmds[n]
        else: 
            raise ProgramFailed(ProgramOutput(return_code, sp.pid, cmds, 
                                              sp.stdout.readlines(), 
                                              sp.stderr.readlines()))

    def nonblocking(self, ex, *args):
        """Run a program locally, but return a Future object instead of blocking.

        Like __call__, takes an Execution as an extra, initial
        argument before the arguments to the decorated function.
        Instead of blocking until the program completes, it runs it in
        a separate thread, and returns a Future object which lets you
        block when you wish.  The future object has a method wait().
        When called, it blocks until the program finishes running,
        then returns the same value as __call__ would have.
        """
        (cmds,n) = self.gen_args(*args)
        class Future(object):
            def __init__(self):
                self.program_output = None
                self.return_value = None
            def wait(self):
                v.wait()
                ex.report(self.program_output)
                return self.return_value
        f = Future()
        v = threading.Event()
        def g():
            sp = subprocess.Popen(cmds, bufsize=-1, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  cwd = ex.exwd)
            return_code = sp.wait()
            f.program_output = ProgramOutput(return_code, sp.pid,
                                             cmds, 
                                             sp.stdout.readlines(), 
                                             sp.stderr.readlines())
            if return_code == 0:
                f.return_value = cmds[n]
            v.set()
        a = threading.Thread(target=g)
        a.start()
        return(f)

    def lsf(self, ex, *args):
        """Run a program via the LSF batch queue, but do not block locally.

        For the programmer, this call appears identical to
        nonblocking, except that the program is run via the LSF batch
        system (using the bsub command).  A Future object is returned
        with the same properties as for nonblocking.
        """
        (cmds,n) = self.gen_args(*args)
        stdout_filename = unique_filename_in(ex.exwd)
        stderr_filename = unique_filename_in(ex.exwd)
        cmds = ["bsub","-cwd",ex.exwd,"-o",stdout_filename,"-e",stderr_filename,
                "-K","-r"] + cmds
        n += 9
        class Future(object):
            def __init__(self):
                self.program_output = None
                self.return_value = None
            def wait(self):
                v.wait()
                ex.report(self.program_output)
                return self.return_value
        f = Future()
        v = threading.Event()
        def g():
            sp = subprocess.Popen(cmds, bufsize=-1)
            return_code = sp.wait()
            stdout = None
            stderr = None
            with open(os.path.join(ex.exwd,stdout_filename), 'r') as fo:
                stdout = fo.readlines()
            with open(os.path.join(ex.exwd,stderr_filename), 'r') as fe:
                stderr = fe.readlines()
            f.program_output = ProgramOutput(return_code, sp.pid,
                                             cmds, stdout, stderr)
            if return_code == 0:
                f.return_value = cmds[n]
            v.set()
        a = threading.Thread(target=g)
        a.start()
        return(f)


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
        return [x for (x,) in self.lims.db.execute("select exportfile(?,?)", 
                                                   (fileid, self.exwd))][0]


@contextmanager
def execution(lims = None):
    execution_dir = unique_filename_in(os.getcwd())
    os.mkdir(os.path.join(os.getcwd(), execution_dir))
    ex = Execution(lims,os.path.join(os.getcwd(), execution_dir))
    yield ex
    ex.finish()
    if lims != None:
        lims.write(ex)
    shutil.rmtree(ex.exwd)


# MiniLIMS


class MiniLIMS:
    """Encapsulates a database and directory to track executions and files.

    Tries to check if it doesn't exist, and creates it if not.  Format of the LIMS repository: name (an SQLite3 database) and name.files (a directory containing the files it refers to).  You should never edit the files directory by hand or you may leave the database inconsistent.

    Give structure of the tables: execution, program, argument, and file.  Make a couple remarks about the triggers.

    Adds Python functions to it (you can't really use the LIMS sensibly without them, so it's limited to Python.  You can easily add your own versions.  The functions are importfile, deletefile, and exportfile.  Give their behaviors.

    'write' writes an execution to the LIMS, including adding files from its working directory.

    search_files looks up files in the LIMS
    """
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
        """Sets up a new MiniLIMS database.

        """
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
        self.db.execute("""
        CREATE TRIGGER prevent_repository_name_change BEFORE UPDATE ON file
        FOR EACH ROW WHEN (OLD.repository_name != NEW.repository_name) BEGIN
             SELECT RAISE(FAIL, 'Cannot change the repository name of a file.');
        END""")
        self.db.commit()

    def copy_file_to_repository(self,src):
        """Copy a file src into the MiniLIMS repository.
        
        src can be a fairly arbitrary path, either from the CWD, or
        using .. and other such shortcuts.  This function should only
        be called from SQLite3, not Python.
        """
        filename = unique_filename_in(self.file_path)
        shutil.copyfile(src,os.path.abspath(os.path.join(self.file_path,filename)))
        return filename

    def delete_repository_file(self,filename):
        """Delete a file from the MiniLIMS repository.

        This function should only be called from SQLite3, not from Python.
        """
        os.remove(os.path.join(self.file_path,filename))
        return None

    def export_file_from_repository(self,fileid,dst):
        """Write a file with id fileid to the directory dst.

        This function should only be called from SQLite3, not Python.
        """
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
        """Write an execution to the MiniLIMS.

        Give some details about where things are written.
        """
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

    def search_files(self, with_text=None, older_than=None, newer_than=None, source=None):
        """Find files matching given criteria in the LIMS.

        source should be a 2-tuple of ('execution',id), etc.  Explain the other fields.
        """
        source = source != None and source or (None,None)
        with_text = with_text != None and '%' + with_text + '%' or None
        sql = """select id from file where ((external_name like ? or ? is null)
                                            or (description like ? or ? is null))
                                          and (created >= ? or ? is null)
                                          and (created <= ? or ? is null)
                 and ((origin = ? and origin_value = ?) or ? is null or ? is null)"""
        matching_files = self.db.execute(sql, (with_text, with_text,
                                               with_text, with_text,
                                               newer_than, newer_than, older_than, older_than,
                                               source[0], source[1], source[0], source[1]))
        return [x for (x,) in matching_files]

    def search_executions(self, with_text=None, started_before=None, started_after=None, ended_before=None, ended_after=None):
        with_text = with_text != None and '%'+with_text+'%' or None
        sql = """select id from execution where 
                 (started_at <= ? or ? is null) and (started_at >= ? or ? is null) and
                 (finished_at <= ? or ? is null) and (finished_at >= ? or ? is null) and
                 (description like ? or ? is null)
              """
        matching_executions = [x for (x,) in self.db.execute(sql, (started_before, started_before,
                                                                   started_after, started_after,
                                                                   ended_before, ended_before,
                                                                   ended_after, ended_after,
                                                                   with_text, with_text))]
        if with_text != None:
            sql = """select distinct execution from argument where argument like ?"""
            matching_programs = [x for (x,) in self.db.execute(sql, (with_text,))]
        else:
            matching_programs = []
        return list(set(matching_executions+matching_programs))

    def copy_file(self, fileid):
        try:
            [(external_name, repository_name, description)] = [x for x in self.db.execute("select external_name,repository_name,description from file where id = ?", (fileid, ))]
            new_repository_name = unique_filename_in(self.file_path)
            [x for x in self.db.execute("insert into file(external_name,repository_name,origin,origin_value) values (?,?,?,?)",
                                        (external_name, new_repository_name, 'copy', fileid))]
            [new_id] = [x for (x,) in self.db.execute("select last_insert_rowid()")]
            shutil.copyfile(os.path.join(self.file_path, repository_name),
                            os.path.join(self.file_path, new_repository_name))
            self.db.commit()
            return new_id
        except ValueError, v:
            raise ValueError("No such file id " + str(fileid))


def get_ex():
    m = MiniLIMS("test")
    with execution(m) as ex:
# #    f = bowtie(ex, '../test_data/selected_transcripts', '../test_data/reads-1-1')
        f = touch(ex)
    return ex
     
#     g = sleep.lsf(ex,1)
#     ex.add(f, "Testing")
#     print g.wait()
    
#with execution(m) as ex:
#     print ex.use(1)
#     print ex.exwd
        

# Program library

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


@program
def sleep(n):
    return (["sleep", str(n)],0)

