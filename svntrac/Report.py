# svntrac
#
# Copyright (C) 2003 Edgewall Software
# Copyright (C) 2003 Jonas Borgstr�m <jonas@edgewall.com>
#
# svntrac is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# svntrac is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Author: Jonas Borgstr�m <jonas@edgewall.com>

from util import *
from Href import href
from Module import Module
import perm
import db

import time
import StringIO

class Report (Module):
    template_name = 'report.template'

    def __init__(self, config, args, pool):
        Module.__init__(self, config, args, pool)
        
    def get_info (self, id):
        cnx = db.get_connection()
        cursor = cnx.cursor()

        if id == -1:
            # If no special report was requested, display
            # a list of available reports instead
            cursor.execute("SELECT id AS report, title "
                           "FROM report "
                           "ORDER BY report")
            title = 'available reports'
        else:
            cursor.execute('SELECT title, sql from report WHERE id=%s', id)
            row = cursor.fetchone()
            title = row[0]
            sql   = row[1]
            cursor.execute(sql)

        # FIXME: fetchall should probably not be used.
        info = cursor.fetchall()
        cols = cursor.rs.col_defs
        # Escape the values so that they are safe to have as html parameters
        info = map(lambda row: map(lambda x: escape(x), row), info)
        return [cols, info, title]
        
    def render_headers(self, out, row):
        """
        render a html table header with the column names from the sql query.
        """
        out.write('<tr>')
	for x in row:
	    out.write('<th class="listing">%s</th>' % x[0])
        out.write('</tr>')
        
    def render_row(self, out, row, cols, row_idx):
        """
        render one html table row from one sql result row.

        Some values are handled specially: ticker and report numbers
        are hyper linked...
        """
        if row_idx % 2:
            out.write('<tr class="item-row-even">\n')
        else:
            out.write('<tr class="item-row-odd">\n')

        idx = 0
        for value in row:
            if cols[idx][0] in ['ticket', '#']:
                out.write('<td class="ticket-column"><a href="%s">#%s</a></td>' % (href.ticket(value),
                                                            value))
            elif cols[idx][0] == 'report':
                out.write('<td class="report-column"><a href="%s">{%s}</a></td>'
                          % (href.report(value), value))
                             
            elif cols[idx][0] in ['time', 'date', 'created', 'modified']:
                out.write('<td class="%s-column">%s</td>'
                          % (cols[idx][0], time.strftime('%F', time.localtime(int(value)))))

            else:
                out.write('<td class="%s-column">%s</td>' % (cols[idx][0], value))
            idx = idx + 1
        out.write('</tr>')

    def create_report(self, title, sql):
        perm.assert_permission(perm.REPORT_CREATE)

        cnx = db.get_connection()
        cursor = cnx.cursor()
        
        cursor.execute('INSERT INTO report (id, title, sql)'
                        'VALUES (NULL, %s, %s)', title, sql)
        id = cnx.db.sqlite_last_insert_rowid()
        cnx.commit()
        redirect (href.report(id))

    def delete_report(self, id):
        perm.assert_permission(perm.REPORT_DELETE)
        
        cnx = db.get_connection()
        cursor = cnx.cursor ()

        cursor.execute('DELETE FROM report WHERE id=%s', id)
        cnx.commit()
        redirect(href.report())

    def commit_changes(self, id):
        """
        saves report changes to the database
        """
        perm.assert_permission(perm.REPORT_MODIFY)

        cnx = db.get_connection()
        cursor = cnx.cursor()

        title = self.args['title']
        sql   = self.args['sql']

        cursor.execute('UPDATE report SET title=%s, sql=%s WHERE id=%s',
                       title, sql, id)
        cnx.commit()
        redirect(href.report(id))

    def render_report_editor(self, out, id, action='commit'):
        cnx = db.get_connection()
        cursor = cnx.cursor()

        if id == -1:
            title = sql = ""
        else:
            cursor.execute('SELECT title, sql FROM report WHERE id=%s', id)
            row = cursor.fetchone()
            sql = row[1]
            title = row[0]
        
        out.write(
            '<form action="%s" method="post">'
            '<input type="hidden" name="mode" value="report">'
            '<input type="hidden" name="id" value="%d">'
            '<input type="hidden" name="action" value="%s">'
            'title:<br><input type="text" name="title" value="%s" size="50">'
            '<br>sql query:'
            '<br>'
            '<textarea name="sql" cols="70" rows="10">%s</textarea>'
            '<br>'
            '<input type="submit" value="commit">&nbsp;'
            '<input type="reset" value="reset">'
            '</form>' % (get_cgi_name(), id, action, title, sql)
            )
    
    def render_report_list(self, out, id):
        """
        uses a user specified sql query to extract some information
        from the database and presents it as a html table.
        """
        try:
            [cols, rows, title] = self.get_info(id)
        except Exception, e:
            out.write('<h3>report failed: %s</h3>' % e)
            out.write('<p><a href="%s">edit</a></p>' % href.report(id, 'edit'))
            return
        if perm.has_permission(perm.REPORT_CREATE):
            out.write('<a href="%s">new report</a>' % href.report(None, 'new'))
        out.write('<h3>%s</h3><p>' % title)
        if id != -1:
            if perm.has_permission(perm.REPORT_MODIFY):
                out.write('<a href="%s">edit</a> | ' % href.report(id, 'edit'))
            if perm.has_permission(perm.REPORT_CREATE):
                out.write('<a href="%s">copy</a> | ' % href.report(id, 'copy'))
            if perm.has_permission(perm.REPORT_DELETE):
                out.write('<a href="%s">delete</a>' % href.report(id, 'delete'))
        out.write('</p>')
        
        out.write('<table class="listing" cellspacing="0" cellpadding="0">')
        self.render_headers(out, cols)
        row_idx = 0
        for row in rows:
            self.render_row(out, row, cols, row_idx)
            row_idx = row_idx + 1
        out.write('</table>')

    def render(self):
        # did the user ask for any special report?
        id = int(dict_get_with_default(self.args, 'id', -1))
        action = dict_get_with_default(self.args, 'action', 'list')

        out = StringIO.StringIO()

        if action == 'create':
            self.create_report(self.args['title'], self.args['sql'])
        elif action == 'delete':
            self.delete_report(id)
        elif action == 'commit':
            self.commit_changes(id)
        elif action == 'new':
            self.render_report_editor(out, -1, 'create')
        elif action == 'copy':
            self.render_report_editor(out, id, 'create')
        elif action == 'edit':
            self.render_report_editor(out, id, 'commit')
        else:
            self.render_report_list(out, id)

        self.namespace['content']  = out.getvalue()
