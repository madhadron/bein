Essay on the design decisions that went into bein.

Design goals

Some history:
Rewritten four times in Erlang, Haskell, Scheme, Python.  Give the details of what happened to each.

Things that were omitted:
Black magic generating scripts for LSF.  Unnecessary.
Nesting executions (unnecessary)
Adding executions and files as an execution proceeds instead of at the end.  Adds lots of complexity and cleanup, but you can get file ids as you go.  Only ever want them for adding aliases and associations, so just added that itself instead.
Multiuser web application.  Turned out to be the wrong thing.  Started out too far from the shell.
User handling and management.  Turned it into a library and this went away.

Finally sat down one Sunday and wrote most of the code of the new version in Python.  Refined it a bit and added features over the next couple weeks as I used it for my own work.  And then it went out into the wide world.
