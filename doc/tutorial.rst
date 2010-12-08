Tutorial
========

What is bein?
-------------

Bein is a small Python library.  It addresses two distinct problems: repeating and organizing sequences of operations on data, and keeping track of the resulting files.  Of course, bein is not the first system to do this.  These two threads have run through all of computing history, and all of human organization before that.  But the "right" way of solving each of them depends on the number and kind of the operations, and on what needs to be tracked in the files.

The venerable Unix shell represents one solution.  It has persisted for forty years because it is probably the fastest way to link together a few programs to operate on a single piece of data.  However, complicated sequences quickly become unwieldy.  Worse, parallel data sets quickly become snarled messes, as programmers realized immediately after the shell's introduction.  They were dealing with multiple versions of source code and running complicated commands to compile that code.  Resolving these problems has driven the last forty years of development of version control systems and build systems.

An identical problem afflicts scientists and engineers.  They often have several sets of data from identical experiments, and suffer the same problems as programmers with multiple versions of source code.  This problem has been solved before, starting with the Discovery Net system from Imperial College London and continuing through modern systems like Galaxy.  These all suffer from one crucial problem which is best illustrated by a quote from Galaxy's website: "Stop wasting time writing interfaces and get your tools used by biologists!"  These systems turn mature, stable workflows into black boxes usable by a layman.  For a mass spectrometry or sequencing center which needs to process and track all the data it produces before turning it over to their customers, these are perfect, but they are little help for the working scientist who is still exploring.

There has been nothing inbetween, no equivalent of ``git`` and ``make`` for the working scientist.  Bein fills that gap.

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

If we click on the "Files" tab in ``beinclient``, it is empty.  Filling this tab is the topic of our next two sections.


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

beinclient open all the time is normal.

Can also work with a MiniLIMS directly: import_file, export_file, copy_file, resolve_path (this is useful if accessing a second MiniLIMS for some files).

Binding programs into bein
--------------------------

How touch is bound.  @program decorator and return values.  Do it without a default for the argument.

@program magic: adds the ex argument, adds auto reporting for the execution, etc.

Can also define a function to do the return.  Show example as wc -l.


Thus it's trivial to bind your own scripts in other languages.  Show binding an R script that calculates the mean of the numbers passed on its command line and prints it.

What happens when things fail
-----------------------------

Do something with the touched boris file, but misspell it.  Show error message, show that it's all properly recorded in bein and cleaned up.  Don't be afraid of failure.

One of the most common mistakes: omit an execution argument to a function, and show that bein gives good error message.

As a matter of course, you'll probably want to delete failures as you go along and debug.  There's no reason to keep them and they clog up the beinclient interface.

