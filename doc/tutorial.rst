Tutorial
========

What is bein?
-------------

What's good about the shell.  What's bad about the shell.  The usual scenario.

What's good about big workflow managers.  What's bad about them.  Why you don't use them for your day to day work.

Why is there nothing inbetween?  That's bein.

Bein itself is a small Python library.  It's just under 1000 lines of code, including blank lines and documentation.  So it's tiny.  Its features were carefully winnowed by use.


Installation
------------

Requirements

Three ways to install: easy_install, tarball, clone from git


Your first workflow
-------------------

First workflow.  Run it.

Two new files.  They're the MiniLIMS repository.  You can move it around.  We'll come back to it later.

Now go through the code line by line and explain roughly what each line does.

bein.util provides pause.  It's a great way to inspect what's going on.  run again with a pause.  go look and see temporary directory with boris in it.

Open up beinclient to look at it.  Executions are recorded.  The files tab is empty though, which brings us to the next topic.


Using the MiniLIMS from executions
----------------------------------

ex.add to preserve files from an execution.  Basic workflow adding boris.

Look in beinclient.  Now there's the file.  Go look at it on disk in the repository directory.  Point out description field.  Executions can also have descriptions, so add one and we'll see how that works.

Delete execution in beinclient, note that its output files are deleted.

Run that again, now let's use it.  Workflow with .use with the file id.  Put in a pause and see what happens: random filename.  And look in beinclient, and it's preserved.  And the previous execution and the file are marked immutable!

Explain bein's immutability rules.

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

