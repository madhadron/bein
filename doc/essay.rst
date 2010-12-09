Essay on the design of bein
===========================

by Fred Ross, <madhadron at gmail dot com>

I am very proud of bein.  At the same time its history makes me feel like something of a fraud.

After being kicked out of gradschool, I was hired to clean up the mess of analysis scripts in the Bioinformatics and Biostatistics Core Facility at the EPFL in Switzerland.  I looked over the reams of brittle Perl and pointed out that some infrastructure would be a good idea.  My boss agreed.  So began a year of writing and rewriting.

The first incarnation of bein was an Erlang web application.  It had programs, files, and executions.  Users could upload scripts in R or Perl as programs, anything they wanted as files, and set up executions of programs running on files.  The results were tracked and all history preserved.

Never write anything that has to play nicely with POSIX in Erlang.  Just a hint.  I had not sufficiencly tested Erlang before I began to make sure it would fulfill my needs.  This was unprofessional of me, and is the part of this history I look on with some shame.  Thus began the great rewrite in Haskell.  This went much better.  I had a functional version in fairly short order.

Then I tried to deploy it on the local Linux cluster.

I couldn't install the Haskell compiler.  I spent hours.  I drove the admins half nuts.  I learned to loathe that cluster.  And the Haskell version went down the drain as well, though not before I learned some valuable lessons.

The web application was a terrible idea.  My colleagues needed to be able to hack together scripts and sequences of programs.  That meant either adding a big graphical workflow manager in the web application, which no one wanted to use, and I didn't want to write, or stripping bein down and making it a scripting environment.

The next version was done in PLT Scheme.  If you need a domain specific language, write Lisp, right?  This version was remarkable.  It embedded a domain specific language for executions, had all kinds of neat things like automatic program binding in Unix, automatically detected files in its database being used by executions and wrote them to working directories, and that was just the normal stuff.  Then there was the black magic.  It could take a script, reflect its source code into text, look up all the necessary libraries to include, write the whole thing to disk, and run that script via the LSF batch system on the cluster.  This means users could seamlessly dispatch arbitrary scripts via LSF.  It had a graphical browser for its database with live search and updating.  I pushed it out to my colleagues in pride.

Two things then happened.

First, no one used the black magic.  It turned out that it just wasn't important for the day to day work of the group.  LSF submission?  They only submitted single programs doing big hunks of calculation to LSF.  All the plumbing inbetween was computationally trivial, and there was no reason to push it out to a compute node.  Automatic program binding?  It turned out fiddling around with stdout to get what you wanted pretty much negated this.  Automatically pulling files from the repositories confused things more than it helped, since every time they forgot to convert an integer to a string in a command, bein thought they were asking for a file.

Second, the Swiss government chose not to renew my visa, despite our best efforts to convince them otherwise.  Suddenly I was going to be leaving the group in a few months, and there wasn't another Lisp programmer to be had.  I would leave them with immature software and no one who could maintain it.  As anyone with a little programming experience can tell you, this is a *bad* thing.

"It's too late to rewrite it," my boss told me.  I thought about this a bit, then one Sunday, just after lunch, stretched out on my couch, and rewrote it from scratch in Python.

At this point the Python fanboys start proclaiming the glory of their language.  Fools.  Much of the black magic in the Scheme version wasn't even possible in Python, but I needed a language other people in the lab knew.  Python's lovely, but rewriting bein's core in a Sunday afternoon was possible because I threw away all the magic.

Really.  All of it.  I'd watched people use the system a bit.  Anywhere that someone hadn't used a magical feature, I ditched it.  The new bein was brutally simple, and under 500 lines of code.  It did 85% of what we needed.  It had no unit tests (the Erlang, Haskell, and Scheme versions had been written in parallel with complete test suites).

I used it for some of my own work on RNASeq over the next two weeks, and added features.  It quickly reached 95%, and the last 5% could be fudged.  The core system remained under 500 lines of code.  I added the simplest web client that could possibly be useful.

So what changed?  Here's a partial list:

**Dispatching arbitrary source code over LSF**
    The Python version can send a single Unix command via LSF and get its results back, and no more.

**Nesting executions**
    If an execution was started inside another execution in the Scheme version, no new execution was actually started.  There was only ever a single layer.  Thus you could wrap "execution" around any fragment just to make sure it would always behave sensibly.  Mathematically it's the right thing to do, but it added a lot of complexity.  No one ever used it.  I threw it away.  Now if you start an execution inside an execution, you get a new execution.

**Immediate tracking and assignment of files**
    The Scheme version tracked the progress of an execution in its database as it went.  A file added to the database was immediately assigned an ID which was available for the rest of the execution.  This made the database access fairly complicated.  In the Python version, everything is written to the database in one go at the end of the execution.  Files don't get an ID until then.  But the only thing you want the ID for in the same execution is to add aliases or associations with other files, though, so I just added that instead.

**Fine grained file origins**
    The Scheme version recorded exactly which program in which execution produced a given file.  The Python version only records which execution it was added by.  The user has to keep all the files from a particular execution straight.  In practice, this isn't a problem, since he just assigns each file a description.

**Configuration and paths and single repositories for users**
    The Scheme version had a primary repository for each person and a configuration file to set where executions should run and where repositories would be found.  In the Python version you have to give it the path to your repository yourself, and it runs executions in whatever directory it finds itself.

The crazy part is that this version is better.  In the Scheme version you always knew that you were dealing with bein, and it wasn't going to let you forget it.  Now you're just writing a Python script, and bein magically takes care of things behind the scenes for you.

You're still reading?  What's wrong with you?  Go get something done!  I built you a workflow and data manager.  What else do you want?!?
