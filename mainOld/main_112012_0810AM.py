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
from xlwt import Workbook

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
	num = []
	R = []
	ROL = []
	XOL = []
	X = []
	den3Real = []
	den3Imag = []
	den3 = []
	den3OLReal = []
	den3OLImag = []
	den3OL = []
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
	for i in range(len(f)):
		#Expand the denominator of Eq. 16.2 on page 127 to get real and imag components.
		#A3 = 0
		R.append(A2*((f2[i])**4) - A0*((f2[i])**2) + K)#Real comp. of CL denom
		X.append(K*T2*f2[i] - A1*((f2[i])**3))#Imag comp. of CL denom
		#Expand denominator of Z(s)/s for 3rd order
		ROL.append(A2*((f2[i])**4) - A0*((f2[i])**2))#Real comp. of OL denom
		XOL.append(-A1*((f2[i])**3))#Imag comp. of OL denom
		den3Real.append(R[i])
		den3Imag.append(X[i])
		den3OLReal.append(ROL[i])
		den3OLImag.append(XOL[i])
		den3.append(complex(den3Real[i],den3Imag[i]))
		den3OL.append(complex(den3OLReal[i],den3OLImag[i]))
		#Transfer function for VCO noise
		vcoTFNumR.append(A2*((f2[i])**4) - A0*((f2[i])**2))
		vcoTFNumX.append(-A1*((f2[i])**3))
		vcoTFNumReal.append(vcoTFNumR[i])
		vcoTFNumImag.append(vcoTFNumX[i])
		vcoTFNum.append(complex(vcoTFNumReal[i],vcoTFNumImag[i]))
		#The denominator is the same as that of the CL transfer function
		#constant.append(K*N)
		#num.append(math.sqrt(1.0+((f[i]/(1/T2))**2)))
		num.append(complex(1.0,f2[i]/(1/T2)))
		magCL.append(20*np.log10(constantCL) + 20*np.log10(np.abs(num[i])) - 20*np.log10(np.abs(den3[i])))
		phaseCL.append((180/math.pi)*(np.angle(num[i]) - np.angle(den3[i])))
		magOL.append(20*np.log10(K) + 20*np.log10(np.abs(num[i])) - 20*np.log10(np.abs(den3OL[i])))
		phaseOL.append((180/math.pi)*(np.angle(num[i]) - np.angle(den3OL[i])) - 180)
		magvcoTF.append(20*np.log10(np.abs(vcoTFNum[i])) - 20*np.log10(np.abs(den3[i])))
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
	return C1/1e-9,C2/1e-9,C3/1e-9,R2/1e3,R3/1e3,f,magCL,magOL,phaseOL,magvcoTF,magprescalerTF,magpfdcpTF,magLFTFR2,magLFTFR3

def noiseContributors(workbook,magCL,magvcoTF,magprescalerTF,magpfdcpTF,R2,magLFTFR2,R3,magLFTFR3):
	R2Noise = 10*np.log10(4*1.3806503e-23*300*R2)
	R2NoiseOut = []
	for i in range(len(magLFTFR2)):
		R2NoiseOut.append(R2Noise + magLFTFR2[i])
	R3Noise = 10*np.log10(4*1.3806503e-23*300*R3)
	R3NoiseOut = []
	for i in range(len(magLFTFR2)):
		R3NoiseOut.append(R3Noise + magLFTFR3[i])
	if workbook == "":#If no file is uploaded or there's an error with the file
		f, PFDCPNoise, PrescalerNoise, VCONoise = defaultNoise()
		PFDCPNoiseOut = []
		for i in range(len(f)):
			PFDCPNoiseOut.append(PFDCPNoise[i] + magpfdcpTF[i])
		PrescalerNoiseOut = []
		for i in range(len(f)):
			PrescalerNoiseOut.append(PrescalerNoise[i] + magprescalerTF[i])
		VCONoiseOut = []
		for i in range(len(f)):
			VCONoiseOut.append(VCONoise[i] + magvcoTF[i])
	else:
		sheetPFDCP = workbook.sheet_by_name("PFDCP")
		PFDCPNoise = []
		PFDCPNoiseOut = []
		for i in range(len(magCL)):
			PFDCPNoise.append(sheetPFDCP.cell(i,1).value)
			PFDCPNoiseOut.append(PFDCPNoise[i] + magpfdcpTF[i])
		sheetPrescaler = workbook.sheet_by_name("Prescaler")
		PrescalerNoise = []
		PrescalerNoiseOut = []
		for i in range(len(magCL)):
			PrescalerNoise.append(sheetPrescaler.cell(i,1).value)
			PrescalerNoiseOut.append(PrescalerNoise[i] + magprescalerTF[i])
		sheetVCO = workbook.sheet_by_name("VCO")
		VCONoise = []
		VCONoiseOut = []
		for i in range(len(magCL)):
			VCONoise.append(sheetVCO.cell(i,1).value)
			VCONoiseOut.append(VCONoise[i] + magvcoTF[i])
	TotalNoise = []
	for i in range(len(magCL)):
		TotalNoise.append(10*np.log10(10**(PFDCPNoiseOut[i]/10.0) + 10**(PrescalerNoiseOut[i]/10.0) + 10**(VCONoiseOut[i]/10.0) + 10**(R2NoiseOut[i]/10.0) ))
		#TotalNoise.append(PFDCPNoiseOut[i] + PrescalerNoiseOut[i] + VCONoiseOut[i])	
	return PFDCPNoiseOut,PrescalerNoiseOut,VCONoiseOut,R2NoiseOut,R3NoiseOut,TotalNoise
	
def defaultNoise():
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
	
		
	

jinja_environment = jinja2.Environment(autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

class MainHandler(webapp2.RequestHandler):
	def write_form(self,Kphi="4E-3",KVCO="30E6",P="8.0",PM="47.0",LoopBW="2E3",Fout="1392E6",Fref="60E3",R="1.0",T31="0.6",Gamma="1.136"):
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
		C1,C2,C3,R2,R3,f,magCL,magOL,phaseOL,magvcoTF,magprescalerTF,magpfdcpTF,magLFTFR2,magLFTFR3 = loopFilter(enteredGamma,enteredLoopBW,enteredPM,enteredKphi,enteredKVCO,enteredP,enteredFout,enteredFref,enteredR,enteredT31)
		dictStringSubst={"Kphi": scientific(enteredKphi), "KVCO": scientific(enteredKVCO), "P": enteredP, "PM": enteredPM, "LoopBW": scientific(enteredLoopBW), "Fout": scientific(enteredFout), "Fref": scientific(enteredFref), "R": enteredR, "T31": enteredT31, "Gamma": enteredGamma}
		template = jinja_environment.get_template('form.html')
		self.response.out.write(template.render(dictStringSubst=dictStringSubst))
		template = jinja_environment.get_template('resultsBorder.html')
		self.response.out.write(template.render())
		try:
			noiseFile = self.request.get("noiseFile")
			workbook = xlrd.open_workbook(file_contents=noiseFile)
			noiseError=""
		except:
			workbook = ""
			noiseError = "***ERROR: Empty noise file or an error occurred while reading the file. Using default noise data instead.***" 
			#template = jinja_environment.get_template('noiseFileError.html')
			#self.response.out.write(template.render())
		template = jinja_environment.get_template('loopFilterTable.html')
		self.response.out.write(template.render(C1=scientific(C1),C2=scientific(C2),C3=scientific(C3),R2=scientific(R2),R3=scientific(R3)))
		index=range(1,len(f))
		template = jinja_environment.get_template('loopResponse.html')
		self.response.out.write(template.render(f=f,magCL=magCL,magOL=magOL,phaseOL=phaseOL,magvcoTF=magvcoTF,index2=index))
		PFDCPNoiseOut,PrescalerNoiseOut,VCONoiseOut,R2NoiseOut,R3NoiseOut,TotalNoise = noiseContributors(workbook,magCL,magvcoTF,magprescalerTF,magpfdcpTF,(R2*1e3),magLFTFR2,(R3*1e3),magLFTFR3)
		template = jinja_environment.get_template('noisePlot.html')
		self.response.out.write(template.render(f=f,PFDCPNoiseOut=PFDCPNoiseOut,PrescalerNoiseOut=PrescalerNoiseOut,VCONoiseOut=VCONoiseOut,R2NoiseOut=R2NoiseOut,R3NoiseOut=R3NoiseOut,TotalNoise=TotalNoise,index2=index,error=noiseError))
		#template = jinja_environment.get_template('loopResponse.html')
		#self.response.out.write(template.render(f=f,magCL=magCL,magOL=magOL,phaseOL=phaseOL,magvcoTF=magvcoTF,index2=index))
		

app = webapp2.WSGIApplication([('/', MainHandler)],
                              debug=True)

