"""
beinclient 0.1
Fred Ross, <fred dot ross at epfl dot ch>

Beinclient is a simple web interface for MiniLIMS repositories.
"""
from bein import *
from datetime import *
import cherrypy
from cherrypy.lib.static import serve_file
import sys
import getopt
import os

from webclient_constants import *

usage = """beinclient [-p port] [-h] repository

-p port    Listen for HTTP connections on 'port' (default: 8080)
-h         Print this message
repository MiniLIMS repository to serve
"""

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
            origin_text = """<a href="#execution-%d" onclick="execution_tab();">execution %d</a> at %s""" % (origin_value, origin_value, created)
        elif origin == 'import':
            origin_text = 'manually imported at %s' % (created, )
        elif origin == 'copy':
            origin_text = 'copy of %d' % (origin_value, )
    return("""<div class="file" id="file-%d">
              <a name="file-%d"></a>
              <h2>%d - %s <a class="download_link" href="download?fileid=%d">Download</a> 
              <input class="delete_link" type="button" value="Delete" onclick="delete_entry('file',%d);" /></h2>
              <p><span class="label">Aliases</span>
                 <span class="aliases">%s</span></p>
              <p><span class="label">External name</span>
                 <span class="external_name">%s</span></p>
              <p><span class="label">Repository name</span>
                 <span class="repository_name">%s</span></p>
              <p><span class="label">Created</span>
                 <span class="created">%s</span></p>
              </div>
	""" % (fileid, fileid, fileid, description, fileid, fileid, alias_text,
               external_name, repository_name, origin_text))

def execution_to_html(lims, exid):
    fields = lims.db.execute("""select started_at, finished_at, 
                                working_directory, description,
                                exception
                                from execution where id=?""",
                             (exid, )).fetchone()
    if fields == None:
        raise ValueError("No such execution " + str(exid) + " in MiniLIMS")
    else:
        [started_at, finished_at, working_directory, description,
         exstr] = fields
    if description == "":
        description = "<em>(no description)</em>"
    if exstr == None:
        exstr = ""
    else:
        exstr="""<p><span style="color: red">FAILED</span>: <pre>%s</pre>""" % (exstr,)
    started_at_text = datetime.fromtimestamp(started_at).strftime("%Y-%m-%d %H:%M:%S")
    finished_at_text = datetime.fromtimestamp(finished_at).strftime("%Y-%m-%d %H:%M:%S")
    used_files_text = ", ".join([str(f) for (f,) in
                                 lims.db.execute("""select file from execution_use 
                                                    where execution=?""", 
                                                 (exid,)).fetchall()])
    if used_files_text != "":
        used_files_text = """<p><span class="label">Used files</span> %s</p>""" % (used_files_text,)
    added_files_text = ", ".join(["""<a href="#file-%d" onclick="file_tab();">%d</a>""" % (f,f) for (f,) in
                                  lims.db.execute("""select id from file where origin='execution' and origin_value=?""", (exid,)).fetchall()])
    if added_files_text != "":
 	added_files_text = """<p><span class="label">Added files</span> %s</p>""" % (added_files_text,)
    return("""<div class="execution" id="execution-%d">
              <a name="execution-%d"></a>
              <h2>%d - %s <input class="delete_link" type="button" value="Delete" onclick="delete_entry('execution',%d);"></h2>
 	<p><span class="label">Ran</span> from %s to %s</p>
 	<p><span class="label">Working directory</span> 
           <span class="working_directory">%s</span></p>
 	%s %s
        %s 
        %s
        </div>
    """ % (exid, exid, exid, description, exid, started_at_text, finished_at_text, working_directory, used_files_text, added_files_text, programs_to_html(lims,exid), exstr))

def programs_to_html(lims, exid):
    progids = [x for (x,) in lims.db.execute("""select pos from program where execution=?""", (exid,))]
    if progids == []:
        return """<div class="program"><h3><em>(no programs)</em></h3></div>"""
    else:
        return "".join([program_to_html(lims,exid,pos) for pos in progids])

def program_to_html(lims, exid, pos):
    fields = lims.db.execute("""select pid,return_code,stdout,stderr from program where pos=? and execution=?""", (pos,exid)).fetchone()
    if fields == None:
        raise ValueError("Could not get values for program " + str(pos) + " in execution " + str(exid))
    else:
        [pid,return_code,stdout,stderr] = fields
        if stdout != "":
            stdout = """<p><span class="program_label">stdout</span><br/><pre>%s</pre></p>""" % (stdout,)
        if stderr != "":
            stderr = """<p><span class="program_label">stderr</span><br/><pre>%s</pre></p>""" % (stderr)
    arguments = " ".join([x for (x,) in 
                          lims.db.execute("""select argument from argument 
                                            where program=? and execution=? 
                                            order by pos""", (pos,exid))])
    argument_color = (return_code == 0) and "black" or "red"
    return """<div class="program">
              <h3 style="color: %s;"><tt>%s</tt></h3>
              <p>Pid %d exited with value %d</p>
              %s
              %s
              </div>""" % (argument_color, arguments, pid, return_code, stdout, stderr)


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

    @cherrypy.expose
    def delete(self, obj_type=None, obj_id=None):
        try:
            obj_id = int(obj_id)
        except ValueError, v:
            return "Bad value!"
        if obj_type == "execution":
            self.minilims.delete_execution(obj_id)
            return ""
        if obj_type == "file":
            self.minilims.delete_file(obj_id)
            return ""
        else:
            return "Unknown object type."

    @cherrypy.expose
    def download(self, fileid=None):
        (repository_name, external_name) = self.minilims.db.execute("select repository_name,external_name from file where id = ?", (fileid,)).fetchone()
        return serve_file(os.path.join(self.minilims.file_path, 
                                       repository_name),
                          content_type = "application/x-download", 
                          disposition = "attachment",
                          name = external_name)

    def executions_tab(self):
        return """<div id="tabs-1" class="tab_content">""" + \
            "".join([execution_to_html(self.minilims, ex)
                     for (ex,) in self.minilims.db.execute("select id from execution").fetchall()]) + \
            """</div>"""

    def files_tab(self):
        return """<div id="tabs-2" class="tab_content">""" + \
            "".join([file_to_html(self.minilims, f)
                     for (f,) in self.minilims.db.execute("select id from file").fetchall()]) + \
            """</div>"""

class Usage(Exception):
    def __init__(self,  msg):
        self.msg = msg

def main(argv = None):
    port = 8080
    if argv is None:
        argv = sys.argv[1:]
    try:
        try:
            opts, args = getopt.getopt(argv, "p:h", ["help"])
        except getopt.error, msg:
            raise Usage(msg)
        for o, a in opts:
            if o in ("-h", "--help"):
                print __doc__
                print usage
                sys.exit(0)
            if o in ("-p",):
                port = int(a)
        if len(args) != 1:
            raise Usage("No MiniLIMS repository specified.")
        minilims = args[0]
        print "MiniLIMS repository: ", minilims
        if not(os.path.exists(minilims)) or \
                not(os.path.isdir(minilims + '.files')):
            raise Usage("No MiniLIMS repository found at " + minilims)
        cherrypy.config.update({'server.socket_port':port})
        cherrypy.quickstart(BeinClient(minilims))
        sys.exit(0)
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, usage
        sys.exit(2)

if __name__ == '__main__':
    sys.exit(main())

