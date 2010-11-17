"""doc string"""
import bein
import cherrypy
import sys
import getopt
import os

from webclient_constants import *

usage = """Write usage info"""

class BeinClient(object):
    def __init__(self, minilims):
        self.minilims_path = minilims
        self.minilims = bein.MiniLIMS(minilims)
    
    @cherrypy.expose
    def index(self):
        return html_header + self.executions_tab() + self.files_tab() \
            + html_footer

    @cherrypy.expose
    def minilimscss(self):
        cherrypy.response.headers['Content-Type']='text/css'
        return css

    @cherrypy.expose
    def jquery(self):
        return jquery

    @cherrypy.expose
    def jscript(self):
        return jscript

    def executions_tab(self):
        return """
      <div id="tabs-1" class="tab_content">
	<h2>1 - Testing bein system</h2>
	<p><span class="label">Ran</span> from 2010-11-15 13:12:12 to 2010-11-15 13:12:52</p>
	<p><span class="label">Working directory</span> /home/ross/data/projects/bein/5rwafGAsdffRFEW32Fsd</p>
	<p><span class="label">Used files</span> (none)</p>
	<p><span class="label">Added files</span> (none)</p>
	
	<div class="program">
	  <h3>touch af432GADfwwkjGweff23</h3>
	  <p>Pid 14332 exited with code 0</p>
	  
	  <div class="output">
	    <div class="row">
	      <div class="stdout">
		<p><b><tt>stdout</tt></b></p>
		<pre>This is some output from stdout</pre>
	      </div>
	      <div class="stderr">
		<p><b><tt>stderr</tt></b></p>
		<pre>And there were error messages!
		  Lawks!</pre>
	      </div>
	    </div>
	  </div>
	</div>
	
	<h2>2 - Simulate RNASeq data sets</h2>
	<p><span class="label">Ran</span> from 2010-11-16 13:13:01 to 2010-11-16 13:52:12</p>
	<p><span class="label">Working directory</span> /home/ross/data/projects/rnaseq/Gfjwer532jASDioiwfVA</p>
	<p><span class="label">Used files</span> (none)</p>
	<p><span class="label">Added files</span> <a href="#file1">1 - FASTA file of selected sequences for RNASeq simulation</a></p>
	
	<div class="program">
	  <h3>python code/simulate.py -n 61300 -p aK234kwwVa23j23f2FW9 aK234kwwVa23j23f2FW9 shhDFmDDMDVsnRcIZ4AH</h3>
	  <p>Pid 1111 exited with code 0</p>
	  <div class="output">
	    <div class="row">
	      <div class="stdout">
		<p><b><tt>stdout</tt></b></p>
		<pre>Importing transcripts...done
		  Simulating...done</pre>
	      </div>
	      <div class="stderr">
		<p><b><tt>stderr</tt></b></p>
		<pre>Meep</pre>
              </div>
            </div>
	  </div>
	</div>

	<div class="program">
	  <h3>python code/simulate.py -n 61300 -p aK234kwwVa23j23f2FW9 aK234kwwVa23j23f2FW9 ELOZw8BZ1gAThoX6KoqZ</h3>
	  <p>Pid 1112 exited with code 0</p>
	  <div class="output">
	    <div class="row">
	      <div class="stdout">
		<p><b><tt>stdout</tt></b></p>
		<pre>Importing transcripts...done
		  Simulating...done</pre>
	      </div>
	      <div class="stderr">
		<p><b><tt>stderr</tt></b></p>
		<pre></pre>
              </div>
            </div>
	  </div>
	</div>
      </div>
"""
    def files_tab(self):
        return """
      <div id="tabs-2" class="tab_content">
	<a name="file1"></a>
	<h2>1 - FASTA file of selected sequences for RNASeq simulation</h2>
	<p><span class="label">Aliases</span> "selected_transcripts"</p>
	<p><span class="label">External name</span> selected_transcripts.fasta</p>
	<p><span class="label">Repository name</span> AfAfwFAGGr324wrfsfer</p>
	<p><span class="label">Created</span> manually imported</p>
	
	<h2>1 - FASTA file of selected sequences for RNASeq simulation</h2>
	<p><span class="label">Aliases</span> "selected_transcripts"</p>
	<p><span class="label">External name</span> selected_transcripts.fasta</p>
	<p><span class="label">Repository name</span> AfAfwFAGGr324wrfsfer</p>
	<p><span class="label">Created</span> 2010-11-16 09:18:13 by execution 3</p>
      </div>
"""

class Usage(Exception):
    def __init__(self,  msg):
        self.msg = msg

def main(argv = None):
    verbose = False
    if argv is None:
        argv = sys.argv[1:]
    try:
        try:
            opts, args = getopt.getopt(argv, "hv", ["help","verbose"])
        except getopt.error, msg:
            raise Usage(msg)
        for o, a in opts:
            if o in ("-h", "--help"):
                print __doc__
                print usage
                sys.exit(0)
            if o in ("-v", "--verbose"):
                verbose = True
        if len(args) != 1:
            raise Usage("No MiniLIMS repository specified.")
        minilims = args[0]
        if not(os.path.exists(minilims)) or \
                not(os.path.isdir(minilims + '.files')):
            raise Usage("No MiniLIMS repository found at " + minilims)
        cherrypy.quickstart(BeinClient(minilims))
        sys.exit(0)
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, usage
        sys.exit(2)

if __name__ == '__main__':
    sys.exit(main())

