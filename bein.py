"""bein - LIMS and workflow manager for bioinformatics
by Frederick Ross <madhadron@gmail.com>

Bein contains a miniature LIMS (Laboratory Information Management
System) and a workflow manager.  It was written for the Bioinformatics
and Biostatistics Core Facility of the Ecole Polytechnique Federale de
Lausanne.  It is aimed at processes just complicated enough where the
Unix shell becomes problematic, but not so large as to justify all the
machinery of big workflow managers like KNIME or Galaxy.

There are three core classes you need to understand:

program
-------
Programs are functions which are turned into callable objects by the
@program decorator.  They provide a very clean way of binding programs
into bein so that all the machinery of workflow management and LIMS
functions properly.

execution
---------
The actual class is Execution, but it is generally created with the
execution contextmanager.  An execution tracks all the information
about a run of a given set of programs.  It corresponds roughly to a
script in shell.

Executions are run in a temporary directory.  The execution provides
methods to pull in files from the LIMS for use, write files back to
the LIMS, and tracks all arguments, pids, outputs, and exit codes of
programs run during the execution.

MiniLIMS
--------
MiniLIMS represents a database and a directory of files.  The database
stores metainformation about the files and records all executions run
with this LIMS.  You can go back and examine the return code, stdout,
stderr, imported files, etc. from any execution.
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

    Bein depends on external programs to do all its work.  In this
    sense, it's a strange version of a shell.  To make it easy to bind
    programs (generally one or two lines), we provide the @program
    decorator.

    To wrap a program, write a function that takes whatever arguments
    you will need to vary in calling the program (for instance, the
    filename for touch or the number of seconds to sleep for sleep).
    This function should return a dictionary containing two keys,
    "arguments" and "return_value".  "arguments" should point to a
    list of strings which is the actual command and arguments to be
    executed (["touch",filename] for touch, for instance).
    "return_value" should point to a value to return, or a callable
    object which takes a ProgramOutput object and returns the value
    that will be passed back to the user when this program is run.

    For example, to wrap touch, we write a one argument function that
    takes the filename of the file to touch, and apply the @program
    decorator to it.

    @program
    def touch(filename):
        return {"arguments": ["touch",filename],
                "return_value": filename}

    Once we have such a function, how do we call it?  We can call it
    directly, but @program inserts an additional argument at the
    beginning of the argument list to take the execution the program
    is run in.  Typically it will be run like

    with execution(lims) as ex:
        touch(ex, "myfile")

    lims is a MiniLIMs object.  The ProgramOutput of touch is
    automatically recorded to the execution 'ex' and stored in the
    MiniLIMS.  The value returned by touch is "myfile", the name of
    the touched file.

    Often you want to call a function, but not block when it returns
    so you can run several in parallel.  @program also creates a
    method 'nonblocking' which does this.  The return value is a
    Future object with a single method: wait().  When you call wait(),
    it blocks until the program finishes, then returns the same value
    that you would get from calling the function directly.  So to
    touch two files, and not block until both commands have started,
    you would write,

    with execution(lims) as ex:
        a = touch.nonblocking(ex, "myfile1")
        b = touch.nonblocking(ex, "myfile2")
        a.wait()
        b.wait()

    If you are on a system using the LSF batch submission system, you
    can also call the lsf method with exactly the same arguments as
    nonblocking to run the program as a batch job.

    with execution(lims) as ex:
        a = touch.lsf(ex, "myfile1")
        a.wait()
    """
    def __init__(self, gen_args):
        self.gen_args = gen_args

    def __call__(self, ex, *args):
        """Run a program locally, and block until it completes.

        This form takes one argument before those to the decorated
        function, an execution the program should be run as part of.
        The return_code, pid, stdout, stderr, and command arguments of
        the program are recorded to that execution, and thus to the
        MiniLIMS object.
        """
        d = self.gen_args(*args)
        sp = subprocess.Popen(d["arguments"], bufsize=-1, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd = ex.exwd)
        return_code = sp.wait()
        po = ProgramOutput(return_code, sp.pid,
                                d["arguments"], 
                                sp.stdout.readlines(),  # stdout and stderr
                                sp.stderr.readlines())  # are lists of strings ending with newlines
        ex.report(po)
        if return_code == 0:
            z = d["return_value"]
            if callable(z):
                return z(po)
            else:
                return z
        else: 
            raise ProgramFailed(po)

    def nonblocking(self, ex, *args):
        """Run a program, but return a Future object instead of blocking.

        Like __call__, nonblocking takes an Execution as an extra,
        initial argument before the arguments to the decorated
        function.  However, instead of blocking, it starts the program
        in a separate thread, and returns an object which lets the
        user choose when to wait for the program by calling its wait()
        method.  When wait() is called, the thread blocks, and the
        program is recorded in the execution and its value returned as
        if the use had called __call__ directory.  Thus,

        with execution(lims) as ex:
            f = touch("boris")

        is exactly equivalent to
        
        with execution(lims) as ex:
            a = touch.nonblocking("boris")
            f = a.wait()
        """
        d = self.gen_args(*args)
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
            sp = subprocess.Popen(d["arguments"], bufsize=-1, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  cwd = ex.exwd)
            return_code = sp.wait()
            f.program_output = ProgramOutput(return_code, sp.pid,
                                             d["arguments"], 
                                             sp.stdout.readlines(), 
                                             sp.stderr.readlines())
            if return_code == 0:
                z = d["return_value"]
                if callable(z):
                    f.return_value = z(f.program_output)
                else:
                    f.return_value = z
            v.set()
        a = threading.Thread(target=g)
        a.start()
        return(f)

    def lsf(self, ex, *args):
        """Run a program via the LSF batch queue.

        For the programmer, this method appears identical to
        nonblocking, except that the program is run via the LSF batch
        system (using the bsub command) instead of as a local
        subprocess.
        """
        d = self.gen_args(*args)
        stdout_filename = unique_filename_in(ex.exwd)
        stderr_filename = unique_filename_in(ex.exwd)
        cmds = ["bsub","-cwd",ex.exwd,"-o",stdout_filename,"-e",stderr_filename,
                "-K","-r"] + d["arguments"]
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
                z = d["return_value"]
                if callable(z):
                    f.return_value = z(f.program_output)
                else:
                    f.return_value = z
            v.set()
        a = threading.Thread(target=g)
        a.start()
        return(f)


class Execution(object):
    """Execution objects hold the state of a current running execution.
    
    You should generally use the execution function below to create an
    Execution, since it sets up the working directory properly.

    Executions are run against a particular MiniLIMS object where it
    records all the information onf programs that were run during it,
    fetches files from it, and writes files back to it.

    The important methods for the user to know are 'add' and 'use'.
    Everything else is used internally by bein.  'add' puts a file
    into the LIMS repository from the execution's working directory.
    'use' fetches a file from the LIMS repository into the working
    directory.
    """
    def __init__(self, lims, exwd):
        self.lims = lims
        self.exwd = exwd
        self.programs = []
        self.files = []
        self.used_files = []
        self.started_at = int(time.time())
        self.finished_at = None
    def report(self, program):
        """Add a ProgramOutput object to the execution.

        When the Execution finishes, all programs added to the
        Execution with 'report', in the order the were added, are
        written into the MiniLIMS repository.
        """
        self.programs.append(program)
    def add(self, filename, description=""):
        """Add a file to the MiniLIMS object from this execution.

        filename is the name of the file in the execution's working
        directory to import.  description is an optional argument to
        assign a string to describe that file in the MiniLIMS
        repository.  The function returns an integer, the file id of
        the file in the MiniLIMS repository.

        Note that the file is not actually added to the repository
        until the execution finishes.
        """
        self.files.append((filename,description))
    def finish(self):
        """Set the time when the execution finished."""
        self.finished_at = int(time.time())
    def use(self, fileid):
        """Fetch a file from the MiniLIMS repository.

        fileid should be an integer assigned to a file in the MiniLIMS
        repository.  The file is copied into the execution's working
        directory with a unique filename.  'use' returns the unique
        filename it copied the file into.
        """
        try:
            filename = [x for (x,) in self.lims.db.execute("select exportfile(?,?)", 
                                                           (fileid, self.exwd))][0]
            self.used_files.append(fileid)
            return filename
        except ValueError, v:
            raise ValueError("Tried to use a nonexistent file id " + str(fileid))


@contextmanager
def execution(lims = None):
    """Create an Execution connected to the given MiniLIMS object.
    
    execution is a contextmanager, so it can be used in a with
    statement, as in,

    with execution(mylims) as ex:
        touch('boris')

    It creates a temporary directory where the execution will work and
    sets up the Execution object, then writes the Execution to the
    MiniLIMS repository and deletes the temporary directory after all
    is finished.
    """
    execution_dir = unique_filename_in(os.getcwd())
    os.mkdir(os.path.join(os.getcwd(), execution_dir))
    ex = Execution(lims,os.path.join(os.getcwd(), execution_dir))
    yield ex
    ex.finish()
    if lims != None:
        lims.write(ex)
    shutil.rmtree(ex.exwd)


class MiniLIMS:
    """Encapsulates a database and directory to track executions and files.

    A MiniLIMS repository consists of a SQLite database and a
    directory of the same name with '.files' appended where all files
    kept in the repository are stored.  For example, if the SQLite
    database is '/home/boris/myminilims', then there is a directory
    '/home/boris/myminilims.files' with all the corresponding files.
    You should never edit the repository by hand!.

    If you create a MiniLIMS object pointing to a nonexistent
    database, then it creates the database and the file directory.

    The MiniLIMS database has a set of tables 'execution', 'program',
    'argument', and 'execution_use' where Execution objects are
    recorded.  Each Execution object corresponds to a single id in the
    execution table.  There is also a table called 'file' which points
    to files added to the repository, and a number of views and
    triggers to maintain the repository's integrity.

    All the work of writing an Execution into the repository is done
    by the 'write' method.  Users should generally not call this.  In
    addition, several methods are meant for use by the database.  The
    methods a user should use are:

       * search_files
       * search_executions
       * copy_file
       * delete_file
       * delete_execution
       * import_file
       * export_file
    """
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.file_path = path +".files"
        if not(os.path.exists(self.file_path)):
            self.initialize_database(self.db)
            os.mkdir(self.file_path)
        self.db.create_function("importfile",1,self._copy_file_to_repository)
        self.db.create_function("deletefile",1,self._delete_repository_file)
        self.db.create_function("exportfile",2,self._export_file_from_repository)

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
        CREATE TABLE execution_use (
               execution integer references execution(id),
               file integer references file(id)
        )""")
        self.db.execute("""
        CREATE TRIGGER prevent_repository_name_change BEFORE UPDATE ON file
        FOR EACH ROW WHEN (OLD.repository_name != NEW.repository_name) BEGIN
             SELECT RAISE(FAIL, 'Cannot change the repository name of a file.');
        END""")
        self.db.execute("""
        CREATE VIEW file_immutability AS 
        SELECT file as id, count(execution) > 0 as immutable from execution_use group by file
        """)
        self.db.execute("""
        CREATE VIEW execution_outputs AS
        select execution.id as execution, file.id as file 
        from execution left join file 
        on execution.id = file.origin_value
        and file.origin='execution'
        """)
        self.db.execute("""
        CREATE VIEW execution_immutability AS
        SELECT eo.execution as id, ifnull(max(fi.immutable),0) from
        execution_outputs as eo left join file_immutability as fi
        on eo.file = fi.immutable
        group by id
        """)
        self.db.execute("""
        CREATE TRIGGER prevent_file_delete BEFORE DELETE ON file 
        FOR EACH ROW WHEN 
            (SELECT immutable FROM file_immutability WHERE id = OLD.id) = 1
        BEGIN
            SELECT RAISE(FAIL, 'File is immutable; cannot delete it.'); 
        END
        """)
        self.db.execute("""
        CREATE TRIGGER prevent_argument_delete BEFORE DELETE ON argument
        FOR EACH ROW WHEN 
            (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 
        BEGIN 
            SELECT RAISE(FAIL, 'Execution is immutable; cannot delete argument.'); 
        END	   
        """)
        self.db.execute("""
        CREATE TRIGGER prevent_argument_update BEFORE UPDATE ON argument
        FOR EACH ROW WHEN
            (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 
        BEGIN
            SELECT RAISE(FAIL, 'Execution is immutable; cannot update command arguments.'); 
        END
        """)
        self.db.execute("""
        CREATE TRIGGER prevent_command_delete BEFORE DELETE ON program
        FOR EACH ROW WHEN 
            (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 
        BEGIN
            SELECT RAISE(FAIL, 'Execution is immutable; cannot delete command.'); 
        END
        """)
        self.db.execute("""
        CREATE TRIGGER prevent_command_update BEFORE UPDATE ON program
        FOR EACH ROW WHEN 
            (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1
        BEGIN
            SELECT RAISE(FAIL, 'Execution is immutable; cannot update commands.'); 
        END
        """)
        self.db.execute("""
        CREATE TRIGGER prevent_execution_delete BEFORE DELETE ON execution 
        FOR EACH ROW WHEN
            (SELECT immutable FROM execution_immutability WHERE id = OLD.id) = 1
        BEGIN
            SELECT RAISE(FAIL, 'Execution is immutable; cannot delete.'); 
        END
        """)
        self.db.execute("""
        CREATE TRIGGER prevent_execution_update BEFORE UPDATE ON execution
        FOR EACH ROW WHEN
            (SELECT immutable FROM execution_immutability WHERE id = OLD.id) = 1 AND 
            (OLD.id != NEW.id OR OLD.started_at != NEW.started_at OR OLD.finished_at != NEW.finished_at
             OR OLD.temp_dir != NEW.temp_dir) 
        BEGIN
            SELECT RAISE(FAIL, 'Execution is immutable; cannot update anything but description.'); 
        END
        """)
        self.db.execute("""
        CREATE TRIGGER prevent_immutable_file_update BEFORE UPDATE on file 
        FOR EACH ROW WHEN 
            (SELECT immutable FROM file_immutability WHERE id = old.id) = 1 AND 
            (OLD.id != NEW.id OR OLD.external_name != NEW.external_name OR 
             OLD.repository_name != NEW.repository_name OR 
             OLD.created != NEW.created OR OLD.origin != NEW.origin OR 
             OLD.origin_value != NEW.origin_value) 
        BEGIN 
            SELECT RAISE(FAIL, 'File is immutable; cannot update except description.'); 
        END
        """)
        self.db.commit()

    def _copy_file_to_repository(self,src):
        """Copy a file src into the MiniLIMS repository.
        
        src can be a fairly arbitrary path, either from the CWD, or
        using .. and other such shortcuts.  This function should only
        be called from SQLite3, not Python.
        """
        filename = unique_filename_in(self.file_path)
        shutil.copyfile(src,os.path.abspath(os.path.join(self.file_path,filename)))
        return filename

    def _delete_repository_file(self,filename):
        """Delete a file from the MiniLIMS repository.

        This function should only be called from SQLite3, not from Python.
        """
        os.remove(os.path.join(self.file_path,filename))
        return None

    def _export_file_from_repository(self,fileid,dst):
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

        The overall Execution object is recorded in the execution
        table.  Each program in it is entered as a row in the program
        table, including their stdout, stderr, etc.  Each argument to
        the program gets a row in the argument table.  All files which
        were used in the execution from the MiniLIMS repository are
        added to the execution_use table.  Any files which were added
        to the repository are copied to the repository and entered in
        the file table.
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
        for used_file in set(ex.used_files):
            [x for x in self.db.execute("""insert into execution_use(execution,file) values (?,?)""", (exid,used_file))]
        self.db.commit()
        return exid

    def search_files(self, with_text=None, older_than=None, newer_than=None, source=None):
        """Find files matching given criteria in the LIMS.

        Finds files which satisfy all the criteria which are not None.
        The criteria are:

           * with_text: The file's external_name or description
             contains 'with_text'

           * older_than: The file's created time is earlier than
             'older_than'.  This should be of the form "YYYY:MM:DD
             HH:MM:SS".  Final fields can be omitted, so "YYYY" and
             "YYYY:MM:DD HH:MM" are also valid date formats.

           * newer_than: The file's created time is later than
             'newer_then', using the same format as 'older_than'.

           * source: Where the file came from.  Can be one of
             'execution', 'copy', 'import', ('execution',exid), or
             ('copy',srcid), where exid is the id of the execution
             that created this file, and srcid is the file id of the
             file which was copied to create this one.
        """
        if not(isinstance(source, tuple)):
            source = (source,None)
        source = source != None and source or (None,None)
        with_text = with_text != None and '%' + with_text + '%' or None
        sql = """select id from file where ((external_name like ? or ? is null)
                                            or (description like ? or ? is null))
                                          and (created >= ? or ? is null)
                                          and (created <= ? or ? is null)
                                          and (origin = ? or ? is null)
                                          and (origin_value = ? or ? is null)"""
        matching_files = self.db.execute(sql, (with_text, with_text,
                                               with_text, with_text,
                                               newer_than, newer_than, older_than, older_than,
                                               source[0], source[0], source[1], source[1]))
        return [x for (x,) in matching_files]

    def search_executions(self, with_text=None, started_before=None,
                          started_after=None, ended_before=None, ended_after=None):
        """Find executions matching the given criteria.

        Returns a list of execution ids of executions which satisfy
        all the criteria which are not None.  The criteria are:

           * with_text: The execution's description or one of the
             program arguments in the execution contains 'with_text'.

           * started_before: The execution started running before
             'start_before'.  This should be of the form "YYYY:MM:DD
             HH:MM:SS".  Final fields can be omitted, so "YYYY" and
             "YYYY:MM:DD HH:MM" are also valid date formats.

           * started_after: The execution started running after
             'started_after'.  The format is identical to
             'started_before'.

           * ended_before: The execution finished running before
             'ended_before'.  The format is the same as for
             'started_before'.

           * ended_after: The execution finished running after
             'ended_after'.  The format is the same as for
             'started_before'.
        """
        with_text = with_text != None and '%'+with_text+'%' or None
        sql = """select id from execution where 
                 (started_at <= ? or ? is null) and 
                 (started_at >= ? or ? is null) and
                 (finished_at <= ? or ? is null) and 
                 (finished_at >= ? or ? is null) and
                 (description like ? or ? is null)
              """
        matching_executions = [x for (x,) in 
                               self.db.execute(sql, 
                                               (started_before,
                                                started_before,
                                                started_after,
                                                started_after,
                                                ended_before,
                                                ended_before,
                                                ended_after, 
                                                ended_after,
                                                with_text,
                                                with_text))]
        if with_text != None:
            sql = """select distinct execution from argument
                     where argument like ?"""
            matching_programs = [x for (x,) in 
                                 self.db.execute(sql, (with_text,))]
        else:
            matching_programs = []
        return list(set(matching_executions+matching_programs))

    def copy_file(self, fileid):
        """Copy the given file in the MiniLIMS repository.

        A copy of the file corresponding to the given fileid is made
        in the MiniLIMS repository, and the file id of the copy is
        returned.  This is most useful to create a mutable copy of an
        immutable file.
        """
        try:
            sql = """select external_name,repository_name,description 
                     from file where id = ?"""
            [(external_name, 
              repository_name, 
              description)] = [x for x in self.db.execute(sql, (fileid, ))]
            new_repository_name = unique_filename_in(self.file_path)
            sql = """insert into file(external_name,repository_name,
                                      origin,origin_value) values (?,?,?,?)"""
            [x for x in self.db.execute(sql, (external_name, 
                                              new_repository_name, 
                                              'copy', fileid))]
            [new_id] = [x for (x,) in 
                        self.db.execute("select last_insert_rowid()")]
            shutil.copyfile(os.path.join(self.file_path, repository_name),
                            os.path.join(self.file_path, new_repository_name))
            self.db.commit()
            return new_id
        except ValueError, v:
            raise ValueError("No such file id " + str(fileid))
    
    def delete_file(self, fileid):
        """Delete a file from the repository."""
        try:
            sql = "select repository_name from file where id = ?"
            [repository_name] = [x for (x,) in self.db.execute(sql, (fileid,))]
            sql = "delete from file where id = ?"
            [x for (x,) in self.db.execute(sql, (fileid, ))]
            os.remove(os.path.join(self.file_path, repository_name))
            self.db.commit()
        except ValueError:
            raise ValueError("No such file id " + str(fileid))

    def delete_execution(self, execution_id):
        """Delete an execution from the MiniLIMS repository."""
        try:
            self.db.execute("delete from argument where execution = ?",
                            (execution_id,))
            self.db.execute("delete from program where execution = ?", 
                            (execution_id,))
            self.db.execute("delete from execution where id = ?", 
                            (execution_id,))
            self.db.commit()
        except ValueError, v:
            raise ValueError("No such execution id " + str(execution_id))

    def import_file(self, src, description=""):
        """Add an external file 'src' to the MiniLIMS repository.

        'src' should be the path to the file to be added.
        'description' is an optional string that will be attached to
        the file in the repository.  import_file returns the file id
        in the repository of the newly imported file.
        """
        self.db.execute("""insert into file(external_name,repository_name,
                                            description,origin,origin_value)
                           values (?,importfile(?),?,?,?)""",
                        (os.path.basename(src),os.path.abspath(src),
                         description,'import',None))
        self.db.commit()
        return [x for (x,) in 
                self.db.execute("""select last_insert_rowid()""")][0]
        
    def export_file(self, fileid, dst):
        """Write fileid from the MiniLIMS repository to dst.

        dst can be either a directory, in which case the file will
        have its repository name in the new directory, or can specify
        a filename, in which case the file will be copied to that
        filename.
        """
        filename = [x for (x,) in 
                    self.db.execute("""select repository_name
                                       from file where id = ?""",
                                    (fileid, ))][0]
        shutil.copy(os.path.join(self.file_path,filename),
                    dst)


# def get_ex():
#     m = MiniLIMS("test")
#     with execution(m) as ex:
# # #    f = bowtie(ex, '../test_data/selected_transcripts', '../test_data/reads-1-1')
#         f = touch(ex)
#         g = sleep.nonblocking(ex,1)
#         ex.add(f)
#         ex.use(1)
#         print g.wait()
    
#with execution(m) as ex:
#     print ex.use(1)
#     print ex.exwd
        

# Program library

@program
def bowtie(index, reads):
    sam_filename = unique_filename_in(os.getcwd())
    return {"arguments": ["bowtie", "-Sra", index, reads,sam_filename],
            "return_value": sam_filename}


@program
def sam_to_bam(sam_filename):
    bam_filename = unique_filename_in(os.getcwd())
    return {"arguments": ["samtools","view","-b","-S","-o",bam_filename,sam_filename],
            "return_value": bam_filename}


@program
def touch():
    filename = unique_filename_in(os.getcwd())
    return {"arguments": ["touch",filename],
            "return_value": filename}


@program
def sleep(n):
    return {"arguments": ["sleep", str(n)],
            "return_value": lambda q: n}

