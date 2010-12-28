Tutorial
========

What is bein?
-------------

Bein is a small Python library.  It addresses two distinct problems: repeating and organizing sequences of operations on data, and keeping track of the resulting files.  Of course, bein is not the first system to do this.  These two threads have run through all of computing history, and all of human organization before that.  But the "right" way of solving each of them depends on the number and kind of the operations, and on what needs to be tracked in the files.

The venerable Unix shell represents one solution.  It has persisted for forty years because it is probably the fastest way to link together a few programs to operate on a single piece of data.  However, complicated sequences quickly become unwieldy.  Worse, parallel data sets quickly become snarled messes, as programmers realized immediately after the shell's introduction.  They were dealing with multiple versions of source code and running complicated commands to compile that code.  Resolving these problems has driven the last forty years of development of version control systems and build systems.

A similar problem afflicts scientists and engineers, who often have several sets of data from related experiments, and suffer the same problems as programmers with multiple versions of source code.  The right tool for the task depends strongly on how many such data sets there are and how complicated the analysis they have to run on it is.  We can take these two aspects as the coordinates of different systems to solve the problem.

.. image:: plot.png

Most solutions have focused on long workflows with huge numbers of parallel data sets, starting with `Discovery Net <http://en.wikipedia.org/wiki/Discovery_Net>`_ from Imperial College London and continuing through modern systems like `Galaxy <http://galaxy.psu.edu/>`_.  These systems are ideal a mass spectrometry or sequencing center which needs to process and track all the data it produces before turning it over to its customers.

On a somewhat smaller scale, another Python based system called `Ruffus <http://www.ruffus.org.uk/>`_ does a great deal of detailed handling of workflows, parallelizing jobs, and restarting workflows that failed.  It assumes some kind of external system to handle the files it produces.  For a well established pipeline, this is again marvelous.

Much of a scientist's day to day work, however, involves fairly simple workflows of no more than ten or twenty steps, and five or six parallel data sets.  In this case all these systems are overkill, and their sophistication becomes a millstone around the practitioner's neck.  This is the niche that bein fills.

Bein is tiny.  It's under 1000 lines of code, and the core logic is under 500.  It is the result of a year of writing, testing, and rewriting to make a tool for the day to day work in the Bioinformatics and Biostatistics Core Facility of the Ecole Polytechnique Federale de Lausanne.


Installation
------------

Bein's core logic depends only on the default Python distribution (version >=2.5) and SQLite.  The included library of utilities also depends on matplotlib, numpy, and scipy, all of which you should install if you are contemplating any scientific computing in Python.

There are three ways to install bein:

#. The simplest way is to fetch and install bein automatically from the Python Package Index.  Just run::

    sudo easy_install bein

#. Download a compressed archive of the source code, and install it by hand.  In the directory you downloaded ``bein-X.tar.gz``, run the commands::

    tar -xvzf bein-X.tar.gz
    cd bein
    python setup.py build
    sudo python setup.py install

#. Fetch the latest version from GitHub, then compile it by hand::

    git clone https://github.com/madhadron/bein.git
    cd bein
    python setup.py build
    sudo python setup.py install

Your first workflow
-------------------

We'll begin with a simple example.  Put the following code in ``test.py``::

    from bein import *
    from bein.util import *

    M = MiniLIMS("data")

    with execution(M) as ex:
       touch(ex, "boris")
       print ex.working_directory

Then run the script::

    $ python test.py
    /Users/ross/scratch/BPFRu4KBXeCwNP9inxmc

In the directory where you ran it, you will find two new files, an SQLite3 database ``data`` and a directory ``data.files``.  Together, they form a MiniLIMS repository, bein's system for tracking files and executions.  As long as you keep them together, you can move them anywhere, put them on a USB key and share them, or email them to someone.  As long as they are in the same place when you try to access them with bein, they will work.  We'll return to all the things the MiniLIMS does in a later section.  For now let's go through this code line by line.

The first two lines will be the same in almost any bein script::

    from bein import *
    from bein.util import *

The ``bein`` module contains the system's core logic.  ``bein.util`` is a library of useful programs and functions built up from bein's day to day use.

Next we connect to the MiniLIMS repository::

    M = MiniLIMS("data")

The single argument to ``MiniLIMS`` is the path to the SQLite database of the repository.  If you need to connect to a MiniLIMS consisting of a database ``boris`` and a directory ``boris.files`` in the directory ``/home/hilda/shared/``, then you would write::

    M = MiniLIMS("/home/hilda/shared/boris")

If you connect to a nonexistent MiniLIMS repository, bein creates it on the fly.

Next we actually run a workflow.  Workflows correspond to a single execution, and we use Python's ``with`` statement to set up this execution and clean up when it is complete::

    with execution(M) as ex:
       touch(ex, "boris")
       print ex.working_directory

``execution(M)`` creates a new execution which will write its data to the MiniLIMS ``M``, and binds it to ``ex`` for the body of the with statement.  

``touch`` is a binding to the Unix ``touch`` command.  Program bindings in bein always take the execution as their first argument.  In this case, we create an empty file named ``boris``.

The second line is a normal Python print statement.  You can use any Python code in an execution body.  When we ran the script this line printed ``/Users/ross/scratch/BPFRu4KBXeCwNP9inxmc`` (or a random string of characters following whatever path you ran the script in on your machine).  If we look in the directory, the two files of the MiniLIMS repository are there, but there is no sign of ``BPFRu4KBXeCwNP9inxmc``.

``bein.util`` provides a function ``pause`` which is useful when diagnosing problems in executions.  It simply stops the execution until the user hits enter.  Meanwhile you can go explore the directory.  If we add it to the end of our execution::

    with execution(M) as ex:
       touch(ex, "boris")
       print ex.working_directory
       pause()

and run the script, it prints a new working directory, not the same as last time: ``/Users/ross/scratch/qK3UEGDCzOlj0hJikG9E``.  If we look in the directory in another terminal, we find that there is indeed a directory named ``qK3UEGDCzOlj0hJikG9E``.  It contains one file, ``boris``.  Then if we hit enter and let the Python script finish, the directory vanishes.

Executions create randomly named working directories, do everything therein, then delete the directory.  This prevents name conflicts and keeps everything tidy.  The execution hasn't disappeared, though.  Its history is stored in the MiniLIMS repository ``M``.

Bein provides a simple webclient to browse MiniLIMS repositories.  Run the command::

    beinclient data

and point your browsier to ``http://localhost:8080``.  

.. image:: beinclient1.png

We have two tabs at the top of the page, one for executions, one for files in the repository.  Each execution is assigned a unique numeric ID.  Every external program run by an execution is recorded.  If it produced output on ``stdout`` or ``stderr`` that is recorded as well (though ``touch`` does not, so it is absent here).  Finally, if an execution had failed, the Python exception from that failure is recorded and displayed.

If we click on the "Files" tab in ``beinclient``, it is empty. Filling this tab is the topic of our next two sections.


Using the MiniLIMS from executions
----------------------------------

Executions delete their working directories when they are finished.  This means any data in the directory is lost.  How do we preserve a file we want to keep?

The execution object has a method called ``add``.  It takes a path to the file, typically just a file name in the execution's working directory, and adds it to the execution's MiniLIMS repository before the directory is deleted.

Let's modify the workflow in ``test.py`` to add the file ``boris`` that we created::

    with execution(M) as ex:
       touch(ex, "boris")
       print ex.working_directory
       ex.add("boris")

We run the script, and look in ``beinclient``.  The execution has a new field, "Added files."

.. image:: beinclient2.png

If we click on the the files "1", we are taken to the "Files" tab, which is no longer empty.

.. image:: beinclient3.png

Don't worry about most of the fields for now.  Note that files, like executions, are assigned numeric IDs.  The "External name" is the name of the file when it was added to the repository.  Internally, bein assigns it a unique, random name, which is the "Repository name."  The file is stored under this name in the ``data.files`` directory of our MiniLIMS.

In the file's header it says "*(no description)*".  Our executions say this as well.  When adding a file to the repository, you can give it a description by setting the ``description`` keyword argument to ``add``.  For instance, we might have written::

    ex.add("boris", description="This is the file boris which I made!")

in our script.  Adding descriptions to executions is almost the same.  Add the ``description`` keyword argument to the ``execution`` function::

    with execution(M, description="Touch the file boris...") as ex:
        ...

If we make these changes to ``test.py`` and run it again, the execution and file that result appear in ``beinclient`` as

.. image:: beinclient-execution-description.png

.. image:: beinclient-file-description.png

One execution can add as many files as you want.  To keep different files from the same execution straight, give them sensible descriptions.  Descriptions for executions are useful when trying to remember later what you did.

The opposite of adding a file to the repository from an execution is pulling a file from the repository to use in an execution.  Executions have a method ``use`` for this case.  Let us write a simple execution that pulls the file we just added (which in my repository has the numeric ID 2) into the working directory::

    with execution(M) as ex:
        filename = ex.use(2)
        print "Used file has name", filename, "in working directory", ex.working_directory
        pause()

When we run this, it prints ``Used file has name 0ktonMhlO3BCl8kH9WqP in working directory /Users/ross/scratch/dEejDD2HHkUd7QawCYRd``.  ``pause`` prevents it from finishing and deleting the working directory, so we can go in and see that there is indeed a file of that name.

What happened to ``boris``?  We could add many files named ``boris`` to the repository, and use them all in the same execution.  To prevent name collisions, ``use`` gives the file a random name in the working directory, and returns that name.

If we run this and look at the execution in ``beinclient``, we find a new field

.. image:: beinclient-used-files.png

Bein tracks not only what execution created a file, but what executions have used it.  If you scroll up, you will see a change in the execution that created this file as well. The Delete button has been replaced by the word "Immutable."

.. image:: beinclient-immutable-execution.png

The file it created has also lost its Delete button.

.. image:: beinclient-file-immutable.png

Bein prevents you from deleting files and executions which have been used later on.  This way you can always trace the origins of a file in the MiniLIMS repository.

Don't be afraid to use the Delete button.  You will create many executions which aren't quite what you want.  The immutability constraints that bein imposes will protect the history of your data.

Using the MiniLIMS outside executions
-------------------------------------

The MiniLIMS provides several methods which are useful outside of executions, or in executions attached to a different MiniLIMS object.  ``import_file`` and ``export_file`` let you manually put files into and get them out of the repository.  Exporting the file with numeric ID 2 from the repository entails::

    M = MiniLIMS("data")
    M.export_file(2, "/path/to/export/to")

If ``/path/to/export/to`` points to a directory, the file is copied there with its repository name.  If it is filename in a directory, then the file is copied to that filename.  This mirrors the semantics of the Unix ``cp`` command.

``import_file`` manually adds a file to the MiniLIMS repository, and returns the numeric ID assigned to the file, as in::

    M = MiniLIMS("data")
    fileid = M.import_file("/path/to/file")

If we import ``test.py`` this way, and look at it in ``beinclient``, we see that bein also tracks whether a file was imported or not.

.. image:: imported_file.png

If a group of people are working on similar problems, they may share a MiniLIMS repository with common reference files.  They could certainly export from this repository into their working directory, but for large files that are only read, this wastes a lot of time and space copying them.

Bein provides a method ``path_to_file`` to get the full path of a file in a MiniLIMS repository.  For instance, if a user needed to read from, but not write to, the file with ID 12 in the shared repository for his own execution, he might write something like::

    from bein import *

    M = MiniLIMS("/path/to/my/repository")
    sharedM = MiniLIMS("/path/to/shared/repository")

    with execution(M) as ex:
        shared_file = sharedM.path_to_file(12)
        ...

MiniLIMS provides a number of other useful methods as well.  In particular, you can delete files and executions, fetch dictionaries with all the information corresponding to a particular file or execution, and search for files and executions by content.

.. class:: bein.MiniLIMS

  .. automethod:: delete_file(file_id)

  .. automethod:: delete_execution

  .. automethod:: fetch_file(file_id)

  .. automethod:: fetch_execution(execution_id)

  .. automethod:: search_files

  .. automethod:: search_executions

Using the MiniLIMS effectively in a program often requires knowing the execution ID of some workflow you just ran.  The execution's ``id`` field is set to this ID after an execution finishes.  During an execution, however, its ID is ``None``.  Consider the code::

    with execution(M) as ex:
        print ex.id

    print ex.id

The print statement in the execution prints ``None``.  The print statement after the execution prints the integer assigned as the execution's ID.


.. _program-binding:

Binding programs into bein
--------------------------

In the simple workflow we gave near the beginning of this tutorial, we called a program ``touch`` from ``bein.util``.  How do we write such external bindings?  To begin with an example, here is a binding for ``touch``::

    @program
    def touch(filename):
        return {'arguments': ['touch', filename],
                'return_value': filename}

The function itself is quite simple.  It takes some arguments, and returns a dictionary containing two keys ``'arguments'`` and ``'return_value'``.  The ``@program`` decorator takes such a function and performs some magic behind the scenes to produce a full program binding for bein.

The value corresponding to ``'arguments'`` is a list of strings which give the external program to run and the arguments to pass to it.  ``['touch', 'abcd']`` is equivalent to running ``touch abcd`` in the Unix shell.

In an execution, if a program exits with return value 0, then the value corresponding to ``'return_value'`` is returned by the function and the execution continues.  If the program exits with another value, the execution terminates and the failure is written to the MiniLIMS.

The binding above is enough to run our basic workflow.  We can remove import of ``bein.util`` and run the script::

    from bein import *

    @program
    def touch(filename):
        return {'arguments': ['touch', filename],
                'return_value': filename}

    M = MiniLIMS("data")

    with execution(M) as ex:
        touch(ex, "boris")
        print ex.working_directory

Observant readers will have remarked that we defined ``touch`` to take only one argument, but in the execution we give it two.  This is part of the magic performed by ``@program``.  It adds an extra, initial argument to the function which should be the execution the program is running in.

One of the most common errors when writing bein scripts is to forget to pass the execution to a bound program.  Don't worry if you do.  Bein will tell you so explicitly.  If we omit the ``ex`` in ``touch`` above, the script fails with the error ``ValueError: First argument to program touch must be an Execution.``

In ``touch`` we know the sensible return value before we run the program.  What do we do if we are running the program to find that value?  For instance, we might run ``wc -l`` to find the number of lines in a file.  The return value when we bind this program should be the number of lines, but we don't know it beforehand.

The value corresponding to ``'return_value'`` need not be a value.  It may be a function.  If it is, then when the program has finished running, the function is called on its results.  The results are passed to the function as a ``ProgramObject``.

.. autoclass:: bein.ProgramOutput

  .. attribute:: return_code

    An integer giving the return code of the program when it exited.  By convention this is 0 if the program succeeded, or some other value if it failed.

  .. attribute:: pid

    An integer giving the process ID under which the program ran.

  .. attribute:: arguments

    A list of strings which were the program and the exact arguments passed to it.

  .. attribute:: stdout

    The text printed by the program to ``stdout``.  It is returned as a list of strings, each corresponding to one line of ``stdout``, and each still carrying their terminal ``\n``.

  .. attribute:: stderr

    The text printed by the program to ``stderr``.  It has the same format as ``stdout``.

Let's bind ``wc -l`` as we discussed above.  The output of ``wc -l`` is a line containing the number of lines followed by the filename, so we will define a function to extract the number of lines with a regular expression::

    @program
    def count_lines(filename):
       def parse_output(p):
            m = re.search(r'^\s+(\d+)\s+' + filename, ''.join(p.stdout))
            return int(m.groups()[0])
       return {'arguments': ["wc","-l",filename],
               'return_value': parse_output}


``parse_output`` takes a program object ``p``.  We join the lines in ``p`` (there is only one, actually), do a regular expression search for the field we want, and return it as an integer.

Binding programs in this way makes it trivial to bind scripts in other languages.  For instance, if we have an R script ``mean.R`` that calculates the mean of the numbers passed on its command line::

    values <- as.numeric(commandArgs(trailingOnly = TRUE))
    cat(mean(values), '\n')

We can bind it into bein with::

    @program
    def mean_R(numbers):
        def read_mean(p):
            return int("".join(p.stdout))
        return {'arguments': ["R","--vanilla","--slave","-f","/path/to/mean.R",
                              "--args"] + [str(n) for n in numbers],
                'return_value': mean_R}

There are two common idioms here worth noting.  First, if you have to pass multiple arguments, append it to the list of other arguments.  Second, you must make sure your arguments are strings.  If you had written ``..."--args"] + numbers`` it would have failed because the ``numbers`` contains integers, not strings.

There is more advice on how to bind programs in the :doc:`advanced_bein` manual, but the best way to learn good practice is to read the source code of existing bindings in :mod:`bein.util`.

What happens when things fail
-----------------------------

Bein is robust.  You don't have to worry about your programs failing.  It will record the failure, clean up, and carry on.  For instance, this script will fail::

    from bein import *
    from bein.util import *

    M = MiniLIMS("data")

    with execution(M) as ex:
        touch(ex, "boris")
        print count_lines(ex, "borsi")

When we run it, we get the error::

    bein.ProgramFailed: Running 'wc -l borsi' failed with stderr:
        wc: borsi: open: No such file or directory

Of course, we misspelled ``boris``.  No harm done.  Fix it and run it again.  If we lose the error before we fix it, there's no problem.  It's displayed in ``beinclient`` as well.

.. image:: failed_execution.png

Do something with the touched boris file, but misspell it.  Show error message, show that it's all properly recorded in bein and cleaned up.  Don't be afraid of failure.

Certain errors show up all the time.  Check for them first:

* Did you forget to pass the execution as the first argument to a bound function?
* Did you convert all of the arguments to a bound program to strings?
* Did you misspell a filename?

Sometimes, though, you expect an error to happen.  In this case you can catch the ``ProgramFailed`` exception inside the execution, as in::

    with execution(M) as ex:
        try:
            ...stuff that fails here...
        except ProgramFailed, pf:
            ...do something with the exception...

Unless you reraise the exception, the execution will terminate as though it had finished without error.

From here, you should go read the advice in :doc:`advanced_bein`, which covers the more advanced features of the system and some useful things you probably hadn't thought of doing with it.
