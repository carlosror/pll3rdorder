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
import xlwt
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

def readNoiseSpreadsheet(workbook):
	f = np.logspace(2,8,31)#Has to match the number of items in a column of the spreadsheet
	sheetPFDCP = workbook.sheet_by_name("PFDCP")
	PFDCPNoise = []
	for i in range(len(f)):
		if is_number(sheetPFDCP.cell(i+1,1).value):
			PFDCPNoise.append(sheetPFDCP.cell(i+1,1).value)
		else:
			return 'bigFatError'#Generates and Error which will be caught by a try-except construct
	sheetXTAL = workbook.sheet_by_name("XTAL")
	XTALNoise = []
	for i in range(len(f)):
		if is_number(sheetXTAL.cell(i+1,1).value):
			XTALNoise.append(sheetXTAL.cell(i+1,1).value)
		else:
			return 'bigFatError'#Generates and Error which will be caught by a try-except construct
	sheetPrescaler = workbook.sheet_by_name("Prescaler")
	PrescalerNoise = []
	for i in range(len(f)):
		if is_number(sheetPrescaler.cell(i+1,1).value):
			PrescalerNoise.append(sheetPrescaler.cell(i+1,1).value)
		else:
			return 'bigFatError'#Generates and Error which will be caught by a try-except construct
	sheetVCO = workbook.sheet_by_name("VCO")
	VCONoise = []
	for i in range(len(f)):
		if is_number(sheetVCO.cell(i+1,1).value):
			VCONoise.append(sheetVCO.cell(i+1,1).value)
		else:
			return 'bigFatError'#Generates and Error which will be caught by a try-except construct
	sheetSD = workbook.sheet_by_name("Sigma Delta")
	SDNoise = []
	for i in range(len(f)):
		if is_number(sheetSD.cell(i+1,1).value):
			SDNoise.append(sheetSD.cell(i+1,1).value)
		else:
			return 'bigFatError'#Generates and Error which will be caught by a try-except construct
	return PFDCPNoise, XTALNoise, PrescalerNoise, VCONoise, SDNoise
	

def noiseContributors(workbook,magCL,magvcoTF,magprescalerTF,magpfdcpTF,R2,magLFTFR2,R3,magLFTFR3, magXTAL,
PFDCPNoise, XTALNoise, PrescalerNoise, VCONoise, SDNoise):
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
		PFDCPNoiseOut = []
		for i in range(len(magCL)):
			PFDCPNoiseOut.append(PFDCPNoise[i] + magpfdcpTF[i])
		XTALNoiseOut = []
		for i in range(len(magCL)):
			XTALNoiseOut.append(XTALNoise[i] + magXTAL[i])
		PrescalerNoiseOut = []
		for i in range(len(magCL)):
			PrescalerNoiseOut.append(PrescalerNoise[i] + magprescalerTF[i])
		VCONoiseOut = []
		for i in range(len(magCL)):
			VCONoiseOut.append(VCONoise[i] + magvcoTF[i])
		SDNoiseOut = []
		for i in range(len(magCL)):
			SDNoiseOut.append(SDNoise[i] + magCL[i])
	TotalNoise = []
	TotalNoise_V2Hz = []
	for i in range(len(magCL)):
		TotalNoise.append(10*np.log10(10**(XTALNoiseOut[i]/10.0) + 10**(PFDCPNoiseOut[i]/10.0) + 10**(PrescalerNoiseOut[i]/10.0) + 10**(VCONoiseOut[i]/10.0) + 10**(R2NoiseOut[i]/10.0) + 10**(R3NoiseOut[i]/10.0) + 10**(SDNoiseOut[i]/10.0) ))
		TotalNoise_V2Hz.append(10**(TotalNoise[i]/10.0))
		#TotalNoise.append(PFDCPNoiseOut[i] + PrescalerNoiseOut[i] + VCONoiseOut[i])
	return XTALNoiseOut, PFDCPNoiseOut,PrescalerNoiseOut,VCONoiseOut,R2NoiseOut,R3NoiseOut,SDNoiseOut, TotalNoise, TotalNoise_V2Hz
	
def interpolate(t,y):
	ydB = []#Convert y to dB
	for i in range(len(y)):
		ydB.append(10*np.log10(y[i]))
	a=[]
	b=[]
	s=[]
	for i in range(len(t)-1):
		a.append((ydB[i+1]-ydB[i])/(t[i+1]-t[i]))
		b.append(ydB[i] - (ydB[i+1]-ydB[i])*t[i]/(t[i+1]-t[i]))
	x1=np.logspace(2,8,601)
	s=[]
	for x in x1:
		if x>=100.0 and x<1.585e2:
			s.append(a[0]*x + b[0])
		elif x>=1.585e2 and x<2.512e2:
			s.append(a[1]*x + b[1])
		elif x>=2.512e2 and x<3.981e2:
			s.append(a[2]*x + b[2])
		elif x>=3.981e2 and x<6.310e2:
			s.append(a[3]*x + b[3])
		elif x>=6.310e2 and x<1e3:
			s.append(a[4]*x + b[4])
		elif x>=1e3 and x<1.585e3:
			s.append(a[5]*x + b[5])
		elif x>=1.585e3 and x<2.512e3:
			s.append(a[6]*x + b[6])
		elif x>=2.512e3 and x<3.981e3:
			s.append(a[7]*x + b[7])
		elif x>=3.981e3 and x<6.310e3:
			s.append(a[8]*x + b[8])
		elif x>=6.310e3 and x<1e4:
			s.append(a[9]*x + b[9])
		elif x>=1e4 and x<1.585e4:
			s.append(a[10]*x + b[10])
		elif x>=1.585e4 and x<2.512e4:
			s.append(a[11]*x + b[11])
		elif x>=2.512e4 and x<3.981e4:
			s.append(a[12]*x + b[12])
		elif x>=3.981e4 and x<6.310e4:
			s.append(a[13]*x + b[13])
		elif x>=6.310e4 and x<1e5:
			s.append(a[14]*x + b[14])
		elif x>=1e5 and x<1.585e5:
			s.append(a[15]*x + b[15])
		elif x>=1.585e5 and x<2.512e5:
			s.append(a[16]*x + b[16])
		elif x>=2.512e5 and x<3.981e5:
			s.append(a[17]*x + b[17])
		elif x>=3.981e5 and x<6.310e5:
			s.append(a[18]*x + b[18])
		elif x>=6.310e5 and x<1e6:
			s.append(a[19]*x + b[19])
		elif x>=1e6 and x<1.585e6:
			s.append(a[20]*x + b[20])
		elif x>=1.585e6 and x<2.512e6:
			s.append(a[21]*x + b[21])
		elif x>=2.512e6 and x<3.981e6:
			s.append(a[22]*x + b[22])
		elif x>=3.981e6 and x<6.310e6:
			s.append(a[23]*x + b[23])
		elif x>=6.310e6 and x<1e7:
			s.append(a[24]*x + b[24])
		elif x>=1e7 and x<1.585e7:
			s.append(a[25]*x + b[25])
		elif x>=1.585e7 and x<2.512e7:
			s.append(a[26]*x + b[26])
		elif x>=2.512e7 and x<3.981e7:
			s.append(a[27]*x + b[27])
		elif x>=3.981e7 and x<6.310e7:
			s.append(a[28]*x + b[28])
		elif x>=6.310e7 and x<=1.01e8:
			s.append(a[29]*x + b[29])
	s2 = []
	for i in range(len(x1)):
		s2.append(10**(s[i]/10.0))
	return x1,s2
	
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
	
def writeResults(C1,C2,C3,R2,R3,f,magCL,magOL,phaseOL,magvcoTF,PFDCPNoiseOut,
PrescalerNoiseOut,VCONoiseOut,R2NoiseOut,R3NoiseOut,XTALNoiseOut,SDNoiseOut,
TotalNoise,t,fT,lockTime_0p001Pcnt, lockTime_0p0001Pcnt, lockTime_0p00001Pcnt, 
lockTime_0p000001Pcnt, f2, fInterpol, TotalNoiseV2HzInterpol, enteredKphi, 
enteredKVCO, enteredPM, enteredLoopBW, enteredFout, enteredFref, enteredR, 
enteredP, enteredT31, enteredGamma, noiseWorkbook,PFDCPNoise, XTALNoise, 
PrescalerNoise, VCONoise, SDNoise):
	book = Workbook()
	whiteCell = easyxf("pattern: fore_colour white, pattern solid;")
	parameter = easyxf('font: name Arial, bold True, height 280; alignment: horizontal center')
	parameterValue = easyxf('font: name Arial, height 280;' 'borders: left thick, right thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour white;', num_format_str='0.000E+00')
	parameterValue2 = easyxf('font: name Arial, height 280;' 'borders: left thick, right thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour white;', num_format_str='0.000')
	parameterValueRed = easyxf('font: name Arial, bold True, height 280, colour red;' 'alignment: horizontal center', num_format_str='0.000E+00')
	parameterValue2Red = easyxf('font: name Arial, bold True, height 280, colour red;' 'alignment: horizontal center', num_format_str='0.000')
	parameterValue3 = easyxf('font: name Arial, height 280;' 'borders: left thick, right thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour white;', num_format_str='0.000000%')
	columnHeader = easyxf('font: name Arial, bold True, height 280; alignment: horizontal center')
	notes = easyxf('font: name Arial, bold True, height 280; alignment: horizontal left;' "pattern: fore_colour white, pattern solid;")
	notesRed = easyxf('font: name Arial, bold True, height 280, colour red; alignment: horizontal left;' "pattern: fore_colour white, pattern solid;")
	link = easyxf('font: name Arial, bold True, italic True, height 240, underline single, colour red; alignment: horizontal left;' "pattern: fore_colour white, pattern solid;")
	linkContact = easyxf('font: name Arial, bold True, italic True, height 240, underline single, colour black; alignment: horizontal left;' "pattern: fore_colour white, pattern solid;")
	columnHeaderBorderL = easyxf('font: name Arial, bold True, height 280;' 'borders: left thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour white;')
	columnHeaderBorderLRed = easyxf('font: name Arial, bold True, height 280, colour red;' 'borders: left thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour gray25;')
	columnHeaderBorderBLRed = easyxf('font: name Arial, bold True, height 280, colour red;' 'borders: left thick, bottom thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour gray25;')
	columnHeaderBorderTL = easyxf('font: name Arial, bold True, height 280;' 'borders: left thick, top thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour white;')
	columnHeaderBorderBL = easyxf('font: name Arial, bold True, height 280;' 'borders: left thick, bottom thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour white;')
	columnHeaderBorderTLBR = easyxf('font: name Arial, bold True, height 280;' 'borders: left thick, top thick, bottom thick, right thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour gray25;')
	columnHeaderBorderTLBRAlignleft = easyxf('font: name Arial, bold True, height 280;' 'borders: left thick, top thick, bottom thick, right thick;' 'alignment: horizontal left;' 'pattern: pattern solid, fore_colour gray25;')
	parameterValue2BorderBR = easyxf('font: name Arial, height 280;' 'borders: right thick, bottom thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour gray25;', num_format_str='0.000')
	parameterValue2BorderR = easyxf('font: name Arial, height 280;' 'borders: right thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour gray25;', num_format_str='0.000')
	parameterValueBorderR = easyxf('font: name Arial, height 280;' 'borders: right thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour gray25;', num_format_str='0.000E+00')
	parameterValueBorderBR = easyxf('font: name Arial, height 280;' 'borders: bottom thick, right thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour gray25;', num_format_str='0.000E+00')
	parameterValueBorderBRWhite = easyxf('font: name Arial, height 280;' 'borders: bottom thick, right thick, left thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour white;', num_format_str='0.000E+00')
	parameterValueBorderTR = easyxf('font: name Arial, height 280;' 'borders: top thick, right thick;' 'alignment: horizontal center;' 'pattern: pattern solid, fore_colour gray25;', num_format_str='0.000E+00')
	redResult = easyxf('font: name Arial, bold True, height 280, colour red;' 'alignment: horizontal center')
	#Write the Loop Parameters worksheet
	sheetLoopParam = book.add_sheet('Loop Parameters')
	for i in range(100):
		sheetLoopParam.row(i).set_style(whiteCell)#Make everything white first
	sheetLoopParam.col(0).width = 8000
	sheetLoopParam.col(1).width = 5000
	sheetLoopParam.insert_bitmap(os.path.abspath("PLL_diagram_Excel.bmp"), 0, 0)
	sheetLoopParam.write(20,0,'Kphi',columnHeaderBorderTL)
	sheetLoopParam.write(20,1,enteredKphi,parameterValueBorderTR)
	sheetLoopParam.write(21,0,'KVCO',columnHeaderBorderL)
	sheetLoopParam.write(21,1,enteredKVCO,parameterValueBorderR)
	sheetLoopParam.write(22,0,'Phase Margin',columnHeaderBorderL)
	sheetLoopParam.write(22,1,enteredPM,parameterValue2BorderR)
	sheetLoopParam.write(23,0,'Loop Bandwidth',columnHeaderBorderL)
	sheetLoopParam.write(23,1,enteredLoopBW,parameterValueBorderR)
	sheetLoopParam.write(24,0,'Fout',columnHeaderBorderL)
	sheetLoopParam.write(24,1,enteredFout,parameterValueBorderR)
	sheetLoopParam.write(25,0,'Fref',columnHeaderBorderL)
	sheetLoopParam.write(25,1,enteredFref,parameterValueBorderR)
	sheetLoopParam.write(26,0,'R',columnHeaderBorderL)
	sheetLoopParam.write(26,1,enteredR,parameterValue2BorderR)
	sheetLoopParam.write(27,0,'P',columnHeaderBorderL)
	sheetLoopParam.write(27,1,enteredP,parameterValue2BorderR)
	sheetLoopParam.write(28,0,'T31',columnHeaderBorderL)
	sheetLoopParam.write(28,1,enteredT31,parameterValue2BorderR)
	sheetLoopParam.write(29,0,'Gamma',columnHeaderBorderBL)
	sheetLoopParam.write(29,1,enteredGamma,parameterValue2BorderBR)
	sheetLoopParam.write(32,0," References:",notes)
	sheetLoopParam.write(33,0, Formula('HYPERLINK("http://www.ti.com/tool/pll_book";" PLL Performance Simulation and Design Handbook - 4th Edition Dean Banerjee. 2006.")'),link)
	sheetLoopParam.write(35,0, Formula('HYPERLINK("mailto:carlosgg123@gmail.com";" Contact")'),linkContact)
	#Write the Noise Sources worksheet
	if noiseWorkbook == "":
		sheetLoopParam.write(37,0,"***WARNING: Empty noise file or an error occurred while reading the file. Using default noise data instead.***",notesRed)
		f, XTALNoise, PFDCPNoise, PrescalerNoise, VCONoise, SDNoise = defaultNoise()
	sheetNoiseSources = book.add_sheet('Noise Sources')
	for i in range(100):
		sheetNoiseSources.row(i).set_style(whiteCell)#Make everything white first
	sheetNoiseSources.col(0).width = 6000
	sheetNoiseSources.col(1).width = 8000
	sheetNoiseSources.col(2).width = 8000
	sheetNoiseSources.col(3).width = 10000
	sheetNoiseSources.col(4).width = 8000
	sheetNoiseSources.col(5).width = 10000
	sheetNoiseSources.write(0,0,'Frequency (Hz)',columnHeaderBorderTLBR)
	sheetNoiseSources.write(0,1,'XTAL Noise (dBc/Hz)',columnHeaderBorderTLBR)
	sheetNoiseSources.write(0,2,'PFDCP Noise (dBc/Hz)',columnHeaderBorderTLBR)
	sheetNoiseSources.write(0,3,'Prescaler Noise (dBc/Hz)',columnHeaderBorderTLBR)
	sheetNoiseSources.write(0,4,'VCO Noise (dBc/Hz)',columnHeaderBorderTLBR)
	sheetNoiseSources.write(0,5,'Sigma Delta Noise (dBc/Hz)',columnHeaderBorderTLBR)
	for i in range(len(f)):
		sheetNoiseSources.write(i+1,0,f[i],parameterValue)
		sheetNoiseSources.write(i+1,1,XTALNoise[i],parameterValue2)
		sheetNoiseSources.write(i+1,2,PFDCPNoise[i],parameterValue2)
		sheetNoiseSources.write(i+1,3,PrescalerNoise[i],parameterValue2)
		sheetNoiseSources.write(i+1,4,VCONoise[i],parameterValue2)
		sheetNoiseSources.write(i+1,5,SDNoise[i],parameterValue2)
	#Write Loop Filter Components worksheet:
	sheetLoopFilter = book.add_sheet('Loop Filter Components')
	for i in range(100):
		sheetLoopFilter.row(i).set_style(whiteCell)#Make everything white first
	sheetLoopFilter.col(0).width = 4000
	sheetLoopFilter.col(1).width = 5000
	sheetLoopFilter.write(0,0,' Loop Filter Components',columnHeaderBorderTLBRAlignleft)
	sheetLoopFilter.write(0,1,None,columnHeaderBorderTLBRAlignleft)
	sheetLoopFilter.write(1,0,'C1',columnHeaderBorderTL)
	sheetLoopFilter.write(1,1,C1,parameterValue)
	sheetLoopFilter.write(2,0,'C2',columnHeaderBorderL)
	sheetLoopFilter.write(2,1,C2,parameterValue)
	sheetLoopFilter.write(3,0,'C3',columnHeaderBorderL)
	sheetLoopFilter.write(3,1,C3,parameterValue)
	sheetLoopFilter.write(4,0,'R2',columnHeaderBorderL)
	sheetLoopFilter.write(4,1,R2,parameterValue)
	sheetLoopFilter.write(5,0,'R3',columnHeaderBorderBL)
	sheetLoopFilter.write(5,1,R3,parameterValueBorderBRWhite)
	#Write Loop Response worksheet:
	sheetLoopResponse = book.add_sheet('Loop Response Data')
	for i in range(100):
		sheetLoopResponse.row(i).set_style(whiteCell)#Make everything white first
	sheetLoopResponse.col(0).width = 6000
	sheetLoopResponse.write(0,0,'Frequency (Hz)',columnHeaderBorderTLBR)
	sheetLoopResponse.col(1).width = 15000
	sheetLoopResponse.write(0,1,'Closed Loop Response Magnitude (dB)',columnHeaderBorderTLBR)
	sheetLoopResponse.col(2).width = 14000
	sheetLoopResponse.write(0,2,'Open Loop Response Magnitude (dB)',columnHeaderBorderTLBR)
	sheetLoopResponse.col(3).width = 14000
	sheetLoopResponse.write(0,3,'Open Loop Response Phase (dB)',columnHeaderBorderTLBR)
	sheetLoopResponse.col(4).width = 14000
	sheetLoopResponse.write(0,4,'VCO Transfer Function Magnitude (dB)',columnHeaderBorderTLBR)
	for i in range(len(f)):
		sheetLoopResponse.write(i+1,0,f[i],parameterValue)
		sheetLoopResponse.write(i+1,1,magCL[i],parameterValue2)
		sheetLoopResponse.write(i+1,2,magOL[i],parameterValue2)
		sheetLoopResponse.write(i+1,3,phaseOL[i],parameterValue2)
		sheetLoopResponse.write(i+1,4,magvcoTF[i],parameterValue2)
	#Write Noise Results worksheet:
	sheetPLLNoise = book.add_sheet('Output Noise Contributors')
	for i in range(100):
		sheetPLLNoise.row(i).set_style(whiteCell)#Make everything white first
	sheetPLLNoise.col(0).width = 6000
	sheetPLLNoise.write(0,0,'Frequency (Hz)',columnHeaderBorderTLBR)
	sheetPLLNoise.col(1).width = 6000
	sheetPLLNoise.write(0,1,'PFDCP (dBc/Hz)',columnHeaderBorderTLBR)
	sheetPLLNoise.col(2).width = 7000
	sheetPLLNoise.write(0,2,'Prescaler (dBc/Hz)',columnHeaderBorderTLBR)
	sheetPLLNoise.col(3).width = 6000
	sheetPLLNoise.write(0,3,'VCO (dBc/Hz)',columnHeaderBorderTLBR)
	sheetPLLNoise.col(4).width = 6000
	sheetPLLNoise.write(0,4,'R2 (dBc/Hz)',columnHeaderBorderTLBR)
	sheetPLLNoise.col(5).width = 6000
	sheetPLLNoise.write(0,5,'R3 (dBc/Hz)',columnHeaderBorderTLBR)
	sheetPLLNoise.col(6).width = 6000
	sheetPLLNoise.write(0,6,'XTAL (dBc/Hz)',columnHeaderBorderTLBR)
	sheetPLLNoise.col(7).width = 8000
	sheetPLLNoise.write(0,7,'Sigma Delta (dBc/Hz)',columnHeaderBorderTLBR)
	sheetPLLNoise.col(8).width = 8000
	sheetPLLNoise.write(0,8,'Total Noise (dBc/Hz)',columnHeaderBorderTLBR)
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
	for i in range(2050):
		sheetPLLTime.row(i).set_style(whiteCell)#Make everything white first
	sheetPLLTime.col(0).width = 5000
	sheetPLLTime.write(0,0,'Time (s)',columnHeaderBorderTLBR)
	sheetPLLTime.col(1).width = 9000
	sheetPLLTime.write(0,1,'Output Frequency (Hz)',columnHeaderBorderTLBR)
	for i in range(len(t)):
		sheetPLLTime.write(i+1,0,t[i],parameterValue)
		sheetPLLTime.write(i+1,1,fT[i],parameterValue)
	#Write lock times
	sheetLockTimes = book.add_sheet('Lock Times')
	for i in range(100):
		sheetLockTimes.row(i).set_style(whiteCell)#Make everything white first
	sheetLockTimes.col(0).width = 11000
	sheetLockTimes.write(0,0,'Locks within what % error',columnHeaderBorderTLBR)
	sheetLockTimes.col(1).width = 11000
	sheetLockTimes.write(0,1,'Locks within how many Hertz',columnHeaderBorderTLBR)
	sheetLockTimes.col(2).width = 6000
	sheetLockTimes.write(0,2,'Lock Time (s)',columnHeaderBorderTLBR)
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
	#Phase Error and Jitter worksheets
	sheetphaseError = book.add_sheet('Phase Error')
	for i in range(650):
		sheetphaseError.row(i).set_style(whiteCell)#Make everything white first
	sheetphaseError.col(0).width = 6000
	sheetphaseError.write(0,0,'Frequency (Hz)',columnHeaderBorderTLBR)
	sheetphaseError.col(1).width = 8000
	sheetphaseError.write(0,1,'Total Noise (V2/Hz)',columnHeaderBorderTLBR)
	sheetphaseError.col(2).width = 12500
	sheetphaseError.write(0,2,'Frequency Error Integrand (V2*Hz)',columnHeaderBorderTLBR)
	for i in range(len(fInterpol)):
		sheetphaseError.write(i+1,0,fInterpol[i],parameterValue)
		sheetphaseError.write(i+1,1,TotalNoiseV2HzInterpol[i],parameterValue)
		sheetphaseError.write(i+1,2,fInterpol[i]*fInterpol[i]*TotalNoiseV2HzInterpol[i],parameterValue)
	sheetphaseError.col(4).width = 12000
	sheetphaseError.write(1,4,"Lower Integration Limit (Hz)", columnHeaderBorderTL)
	sheetphaseError.write(2,4,"Upper Integration Limit (Hz)", columnHeaderBorderBL)
	sheetphaseError.write(3,4,"RMS Phase Error (degrees)", columnHeaderBorderL)
	sheetphaseError.write(4,4,"Jitter (s)", columnHeaderBorderL)
	sheetphaseError.write(5,4,"RMS Frequency Error (Hz)", columnHeaderBorderBL)
	sheetphaseError.col(5).width = 6000
	sheetphaseError.write(1,5,1.7e3,parameterValueBorderTR)
	sheetphaseError.write(2,5,200e3,parameterValueBorderBR)
	sheetphaseError.write(7,4,"Enter lower and upper integration limits to calculate RMS Phase Error",notes)
	sheetphaseError.write(8,4,"Required: (Upper Int. Limit) >= 20*(Lower Int. Limit)",notes)
	sheetphaseError.write(9,4,"Calculations made using interpolated data",notes)
	#x="(180/PI())*SQRT(2*((VLOOKUP(E3,A2:B32,1)-VLOOKUP(E2,A2:B32,1))/6)*(VLOOKUP(E2,A2:B32,2)+VLOOKUP(E3,A2:B32,2)+4*VLOOKUP(((VLOOKUP(E2,A2:B32,1)+VLOOKUP(E3,A2:B32,1))/2.0),A2:B32,2)))"
	freqError="""SQRT(
	2*((F3-F3/1.5)/6)*(VLOOKUP(F3,A2:C602,3) + VLOOKUP(F3/1.5,A2:C602,3) + 4*VLOOKUP((F3 + F3/1.5)/2,A2:C602,3))
	 + 2*((F3/1.5-F3/2.25)/6)*(VLOOKUP(F3/1.5,A2:C602,3) + VLOOKUP(F3/2.25,A2:C602,3) + 4*VLOOKUP((F3/1.5 + F3/2.25)/2,A2:C602,3))
	 + 2*((F3/2.25-F3/3.375)/6)*(VLOOKUP(F3/2.25,A2:C602,3) + VLOOKUP(F3/3.375,A2:C602,3) + 4*VLOOKUP((F3/2.25 + F3/3.375)/2,A2:C602,3))
	 + 2*((F3/3.375-F3/5.0625)/6)*(VLOOKUP(F3/3.375,A2:C602,3) + VLOOKUP(F3/5.0625,A2:C602,3) + 4*VLOOKUP((F3/3.375 + F3/5.0625)/2,A2:C602,3))
	 + 2*((F3/5.0625-F3/7.594)/6)*(VLOOKUP(F3/5.0625,A2:C602,3) + VLOOKUP(F3/7.594,A2:C602,3) + 4*VLOOKUP((F3/5.0625 + F3/7.594)/2,A2:C602,3))
	 + 2*((F3/7.594-F3/11.39)/6)*(VLOOKUP(F3/7.594,A2:C602,3) + VLOOKUP(F3/11.39,A2:C602,3) + 4*VLOOKUP((F3/7.594 + F3/11.39)/2,A2:C602,3))
	 + 2*((F3/11.39-F3/17.086)/6)*(VLOOKUP(F3/11.39,A2:C602,3) + VLOOKUP(F3/17.086,A2:C602,3) + 4*VLOOKUP((F3/11.39 + F3/17.086)/2,A2:C602,3))
	 + 2*((F3/17.086-F2)/6)*(VLOOKUP(F3/17.086,A2:C602,3) + VLOOKUP(F2,A2:C602,3) + 4*VLOOKUP((F3/17.086 + F2)/2,A2:C602,3))
	 )"""#Take the Simpson integral over several intervals.
	phaseError="""(180/PI())*SQRT(
	2*((F2*1.5-F2)/6)*(VLOOKUP(F2*1.5,A2:C602,2) + VLOOKUP(F2,A2:C602,2) + 4*VLOOKUP((F2*1.5 + F2)/2,A2:C602,2))
	+ 2*((F2*2.25-F2*1.5)/6)*(VLOOKUP(F2*2.25,A2:C602,2) + VLOOKUP(F2*1.5,A2:C602,2) + 4*VLOOKUP((F2*2.25 + F2*1.5)/2,A2:C602,2))
	+ 2*((F2*3.375-F2*2.25)/6)*(VLOOKUP(F2*3.375,A2:C602,2) + VLOOKUP(F2*2.25,A2:C602,2) + 4*VLOOKUP((F2*3.375 + F2*2.25)/2,A2:C602,2))
	+ 2*((F2*5.0625-F2*3.375)/6)*(VLOOKUP(F2*5.0625,A2:C602,2) + VLOOKUP(F2*3.375,A2:C602,2) + 4*VLOOKUP((F2*5.0625 + F2*3.375)/2,A2:C602,2))
	+ 2*((F2*7.594-F2*5.0625)/6)*(VLOOKUP(F2*7.594,A2:C602,2) + VLOOKUP(F2*5.0625,A2:C602,2) + 4*VLOOKUP((F2*7.594 + F2*5.0625)/2,A2:C602,2))
	+ 2*((F2*11.39-F2*7.594)/6)*(VLOOKUP(F2*11.39,A2:C602,2) + VLOOKUP(F2*7.594,A2:C602,2) + 4*VLOOKUP((F2*11.39 + F2*7.594)/2,A2:C602,2))
	+ 2*((F2*17.086-F2*11.39)/6)*(VLOOKUP(F2*17.086,A2:C602,2) + VLOOKUP(F2*11.39,A2:C602,2) + 4*VLOOKUP((F2*17.086 + F2*11.39)/2,A2:C602,2))
	+ 2*((F3-F2*17.086)/6)*(VLOOKUP(F3,A2:C602,2) + VLOOKUP(F2*17.086,A2:C602,2) + 4*VLOOKUP((F3 + F2*17.086)/2,A2:C602,2))
	)"""#Take the Simpson integral over several intervals.
	jitter="F4/360.0/'Loop Parameters'!B25"
	y="(180/PI())*SQRT(2*((E3-E2)/6)*(VLOOKUP(E2,A2:B32,2)+VLOOKUP(E3,A2:B32,2)+4*VLOOKUP(((E3+E2)/2.0),A2:B32,2)))"
	sheetphaseError.write(3,5,Formula(phaseError),parameterValue2BorderR)
	sheetphaseError.write(4,5,Formula(jitter),parameterValueBorderR)
	sheetphaseError.write(5,5,Formula(freqError),parameterValue2BorderBR)
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
	return t, fT, lockTime_0p001Pcnt, lockTime_0p0001Pcnt, lockTime_0p00001Pcnt, lockTime_0p000001Pcnt, f2

jinja_environment = jinja2.Environment(autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

class MainHandler(webapp2.RequestHandler):
	def write_form(self,Kphi="5E-3",KVCO="30E6",P="8.0",PM="50.0",LoopBW="5.1E3",Fout="900E6",Fref="200E3",R="1.0",T31="0.6",Gamma="1.136",error=""):
		dictStringSubst={"Kphi": Kphi, "KVCO": KVCO, "P": P, "PM": PM, "LoopBW": LoopBW, "Fout": Fout, "Fref": Fref, "R": R, "T31": T31, "Gamma": Gamma, "error": error}
		# self.response.out.write('Hello world! <img src="favicon.ico">')
		template = jinja_environment.get_template('formzw.html')
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
		error="***INPUT ERROR: Please double-check your inputs.***"
		try:
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
		except:
			self.write_form(enteredpKphi,entereddKVCO,enteredP,enteredPM,enteredLoopBW,enteredFout,enteredFref,enteredR,enteredT31,enteredGamma,error)
			return
		(C1,C2,C3,R2,R3,f,magCL,magOL,phaseOL,magvcoTF,magprescalerTF,magpfdcpTF,
		magLFTFR2,magLFTFR3, magXTAL, t, fT, lockTime_0p001Pcnt, lockTime_0p0001Pcnt, 
		lockTime_0p00001Pcnt, lockTime_0p000001Pcnt, f2) = loopFilter(enteredGamma,
		enteredLoopBW,enteredPM,enteredKphi,enteredKVCO,enteredP,enteredFout,
		enteredFref,enteredR,enteredT31)
		index=range(1,len(f))
		try:
			noiseFile = self.request.get("noiseFile")
			workbook = xlrd.open_workbook(file_contents=noiseFile)
			PFDCPNoise, XTALNoise, PrescalerNoise, VCONoise, SDNoise = readNoiseSpreadsheet(workbook)
			noiseError=""
		except:
			workbook = ""
			PFDCPNoise = ""
			XTALNoise = ""
			PrescalerNoise = ""
			VCONoise = ""
			SDNoise = ""
			noiseError = "***WARNING: Empty noise file or an error occurred while reading it. Using default noise data instead.***" 
		XTALNoiseOut, PFDCPNoiseOut,PrescalerNoiseOut,VCONoiseOut,R2NoiseOut,R3NoiseOut,SDNoiseOut,TotalNoise, TotalNoise_V2Hz = noiseContributors(workbook,magCL,magvcoTF,magprescalerTF,magpfdcpTF,(R2*1e3),magLFTFR2,(R3*1e3),magLFTFR3, magXTAL,PFDCPNoise, XTALNoise, PrescalerNoise, VCONoise, SDNoise)
		fInterpol, TotalNoiseV2HzInterpol = interpolate(f, TotalNoise_V2Hz)
		if (self.request.get("excelResults") == "wantExcelResults"):
			book2 = writeResults(C1*1e-9,C2*1e-9,C3*1e-9,R2*1e3,R3*1e3,f,magCL,
			magOL,phaseOL,magvcoTF,PFDCPNoiseOut,PrescalerNoiseOut,VCONoiseOut,
			R2NoiseOut,R3NoiseOut, XTALNoiseOut, SDNoiseOut, TotalNoise, t, fT,
			lockTime_0p001Pcnt, lockTime_0p0001Pcnt, lockTime_0p00001Pcnt, 
			lockTime_0p000001Pcnt, f2, fInterpol, TotalNoiseV2HzInterpol,
			enteredKphi, enteredKVCO, enteredPM, enteredLoopBW, enteredFout,
			enteredFref, enteredR, enteredP, enteredT31, enteredGamma, workbook,
			PFDCPNoise, XTALNoise, PrescalerNoise, VCONoise, SDNoise)
			self.response.headers['Content-Type'] = 'application/ms-excel'
			self.response.headers['Content-Transfer-Encoding'] = 'Binary'
			self.response.headers['Content-disposition'] = 'attachment; filename="PLL3rdOrderReport.xls"'
			book2.save(self.response.out)
		else:
			dictStringSubst={"Kphi": scientific(enteredKphi), "KVCO": scientific(enteredKVCO), "P": enteredP, "PM": enteredPM, "LoopBW": scientific(enteredLoopBW), "Fout": scientific(enteredFout), "Fref": scientific(enteredFref), "R": enteredR, "T31": enteredT31, "Gamma": enteredGamma}
			template = jinja_environment.get_template('formzw.html')
			self.response.out.write(template.render(dictStringSubst=dictStringSubst))
			template = jinja_environment.get_template('resultsBorderzw.html')
			self.response.out.write(template.render())
			template = jinja_environment.get_template('loopFilterTablezw.html')
			self.response.out.write(template.render(C1=scientific(C1),C2=scientific(C2),C3=scientific(C3),R2=scientific(R2),R3=scientific(R3)))
			template = jinja_environment.get_template('loopResponsezw.html')
			self.response.out.write(template.render(f=f,magCL=magCL,magOL=magOL,phaseOL=phaseOL,magvcoTF=magvcoTF,index2=index))
			template = jinja_environment.get_template('noisePlotzw.html')
			indexInterpol=range(1,len(fInterpol))
			self.response.out.write(template.render(f=f, fInterpol=fInterpol, index3=indexInterpol, fout=enteredFout, TotalNoise_V2Hz = TotalNoiseV2HzInterpol, XTALNoiseOut=XTALNoiseOut, PFDCPNoiseOut=PFDCPNoiseOut,PrescalerNoiseOut=PrescalerNoiseOut,VCONoiseOut=VCONoiseOut,R2NoiseOut=R2NoiseOut,R3NoiseOut=R3NoiseOut,SDNoiseOut=SDNoiseOut,TotalNoise=TotalNoise,index2=index,error=noiseError))
			#template = jinja_environment.get_template('phaseError.html')
			#indexInterpol=range(1,len(fInterpol))
			#self.response.out.write(template.render(f=fInterpol, fout=enteredFout, index2=indexInterpol, TotalNoise_V2Hz = TotalNoiseV2HzInterpol))
			indexT = range(len(t))
			template = jinja_environment.get_template('timeResponsezw.html')
			self.response.out.write(template.render(t=t, fT=fT, indexT=indexT, lT_0p001Pcnt=scientific(lockTime_0p001Pcnt),lT_0p0001Pcnt=scientific(lockTime_0p0001Pcnt),lT_0p00001Pcnt=scientific(lockTime_0p00001Pcnt),lT_0p000001Pcnt=scientific(lockTime_0p000001Pcnt),
			lT_0p001PcntActual=scientific(0.00001*f2), lT_0p0001PcntActual=scientific(0.000001*f2), lT_0p00001PcntActual=scientific(0.0000001*f2),lT_0p000001PcntActual=scientific(0.00000001*f2)))
			#template = jinja_environment.get_template('loopLockTimes.html')
			#self.response.out.write(template.render(lT_0p001Pcnt=scientific(lockTime_0p001Pcnt),lT_0p0001Pcnt=scientific(lockTime_0p0001Pcnt),lT_0p00001Pcnt=scientific(lockTime_0p00001Pcnt),lT_0p000001Pcnt=scientific(lockTime_0p000001Pcnt),
			#lT_0p001PcntActual=scientific(0.00001*f2), lT_0p0001PcntActual=scientific(0.000001*f2), lT_0p00001PcntActual=scientific(0.0000001*f2),lT_0p000001PcntActual=scientific(0.00000001*f2)))

		

app = webapp2.WSGIApplication([('/zw', MainHandler)],
                              debug=True)

