from __future__ import with_statement
# bein/__init__.py
# Copyright 2010 Frederick Ross

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
:mod:`bein` -- LIMS and workflow manager for bioinformatics
===========================================================

.. module:: bein
   :platform: Unix
   :synopsis: Workflow and provenance manager for bioinformatics
.. moduleauthor:: Fred Ross <madhadron at gmail dot com>   

Bein contains a miniature LIMS (Laboratory Information Management
System) and a workflow manager.  It was written for the Bioinformatics
and Biostatistics Core Facility of the Ecole Polytechnique Federale de
Lausanne.  It is aimed at processes just complicated enough where the
Unix shell becomes problematic, but not so large as to justify all the
machinery of big workflow managers like KNIME or Galaxy.

This module contains all the core logic and functionality of bein.

There are three core classes you need to understand:

execution
    The actual class is Execution, but it is generally created with the
    execution contextmanager.  An execution tracks all the information
    about a run of a given set of programs.  It corresponds roughly to a
    script in shell.

MiniLIMS
    MiniLIMS represents a database and a directory of files.  The database
    stores metainformation about the files and records all executions run
    with this MiniLIMS.  You can go back and examine the return code, stdout,
    stderr, imported files, etc. from any execution.

program
    The @program decorator provides a very simple way to bind external
    programs into bein for use in executions.
"""
import subprocess
import random
import traceback
import string
import sys
import os
import sqlite3
import time
import shutil
import threading
import traceback
import re
from contextlib import contextmanager


# miscellaneous types

class ProgramOutput(object):
    """Object passed to return_value functions when binding programs.

    Programs bound with ``@program`` can call a function when they are
    finished to create a return value from their output.  The output
    is passed as a ``ProgramObject``, containing all the information
    available to bein about that program.
    """
    def __init__(self, return_code, pid, arguments, stdout, stderr):
        self.return_code = return_code
        self.pid = pid
        self.arguments = arguments
        self.stdout = stdout
        self.stderr = stderr


class ProgramFailed(Exception):
    """Thrown when a program bound by ``@program`` exits with a value other than 0."""
    def __init__(self, output):
        self.output = output
    def __str__(self):
        return("Running '" + " ".join(self.output.arguments) + \
                   "' failed with stderr:\n\t" + "\t".join(self.output.stderr))

def unique_filename_in(path=None):
    """Return a random filename unique in the given path.

    The filename returned is twenty alphanumeric characters which are
    not already serving as a filename in *path*.  If *path* is
    omitted, it defaults to the current working directory.
    """
    if path == None:
        path = os.getcwd()
    def random_string():
        return "".join([random.choice(string.letters + string.digits) 
                        for x in range(20)])
    while True:
        filename = random_string()
        files = [f for f in os.listdir(path) if f.startswith(filename)]
        if files == []:
            break
    return filename


# programs

class program(object):
    """Decorator to wrap external programs for use by bein.

    Bein depends on external programs to do most of its work.  In this
    sense, it's a strange version of a shell.  The ``@program`` decorator
    makes bindings to external programs only a couple lines long.

    To wrap a program, write a function that takes whatever arguments
    you will need to vary in calling the program (for instance, the
    filename for touch or the number of seconds to sleep for sleep).
    This function should return a dictionary containing two keys,
    ``'arguments'`` and ``'return_value'``.  ``'arguments'`` should
    point to a list of strings which is the actual command and
    arguments to be executed (``["touch",filename]`` for touch, for instance).
    ``'return_value'`` should point to a value to return, or a callable
    object which takes a ProgramOutput object and returns the value
    that will be passed back to the user when this program is run.

    For example, to wrap touch, we write a one argument function that
    takes the filename of the file to touch, and apply the ``@program``
    decorator to it::

        @program
        def touch(filename):
            return {"arguments": ["touch",filename],
                    "return_value": filename}

    Once we have such a function, how do we call it?  We can call it
    directly, but ``@program`` inserts an additional argument at the
    beginning of the argument list to take the execution the program
    is run in.  Typically it will be run like::

        with execution(lims) as ex:
            touch(ex, "myfile")

    where ``lims`` is a MiniLIMs object.  The ProgramOutput of touch
    is automatically recorded to the execution ``ex`` and stored in the
    MiniLIMS.  The value returned by touch is ``"myfile"``, the name of
    the touched file.

    Often you want to call a function, but not block when it returns
    so you can run several in parallel.  ``@program`` also creates a
    method ``nonblocking`` which does this.  The return value is a
    Future object with a single method: ``wait()``.  When you call
    ``wait()``, it blocks until the program finishes, then returns the
    same value that you would get from calling the function directly.
    So to touch two files, and not block until both commands have
    started, you would write::

        with execution(lims) as ex:
            a = touch.nonblocking(ex, "myfile1")
            b = touch.nonblocking(ex, "myfile2")
            a.wait()
            b.wait()

    By default, ``nonblocking`` runs local processes, but you can
    control how it runs its processes with the ``via`` keyword
    argument.  For example, on systems using the LSF batch submission
    system,s you can run commands via batch submission by passing the
    ``via`` argument the value ``"lsf"``::

        with execution(lims) as ex:
            a = touch.nonblocking(ex, "myfile1", via="lsf")
            a.wait()

    You can force local execution with ``via="local"``.

    Some programs do not accept an output file as an argument and only
    write to ``stdout``.  Alternately, you might need to capture
    ``stderr`` to a file.  All the methods of ``@program`` accept
    keyword arguments ``stdout`` and ``stderr`` to specify files to
    write these streams to.  If they are omitted, then both streams
    are captured and returned in the ``ProgramOutput`` object.
    """
    def __init__(self, gen_args):
        self.gen_args = gen_args
        self.__doc__ = gen_args.__doc__
        self.__name__ = gen_args.__name__

    def __call__(self, ex, *args, **kwargs):
        """Run a program locally, and block until it completes.

        This form takes one argument before those to the decorated
        function, an execution the program should be run as part of.
        The return_code, pid, stdout, stderr, and command arguments of
        the program are recorded to that execution, and thus to the
        MiniLIMS object.
        """
        if not(isinstance(ex,Execution)):
            raise ValueError("First argument to program " + self.gen_args.__name__ + " must be an Execution.")
        elif ex.id != None:
            raise SyntaxError("Program being called on an execution that has already terminated.")

        if kwargs.has_key('stdout'):
            stdout = open(kwargs['stdout'],'w')
            kwargs.pop('stdout')
        else:
            stdout = subprocess.PIPE

        if kwargs.has_key('stderr'):
            stderr = open(kwargs['stderr'],'w')
            kwargs.pop('stderr')
        else:
            stderr = subprocess.PIPE


        d = self.gen_args(*args, **kwargs)

        try:
            sp = subprocess.Popen(d["arguments"], bufsize=-1, stdout=stdout,
                                  stderr=stderr,
                                  cwd = ex.working_directory)
        except OSError, ose:
            raise ValueError("Program %s does not seem to exist in your $PATH." % d['arguments'][0])

        return_code = sp.wait()
        if isinstance(stdout,file):
            stdout_value = None
        else:
            stdout_value = sp.stdout.readlines()
            
        if isinstance(stderr,file):
            stderr_value = None
        else:
            stderr_value = sp.stderr.readlines()
                
        po = ProgramOutput(return_code, sp.pid,
                           d["arguments"], 
                           stdout_value, stderr_value)
        ex.report(po)
        if return_code == 0:
            z = d["return_value"]
            if callable(z):
                return z(po)
            else:
                return z
        else: 
            raise ProgramFailed(po)

    def nonblocking(self, ex, *args, **kwargs):
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

        All the methods are named as _method, with the same arguments
        as ``nonblocking``.  That is, the ``via="local"`` method is
        implemented by ``_local``, the ``via="lsf"`` method by
        ``_lsf``, etc.  When writing a new method, name it in the same
        way, and add a condition to the ``if`` statement in
        ``nonblocking``.

        If you need to pass a keyword argument ``via`` to your
        program, you will need to call one of the hidden methods
        (``_local`` or ``_lsf``) directly.
        """
        if not(isinstance(ex,Execution)):
            raise ValueError("First argument to a program must be an Execution.")
        elif ex.id != None:
            raise SyntaxError("Program being called on an execution that has already terminated.")

        if kwargs.has_key('via'):
            via = kwargs['via']
            kwargs.pop('via')
        else:
            via = 'local'

        if via == 'local':
            return self._local(ex, *args, **kwargs)
        elif via == 'lsf':
            return self._lsf(ex, *args, **kwargs)

    def _local(self, ex, *args, **kwargs):
        """Method called by ``nonblocking`` for running locally.

        If you need to pass a ``via`` keyword argument to your
        function, you will have to call this method directly.
        """
        if kwargs.has_key('stdout'):
            stdout = open(kwargs['stdout'],'w')
            kwargs.pop('stdout')
        else:
            stdout = subprocess.PIPE

        if kwargs.has_key('stderr'):
            stderr = open(kwargs['stderr'],'w')
            kwargs.pop('stderr')
        else:
            stderr = subprocess.PIPE

        d = self.gen_args(*args, **kwargs)

        class Future(object):
            def __init__(self):
                self.program_output = None
                self.return_value = None
            def wait(self):
                v.wait()
                ex.report(self.program_output)
                if isinstance(f.return_value, Exception):
                    raise self.return_value
                else:
                    return self.return_value
        f = Future()
        v = threading.Event()
        def g():
            try:
                try:
                    sp = subprocess.Popen(d["arguments"], bufsize=-1, 
                                          stdout=stdout,
                                          stderr=stderr,
                                          cwd = ex.working_directory)
                except OSError, ose:
                    raise ValueError("Program %s does not seem to exist in your $PATH." % d['arguments'][0])

                return_code = sp.wait()
                if isinstance(stdout,file):
                    stdout_value = None
                else:
                    stdout_value = sp.stdout.readlines()

                if isinstance(stderr,file):
                    stderr_value = None
                else:
                    stderr_value = sp.stderr.readlines()

                f.program_output = ProgramOutput(return_code, sp.pid,
                                                 d["arguments"], 
                                                 stdout_value,
                                                 stderr_value)
                if return_code == 0:
                    z = d["return_value"]
                    if callable(z):
                        f.return_value = z(f.program_output)
                    else:
                        f.return_value = z
                v.set()
            except Exception, e:
                f.return_value = e
                v.set()
        a = threading.Thread(target=g)
        a.start()
        return f

    def lsf(self, ex, *args, **kwargs):
        """Deprecated.  Use nonblocking(via="lsf") instead."""
        raise DeprecationWarning("Use nonblocking(via='lsf') instead.")
        return self._lsf(ex, *args, **kwargs)

    def _lsf(self, ex, *args, **kwargs):
        """Method called by ``nonblocking`` to run via LSF."""
        if not(isinstance(ex,Execution)):
            raise ValueError("First argument to a program must be an Execution.")

        if kwargs.has_key('stdout'):
            stdout = kwargs['stdout']
            kwargs.pop('stdout')
            load_stdout = False
        else:
            stdout = unique_filename_in(ex.working_directory)
            load_stdout = True

        if kwargs.has_key('stderr'):
            stderr = kwargs['stderr']
            kwargs.pop('stderr')
            load_stderr = False
        else:
            stderr = unique_filename_in(ex.working_directory)
            load_stderr = True

        d = self.gen_args(*args, **kwargs)

        # Jacques Rougemont figured out the following syntax that works in
        # both bash and tcsh.
        remote_cmd = " ".join(d["arguments"])
        remote_cmd += " > "+stdout
        remote_cmd = " ( "+remote_cmd+" ) >& "+stderr
        cmds = ["bsub","-cwd",ex.remote_working_directory,"-o","/dev/null",
                "-e","/dev/null","-K","-r",remote_cmd]
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
            try:
                nullout = open(os.path.devnull, 'w')
                sp = subprocess.Popen(cmds, bufsize=-1, stdout=nullout, 
                                      stderr=nullout)
                return_code = sp.wait()
                while not(os.path.exists(os.path.join(ex.working_directory,
                                                      stdout))):
                    pass # We need to wait until the files actually show up
                if load_stdout:
                    with open(os.path.join(ex.working_directory,stdout), 'r') as fo:
                        stdout_value = fo.readlines()
                else:
                    stdout_value = None

                while not(os.path.exists(os.path.join(ex.working_directory,stderr))):
                    pass # We need to wait until the files actually show up
                if load_stderr:
                    with open(os.path.join(ex.working_directory,stderr), 'r') as fe:
                        stderr_value = fe.readlines()
                else:
                    stderr_value = None

                f.program_output = ProgramOutput(return_code, sp.pid,
                                                 cmds, stdout_value, stderr_value)
                if return_code == 0:
                    z = d["return_value"]
                    if callable(z):
                        f.return_value = z(f.program_output)
                    else:
                        f.return_value = z
                v.set()
            except:
                f.return_value = None
                v.set()
                raise
        a = threading.Thread(target=g)
        a.start()
        return(f)


class Execution(object):
    """``Execution`` objects hold the state of a current running execution.
    
    You should generally use the execution function below to create an
    Execution, since it sets up the working directory properly.

    Executions are run against a particular MiniLIMS object where it
    records all the information onf programs that were run during it,
    fetches files from it, and writes files back to it.

    The important methods for the user to know are ``add`` and ``use``.
    Everything else is used internally by bein.  ``add`` puts a file
    into the LIMS repository from the execution's working directory.
    ``use`` fetches a file from the LIMS repository into the working
    directory.
    """
    def __init__(self, lims, working_directory):
        self.lims = lims
        self.working_directory = working_directory
        self.programs = []
        self.files = []
        self.used_files = []
        self.started_at = int(time.time())
        self.finished_at = None
        self.id = None
    def path_to_file(self, id_or_alias):
        """Fetch the path to *id_or_alias* in the attached LIMS."""
        if self.lims == None:
            raise ValueError("Cannot use path_to_file; no attached LIMS.")
        else:
            return self.lims.path_to_file(id_or_alias)

    def report(self, program):
        """Add a ProgramOutput object to the execution.

        When the Execution finishes, all programs added to the
        Execution with 'report', in the order the were added, are
        written into the MiniLIMS repository.
        """
        self.programs.append(program)
    def add(self, filename, description="", associate_to_id=None, 
            associate_to_filename=None, template=None, alias=None):
        """Add a file to the MiniLIMS object from this execution.

        filename is the name of the file in the execution's working
        directory to import.  description is an optional argument to
        assign a string to describe that file in the MiniLIMS
        repository.  The function returns an integer, the file id of
        the file in the MiniLIMS repository.

        Note that the file is not actually added to the repository
        until the execution finishes.
        """
        if filename == None:
            if description == "":
                raise(IOError("Tried to add None to repository."))
            else:
                raise(IOError("Tried to add None with descrition '" + description +"' to repository."))
        elif not(os.path.exists(filename)):
            raise IOError("No such file or directory: '"+filename+"'")
        else:
            self.files.append((filename,description,associate_to_id,
                               associate_to_filename,template,alias))
    def finish(self):
        """Set the time when the execution finished."""
        self.finished_at = int(time.time())

    def use(self, file_or_alias):
        """Fetch a file from the MiniLIMS repository.

        fileid should be an integer assigned to a file in the MiniLIMS
        repository, or a string giving a file alias in the MiniLIMS 
        repository.  The file is copied into the execution's working
        directory with a unique filename.  'use' returns the unique
        filename it copied the file into.
        """
        fileid = self.lims.resolve_alias(file_or_alias)
        try:
            filename = [x for (x,) in 
                        self.lims.db.execute("select exportfile(?,?)", 
                                             (fileid, self.working_directory))][0]
            for (f,t) in self.lims.associated_files_of(fileid):
                self.lims.db.execute("select exportfile(?,?)",
                                     (f, os.path.join(self.working_directory,t % filename)))
            self.used_files.append(fileid)
            return filename
        except ValueError, v:
            raise ValueError("Tried to use a nonexistent file id " + str(fileid))


@contextmanager
def execution(lims = None, description="", remote_working_directory=None):
    """Create an ``Execution`` connected to the given MiniLIMS object.
    
    ``execution`` is a ``contextmanager``, so it can be used in a ``with``
    statement, as in::

        with execution(mylims) as ex:
            touch('boris')

    It creates a temporary directory where the execution will work,
    sets up the ``Execution`` object, then runs the body of the
    ``with`` statement.  After the body finished, or if it fails and
    throws an exception, ``execution`` writes the ``Execution`` to the
    MiniLIMS repository and deletes the temporary directory after all
    is finished.

    The ``Execution`` has field ``id`` set to ``None`` during the
    ``with`` block, but afterwards ``id`` is set to the execution ID
    it ran as.  For example::

        with execution(mylims) as ex:
            pass

        print ex.id

    will print the execution ID the ``with`` block ran as.

    On some clusters, such as VITAL-IT in Lausanne, the path to the
    current directory is different on worker nodes where batch jobs
    run than on the nodes from which jobs are submitted.  For
    instance, if you are working in /scratch/abc on your local node,
    the worker nodes might mount the same directory as
    /nfs/boris/scratch/abc.  In this case, running programs via LSF
    would not work correctly.

    If this is the case, you can pass the equivalent directory on
    worker nodes as *remote_working_directory*.  In the example above,
    an execution may create a directory lK4321fdr21 in /scratch/abc.
    On the worker node, it would be /nfs/boris/scratch/abc/lK4321fd21,
    so you pass /nfs/boris/scratch/abc as *remote_working_directory*.
    """
    execution_dir = unique_filename_in(os.getcwd())
    os.mkdir(os.path.join(os.getcwd(), execution_dir))
    ex = Execution(lims,os.path.join(os.getcwd(), execution_dir))
    if remote_working_directory == None:
        ex.remote_working_directory = ex.working_directory
    else:
        ex.remote_working_directory = os.path.join(remote_working_directory,
                                                   execution_dir)
    os.chdir(os.path.join(os.getcwd(), execution_dir))
    exception_string = None
    try:
        yield ex
    except:
        (exc_type, exc_value, exc_traceback) = sys.exc_info()
        exception_string = ''.join(traceback.format_exception(exc_type, exc_value,
                                                            exc_traceback))
        raise
    finally:
        ex.finish()
        try:
            if lims != None:
                ex.id = lims.write(ex, description, exception_string)
        finally:
            os.chdir("..")
            shutil.rmtree(ex.working_directory, ignore_errors=True)
            cleaned_up = True
        assert(cleaned_up)


class MiniLIMS(object):
    """Encapsulates a database and directory to track executions and files.

    A MiniLIMS repository consists of a SQLite database and a
    directory of the same name with ``.files`` appended where all files
    kept in the repository are stored.  For example, if the SQLite
    database is ``/home/boris/myminilims``, then there is a directory
    ``/home/boris/myminilims.files`` with all the corresponding files.
    You should never edit the repository by hand!.

    If you create a MiniLIMS object pointing to a nonexistent
    database, then it creates the database and the file directory.

    Basic file operations:
      * :meth:`import_file`
      * :meth:`export_file`
      * :meth:`path_to_file`
      * :meth:`copy_file`

    Fetching files and executions:
      * :meth:`fetch_file`
      * :meth:`fetch_execution`

    Deleting files and executions:
      * :meth:`delete_file`
      * :meth:`delete_execution`

    Searching files and executions:      
      * :meth:`search_files`
      * :meth:`search_executions`

    File aliases:
      * :meth:`resolve_alias`
      * :meth:`add_alias`
      * :meth:`delete_alias`

    File associations:      
      * :meth:`associate_file`
      * :meth:`delete_file_association`
      * :meth:`associated_files_of`
    """
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.file_path = os.path.abspath(path +".files")
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
             description text not null default '',
             exception text default null
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
        CREATE TABLE file_alias (
               alias text primary key,
               file integer references file(id)
        )""")
        self.db.execute("""
        CREATE TABLE file_association (
               id integer primary key,
               fileid integer references file(id) not null,
               associated_to integer references file(id) not null,
               template text not null
        )""")
        self.db.execute("""
        CREATE TRIGGER prevent_repository_name_change BEFORE UPDATE ON file
        FOR EACH ROW WHEN (OLD.repository_name != NEW.repository_name) BEGIN
             SELECT RAISE(FAIL, 'Cannot change the repository name of a file.');
        END""")
        self.db.execute("""
        CREATE VIEW file_direct_immutability AS 
        SELECT file.id as id, count(execution) > 0 as immutable 
        from file left join execution_use 
        on file.id = execution_use.file
        group by file.id
        """)
        self.db.execute("""
        create view all_associations as
        select file.id as id, file_association.associated_to as target
        from file inner join file_association
        on file.id = file_association.fileid
        union all
        select file.id as id, file.id as target
        from file
        order by id asc
        """)
        self.db.execute("""
        create view file_immutability as
        select aa.id as id, max(fdi.immutable) as immutable
        from all_associations as aa left join file_direct_immutability as fdi
        on aa.target = fdi.id
        group by aa.id
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
        SELECT eo.execution as id, ifnull(max(fi.immutable),0) as immutable from
        execution_outputs as eo left join file_immutability as fi
        on eo.file = fi.id
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
        if os.path.isdir(dst):
            filename = unique_filename_in(dst)
        else:
            filename = ""
        try:
            [repository_filename] = [x for (x,) in self.db.execute("select repository_name from file where id=?", 
                                                                   (fileid,))]
            shutil.copyfile(os.path.abspath(os.path.join(self.file_path,repository_filename)),
                            os.path.abspath(os.path.join(dst, filename)))
            return filename
        except ValueError, v:
            return None

    def write(self, ex, description = "", exception_string=None):
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
        self.db.execute("""insert into execution
                           (started_at, finished_at, working_directory,
                            description, exception) 
                           values (?,?,?,?,?)""",
                        (ex.started_at, ex.finished_at, ex.working_directory, 
                         description, exception_string))
        exid = self.db.execute("select last_insert_rowid()").fetchone()[0]

        # Write all the programs
        for i,p in enumerate(ex.programs):
            if p.stdout == None:
                stdout_value = ""
            else:
                stdout_value = "".join(p.stdout)
            if p.stderr == None:
                stderr_value = ""
            else:
                stderr_value = "".join(p.stderr)

            self.db.execute("""insert into program(pos,execution,pid,
                                                   return_code,stdout,stderr)
                               values (?,?,?,?,?,?)""",
                            (i, exid, p.pid, p.return_code,
                             stdout_value, stderr_value))
            for j,a in enumerate(p.arguments):
                self.db.execute("""insert into argument(pos,program,execution,
                                   argument) values (?,?,?,?)""",
                                (j,i,exid,a))

        # Write the files

        # This section is rather complicated due to the necessity of
        # handling hierarchies of associations correctly.  The
        # algorithm is roughly as follows:

        # remaining = files which have yet to be inserted
        # removed = those files already processed
        # while True:
        #     these = all files to be processed this round,
        #             defined as those whose associate_to_file field
        #             (field 3 of the tuple) is in removed.
        #     for file in these:
        #         insert the file
        #         add any alias
        #         associate the file, renaming it so association namings are
        #             preserved even in the repository

        fileids = {}
        removed = [(None,)]
        remaining = ex.files
        while remaining != []:
            these = [k for k in ex.files if k[3] in [x[0] for x in removed]]

            for (filename,description,associate_to_id,associate_to_filename,
                 template,alias) in these:

                fileids[filename] = self._insert_file(ex, exid, filename, description)

                if alias != None:
                    self.add_alias(fileids[filename], alias)

                if associate_to_id != None or associate_to_filename != None:
                    if template == None:
                        raise ValueError("Must provide a template for an association.")
                    elif template == "%s":
                        raise ValueError("Template must be more than just %s")
                    elif template.index("%s") == -1:
                        raise ValueError("Template must contain %s")
                    elif associate_to_id != None:
                        self._associate_file(fileids[filename], associate_to_id, template)
                    else:
                        self._associate_file(fileids[filename], fileids[associate_to_filename], template)

            [remaining.remove(t) for t in these]
            removed.extend(these)


        for used_file in set(ex.used_files):
            self.db.execute("""insert into execution_use(execution,file) 
                               values (?,?)""", (exid,used_file))
        self.db.commit()
        return exid

    def _insert_file(self, ex, exid, filename, description):
        self.db.execute("""insert into file(external_name,repository_name,
                                            description,origin,origin_value) 
                           values (?,importfile(?),?,?,?)""",
                        (filename,
                         os.path.abspath(os.path.join(ex.working_directory,filename)),
                         description, 'execution', exid))
        return self.db.execute("""select last_insert_rowid()""").fetchone()[0]

    def _rename_in_repository(self, fileid, new_repository_name):
        old_target_name = self.db.execute("""select repository_name from file
                                             where id=?""", (fileid,)).fetchone()[0]
        self.db.execute("""drop trigger prevent_repository_name_change""")
        self.db.execute("""update file set repository_name=? where id=?""",
                        (new_repository_name, fileid))
        self.db.execute("""CREATE TRIGGER prevent_repository_name_change
                           BEFORE UPDATE ON file
                           FOR EACH ROW WHEN (OLD.repository_name != NEW.repository_name) BEGIN
                           SELECT RAISE(FAIL, 'Cannot change the repository name of a file.');
                           END""")
        shutil.move(os.path.join(self.file_path, old_target_name),
                    os.path.join(self.file_path, new_repository_name))

    def _associate_file(self, thisid, targetid, template):
        # Make the filename in the repository match this association
        raw_name = self.db.execute("""select repository_name from file where id=?""", 
                                   (targetid,)).fetchone()[0]
        new_target_name = template % raw_name
        self._rename_in_repository(thisid, new_target_name)
        self.associate_file(thisid, targetid, template)

    def search_files(self, with_text=None, older_than=None, newer_than=None, source=None):
        """Find files matching given criteria in the LIMS.

        Finds files which satisfy all the criteria which are not None.
        The criteria are:

           * *with_text*: The file's external_name or description
             contains *with_text*

           * *older_than*: The file's created time is earlier than
             *older_than*.  This should be of the form "YYYY:MM:DD
             HH:MM:SS".  Final fields can be omitted, so "YYYY" and
             "YYYY:MM:DD HH:MM" are also valid date formats.

           * *newer_than*: The file's created time is later than
             *newer_then*, using the same format as *older_than*.

           * *source*: Where the file came from.  Can be one of
             ``'execution'``, ``'copy'``, ``'import'``,
             ``('execution',exid)``, or ``('copy',srcid)``, where
             ``exid`` is the numeric ID of the execution that created
             this file, and ``srcid`` is the file ID of the file which
             was copied to create this one.
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

           * *with_text*: The execution's description or one of the
             program arguments in the execution contains *with_text*.

           * *started_before*: The execution started running before
             *start_before*.  This should be of the form "YYYY:MM:DD
             HH:MM:SS".  Final fields can be omitted, so "YYYY" and
             "YYYY:MM:DD HH:MM" are also valid date formats.

           * *started_after*: The execution started running after
             *started_after*.  The format is identical to
             *started_before*.

           * *ended_before*: The execution finished running before
             *ended_before*.  The format is the same as for
             *started_before*.

           * *ended_after*: The execution finished running after
             *ended_after*.  The format is the same as for
             *started_before*.
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

    def last_id(self):
        """Return the id of the last thing written to the repository."""
        return self.db.execute("select last_insert_rowid()").fetchone()[0]

    def fetch_file(self, id_or_alias):
        """Returns a dictionary describing the given file."""
        fileid = self.resolve_alias(id_or_alias)
        fields = self.db.execute("""select external_name, repository_name,
                                    created, description, origin, origin_value
                                    from file where id=?""", 
                                 (fileid,)).fetchone()
        if fields == None:
            raise ValueError("No such file " + str(id_or_alias) + " in MiniLIMS.")
        else:
            [external_name, repository_name, created, description,
             origin_type, origin_value] = fields
        if origin_type == 'copy':
            origin = ('copy',origin_value)
        elif origin_type == 'execution':
            origin = ('execution',origin_value)
        elif origin_type == 'import':
            origin = 'import'
        aliases = [a for (a,) in 
                   self.db.execute("select alias from file_alias where file=?",
                                   (fileid,))]
        associations = self.db.execute("""select fileid,template from file_association where
                                          associated_to=?""", (fileid,)).fetchall()
        associated_to = self.db.execute("""select associated_to,template from file_association
                                           where fileid=?""", (fileid,)).fetchall()
        immutable = self.db.execute("select immutable from file_immutability where id=?",
                                    (fileid,)).fetchone()[0]
        return {'external_name': external_name,
                'repository_name': repository_name,
                'created': created,
                'description': description,
                'origin': origin,
                'aliases': aliases,
                'associations': associations,
                'associated_to': associated_to,
                'immutable': immutable == 1}
 
    
    def fetch_execution(self, exid):
        """Returns a dictionary of all the data corresponding to the given execution id."""
        def fetch_program(exid, progid):
            fields = self.db.execute("""select pid,return_code,stdout,stderr
                                        from program where execution=? and pos=?""",
                                     (exid, progid)).fetchone()
            if fields == None:
                raise ValueError("No such program: execution %d, program %d" % (exid, progid))
            else:
                [pid, return_code, stdout, stderr] = fields
            arguments = [a for (a,) in self.db.execute("""select argument from argument
                                                          where execution=? and program=?
                                                          order by pos asc""", (exid,progid))]
            return {'pid': pid,
                    'return_code': return_code,
                    'stdout': stdout,
                    'stderr': stderr,
                    'arguments': arguments}
        exfields = self.db.execute("""select started_at, finished_at, working_directory,
                                           description, exception from execution
                                    where id=?""", (exid,)).fetchone()
        if exfields == None:
            raise ValueError("No such execution with id %d" % (exid,))
        else:
            (started_at,finished_at,working_directory,
             description, exception) = exfields
        progids = [a for (a,) in self.db.execute("""select pos from program where execution=?
                                                  order by pos asc""", (exid,))]
        progs = [fetch_program(exid,i) for i in progids]
        added_files = [a for (a,) in self.db.execute("""select id from file where
                                                        origin='execution' and origin_value=?""",
                                                     (exid,))]
        used_files = [a for (a,) in self.db.execute("""select file from execution_use
                                                       where execution=?""", (exid,))]
        immutability = self.db.execute("""select immutable from execution_immutability
            where id=?""", (exid,)).fetchone()[0]
            
        return {'started_at': started_at,
                'finished_at': finished_at,
                'working_directory': working_directory,
                'description': description,
                'exception_string': exception,
                'programs': progs,
                'added_files': added_files,
                'used_files': used_files,
                'immutable': immutability == 1}

    def copy_file(self, file_or_alias):
        """Copy the given file in the MiniLIMS repository.

        A copy of the file corresponding to the given fileid is made
        in the MiniLIMS repository, and the file id of the copy is
        returned.  This is most useful to create a mutable copy of an
        immutable file.
        """
        fileid = self.resolve_alias(file_or_alias)
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
    
    def delete_file(self, file_or_alias):
        """Delete a file from the repository."""
        fileid = self.resolve_alias(file_or_alias)
        try:
            try:
                for (f,t) in self.associated_files_of(fileid):
                    self.delete_file(f)
            except ValueError, v:
                pass
            sql = "select repository_name from file where id = ?"
            [repository_name] = [x for (x,) in self.db.execute(sql, (fileid,))]
            sql = "delete from file where id = ?"
            [x for (x,) in self.db.execute(sql, (fileid, ))]
            os.remove(os.path.join(self.file_path, repository_name))
            sql = "delete from file_alias where file=?"
            self.db.execute(sql, (fileid,)).fetchone()
            self.db.commit()
        except ValueError:
            raise ValueError("No such file id " + str(fileid))

    def delete_execution(self, execution_id):
        """Delete an execution from the MiniLIMS repository."""
        try:
            files = self.search_files(source=('execution',execution_id))
            for i in files:
                try:
                    self.delete_file(i)
                except ValueError, v:
                    pass
            self.db.execute("delete from argument where execution = ?",
                            (execution_id,))
            self.db.execute("delete from program where execution = ?", 
                            (execution_id,))
            self.db.execute("delete from execution where id = ?", 
                            (execution_id,))
            self.db.execute("delete from execution_use where execution=?",
                            (execution_id,))
            self.db.commit()
        except ValueError, v:
            raise ValueError("No such execution id " + str(execution_id) + ": " + v.message)

    def import_file(self, src, description=""):
        """Add an external file *src* to the MiniLIMS repository.

        *src* should be the path to the file to be added.
        *description* is an optional string that will be attached to
        the file in the repository.  ``import_file`` returns the file id
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
        
    def export_file(self, file_or_alias, dst):
        """Write *file_or_alias* from the MiniLIMS repository to *dst*.

        *dst* can be either a directory, in which case the file will
        have its repository name in the new directory, or can specify
        a filename, in which case the file will be copied to that
        filename.
        """
        shutil.copy(self.path_to_file(file_or_alias), dst)

    def path_to_file(self, file_or_alias):
        """Return the full path to a file in the repository.

        It is often useful to be able to read a file in the repository
        without actually copying it.  If you are not planning to write
        to it, this presents no problem.
        """
        fileid = self.resolve_alias(file_or_alias)
        filename = [x for (x,) in 
                    self.db.execute("""select repository_name
                                       from file where id = ?""",
                                    (fileid, ))][0]
        return(os.path.join(self.file_path,filename))

    def resolve_alias(self, alias):
        """Resolve an alias to an integer file id.

        If an integer is passed to ``resolve_alias``, it is returned as is,
        so this method can be used without worry any time any alias
        might have to be resolved.        
        """
        if isinstance(alias, int):
            x = self.db.execute("select id from file where id=?", (alias,)).fetchall()
            if x != [] and x != None:
                return alias
            else:
                raise ValueError("No such file with id %d" % alias)
        elif isinstance(alias, str):
            x = self.db.execute("select file from file_alias where alias=?", (alias,)).fetchone()
            if x == None:
                raise ValueError("No such file alias: " + alias)
            else:
                return x[0]

    def add_alias(self, fileid, alias):
        """Make the string *alias* an alias for *fileid* in the repository.

        An alias can be used in place of an integer file ID in 
        all methods that take a file ID.
        """
        self.db.execute("""insert into file_alias(alias,file) values (?,?)""",
                        (alias, self.resolve_alias(fileid)))
        self.db.commit()

    def delete_alias(self, alias):
        """Delete the alias *alias* from the repository.

        The file itself is untouched.  This only affects the alias.
        """
        self.db.execute("""delete from file_alias where alias = ?""", (alias,))
        self.db.commit()

    def associated_files_of(self, file_or_alias):
        """Find all files associated to *file_or_alias*.

        Return a list of ``(fileid, template)`` of all files associated 
        to *file_or_alias*.
        """
        f = self.resolve_alias(file_or_alias)
        return self.db.execute("""select fileid,template from file_association where associated_to = ?""", (f,)).fetchall()

    def associate_file(self, file_or_alias, associate_to, template):
        """Add a file association from *file_or_alias* to *associate_to*.

        When the file *associate_to* is used in an execution, 
        *file_or_alias* is also used, and named according to *template*. 
        *template* should be a string containing ``%s``, which will be
        replaced with the name *associate_to* is copied to.  So if
        *associate_to* is copied to *X* in the working directory, and
        the template is ``"%s.idx"``, then `file_or_alias` is copied 
        to *X*``.idx``.
        """
        src = self.resolve_alias(file_or_alias)
        dst = self.resolve_alias(associate_to)
        if template.find("%s") == -1:
            raise ValueError("Template of a file association must contain exactly one %s.")
        else:
            self.db.execute("""insert into file_association(fileid,associated_to,template) values (?,?,?)""", (src, dst, template))
            self.db.commit()
            
    def delete_file_association(self, file_or_alias, associated_to):
        """Remove the file association from *file_or_alias* to *associated_to*.

        Both fields can be either an integer or an alias string.
        """
        src = self.resolve_alias(file_or_alias)
        dst = self.resolve_alias(associated_to)
        self.db.execute("""delete from file_association where fileid=? and associated_to=?""", (src,dst))
        self.db.commit()
