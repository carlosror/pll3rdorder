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
import numpy as np

def noiseSources():
	f=np.logspace(2,8,31)
	PFDCPNoise = [-187.996638103093, -190.241344070243, -192.467214887174, -194.674330247768, -196.862613308754, 
	-199.031802524807, -201.181485227834, -203.310850741274, -205.418246002278, -207.500600033455, -209.552629371424, 
	-211.5657272981, -213.526498173049, -215.415090356603, -217.203882681849, -218.857723409653, -220.337480233407, 
	-221.608188539349, -222.650805614662, -223.474206496704, -224.125088621452, -224.692297457423, -225.285683150649, 
	-225.949869574455, -226.571646736869, -226.996978167618, -227.201392887084, -227.225489194934, -226.844381692946, 
	-226.905230648123, -227.0]
	PrescalerNoise = [-105.4, -107.5, -109.6, -111.7, -113.7, -115.7, -117.7, -119.7, -121.6, -123.5, -125.4, -127.1, 
	-128.8, -130.3, -131.6, -132.7, -133.6, -134.4, -135.1, -135.7, -136.6, -137.7, -138.8, -139.4, -139.9, -140.4, 
	-141.1, -141.9, -142.5, -142.9, -143.2]
	VCONoise = [-16.84, -23.34, -29.84, -36.34, -42.84, -49.34, -55.84, -62.34, -68.84, -75.34, -81.83, -88.33, 
	-94.82, -101.3, -107.8, -114.2, -120.6, -126.9, -133.1, -139.0, -144.7, -150.1, -155.1, -159.7, -164.1, -168.3, 
	-172.3, -176.3, -180.3, -184.5, -188.8]
	return f, PFDCPNoise, PrescalerNoise, VCONoise
	

class MainHandler(webapp2.RequestHandler):
	def get(self):
		f, PFDCPNoise, PrescalerNoise, VCONoise = noiseSources() 
		book = Workbook()
		# book = xlrd.open_workbook("count.xls")
		sheetPFDCP = book.add_sheet('PFDCP')
		sheetPrescaler = book.add_sheet('Prescaler')
		sheetVCO = book.add_sheet('VCO')
		for i in range(len(f)):
			sheetPFDCP.write(i,0,f[i])
			sheetPrescaler.write(i,0,f[i])
			sheetVCO.write(i,0,f[i])
			sheetPFDCP.write(i,1,PFDCPNoise[i])
			sheetPrescaler.write(i,1,PrescalerNoise[i])
			sheetVCO.write(i,1,VCONoise[i])
			
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
    ('/download/noiseSources', MainHandler)
], debug=True)
