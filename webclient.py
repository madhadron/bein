"""doc string"""
from bein import *
from datetime import *
import cherrypy
import sys
import getopt
import os

from webclient_constants import *

usage = """Write usage info"""

def file_to_html(lims, id_or_alias):
    fileid = lims.resolve_alias(id_or_alias)
    fields = lims.db.execute("""select external_name, repository_name,
                                      created, description, origin,
                                      origin_value
                                from file where id=?""", 
                             (fileid,)).fetchone()
    if fields == None:
        raise ValueError("No such file " + str(id_or_alias) + " in MiniLIMS.")
    else:
        [external_name, repository_name, created, description,
         origin, origin_value] = fields
        aliases = ['"' + a + '"' for (a,) in 
                   lims.db.execute("select alias from file_alias where file=?",
                                   (fileid,))]
        if aliases == []:
            alias_text = "<em>(no aliases)</em>"
        else:
            alias_text = ", ".join(aliases)
        if description == "":
            description = '<em>(no description)</em>'
        if origin == 'execution':
            origin_text = 'execution %d at %s' % (origin_value, created)
        elif origin == 'import':
            origin_text = 'manually imported at %s' % (created, )
        elif origin == 'copy':
            origin_text = 'copy of %d' % (origin_value, )
    return("""<div class="file">
              <a name="file%d"></a>
              <h2>%d - %s</h2>
              <p><span class="label">Aliases</span>
                 <span class="aliases">%s</span></p>
              <p><span class="label">External name</span>
                 <span class="external_name">%s</span></p>
              <p><span class="label">Repository name</span>
                 <span class="repository_name">%s</span></p>
              <p><span class="label">Created</span>
                 <span class="created">%s</span></p>
              </div>
	""" % (fileid, fileid, description, alias_text,
               external_name, repository_name, origin_text))

def execution_to_html(lims, exid):
    fields = lims.db.execute("""select started_at, finished_at, 
                                working_directory, description
                                from execution where id=?""",
                             (exid, )).fetchone()
    if fields == None:
        raise ValueError("No such execution " + str(exid) + " in MiniLIMS")
    else:
        [started_at, finished_at, working_directory, description] = fields
    if description == "":
        description = "<em>(no description)</em>"
    started_at_text = datetime.fromtimestamp(started_at).strftime("%Y-%m-%d %H:%M:%S")
    finished_at_text = datetime.fromtimestamp(finished_at).strftime("%Y-%m-%d %H:%M:%S")
    used_files_text = ", ".join([str(f) for (f,) in
                                 lims.db.execute("""select file from execution_use 
                                                    where execution=?""", 
                                                 (exid,)).fetchall()])
    if used_files_text == "":
        used_files_text = "<em>(no used files)</em>"

    return("""<div class="execution">
              <a name="execution%d"></a>
              <h2>%d - %s</h2>
 	<p><span class="label">Ran</span> from %s to %s</p>
 	<p><span class="label">Working directory</span> 
           <span class="working_directory">%s</span></p>
 	<p><span class="label">Used files</span> %s</p>
 	<p><span class="label">Added files</span> (none)</p>

    """ % (exid, exid, description, started_at_text, finished_at_text, working_directory, used_files_text))
	
# 	<div class="program">
# 	  <h3>touch af432GADfwwkjGweff23</h3>
# 	  <p>Pid 14332 exited with code 0</p>
	  
# 	  <div class="output">
# 	    <div class="row">
# 	      <div class="stdout">
# 		<p><b><tt>stdout</tt></b></p>
# 		<pre>This is some output from stdout</pre>
# 	      </div>
# 	      <div class="stderr">
# 		<p><b><tt>stderr</tt></b></p>
# 		<pre>And there were error messages!
# 		  Lawks!</pre>
# 	      </div>
# 	    </div>
# 	  </div>
# 	</div>
	


class BeinClient(object):
    def __init__(self, minilims):
        self.minilims_path = minilims
        self.minilims = MiniLIMS(minilims)
    
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
        return """<div id="tabs-1" class="tab_content">""" + \
            "".join([execution_to_html(self.minilims, ex)
                     for (ex,) in self.minilims.db.execute("select id from execution").fetchall()]) + \
            """</div>"""
    
# 	<h2>1 - Testing bein system</h2>
# 	<p><span class="label">Ran</span> from 2010-11-15 13:12:12 to 2010-11-15 13:12:52</p>
# 	<p><span class="label">Working directory</span> /home/ross/data/projects/bein/5rwafGAsdffRFEW32Fsd</p>
# 	<p><span class="label">Used files</span> (none)</p>
# 	<p><span class="label">Added files</span> (none)</p>
	
# 	<div class="program">
# 	  <h3>touch af432GADfwwkjGweff23</h3>
# 	  <p>Pid 14332 exited with code 0</p>
	  
# 	  <div class="output">
# 	    <div class="row">
# 	      <div class="stdout">
# 		<p><b><tt>stdout</tt></b></p>
# 		<pre>This is some output from stdout</pre>
# 	      </div>
# 	      <div class="stderr">
# 		<p><b><tt>stderr</tt></b></p>
# 		<pre>And there were error messages!
# 		  Lawks!</pre>
# 	      </div>
# 	    </div>
# 	  </div>
# 	</div>
	
# 	<h2>2 - Simulate RNASeq data sets</h2>
# 	<p><span class="label">Ran</span> from 2010-11-16 13:13:01 to 2010-11-16 13:52:12</p>
# 	<p><span class="label">Working directory</span> /home/ross/data/projects/rnaseq/Gfjwer532jASDioiwfVA</p>
# 	<p><span class="label">Used files</span> (none)</p>
# 	<p><span class="label">Added files</span> <a href="#file1">1 - FASTA file of selected sequences for RNASeq simulation</a></p>
	
# 	<div class="program">
# 	  <h3>python code/simulate.py -n 61300 -p aK234kwwVa23j23f2FW9 aK234kwwVa23j23f2FW9 shhDFmDDMDVsnRcIZ4AH</h3>
# 	  <p>Pid 1111 exited with code 0</p>
# 	  <div class="output">
# 	    <div class="row">
# 	      <div class="stdout">
# 		<p><b><tt>stdout</tt></b></p>
# 		<pre>Importing transcripts...done
# 		  Simulating...done</pre>
# 	      </div>
# 	      <div class="stderr">
# 		<p><b><tt>stderr</tt></b></p>
# 		<pre>Meep</pre>
#               </div>
#             </div>
# 	  </div>
# 	</div>

# 	<div class="program">
# 	  <h3>python code/simulate.py -n 61300 -p aK234kwwVa23j23f2FW9 aK234kwwVa23j23f2FW9 ELOZw8BZ1gAThoX6KoqZ</h3>
# 	  <p>Pid 1112 exited with code 0</p>
# 	  <div class="output">
# 	    <div class="row">
# 	      <div class="stdout">
# 		<p><b><tt>stdout</tt></b></p>
# 		<pre>Importing transcripts...done
# 		  Simulating...done</pre>
# 	      </div>
# 	      <div class="stderr">
# 		<p><b><tt>stderr</tt></b></p>
# 		<pre></pre>
#               </div>
#             </div>
# 	  </div>
# 	</div>
#       </div>
# """

    def files_tab(self):
        return """<div id="tabs-2" class="tab_content">""" + \
            "".join([file_to_html(self.minilims, f)
                     for (f,) in self.minilims.db.execute("select id from file").fetchall()]) + \
            """</div>"""

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

