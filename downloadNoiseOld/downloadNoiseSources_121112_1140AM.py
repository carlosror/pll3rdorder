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
from xlwt import Workbook, easyxf
import numpy as np

def defaultNoise():
	f=np.logspace(2,8,31)
	XTALNoise = [-135.0, -139.0, -143.0, -147.0, -151.0, -155.0, -159.0, -163.0, -167.0, -171.0, -175.0, -175.0, 
	-175.0, -175.0, -175.0, -175.0, -175.0, -175.0, -175.0, -175.0, -175.0, -175.0, -175.0, -175.0, -175.0, -175.0, 
	-175.0, -175.0, -175.0, -175.0, -175.0]
	PFDCPNoise = [-187.996638103093, -190.241344070243, -192.467214887174, -194.674330247768, -196.862613308754, 
	-199.031802524807, -201.181485227834, -203.310850741274, -205.418246002278, -207.500600033455, -209.552629371424, 
	-211.5657272981, -213.526498173049, -215.415090356603, -217.203882681849, -218.857723409653, -220.337480233407, 
	-221.608188539349, -222.650805614662, -223.474206496704, -224.125088621452, -224.692297457423, -225.285683150649, 
	-225.949869574455, -226.571646736869, -226.996978167618, -227.201392887084, -227.225489194934, -226.844381692946, 
	-226.905230648123, -227.0]
	PrescalerNoise = [-105.4, -107.5, -109.6, -111.7, -113.7, -115.7, -117.7, -119.7, -121.6, -123.5, -125.4, -127.1, 
	-128.8, -130.3, -131.6, -132.7, -133.6, -134.4, -135.1, -135.7, -136.6, -137.7, -138.8, -139.4, -139.9, -140.4, 
	-141.1, -141.9, -142.5, -142.9, -143.2]
	VCONoise = [-65.0, -69.0, -73.0, -77.0, -81.0, -85.0, -89.0, -93.0, -97.0, -101.0, -105.0, -109.0, -113.0, 
	-117.0, -121.0, -125.0, -129.0, -133.0, -137.0, -141.0, -145.0, -149.0, -153.0, -157.0, -161.0, -165.0, -169.0, 
	-173.0, -177.0, -181.0, -185.0]
	SDNoise = [-200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, 
	-200.0, -200.0, -200.0, -200.0, -192.0, -184.0, -176.0, -167.99999999999997, -160.0, -152.0, -144.0, -136.0, 
	-128.0, -120.0, -112.0, -104.0, -96.0, -88.0, -80.0]
	return f, XTALNoise, PFDCPNoise, PrescalerNoise, VCONoise, SDNoise
	
def writeNoiseSources():
	f, XTALNoise, PFDCPNoise, PrescalerNoise, VCONoise, SDNoise = defaultNoise() 
	book = Workbook()
	parameter = easyxf('font: name Arial, bold True, height 280; alignment: horizontal center')
	parameterValue = easyxf('font: name Arial, height 280; alignment: horizontal center', num_format_str='0.000E+00')
	parameterValue2 = easyxf('font: name Arial, height 280; alignment: horizontal center', num_format_str='0.000')
	columnHeader = easyxf('font: name Arial, bold True, height 240; alignment: horizontal center')
	# book = xlrd.open_workbook("count.xls")
	sheetXTAL = book.add_sheet('XTAL')
	sheetXTAL.col(0).width = 6000
	sheetXTAL.col(1).width = 8000
	sheetXTAL.write(0,0,'Frequency (Hz)',columnHeader)
	sheetXTAL.write(0,1,'XTAL Noise (dBc/Hz)',columnHeader)
	sheetPFDCP = book.add_sheet('PFDCP')
	sheetPFDCP.col(0).width = 6000
	sheetPFDCP.col(1).width = 8000
	sheetPFDCP.write(0,0,'Frequency (Hz)',columnHeader)
	sheetPFDCP.write(0,1,'PFDCP Noise (dBc/Hz)',columnHeader)
	sheetPrescaler = book.add_sheet('Prescaler')
	sheetPrescaler.col(0).width = 6000
	sheetPrescaler.col(1).width = 8000
	sheetPrescaler.write(0,0,'Frequency (Hz)',columnHeader)
	sheetPrescaler.write(0,1,'Prescaler Noise (dBc/Hz)',columnHeader)
	sheetVCO = book.add_sheet('VCO')
	sheetVCO.col(0).width = 6000
	sheetVCO.col(1).width = 8000
	sheetVCO.write(0,0,'Frequency (Hz)',columnHeader)
	sheetVCO.write(0,1,'VCO Noise (dBc/Hz)',columnHeader)
	sheetSD = book.add_sheet('Sigma Delta')
	sheetSD.col(0).width = 6000
	sheetSD.col(1).width = 10000
	sheetSD.write(0,0,'Frequency (Hz)',columnHeader)
	sheetSD.write(0,1,'Sigma Delta Noise (dBc/Hz)',columnHeader)
	for i in range(len(f)):
		sheetPFDCP.write(i+1,0,f[i],parameterValue)
		sheetXTAL.write(i+1,0,f[i],parameterValue)
		sheetPrescaler.write(i+1,0,f[i],parameterValue)
		sheetVCO.write(i+1,0,f[i],parameterValue)
		sheetSD.write(i+1,0,f[i],parameterValue)
		sheetPFDCP.write(i+1,1,PFDCPNoise[i],parameterValue2)
		sheetPrescaler.write(i+1,1,PrescalerNoise[i],parameterValue2)
		sheetVCO.write(i+1,1,VCONoise[i],parameterValue2)
		sheetSD.write(i+1,1,SDNoise[i],parameterValue2)
		sheetXTAL.write(i+1,1,XTALNoise[i],parameterValue2)
	return book
	

class MainHandler(webapp2.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'application/ms-excel'
		self.response.headers['Content-Transfer-Encoding'] = 'Binary'
		self.response.headers['Content-disposition'] = 'attachment; filename="PLLNoiseSources.xls"'
		writeNoiseSources().save(self.response.out)
 
		

app = webapp2.WSGIApplication([
    ('/download/noiseSources', MainHandler)
], debug=True)
