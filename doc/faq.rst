FAQ
===

Why another workflow manager?
-----------------------------

Why didn't we just use Galaxy or OpenBIS or whatever?  Because trying to muck around with them to figure out how to do something is nightmarish.  They're meant to package things up for those who can only point and click, not to support you while you figure out what it is you're supposed to package up.

Python sucks!  Why didn't you write it in X?
--------------------------------------------

If X is Erlang, Haskell, or Scheme, then I already did.  Go read my :doc:`essay`.  Otherwise, I needed a language that I knew, that other people in my group knew, that had an interactive REPL, plenty of libraries, and didn't make me want to gouge my eyes out.  That last criterion eliminates Perl.  The only other languages that meet these criteria are Ruby and Python, and the scientific libraries in Python are so much more advanced than in Ruby that it was no decision at all.

What operating systems does it run on?
--------------------------------------

Linux and MacOS X, certainly.  I know of no reason why it wouldn't run on Windows, but I can count the number of hours I have spent using a Windows machine since Windows 98 was exciting and new on my hands.

Is it only for bioinformatics?  What about my field?
----------------------------------------------------

Bein's core logic should be useful almost anywhere.  The current utilities are mostly for bioinformatics just because it was written in a bioinformatics group.  If you write a set of utilities for mass spectrometry or analytical chemistry or whatever other field, please send them to me and I'll happily add them to bein.
