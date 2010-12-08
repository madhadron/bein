Advanced techniques in bein
===========================

File aliases
------------


File associations
-----------------


Parallel executions
-------------------

Writing robust program bindings
-------------------------------

Combining bindings into larger actions
--------------------------------------

Keep an initial execution argument for consistency of syntax.


Custom ``add`` commands
-----------------------


Structuring complicated workflows
---------------------------------

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



