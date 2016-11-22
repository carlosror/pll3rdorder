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
import os
import jinja2
import numpy as np
import math
import xlrd
from xlwt import Workbook, easyxf, Formula
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers


def is_number(s):
	try:
		float(s)
		return True
	except ValueError:
		return False
		
def scientific(number):
	'Takes a number and returns its scientific notation representation'
	#Remember it will return a STRING.
	return "{:.3e}".format(number)

def loopFilter(gamma,LoopBW,PM,CPGain,KVCO,P,Fout,Fref,R,T31):
	Fcomp = float(Fref/R)
	LoopBWRads = 2*math.pi*LoopBW
	#######
	#Numerical solution of T1 using bisection method
	#######
	def T1est(T1guess):
		wcT1 = LoopBWRads*T1guess
		#return wcT1,math.atan(wcT1)
		return PM - (180/math.pi)*(math.atan(gamma/wcT1/(1+T31)) - math.atan(wcT1) - math.atan(wcT1*T31))
	#Approximate value from Banerjee
	T1approx = ((1/math.cos(PM*math.pi/180))-math.tan(PM*math.pi/180))/LoopBWRads/(1+T31)
	#Create a bracket such T1est(a) and T1est(b) have opposite signs.
	#So that bisection method converges to a solution.
	#Since T1est(Tapprox) will be small, if it's negative and we double it, we will have a good bracket.
	#If it's positive and we halve it we'll also have a good bracket.
	if T1est(T1approx)<0:
		a=T1approx
		b=T1approx*2.0
		# print a, b
	else:
		a=T1approx*0.5
		b=T1approx
		#print a, b
	tol = 0.01
	c= (a+b)/2.0#Mid point. First guess
	#First guess will be worse than T1approx but the algorithm should still converge quickly.
	while math.fabs(T1est(c))>tol:
		# print a,b,c
		if (T1est(a)<0 and T1est(c)<0) or (T1est(a)>0 and T1est(c)>0):
			a = c
		else:
			b = c
		c= (a+b)/2.0
		# print c, T1est(c,gamma,LoopBWRads,T31,PM)
	T1approx = c
	#######
	#Rest of calculations
	#######
	
	T3 = T1approx*T31
	T2 = gamma/((LoopBWRads)**2)/(T1approx + T3)
	#print "T1approx = ",T1approx," T2 = ",T2," T3 = ",T3
	N = float(Fout/Fcomp)
	Ndig = float(N/P)
	A0_sqrt = math.sqrt((1 + (LoopBWRads*T2)**2)/(1 + (LoopBWRads*T1approx)**2)/(1 + (LoopBWRads*T3)**2))
	A0_coeff = CPGain*KVCO/((LoopBWRads)**2)/N
	A0 = A0_coeff*A0_sqrt
	A1 = A0*(T1approx + T3)
	A2 = A0*T1approx*T3
	#print "A0 = ",A0," A1 = ",A1," A2 = ",A2
	C1_sqrt = math.sqrt(1+T2*(T2*A0-A1)/A2)
	C1 = A2*(1+C1_sqrt)/(T2**2)
	C3 = (-(T2**2)*(C1**2) + T2*A1*C1 - A2*A0) / ((T2**2)*C1 - A2)
	C2 = A0 - C1 - C3
	R2 = T2/C2
	R3 = A2/C1/C3/T2
	#print "C1 = ",C1," C2 = ",C2," C3 = ",C3," R2 = ",R2," R3 = ",R3
	#return C1/1e-9,C2/1e-9,C3/1e-9,R2/1e3,R3/1e3,A2,A1,A0,N
	f=np.logspace(2,8,31)
	f2=[]
	for i in range(len(f)):
		f2.append(f[i]*2*math.pi)
	K = KVCO*CPGain/N
	numCL = []
	magCL_R = []
	magOL_R = []
	magOL_X = []
	magCL_X = []
	denCL = []
	denOL = []
	constantCL = K*N
	magCL = []
	phaseCL = []
	magOL = []
	phaseOL = []
	vcoTFNumR = []
	vcoTFNumX = []
	vcoTFNumReal = []
	vcoTFNumImag = []
	vcoTFNum = []
	magvcoTF = []
	magprescalerTF = []
	magpfdcpTF = []
	denR2 = []
	denR2_R = []
	denR2_X = []
	magR2TF = []
	magLFTF_num_R = []
	magLFTF_num_X = []
	magLFTF_num = []
	magLFTF_den_R = []
	magLFTF_den_X = []
	magLFTF_den = []
	magLFTF = []
	magLFTFR2 = []
	numR3_R = []
	numR3_X = []
	numR3 = []
	denR3 = []
	denR3_R = []
	denR3_X = []
	magR3TF = []
	magLFTFR3 = []
	magXTAL = []
	for i in range(len(f)):
		#Expand the denominator of Eq. 16.2 on page 127 to get real and imag components.
		#A3 = 0
		magCL_R.append(A2*((f2[i])**4) - A0*((f2[i])**2) + K)#Real comp. of CL denom
		magCL_X.append(K*T2*f2[i] - A1*((f2[i])**3))#Imag comp. of CL denom
		#Expand denominator of Z(s)/s for 3rd order
		magOL_R.append(A2*((f2[i])**4) - A0*((f2[i])**2))#Real comp. of OL denom
		magOL_X.append(-A1*((f2[i])**3))#Imag comp. of OL denom
		denCL.append(complex(magCL_R[i],magCL_X[i]))
		denOL.append(complex(magOL_R[i],magOL_X[i]))
		#Transfer function for VCO noise
		vcoTFNumR.append(A2*((f2[i])**4) - A0*((f2[i])**2))
		vcoTFNumX.append(-A1*((f2[i])**3))
		vcoTFNumReal.append(vcoTFNumR[i])
		vcoTFNumImag.append(vcoTFNumX[i])
		vcoTFNum.append(complex(vcoTFNumReal[i],vcoTFNumImag[i]))
		#The denominator is the same as that of the CL transfer function
		#constant.append(K*N)
		#num.append(math.sqrt(1.0+((f[i]/(1/T2))**2)))
		numCL.append(complex(1.0,f2[i]/(1/T2)))
		magCL.append(20*np.log10(constantCL) + 20*np.log10(np.abs(numCL[i])) - 20*np.log10(np.abs(denCL[i])))
		phaseCL.append((180/math.pi)*(np.angle(numCL[i]) - np.angle(denCL[i])))
		magOL.append(20*np.log10(K) + 20*np.log10(np.abs(numCL[i])) - 20*np.log10(np.abs(denOL[i])))
		phaseOL.append((180/math.pi)*(np.angle(numCL[i]) - np.angle(denOL[i])) - 180)
		magvcoTF.append(20*np.log10(np.abs(vcoTFNum[i])) - 20*np.log10(np.abs(denCL[i])))
		magprescalerTF.append(magCL[i] + 20*np.log10(1/Ndig))
		magpfdcpTF.append(magCL[i] + 20*np.log10(1/CPGain))
		denR2_R.append((C1+C2+C3) - ((2*math.pi*f[i])**2)*C3*C2*C1*R2*R3)
		denR2_X.append(2*math.pi*f[i]*(C3*R3*(C1+C2) + C2*R2*(C1+C3)))
		denR2.append(complex(denR2_R[i],denR2_X[i]))
		magR2TF.append(20*np.log10(C2) - 20*np.log10(np.abs(denR2[i])))
		magLFTF_num_R.append(-KVCO*A1*(f2[i])**2)
		magLFTF_num_X.append(A0*KVCO*f2[i] - A2*KVCO*(f2[i])**3)
		magLFTF_num.append(complex(magLFTF_num_R[i],magLFTF_num_X[i]))
		magLFTF_den_R.append(A2*(f2[i])**4 - A0*(f2[i])**2 + K)
		magLFTF_den_X.append(K*T2*f2[i] - A1*(f2[i])**3)
		magLFTF_den.append(complex(magLFTF_den_R[i],magLFTF_den_X[i]))
		magLFTF.append(20*np.log10(np.abs(magLFTF_num[i])) - 20*np.log10(np.abs(magLFTF_den[i])))
		magLFTFR2.append(magLFTF[i] + magR2TF[i])#adds the R2 TF and the LFTF
		numR3_R.append(C1+C2)
		numR3_X.append(2*math.pi*f[i]*C1*C2*R2)
		numR3.append(complex(numR3_R[i],numR3_X[i]))
		denR3_R.append((C1+C2+C3) - ((2*math.pi*f[i])**2)*C3*C2*C1*R2*R3)
		denR3_X.append(2*math.pi*f[i]*(C3*R3*(C1+C2) + C2*R2*(C1+C3)))
		denR3.append(complex(denR3_R[i],denR3_X[i]))
		magR3TF.append(20*np.log10(np.abs(numR3[i])) - 20*np.log10(np.abs(denR3[i])))
		magLFTFR3.append(magLFTF[i] + magR3TF[i])#adds the R3 TF and the LFTF
		magXTAL.append(magCL[i] - 20*np.log10(R))
	t, fT, lockTime_0p001Pcnt, lockTime_0p0001Pcnt, lockTime_0p00001Pcnt, lockTime_0p000001Pcnt, f2 = timeResponse(A2,A1,A0,T2,Fcomp,Fout,LoopBW,KVCO,CPGain)
	return C1/1e-9,C2/1e-9,C3/1e-9,R2/1e3,R3/1e3,f,magCL,magOL,phaseOL,magvcoTF,magprescalerTF,magpfdcpTF,magLFTFR2,magLFTFR3, magXTAL, t, fT, lockTime_0p001Pcnt, lockTime_0p0001Pcnt, lockTime_0p00001Pcnt, lockTime_0p000001Pcnt, f2

def noiseContributors(workbook,magCL,magvcoTF,magprescalerTF,magpfdcpTF,R2,magLFTFR2,R3,magLFTFR3, magXTAL):
	R2Noise = 10*np.log10(4*1.3806503e-23*300*R2)
	R2NoiseOut = []
	for i in range(len(magLFTFR2)):
		R2NoiseOut.append(R2Noise + magLFTFR2[i])
	R3Noise = 10*np.log10(4*1.3806503e-23*300*R3)
	R3NoiseOut = []
	for i in range(len(magLFTFR2)):
		R3NoiseOut.append(R3Noise + magLFTFR3[i])
	if workbook == "":#If no file is uploaded or there's an error with the file
		f, XTALNoise, PFDCPNoise, PrescalerNoise, VCONoise, SDNoise = defaultNoise()
		XTALNoiseOut = []
		for i in range(len(f)):
			XTALNoiseOut.append(XTALNoise[i] + magXTAL[i])
		PFDCPNoiseOut = []
		for i in range(len(f)):
			PFDCPNoiseOut.append(PFDCPNoise[i] + magpfdcpTF[i])
		PrescalerNoiseOut = []
		for i in range(len(f)):
			PrescalerNoiseOut.append(PrescalerNoise[i] + magprescalerTF[i])
		VCONoiseOut = []
		for i in range(len(f)):
			VCONoiseOut.append(VCONoise[i] + magvcoTF[i])
		SDNoiseOut = []
		for i in range(len(f)):
			SDNoiseOut.append(SDNoise[i] + magCL[i])
	else:#Work with the uploaded file
		sheetPFDCP = workbook.sheet_by_name("PFDCP")
		PFDCPNoise = []
		PFDCPNoiseOut = []
		for i in range(len(magCL)):
			PFDCPNoise.append(sheetPFDCP.cell(i+1,1).value)
			PFDCPNoiseOut.append(PFDCPNoise[i] + magpfdcpTF[i])
		sheetXTAL = workbook.sheet_by_name("XTAL")
		XTALNoise = []
		XTALNoiseOut = []
		for i in range(len(magCL)):
			XTALNoise.append(sheetXTAL.cell(i+1,1).value)
			XTALNoiseOut.append(XTALNoise[i] + magXTAL[i])
		sheetPrescaler = workbook.sheet_by_name("Prescaler")
		PrescalerNoise = []
		PrescalerNoiseOut = []
		for i in range(len(magCL)):
			PrescalerNoise.append(sheetPrescaler.cell(i+1,1).value)
			PrescalerNoiseOut.append(PrescalerNoise[i] + magprescalerTF[i])
		sheetVCO = workbook.sheet_by_name("VCO")
		VCONoise = []
		VCONoiseOut = []
		for i in range(len(magCL)):
			VCONoise.append(sheetVCO.cell(i+1,1).value)
			VCONoiseOut.append(VCONoise[i] + magvcoTF[i])
		sheetSD = workbook.sheet_by_name("Sigma Delta")
		SDNoise = []
		SDNoiseOut = []
		for i in range(len(magCL)):
			SDNoise.append(sheetSD.cell(i+1,1).value)
			SDNoiseOut.append(SDNoise[i] + magCL[i])
	TotalNoise = []
	TotalNoise_V2Hz = []
	for i in range(len(magCL)):
		TotalNoise.append(10*np.log10(10**(XTALNoiseOut[i]/10.0) + 10**(PFDCPNoiseOut[i]/10.0) + 10**(PrescalerNoiseOut[i]/10.0) + 10**(VCONoiseOut[i]/10.0) + 10**(R2NoiseOut[i]/10.0) + 10**(R3NoiseOut[i]/10.0) + 10**(SDNoiseOut[i]/10.0) ))
		TotalNoise_V2Hz.append(10**(TotalNoise[i]/10.0))
		#TotalNoise.append(PFDCPNoiseOut[i] + PrescalerNoiseOut[i] + VCONoiseOut[i])
	print TotalNoise_V2Hz
	return XTALNoiseOut, PFDCPNoiseOut,PrescalerNoiseOut,VCONoiseOut,R2NoiseOut,R3NoiseOut,SDNoiseOut, TotalNoise, TotalNoise_V2Hz
	

	
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
	VCONoise = [-75.0, -79.0, -83.0, -87.0, -91.0, -95.0, -99.0, -103.0, -107.0, -111.0, -115.0, -119.0, -123.0, 
	-127.0, -131.0, -135.0, -139.0, -143.0, -147.0, -151.0, -155.0, -159.0, -163.0, -167.0, -171.0, -175.0, -179.0, 
	-183.0, -187.0, -191.0, -195.0]
	SDNoise = [-200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, -200.0, 
	-200.0, -200.0, -200.0, -200.0, -192.0, -184.0, -176.0, -167.99999999999997, -160.0, -152.0, -144.0, -136.0, 
	-128.0, -120.0, -112.0, -104.0, -96.0, -88.0, -80.0]
	return f, XTALNoise, PFDCPNoise, PrescalerNoise, VCONoise, SDNoise
	
def writeResults(C1,C2,C3,R2,R3,f,magCL,magOL,phaseOL,magvcoTF,PFDCPNoiseOut,
PrescalerNoiseOut,VCONoiseOut,R2NoiseOut,R3NoiseOut,XTALNoiseOut,SDNoiseOut,
TotalNoise,t,fT,lockTime_0p001Pcnt, lockTime_0p0001Pcnt, lockTime_0p00001Pcnt, 
lockTime_0p000001Pcnt, f2):
	book = Workbook()
	parameter = easyxf('font: name Arial, bold True, height 280; alignment: horizontal center')
	parameterValue = easyxf('font: name Arial, height 280; alignment: horizontal center', num_format_str='0.000E+00')
	parameterValue2 = easyxf('font: name Arial, height 280; alignment: horizontal center', num_format_str='0.000')
	parameterValue3 = easyxf('font: name Arial, height 280; alignment: horizontal center', num_format_str='0.000000%')
	columnHeader = easyxf('font: name Arial, bold True, height 280; alignment: horizontal center')
	redResult = easyxf('font: name Arial, bold True, height 280, colour red;' 'alignment: horizontal center')
	#Write Loop Filter Components worksheet:
	sheetLoopFilter = book.add_sheet('Loop Filter Components')
	sheetLoopFilter.col(1).width = 5000
	sheetLoopFilter.write(0,0,'C1',parameter)
	sheetLoopFilter.write(0,1,C1,parameterValue)
	sheetLoopFilter.write(1,0,'C2',parameter)
	sheetLoopFilter.write(1,1,C2,parameterValue)
	sheetLoopFilter.write(2,0,'C3',parameter)
	sheetLoopFilter.write(2,1,C3,parameterValue)
	sheetLoopFilter.write(3,0,'R2',parameter)
	sheetLoopFilter.write(3,1,R2,parameterValue)
	sheetLoopFilter.write(4,0,'R3',parameter)
	sheetLoopFilter.write(4,1,R3,parameterValue)
	#Write Loop Response worksheet:
	sheetLoopResponse = book.add_sheet('Loop Response Data')
	sheetLoopResponse.col(0).width = 6000
	sheetLoopResponse.write(0,0,'Frequency (Hz)',columnHeader)
	sheetLoopResponse.col(1).width = 15000
	sheetLoopResponse.write(0,1,'Closed Loop Response Magnitude (dB)',columnHeader)
	sheetLoopResponse.col(2).width = 14000
	sheetLoopResponse.write(0,2,'Open Loop Response Magnitude (dB)',columnHeader)
	sheetLoopResponse.col(3).width = 14000
	sheetLoopResponse.write(0,3,'Open Loop Response Phase (dB)',columnHeader)
	sheetLoopResponse.col(4).width = 14000
	sheetLoopResponse.write(0,4,'VCO Transfer Function Magnitude (dB)',columnHeader)
	for i in range(len(f)):
		sheetLoopResponse.write(i+1,0,f[i],parameterValue)
		sheetLoopResponse.write(i+1,1,magCL[i],parameterValue2)
		sheetLoopResponse.write(i+1,2,magOL[i],parameterValue2)
		sheetLoopResponse.write(i+1,3,phaseOL[i],parameterValue2)
		sheetLoopResponse.write(i+1,4,magvcoTF[i],parameterValue2)
	#Write Noise Results worksheet:
	sheetPLLNoise = book.add_sheet('PLL Noise Contributors')
	sheetPLLNoise.col(0).width = 6000
	sheetPLLNoise.write(0,0,'Frequency (Hz)',columnHeader)
	sheetPLLNoise.col(1).width = 6000
	sheetPLLNoise.write(0,1,'PFDCP (dBc/Hz)',columnHeader)
	sheetPLLNoise.col(2).width = 7000
	sheetPLLNoise.write(0,2,'Prescaler (dBc/Hz)',columnHeader)
	sheetPLLNoise.col(3).width = 6000
	sheetPLLNoise.write(0,3,'VCO (dBc/Hz)',columnHeader)
	sheetPLLNoise.col(4).width = 6000
	sheetPLLNoise.write(0,4,'R2 (dBc/Hz)',columnHeader)
	sheetPLLNoise.col(5).width = 6000
	sheetPLLNoise.write(0,5,'R3 (dBc/Hz)',columnHeader)
	sheetPLLNoise.col(6).width = 6000
	sheetPLLNoise.write(0,6,'XTAL (dBc/Hz)',columnHeader)
	sheetPLLNoise.col(7).width = 8000
	sheetPLLNoise.write(0,7,'Sigma Delta (dBc/Hz)',columnHeader)
	sheetPLLNoise.col(8).width = 8000
	sheetPLLNoise.write(0,8,'Total Noise (dBc/Hz)',columnHeader)
	for i in range(len(f)):
		sheetPLLNoise.write(i+1,0,f[i],parameterValue)
		sheetPLLNoise.write(i+1,1,PFDCPNoiseOut[i],parameterValue2)
		sheetPLLNoise.write(i+1,2,PrescalerNoiseOut[i],parameterValue2)
		sheetPLLNoise.write(i+1,3,VCONoiseOut[i],parameterValue2)
		sheetPLLNoise.write(i+1,4,R2NoiseOut[i],parameterValue2)
		sheetPLLNoise.write(i+1,5,R3NoiseOut[i],parameterValue2)
		sheetPLLNoise.write(i+1,6,XTALNoiseOut[i],parameterValue2)
		sheetPLLNoise.write(i+1,7,SDNoiseOut[i],parameterValue2)
		sheetPLLNoise.write(i+1,8,TotalNoise[i],parameterValue2)
	#Write Time Response worksheet:
	sheetPLLTime = book.add_sheet('Time Response')
	sheetPLLTime.col(0).width = 5000
	sheetPLLTime.write(0,0,'Time (s)',columnHeader)
	sheetPLLTime.col(1).width = 9000
	sheetPLLTime.write(0,1,'Output Frequency (Hz)',columnHeader)
	for i in range(len(t)):
		sheetPLLTime.write(i+1,0,t[i],parameterValue)
		sheetPLLTime.write(i+1,1,fT[i],parameterValue)
	sheetLockTimes = book.add_sheet('Lock Times')
	sheetLockTimes.col(0).width = 11000
	sheetLockTimes.write(0,0,'Locks within what % error',columnHeader)
	sheetLockTimes.col(1).width = 11000
	sheetLockTimes.write(0,1,'Locks within how many Hertz',columnHeader)
	sheetLockTimes.col(2).width = 6000
	sheetLockTimes.write(0,2,'Lock Time (s)',columnHeader)
	sheetLockTimes.write(1,0,0.00001,parameterValue3)
	sheetLockTimes.write(1,1,float(scientific(0.00001*f2)),parameterValue)
	sheetLockTimes.write(1,2,lockTime_0p001Pcnt,parameterValue)
	sheetLockTimes.write(2,0,0.000001,parameterValue3)
	sheetLockTimes.write(2,1,float(scientific(0.000001*f2)),parameterValue)
	sheetLockTimes.write(2,2,lockTime_0p0001Pcnt,parameterValue)
	sheetLockTimes.write(3,0,0.0000001,parameterValue3)
	sheetLockTimes.write(3,1,float(scientific(0.0000001*f2)),parameterValue)
	sheetLockTimes.write(3,2,lockTime_0p00001Pcnt,parameterValue)
	sheetLockTimes.write(4,0,0.00000001,parameterValue3)
	sheetLockTimes.write(4,1,float(scientific(0.00000001*f2)),parameterValue)
	sheetLockTimes.write(4,2,lockTime_0p000001Pcnt,parameterValue)
	sheetphaseError = book.add_sheet('Phase Error')
	sheetphaseError.col(0).width = 6000
	sheetphaseError.write(0,0,'Frequency (Hz)',columnHeader)
	sheetphaseError.col(1).width = 8000
	sheetphaseError.write(0,1,'Total Noise (V2/Hz)',columnHeader)
	for i in range(len(f)):
		sheetphaseError.write(i+1,0,f[i],parameterValue)
		sheetphaseError.write(i+1,1,10**(TotalNoise[i]/10.0),parameterValue)
	sheetphaseError.col(3).width = 10000
	sheetphaseError.write(1,3,"Lower Integration Limit", columnHeader)
	sheetphaseError.write(2,3,"Upper Integration Limit", columnHeader)
	sheetphaseError.write(4,3,"Phase Error", redResult)
	sheetphaseError.col(4).width = 6000
	sheetphaseError.write(1,4,1.7e3,parameterValue)
	sheetphaseError.write(2,4,200e3,parameterValue)
	x="(180/PI())*SQRT(2*((VLOOKUP(E3,A2:B32,1)-VLOOKUP(E2,A2:B32,1))/6)*(VLOOKUP(E2,A2:B32,2)+VLOOKUP(E3,A2:B32,2)+4*VLOOKUP(((VLOOKUP(E2,A2:B32,1)+VLOOKUP(E3,A2:B32,1))/2.0),A2:B32,2)))"
	y="(180/PI())*SQRT(2*((E3-E2)/6)*(VLOOKUP(E2,A2:B32,2)+VLOOKUP(E3,A2:B32,2)+4*VLOOKUP(((E3+E2)/2.0),A2:B32,2)))"
	#y="4*VLOOKUP(((VLOOKUP(E2,A2:B32,1)+VLOOKUP(E3,A2:B32,1))/2.0),A2:B32,2)"
	sheetphaseError.write(4,4,Formula(y),parameterValue)
	return book

def timeResponse(A2,A1,A0,T2,Fcomp,Fout,LoopBW,KVCO,CPGain):
	f1 = 0.99*Fout
	f2 = 1.01*Fout
	N2 = float(f2/Fcomp)#Need to use N of final frequency
	K = KVCO*CPGain/N2
	denCoeff=[A2,A1,A0,K*T2,K]
	denRoots=np.roots(denCoeff)
	p=[]
	for root in denRoots:
		p.append(root)
	#print p
	B = []
	Bconst = K*(f2 - f1)/A2
	B.append(Bconst*((1/(p[0]-p[1]))*(1/(p[0]-p[2]))*(1/(p[0]-p[3]))))
	B.append(Bconst*((1/(p[1]-p[0]))*(1/(p[1]-p[2]))*(1/(p[1]-p[3]))))
	B.append(Bconst*((1/(p[2]-p[0]))*(1/(p[2]-p[1]))*(1/(p[2]-p[3]))))
	B.append(Bconst*((1/(p[3]-p[0]))*(1/(p[3]-p[1]))*(1/(p[3]-p[2]))))
	#print 'B = ', B
	# natFreq=math.sqrt(KVCO*CPGain/(N2*A0))
	# dampFactor=T2*natFreq/2
	# tol = (f2-f1)/1e5
	# lockTimeApprox = -math.log((tol/(f2-f1))*math.sqrt(1.0-dampFactor**2))/(dampFactor*natFreq)
	# print 'Lock time approx: ',lockTimeApprox
	t=np.linspace(0,8.0/LoopBW/1.0,2000)
	fT = []
	B0 = []
	B1 = []
	B2 = []
	B3 = []
	errorfT = []
	def expComplex(alpha,beta):
		#Euler's formula: exp(beta) = cos(beta) + 1j*sin(beta)
		return (math.exp(alpha)*(math.cos(beta)+1j*math.sin(beta)))
	for i in range(len(t)):
		B0.append(B[0]*expComplex((p[0]*t[i]).real, (p[0]*t[i]).imag)*((1/p[0])+T2))
		B1.append(B[1]*expComplex((p[1]*t[i]).real, (p[1]*t[i]).imag)*((1/p[1])+T2))
		B2.append(B[2]*expComplex((p[2]*t[i]).real, (p[2]*t[i]).imag)*((1/p[2])+T2))
		B3.append(B[3]*expComplex((p[3]*t[i]).real, (p[3]*t[i]).imag)*((1/p[3])+T2))
		fT.append((f2 + B0[i] + B1[i] + B2[i] + B3[i]).real)
		errorfT.append(abs(fT[i]-f2))
	Tol_0p001Pcnt = (0.001/100.00)*f2
	Tol_0p0001Pcnt = (0.0001/100.00)*f2
	Tol_0p00001Pcnt = (0.00001/100.00)*f2
	Tol_0p000001Pcnt = (0.000001/100.00)*f2
	def findError(t,errorfT,tol,index):
		#Looks in errorfT for errorfT[i]<tol.
		#Starts looking at i=index
		#As soon as it finds one it returns the index and the corresponding errorfT.
		for i in range(index,len(t)):
			if errorfT[i]<tol:
				return i, errorfT[i]
		return t, fT
	def findLockTime(t,errotfT,tol,startIndex,error):
		for i in range(startIndex,len(t)):
			if (errorfT[i] > error):#if there's an errorfT[i] that is larger than the error found:
				#It means the given error is bogus, later in time there'll be bigger errors.
				#Start looking in errorfT, starting at i+1, for an error smaller than tol
				newStartIndex,newError=findError(t,errorfT,tol,i+1)#returns a new index and corresponding error 
				#and need to look again in errorfT *in the new range* for errorfT < tol
				return findLockTime(t,errotfT,tol,newStartIndex,newError)#Recursion!
		return t[startIndex]#if there's no error in errorfT larger than the given one, return t[i], i.e. the lock time.
	lockTime_0p001Pcnt = findLockTime(t,errorfT,Tol_0p001Pcnt,0,Tol_0p001Pcnt)
	lockTime_0p0001Pcnt = findLockTime(t,errorfT,Tol_0p0001Pcnt,0,Tol_0p0001Pcnt)
	lockTime_0p00001Pcnt = findLockTime(t,errorfT,Tol_0p00001Pcnt,0,Tol_0p00001Pcnt)
	lockTime_0p000001Pcnt = findLockTime(t,errorfT,Tol_0p000001Pcnt,0,Tol_0p000001Pcnt)
	# print '0.001% Lock Time = ', lockTime_0p001Pcnt	
	# print '0.0001% Lock Time = ', lockTime_0p0001Pcnt
	# print '0.00001% Lock Time = ', lockTime_0p00001Pcnt	
	# print '0.000001% Lock Time = ', lockTime_0p000001Pcnt	
	return t, fT, lockTime_0p001Pcnt, lockTime_0p0001Pcnt, lockTime_0p00001Pcnt, lockTime_0p000001Pcnt, f2

jinja_environment = jinja2.Environment(autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

class MainHandler(webapp2.RequestHandler):
	def write_form(self,Kphi="5E-3",KVCO="30E6",P="8.0",PM="50.0",LoopBW="5.1E3",Fout="900E6",Fref="200E3",R="1.0",T31="0.6",Gamma="1.136"):
		dictStringSubst={"Kphi": Kphi, "KVCO": KVCO, "P": P, "PM": PM, "LoopBW": LoopBW, "Fout": Fout, "Fref": Fref, "R": R, "T31": T31, "Gamma": Gamma}
		#dictStringSubstError={"errorpPrice": errorpPrice,"errordPymnt": errordPymnt,"errormTerm": errormTerm, "erroriRate": erroriRate, "errorcCosts": errorcCosts, "erroriCosts": erroriCosts, "errormTerm": errormTerm}
		template = jinja_environment.get_template('form.html')
		self.response.out.write(template.render(dictStringSubst=dictStringSubst))
	def get(self):
		self.write_form()
	def post(self):
		enteredpKphi=self.request.get('Kphi').replace(',','')
		entereddKVCO=self.request.get('KVCO').replace(',','')
		enteredPM=self.request.get('PM').replace(',','')
		enteredLoopBW=self.request.get('LoopBW').replace(',','')
		enteredFout=self.request.get('Fout').replace(',','')
		enteredFref=self.request.get('Fref').replace(',','')
		enteredR=self.request.get('R').replace(',','')
		enteredP=self.request.get('P').replace(',','')
		enteredT31=self.request.get('T31').replace(',','')
		enteredGamma=self.request.get('Gamma').replace(',','')
		displayError1="ERROR"
		if not is_number(enteredpKphi):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,displayError1,'','','','','','')
			return
		elif not is_number(entereddKVCO):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'',displayError1,'','','','','')
			return
		elif not is_number(enteredPM):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'','',displayError1,'','','','')
			return
		elif not is_number(enteredLoopBW):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'','','',displayError1,'','','')
			return
		elif not is_number(enteredFout):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'','','','',displayError1,'','')
			return
		elif not is_number(enteredFref):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'','','','','',displayError1,'')
			return
		elif not is_number(enteredT31):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'','','','','','',displayError1)
			return
		elif not is_number(enteredGamma):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'','','','','','',displayError1)
			return
		elif not is_number(enteredR):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'','','','','','',displayError1)
			return
		elif not is_number(enteredP):
			self.write_form(enteredpPrice,entereddPymnt,enteredmTerm,enterediRate,enteredcCosts,enterediCosts,enteredmRent,'','','','','','',displayError1)
			return
		else:
			enteredKphi = float(enteredpKphi)
			enteredKVCO = float(entereddKVCO)
			enteredPM = float(enteredPM)
			enteredLoopBW = float(enteredLoopBW)
			enteredFout = float(enteredFout)
			enteredFref = float(enteredFref)
			enteredR = float(enteredR)
			enteredP = float(enteredP)
			enteredT31 = float(enteredT31)
			enteredGamma = float(enteredGamma)
		(C1,C2,C3,R2,R3,f,magCL,magOL,phaseOL,magvcoTF,magprescalerTF,magpfdcpTF,
		magLFTFR2,magLFTFR3, magXTAL, t, fT, lockTime_0p001Pcnt, lockTime_0p0001Pcnt, 
		lockTime_0p00001Pcnt, lockTime_0p000001Pcnt, f2) = loopFilter(enteredGamma,
		enteredLoopBW,enteredPM,enteredKphi,enteredKVCO,enteredP,enteredFout,
		enteredFref,enteredR,enteredT31)
		index=range(1,len(f))
		try:
			noiseFile = self.request.get("noiseFile")
			workbook = xlrd.open_workbook(file_contents=noiseFile)
			noiseError=""
		except:
			workbook = ""
			noiseError = "***WARNING: Empty noise file or an error occurred while reading the file. Using default noise data instead.***" 
			#template = jinja_environment.get_template('noiseFileError.html')
			#self.response.out.write(template.render())
		XTALNoiseOut, PFDCPNoiseOut,PrescalerNoiseOut,VCONoiseOut,R2NoiseOut,R3NoiseOut,SDNoiseOut,TotalNoise, TotalNoise_V2Hz = noiseContributors(workbook,magCL,magvcoTF,magprescalerTF,magpfdcpTF,(R2*1e3),magLFTFR2,(R3*1e3),magLFTFR3, magXTAL)
		if (self.request.get("excelResults") == "wantExcelResults"):
			book2 = writeResults(C1*1e-9,C2*1e-9,C3*1e-9,R2*1e3,R3*1e3,f,magCL,
			magOL,phaseOL,magvcoTF,PFDCPNoiseOut,PrescalerNoiseOut,VCONoiseOut,
			R2NoiseOut,R3NoiseOut, XTALNoiseOut, SDNoiseOut, TotalNoise, t, fT,
			lockTime_0p001Pcnt, lockTime_0p0001Pcnt, lockTime_0p00001Pcnt, 
			lockTime_0p000001Pcnt, f2)
			self.response.headers['Content-Type'] = 'application/ms-excel'
			self.response.headers['Content-Transfer-Encoding'] = 'Binary'
			self.response.headers['Content-disposition'] = 'attachment; filename="PLL3rdOrderResults.xls"'
			book2.save(self.response.out)
		else:
			dictStringSubst={"Kphi": scientific(enteredKphi), "KVCO": scientific(enteredKVCO), "P": enteredP, "PM": enteredPM, "LoopBW": scientific(enteredLoopBW), "Fout": scientific(enteredFout), "Fref": scientific(enteredFref), "R": enteredR, "T31": enteredT31, "Gamma": enteredGamma}
			template = jinja_environment.get_template('form.html')
			self.response.out.write(template.render(dictStringSubst=dictStringSubst))
			template = jinja_environment.get_template('resultsBorder.html')
			self.response.out.write(template.render())
			template = jinja_environment.get_template('loopFilterTable.html')
			self.response.out.write(template.render(C1=scientific(C1),C2=scientific(C2),C3=scientific(C3),R2=scientific(R2),R3=scientific(R3)))
			template = jinja_environment.get_template('loopResponse.html')
			self.response.out.write(template.render(f=f,magCL=magCL,magOL=magOL,phaseOL=phaseOL,magvcoTF=magvcoTF,index2=index))
			template = jinja_environment.get_template('noisePlot.html')
			self.response.out.write(template.render(f=f, XTALNoiseOut=XTALNoiseOut, PFDCPNoiseOut=PFDCPNoiseOut,PrescalerNoiseOut=PrescalerNoiseOut,VCONoiseOut=VCONoiseOut,R2NoiseOut=R2NoiseOut,R3NoiseOut=R3NoiseOut,SDNoiseOut=SDNoiseOut,TotalNoise=TotalNoise,index2=index,error=noiseError))
			template = jinja_environment.get_template('phaseError.html')
			self.response.out.write(template.render(f=f, fout=enteredFout, index2=index, TotalNoise_V2Hz=TotalNoise_V2Hz))
			indexT = range(len(t))
			template = jinja_environment.get_template('timeResponse.html')
			self.response.out.write(template.render(t=t, fT=fT, indexT=indexT))
			template = jinja_environment.get_template('loopLockTimes.html')
			self.response.out.write(template.render(lT_0p001Pcnt=scientific(lockTime_0p001Pcnt),lT_0p0001Pcnt=scientific(lockTime_0p0001Pcnt),lT_0p00001Pcnt=scientific(lockTime_0p00001Pcnt),lT_0p000001Pcnt=scientific(lockTime_0p000001Pcnt),
			lT_0p001PcntActual=scientific(0.00001*f2), lT_0p0001PcntActual=scientific(0.000001*f2), lT_0p00001PcntActual=scientific(0.0000001*f2),lT_0p000001PcntActual=scientific(0.00000001*f2)))

		
		#template = jinja_environment.get_template('loopResponse.html')
		#self.response.out.write(template.render(f=f,magCL=magCL,magOL=magOL,phaseOL=phaseOL,magvcoTF=magvcoTF,index2=index))
		

app = webapp2.WSGIApplication([('/', MainHandler)],
                              debug=True)

