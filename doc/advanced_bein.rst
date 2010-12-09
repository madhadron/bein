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



Writing robust program bindings
*******************************

Combining bindings into larger actions
**************************************

Keep an initial execution argument for consistency of syntax.


Custom ``add`` commands
***********************


Structuring complicated workflows
*********************************

Put it in a single module

Pickle any intermediate computations you may want later

Don't be afraid of plotting as you go along

Put your workflow in a function, not just toplevel in the module.

Make it work crudely first, then make it elegant.

Factor out actions contributing to common tasks into functions.

Get unique filenames whenever you need them with ``unique_filename_in``.

Organize parallel jobs and use list comprehension idiom to use them as a "checkpoint."

Put your MiniLIMS toplevel in the module.  Makes it easier to get to.  I generally call it ``M`` because I refer to it so much.

Keep an ipython open and run ``import modulename`` and ``reload(modulename)`` as you go to make things fast.

As you get bindings and functions that are really robust and general, move them into your own utilities library, and send them to me so I can add them to bein.util for everyone else.

When binding a program, don't try to handle all its arbitrary cases with different arguments.  Just choose the arguments you need now and make that work.  You can bind another case if you need it so fast that you shouldn't worry about it.  On the other hand, if you have a function that prints out a lot of structured information, go ahead and spend the time to parse it all and make it into a nice Python dictionary.

When binding programs, remember that your return_value function will only get called if the program succeeded (returned 0) so you can pretty much assume that your stdout and stderr look the way they're supposed to and not bother with error conditions.  This makes binding much simpler.



