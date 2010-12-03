# bein/webclient.py
# Copyright 2010 Frederick Ross

# This file is part of bein.

# Bein is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your
# option) any later version.

# Bein is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# You should have received a copy of the GNU General Public License
# along with bein.  If not, see <http://www.gnu.org/licenses/>.

"""
beinclient 0.1
Fred Ross, <fred dot ross at epfl dot ch>

Beinclient is a simple web interface for MiniLIMS repositories.  It
has no security or concept of users, and is meant purely for
individual use.  However, it may serve as a model if you need to
access the repository for more sophisticated interfaces.
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
-h         Print this message and exit
repository MiniLIMS repository to serve
"""

def file_to_html(fileid, file):
    """Format a file from the MiniLIMS as HTML.

    'fileid' is the id the File object was stored under in the
    repository.  'file' should be a dictionary such as that returned
    by the fetch_file method of a MiniLIMS object.  The returned HTML
    is a self contained div.
    """
    if file['origin'] == 'import':
        origin_text = 'manually imported at %s' % file['created']
        created_by = 'import'
    elif file['origin'][0] == 'execution':
        origin_text = '<a href="#execution-%d" onclick="execution_tab();">execution %d</a> at %s' % \
                      (file['origin'][1], file['origin'][1], file['created'])
        created_by = 'ex%d' % file['origin'][1]
    elif file['origin'][0] == 'copy':
        origin_text = 'copy of %d' % file['origin'][1]
        created_by = 'copy%d' % file['origin'][1]

    if file['description'] == "":
        description = '<em>(no description)</em>'
    else:
        description = file['description']

    if file['immutable']:
        delete_text = """<span class="delete_link">Immutable</span>"""
    else:
        delete_text = """<input class="delete_link" type="button" value="Delete" onclick="delete_entry('file',%d);" />""" % (fileid,)

    if file['aliases'] == []:
        alias_text = "<em>(no aliases)</em>"
    else:
        alias_text = ", ".join(['"'+a+'"' for a in file['aliases']])

    if file['associations'] == []:
        association_text = "<em>(no associations)</em>"
    else:
        association_text = ", ".join(["""'%s' on file <a href="#file-%d">%d</a> """ % (t,f,f) for (f,t) in file['associations']])

    if file['associated_to'] == []:
        associated_to_text = "<em>(not associated to any files)</em>"
    else:
        associated_to_text = ", ".join(["""'%s' on file <a href="#file-%d">%d</a> """ % (t,f,f) for (f,t) in file['associated_to']])
        
    return """<div class="created-by-%s">
              <div class="file" id="file-%d">
              <a name="file-%d"></a>
              <h2>%d - %s <a class="download_link" href="download?fileid=%d">Download</a> %s</h2>
              <p><span class="label">Aliases</span>
                 <span class="aliases">%s</span></p>
              <p><span class="label">Associations</span>
                 <span class="associations">%s</span></p>
              <p><span class="label">Associated to</span>
                 <span class="associated_to">%s</span></p>
              <p><span class="label">External name</span>
                 <span class="external_name">%s</span></p>
              <p><span class="label">Repository name</span>
                 <span class="repository_name">%s</span></p>
              <p><span class="label">Created</span>
                 <span class="created">%s</span></p>
              </div></div>
	""" % (created_by, fileid, fileid, fileid, description, fileid, delete_text,
               alias_text, association_text, associated_to_text, file['external_name'],
               file['repository_name'], origin_text)


def execution_to_html(exid, ex):
    """Render an execution into HTML.

    'exid' is the id under which the execution is stored in the
    repository, and 'ex' is a dictionary such as that returned by the
    fetch_execution method of a MiniLIMS object.  The returned HTML is
    a standalone div.
    """
    if ex['description'] == "":
        description = "<em>(no description)</em>"
    else:
        description = ex['description']

    if ex['immutable']:
        delete_text = """<span class="delete_link">Immutable</span>"""
    else:
        delete_text = """<input class="delete_link" type="button" value="Delete" onclick="delete_entry('execution',%d);">""" % exid

    started_at_text = datetime.fromtimestamp(ex['started_at']).strftime("%Y-%m-%d %H:%M:%S")
    finished_at_text = datetime.fromtimestamp(ex['finished_at']).strftime("%Y-%m-%d %H:%M:%S")

    if ex['used_files'] == []:
        used_files_text = ""
    else:
        used_files_text = """<p><span class="label">Used files</span> %s</p>""" % \
                          (", ".join(["""<a href="#file-%d" onclick="file_tab();">%d</a>""" % (f,f) for f in ex['used_files']]))

    if ex['added_files'] == []:
        added_files_text = ""
    else:
        added_files_text = """<p><span class="label">Added files</span> %s</p>""" % \
                           (", ".join(["""<a href="#file-%d" onclick="file_tab();">%d</a>""" % (f,f) for f in ex['added_files']]))

    if ex['exception_string'] == None:
        exstr = ""
    else:
        exstr="""<p><span style="color: red">FAILED</span>: <pre>%s</pre>""" % ex['exception_string']

    if ex['programs'] == []:
        program_text = """<div class="program"><h3><em>(no programs)</em></h3></div>"""
    else:
        program_text = "".join([program_to_html(p) for p in ex['programs']])
                                       
    return """<div class="execution" id="execution-%d">
              <a name="execution-%d"></a>
              <h2>%d - %s %s</h2>
              <p><span class="label">Ran</span> from %s to %s</p>
              <p><span class="label">Working directory</span> 
              <span class="working_directory">%s</span></p>
              %s %s %s %s
              </div>
              """ % (exid, exid, exid, description, delete_text,
                     started_at_text, finished_at_text, ex['working_directory'],
                     used_files_text, added_files_text, program_text, exstr)

def program_to_html(program):
    """Render a program to HTML.

    'program' is a dictionary such as that in the programs field of an
    execution dictionary returned by the fetch_execution method of a
    MiniLIMS object.
    """
    if program['stdout'] != "":
        stdout = """<p><span class="program_label">stdout</span><br/><pre>%s</pre></p>""" % program['stdout']
    else:
        stdout = ""
    if program['stderr'] != "":
        stderr = """<p><span class="program_label">stderr</span><br/><pre>%s</pre></p>""" % program['stderr']
    else:
        stderr = ""
    arguments = " ".join(program['arguments'])
    argument_color = (program['return_code'] == 0) and "black" or "red"
    return """<div class="program">
              <h3 style="color: %s;"><tt>%s</tt></h3>
              <p>Pid %d exited with value %d</p>
              %s
              %s
              </div>""" % (argument_color, arguments, program['pid'],
                           program['return_code'], stdout, stderr)


class BeinClient(object):
    def __init__(self, lims):
        self.lims = MiniLIMS(lims)
    
    @cherrypy.expose
    def index(self):
        return html_header + self.executions_tab() + self.files_tab() \
            + html_footer

    # minilimscss, jquery, and jscript are ancillary files giving the
    # CSS and JavaScript for the client.
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

    # delete is a method to be called by JQuery.  It doesn't return
    # anything in particular, but deletes a file.
    @cherrypy.expose
    def delete(self, obj_type=None, obj_id=None):
        try:
            obj_id = int(obj_id)
        except ValueError, v:
            return "Bad value!"
        if obj_type == "execution":
            self.lims.delete_execution(obj_id)
            return ""
        if obj_type == "file":
            self.lims.delete_file(obj_id)
            return ""
        else:
            return "Unknown object type."

    @cherrypy.expose
    def download(self, fileid=None):
        """Serve a file to the user with the MiniLIMS external name."""
        external_name = self.lims.fetch_file(int(fileid))['external_name']
        repository_path = self.lims.path_to_file(int(fileid))
        return serve_file(repository_path,
                          content_type = "application/x-download", 
                          disposition = "attachment",
                          name = external_name)

    def executions_tab(self):
        exids = self.lims.search_executions()
        exids.sort()
        return """<div id="tabs-1" class="tab_content">%s</div>""" % \
               "".join([execution_to_html(exid, self.lims.fetch_execution(exid))
                        for exid in exids])
    
    def files_tab(self):
        fileids = self.lims.search_files()
        fileids.sort()
        return """<div id="tabs-2" class="tab_content">%s</div>""" % \
               "".join([file_to_html(id,self.lims.fetch_file(id)) for id in fileids])

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
        lims = args[0]
        print "MiniLIMS repository: ", lims
        if not(os.path.exists(lims)) or \
                not(os.path.isdir(lims + '.files')):
            raise Usage("No MiniLIMS repository found at " + lims)
        cherrypy.config.update({'server.socket_port':port})
        cherrypy.quickstart(BeinClient(lims))
        sys.exit(0)
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, usage
        sys.exit(2)

if __name__ == '__main__':
    sys.exit(main())

