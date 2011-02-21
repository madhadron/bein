Advanced techniques in bein
===========================

After you have read the :doc:`tutorial` and played with bein a bit,
you're ready to learn about the rest of its features and the best way
to use the system.

After you have absorbed what's in this page, you should go browse
:mod:`bein.util` to learn what is available and to get ideas for good
practices in your own code.

File aliases
************

Imagine you have the annotation file for your favorite organism in a MiniLIMS repository.  You refer to it in many of your workflows, so your workflows refer always to file 32, an inscrutable number.  Initially you added a comment that this was the annotation file, but after the tenth time you couldn't be bothered.  Now a new version of the annotation file comes out.  You want to switch over to using it, so you add it to your repository and start editing all your workflows to refer to the new file's id of 117.

This would all be much simpler if you could simply assign a name such as ``"annotations"`` to the file, and then redirect the name to the new version when you added it.  Bein supports this as a feature called file aliases.

If ``M`` is your MiniLIMS, you could assign the name to file 32 with::

    M.add_alias(32, "annotations")

Then, wherever you would have written ``ex.use(32)`` in your executions, you can write ``ex.use("annotations")``.  Indeed, anywhere in bein that you could use a file ID, you can use an alias.

When the new version of the annotations file comes out, you add it to your repository, and redirect the alias with::

    M.delete_alias("annotations")
    M.add_alias(117, "annotations")

You can have as many aliases to a file as you like, so you could add a second alias to the new annotations file for when you need to distinguish it from the old one::

    M.add_alias(117, "new annotations")

Now both ``"annotations"`` and ``"new annotations"`` refer to file 117.

You may wish to give an alias to a file you have just created in a workflow, as in::

    with execution(M) as ex:
        ...do something...
        ex.add("myfile", description="This is something important")
        M.add_alias(??, "an alias")

How do you get the file ID to add the alias?  You can't.  File IDs aren't assigned until the execution completes.  Instead, the ``add`` method has a keyword argument *alias* for exactly this purpose.  You would write::

    with execution(M) as ex:
        ...do something...
        ex.add("myfile", alias="an alias", 
               description="This is something important")

Now when the file is added to the MiniLIMS at the end of the execution, the alias ``"an alias"`` will be assigned to it.

See also "File aliases" in :ref:`minilims`.

File associations
*****************

Many bioinformatics tools sloppily spread their data across several files.  A BAM file ``a.bam`` keeps its index in ``a.bam.bai``.  ``bowtie`` splits its indices across no fewer than six files.  You never want to use one of these files, only the whole group.  If a ``bowtie`` index is stored in the MiniLIMS as files 13 through 18, getting them all into place would take appalling code like::

    with execution(M) as ex:
        f = ex.use(13)
        move(ex, f, "index.1.ebwt")
        f = ex.use(14)
        move(ex, f, "index.2.ebwt")
        f = ex.use(15)
        ...

Bein fixes this by letting you associate one file to another.  When you use a file in an execution, any files associated to it are used as well.  So if file 97 is associated to file 63, calling ``ex.use(63)`` will copy by 97 and 63 into the working directory.

File 63 is given a random name in the working directory, and ``use`` returns that name.  But what is the filename of file 97?  When you associate a file to another, you also create a template which determines its filename in the working directory.  A template is a string containing ``%s``.  When the file is copied into the working directory, ``%s`` is replaced by the filename of the file it is associated to, and that is the filename used.

So if file 97 were associated to file 63 with template ``"%s.bai"``, then if file 63 were given the random filename ``xxyz`` in the working directory, file 97 is named ``xxyz.bai``.  We can create this association on a MiniLIMS ``M`` with::

    M.associate_file(97, 63, "%s.bai")

The bowtie index is slightly trickier.  None of the files has a name that can be used as a template for the others.  If we associate `index.2.ebwt` to `index.1.ebwt`, there is no way to give a sensible template to ensure they are properly named.  Instead we create an empty file to which we associate all of the index files.  If the empty file has ID 41, and the bowtie index again consists of files 13 to 18, we could set up the associations with::

    M.associate_file(13, 41, "%s.1.ebwt")
    M.associate_file(14, 41, "%s.2.ebwt")
    M.associate_file(15, 41, "%s.3.ebwt")
    M.associate_file(16, 41, "%s.4.ebwt")
    M.associate_file(17, 41, "%s.rev.1.ebwt")
    M.associate_file(18, 41, "%s.rev.2.ebwt")

Now when we use file 41 in an execution, it is assigned a random name such as ``pqrs``.  Then its associated files are copied as well with the names ``pqrs.1.ebwt``, ``pqrs.2.ebwt``, etc.

As with file aliases, it seems like we would want to assign associations when we are creating files in workflows, but at that point files don't have IDs.  The ``add`` method of ``Execution`` has three keyword arguments to set up associations: *associate_to_id*, *associate_to_filename*, and *template*.  To set up an association, we must always supply *template*, but only one of *associate_to_id* or *associate_to_filename*.

Say we have a BAM file in the MiniLIMS with ID 75.  As part of an execution we create an index for it which we wish to associate to it.  The BAM file already has an ID, so we use the *associate_to_id* argument::

    with execution(M) as ex:
        ...
        ex.add(bam_index, associate_to_id=75, template="%s.bai")
        ...

If the file we want to associate to was created in the same execution, then it also does not have an ID in the MiniLIMS.  In this case we create the association by filename and bein works out the details.  To create the bowtie index associated to an empty file above::

    with execution(M) as ex:
        ...create a bowtie index with prefix pqrs...
        touch(ex, "pqrs")
        ex.add("pqrs")
        ex.add("pqrs.1.ebwt", associate_to_filename="pqrs", template="%s.1.ebwt")
        ex.add("pqrs.2.ebwt", associate_to_filename="pqrs", template="%s.2.ebwt")
        ex.add("pqrs.3.ebwt", associate_to_filename="pqrs", template="%s.3.ebwt")
        ex.add("pqrs.4.ebwt", associate_to_filename="pqrs", template="%s.4.ebwt")
        ex.add("pqrs.rev.1.ebwt", associate_to_filename="pqrs", template="%s.rev.1.ebwt")
        ex.add("pqrs.rev.2.ebwt", associate_to_filename="pqrs", template="%s.rev.2.ebwt")

See also "File associations" in :ref:`minilims`.

Parallel executions
*******************

Many problems in bioinformatics parallelize nicely.  For example, mapping short reads from high throughput sequencers to a reference sequence parallelizes by splitting the reads into subsets and mapping the subsets in parallel.

The ``@program`` decorator provides some magic to make this parallelization easy.  For example, if we have three files ``reads1``, ``reads2``, and ``reads3`` that we want to map to an index ``index`` with bowtie, we might naively write it as::

    with execution(M) as ex:
        ...
        samfiles = [bowtie(ex, index, f) for f 
                    in ["reads1","reads2","reads3"]]
        ...

But in the list comprehension, each bowtie is run one after another.  The parallel version is::

    with execution(M) as ex:
        ...
        futures = [bowtie.nonblocking(ex, index, f) for f
                   in ["reads1","reads2","reads3"]]
        samfiles = [f.wait() for f in futures]
        ...

Every binding created with ``@program`` has a ``nonblocking`` method.  The ``nonblocking`` method returns an object called a "future" instead of the normal value.  The program is started in a separate thread and the execution continues.  If you are working on a cluster using the LSF batch submission system, you can use the keyword argument ``via`` to control how the background jobs are executed.  The default is ``via="local"``, which runs the jobs as processes on the same machine.  You can also use ``via="lsf"`` to submit the jobs via the LSF batch queue on clusters running this system.

When you need the value from the program, call the method ``wait`` on the future.  ``wait`` blocks until the program finishes, then returns the value that would have been returned if you had called the program without ``nonblocking``.  In the example above, ``futures`` is a list of futures, one for each instance of bowtie.  Bowtie runs in parallel on all three files, and when all three have finished, the list of their output files is assigned to ``samfiles``.

The example shows a common idiom for writing parallel executions in bein: use list comprehensions to get a list of futures, then wait on the list of futures to get a list of return values.  It is often used several times, one after another, to run a series of steps in parallel, as in::

    with execution(M) as ex:
        ...
        futures = [bowtie.nonblocking(ex, index, f) for f
                   in ["reads1","reads2","reads3"]]
        samfiles = [f.wait() for f in futures]
        futures = [sam_to_bam.nonblocking(ex, samfile) 
                   for samfile in samfiles]
        bamfiles = [f.wait() for f in futures]
        ...

Note that all the instances of bowtie will finish before any instance of ``sam_to_bam`` begin.  If one of the instances of bowtie finishes much earlier than the other, one of the computer's processors may sit idle until the other instances of bowtie finish.  To avoid this, divide your work evenly among the parallel jobs.

The ``nonblocking`` method only exists on objects created with the ``@program`` decorator.  This includes some, but not all, of the functions in :mod:`bein.util`.  Check the source code for a function to see if you can call it in parallel.

Capturing ``stdout`` and ``stderr``
***********************************

Some programs, such as ``cat``, do not let you specify where to write their output.  They always write to ``stdout``.  In order to capture this, Bein lets you redirect ``stdout`` to a file with the ``stdout`` keyword argument.  If you have a program ``p`` and you want it to write its ``stdout`` to a file named ``boris``, you would write::

    with execution(M) as ex:
        p(ex, arg, ..., stdout="boris")

Every method of a binding created with ``@program`` accepts these arguments, so you could just as easily have called ``p.nonblocking``.

Everywhere you could use ``stdout``, you can also use the keyword argument ``stderr`` to redirect that stream to a file.

When binding a program that must have its ``stdout`` redirected, it is best to write a wrapper around it so that it feels like other, normal program bindings.  For example, for ``cat`` (which is not actually in the library because it's useless inside Bein) we would write::

    @program
    def _cat(input_file):
        return {'arguments': ['cat',input_file],
                'return_value': None}
    
    def cat(ex, input_file, filename=None):
        if filename == None:
            filename = unique_filename_in()
        _cat(ex, input_file, stdout=filename)
        return filename

Unfortunately, you have to add your own ``nonblocking`` binding by hand, as in::

    def _cat_nonblocking(ex, input_file, filename=None):
        if filename == None:
            filename = unique_filename_in()
        f = _cat.nonblocking(ex, input_file, stdout=filename)
        class Future(object):
            def __init__(self, f):
                self.future = f
            def wait(self):
                self.future.wait()
                return filename
        return Future(f)
    
    cat.nonblocking = _cat_nonblocking

You may also want to use these keyword arguments if you expect enormous amounts of data on ``stdout`` or ``stderr``, more than can be reasonably bassed back in a ``ProgramOutput`` object.

Writing robust program bindings
*******************************

The tutorial's section on :ref:`program-binding` covers all the mechanics of writing a program binding.  This section is largely advice on how to write a good program binding.

**Avoid unnecessary generality.**
    If a change in command line arguments will produce vastly different behavior from the program you're binding, just choose one set of arguments that do what you want at the moment and bind that.  If you need the other arguments, and if they behavior is really that different, write another program binding for them when you need them.

**Parse the whole output.**
    At the moment you may only need two numbers of the twenty that this program calculates on your file, but chances are in a week's time you'll need another couple, and a few more after that.  Go ahead and parse the whole thing now.  When you have a lot of values to return, organize them into a dictionary.

**Eschew abbreviations.**
    Program bindings aren't meant for interactive shell use, so there is no reason not to make them easy to read.  Use 'copy' instead of 'cp,' 'antibody' instead of 'ab,' etc.

**Parse in paranoia.**
    ``wc`` formats its output slightly differently on different platforms.  Some programs might have additional headers on some systems.  Some batch processing systems also add headers to the output of a program.  Parse the output knowing that these things happen.  For instance, to parse the output of ``wc -l``, the naive function would be::

        def parse_output(p):
            m = re.search(r'(\d+)', ''.join(p.stdout))
            return int(m.groups()[0])

    This returns the first integer in the output, not necessarily anything of interest.  The paranoid parser is::

        def parse_output(p):
            m = re.search(r'^\s+(\d+)\s+' + filename + r'\s*$',
                          ''.join(p.stdout))
            return int(m.groups()[-1])

    This time we ensure we really do have the line we want, and in case the LSF output might contain a similarly formatted line, we take the last one in the text.

    On the other hand, your parsing function will never get called unless the program exited with return code 0, so you can assume that it succeeded.  The output you want should be in there somewhere.

**Return a value if you can, a function if you must.**
    If you know the value you will return from a program binding before you run the program, as for the binding to ``touch``, return that value directly.  That is, write::

        @program
        def touch(filename):
            return {'arguments': ['touch',filename],
                    'return_value': filename}

    and not::

        @program
        def touch(filename):
           def parse_output(p):
               return filename
           return {'arguments': ['touch',filename],
                   'return_value': parse_output}

    Not only is it less efficient, it confuses the reader.

**Accept a single argument or a list of arguments where appropriate.**
    If a program can take several input files, such as ``cat``, then
    let the user provide either a single filename or a list of
    filenames.  Similarly, if the program takes one or more integers,
    let the user provide an integer or a list of integers.

    For example, here is a binding of `bowtie`` that can accept one or
    several files of reads to map to a reference::

        @program
        def bowtie(index, reads, args="-Sra"):
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
            return {'arguments': ['bowtie'] + options + [index, reads,sam_filename],
                    'return_value': sam_filename}

**Use** :func:`~bein.unique_filename_in` **to name output files.** 
    If a program will create an output file, use
    :func:`~bein.unique_filename_in` to get a name for it.  Don't hard
    code names.

**Let the program fail if at all possible.** 
    Check the arguments passed to your function only enough to
    actually produce a sensible argument list.  Otherwise let the
    external program fail and bein clean up the mess.  You gain no
    safety by carefully checking the arguments beforehand, you may
    impose arbitrary restrictions that do not correspond to the
    underlying program, and it makes program bindings much longer and
    more onerous to read and write.

**Document your binding.**
    If the first thing in your function is a string, Python interprets it as documentation.  Use this!  List the exact command the program is running, the meaning of the arguments, and the return value.

**No magic in program bindings.**
    Don't try to cram all kinds of things into your program binding.  Just run the program and get the information in its basic form out of the results.  Do no more.  Write another function that calls the program binding which does anything more sophisticated.

**Provide sensible defaults to keyword arguments.**
    Many program bindings will have a number of arguments which can be safely omitted in the majority of cases.  For instance, :func:`~bein.util.split_file` accepts an argument *prefix* which lets you set the name of the output files.  In most cases this isn't necessary, so it has a default value of ``None``, which makes the function call :func:`~bein.unique_filename_in` to get a prefix.  Wherever possible, include a sane default.


Combining bindings into larger actions
**************************************

A workflow usually divides into sets of actions, each of which form a logical component of the whole.  Such components tend to be reusable with a little generalization, so it's worth breaking them out into separate functions.  For example, here is simplified code for :func:`~bein.util.parallel_bowtie`, which splits a file into pieces, runs bowtie in parallel on each piece, and reassembles the results::

    def parallel_bowtie(ex, index, reads, n_lines = 1000000, 
                        bowtie_args="-Sra"):
        subfiles = split_file(ex, reads, n_lines = n_lines)
        futures = [bowtie.nonblocking(ex, index, sf, args = bowtie_args) 
                   for sf in subfiles]
        samfiles = [f.wait() for f in futures]
        futures = [sam_to_bam.nonblocking(ex, sf) for sf in samfiles]
        bamfiles = [f.wait() for f in futures]
        return merge_bamfiles.nonblocking(ex, bamfiles).wait()

There are several points to keep in mind when writing such functions, all of which are illustrated by this example.  Most of them boil down to "don't surprise the user."

* Assume the function with called in a ``with execution(M)...`` block.
* The first argument should always be the execution, to maintain similarity with the program bindings.
* Don't assume any file names from the surrounding execution.  Pass everything you need as arguments to the function.
* Include keyword arguments with sane defaults for any optional arguments to programs you call in the function (such as *n_lines* in ``split_file``).
* Do not delete or rename files in the working directory.
* Return everything a user might need to know from the inside of the function.  If this is more than one thing, organize it in a dictionary.
* Don't add files to the repository or use files from the repository inside the function.  Assume that all the files needed are already in place and their filenames have been passed as arguments.

Custom ``add`` commands
***********************

In `File associations`_ we saw commands to associate index files with BAM files, and to add and associate the complicated indices that ``bowtie`` uses.  Rather than rewriting this code again and again, it is better to write your own functions to add these in a structured way.

The last point in `Combining bindings into larger actions`_ warned against adding or using files from the repository in a function.  Let us add a caveat: unless that function was written specifically to add files in some complicated way.  For example, here is a function that adds a bowtie index (it is a simplified version of :func:`~bein.util.add_bowtie_index`)::

    def add_bowtie_index(execution, files, description="", alias=None):
        index = bowtie_build(execution, files)
        touch(ex, index)
        execution.add(index, description=description, alias=alias)
        execution.add(index + ".1.ebwt", associate_to_filename=index, template='%s.1.ebwt')
        execution.add(index + ".2.ebwt", associate_to_filename=index, template='%s.2.ebwt')
        execution.add(index + ".3.ebwt", associate_to_filename=index, template='%s.3.ebwt')
        execution.add(index + ".4.ebwt", associate_to_filename=index, template='%s.4.ebwt')
        execution.add(index + ".rev.1.ebwt", associate_to_filename=index, template='%s.rev.1.ebwt')
        execution.add(index + ".rev.2.ebwt", associate_to_filename=index, template='%s.rev.2.ebwt')
        return index

Functions that add files should obey several conventions for consistency.

* The function's name should begin with ``add_``.
* The first argument should be an execution.
* There should be one file which all other files added to the repository in the function are associated to.  That is, using that one file in another execution should pull in all files added by this function.  The function should return the filename of this file.
* The function should have keyword arguments *description* (defaulting to ``""``) and *alias* (defaulting to ``None``).  The one file to which all others added by the function are associated should have its description set to *description* and its alias set to *alias*.

``add_bowtie_index`` above obeys all of these.  Here is a simpler function that creates an index for a BAM file, then adds both BAM and index to the repository::

    def add_and_index_bam(ex, bamfile, description="", alias=None):
        sort = sort_bam(ex, bamfile)
        index = index_bam(ex, sort)
        ex.add(sort, description=description, alias=alias)
        ex.add(index, description=description + " (BAM index)",
               associate_to_filename=sort, template='%s.bai')
        return fileid

A file adding function need not add multiple files to be useful.  One of the most useful file adding functions in :mod:`bein.util` is :func:`~bein.util.add_pickle`, which takes any Python value, serializes it to a file, and adds that file to the repository::

    def add_pickle(execution, val, description="", alias=None):
        filename = unique_filename_in()
        with open(filename, 'wb') as f:
            pickle.dump(val, f)
        execution.add(filename, description=description, alias=None)
        return filename

There is another useful idiom for file adding functions.  If you have a series of commands that construct an object, such as a plot, then you can write the file adding function as a context manager to wrap those commands.  For instance, the function :func:`~bein.util.add_figure` in :mod:`bein.util` creates plots with `matplotlib`, as in::

    with execution(M) as ex:
        ...
        with add_figure(ex, 'eps', alias='my histogram') as fig:
            hist(a)
            xlabel('Random things I found')
        ...

This plots a histogram of whatever is in ``a``, and adds it to the repository as an EPS file with the alias ``'my histogram'``.  To write such file adding functions, decorate the function with ``@contextmanager`` (you will need to import is, such as with ``from contextlib import contextmanager``).  The function should do any setup required, then ``yield`` a value representing the object (in the case above, the figure), then add any necessary files and do any cleanup required.  At the ``yield`` statement, the body of the ``with`` statement is run.  Here is the code for ``add_figure``::

    @contextmanager
    def add_figure(ex, figure_type='eps', description="", alias=None):
        f = pylab.figure()
        yield f
        filename = unique_filename_in() + '.' + figure_type
        f.savefig(filename)
        ex.add(filename, description=description, alias=alias)
        return filename

It may seem odd to have *description* and *alias* arguments, but not the arguments to associate a file to another that :meth:`bein.Execution.add` has.  In practice, these turn out not to be very useful for file adding functions, so you feel no qualm about omitting them.

Structuring complicated workflows
*********************************

This guide has given a lot of advice on how to structure individual functions and programs in bein, but what advice can we give on arranging a workflow as a whole?

First, put it in a single module unless it grows truly enormous.  If it reaches that point, you probably have a number of functions that should be cleaned up and contributed to :mod:`bein.util`.  I look forward to receiving them.  Once they are in the library for you to call, your module will shrink back to a usable size.

While developing, keep an ``ipython`` session running in a terminal in the same directory as your module.  As you make changes to the module, run::

    import modulename
    reload(modulename)

to load your changes into ``ipython``.

Inside the module, connect to your MiniLIMS first thing, and leave it as a global variable in the module.  Yes, global variables are bad practice, but you will use this one so universally that it justifies the practice.  All your actual workflows, on the other hand, you should put inside functions.  That way when you load or reload the module, they don't automatically run.  For workflows that take a lot of time, this would be especially annoying.

Begin crudely.  Get the first steps of your workflow working first, and inspect them with ``beinclient``.  Add a piece at a time, making sure it works.  Use :func:`~bein.util.add_pickle` and :func:`~bein.util.add_figure` to store and plot and intermediate computations that will be helpful to you.  However, don't try to do publication quality plots in a workflow.  You will inevitably want to tweak them and the time waiting for the workflow to finish is wasted.  Instead, build them from pickled intermediates.

Once the whole thing is working, then go back and start editing it to make it elegant.  Factor out logical sections of the workflow into functions, and generalize those functions.  Parallelize any places you can.  Look for any repeated additions of structured sets of files to the repository and write a file adding function to handle that case.

Don't make your executions small and atomic.  Executions are a very crude form of isolation, and should usually be made as large as possible, say, one per script.

From here, spend some time with the documentation for bein's modules, and read the source code of bein itself.  Remember, it's short, less than 500 lines not counting blank lines and documentation.  You might also be interested in the :doc:`essay`.
