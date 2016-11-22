#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
from xlwt import Workbook
import xlrd

class MainHandler(webapp2.RequestHandler):
	def get(self):
		book = Workbook()
		# book = xlrd.open_workbook("count.xls")
		sheet1 = book.add_sheet('Sheet 1')
		book.add_sheet('Sheet 2')
		sheet1.write(0,0,'A1')
		sheet1.write(0,1,'B1')
		# row1 = sheet1.row(1)
		# row1.write(0,'A2')
		# row1.write(1,'B2')
		# sheet1.col(0).width = 10000
		# sheet2 = book.get_sheet(1)
		# sheet2.row(0).write(0,'Sheet 2 A1')
		# sheet2.row(0).write(1,'Sheet 2 B1')
		# sheet2.flush_row_data()
		# sheet2.write(1,0,'Sheet 2 A3')
		# sheet2.col(0).width = 5000
		# sheet2.col(0).hidden = True
		
		self.response.headers['Content-Type'] = 'application/ms-excel'
		self.response.headers['Content-Transfer-Encoding'] = 'Binary'
		self.response.headers['Content-disposition'] = 'attachment; filename="whatever.xls"'
		book.save(self.response.out)
 
		

app = webapp2.WSGIApplication([
    ('/download', MainHandler)
], debug=True)
