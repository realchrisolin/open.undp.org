# ------------------
# UNDP Import Script
# ------------------
# This script runs Python commands to create the JSON API. 
# Requirements: Python 2.6 or greater 

import time, csv, json,  os, copy, re, sys, requests, chardet
from lxml import etree
from itertools import groupby
from datetime import datetime

t0 = time.time()
print "processing ..."

# Global Output Arrays
# ********************
fiscalYears = []
row_count = 0
outputs = []
outputsFull = []
locationsFull = []

# For donor JSONs
cntry_donors = csv.DictReader(open('download/undp_export/country_donors_updated.csv','rb'), delimiter = ',', quotechar = '"')
cntry_donors_sort = sorted(cntry_donors, key = lambda x: x['id'])

# Global Donors Arrays
dctry_index = [
	    {"id": "OTH","name": "Others"},
	    {"id": "MULTI_AGY","name": "Multi-lateral Agency"}
	]
donor_index = []
# for donor index JSON
donor_header = ['id','name','country']
donorCtryCheck = []
donorCtry_index = []
# for donor country index JSON
donorCtry_header = ['id','name']
donorCheck = []

# For CRS-index.json
crs_index = []
crsCheck = []
crsHeader = ['id','name']
# For focus-areas.json
focusAreasCheck = []
focusAreas = []

# Outputs function
# ****************
def outputsLoop(o, output_id):
	related = o.find("./related-activity[@type='1']")
	relatedArray = related.get('ref').split('-', 2)
	rltdProject = relatedArray[2]
	outputTitle = o.find("./title").text
	outputDescr = o.find("./description").text
	gen = o.find(".policy-marker").attrib
	outputGenID = gen.get('code')
	outputGenDescr = o.find(".policy-marker").text
	
	# Find sectors for crs-index.json
	outputCRSdescr = []
	outputCRS = []
	sector = o.find("./sector[@vocabulary='DAC']")
	# Set CRS for the output itself
	outputCRSdescr = sector.text
	outputCRS = sector.get('code')

	if sector.text not in crsCheck:
		# Append CRS to global array for index JSON
		sectorTemp = []
		crsCheck.append(sector.text)
		sectorTemp.append(sector.text)
		sectorTemp.append(sector.get('code'))
		crs_index.append(dict(zip(crsHeader, sectorTemp)))
	
	# Focus areas
	try:
		focusTemp = {}
		outputAll = o.find("./sector[@vocabulary='RO']")
		outputFA = outputAll.get('code')
		outputFAdescr = outputAll.text
		# For focus-areas.json
		if outputFA not in focusAreasCheck:
			focusAreasCheck.append(outputFA)
			focusTemp['id'] = outputFA
			focusTemp['name'] = outputFAdescr
			focusAreas.append(focusTemp)
	except: 
		outputFA = "-"
		outputFAdescr = "-"
	outputList = [output_id]
	outputAward = rltdProject
	outputFY = []
	# Donors
	donorIDCheck = []
	donorIDs = []
	donorNames = []
	donorShort = []
	donorTypeID = []
	donorType = []
	donorCtyID = []
	donorCty = []
	for donor in o.findall("./participating-org[@role='Funding']"):	
		ref = donor.get('ref')
		if ref not in donorIDCheck:
			donorIDCheck.append(ref)
			donorIDs.append(ref)
			if ref == '00012':
				donorNames.append('Voluntary Contributions')
			else: 
				donorNames.append(donor.text)
		
		for d in cntry_donors_sort:
			# Check IDs from the CSV against the cntry_donors_sort. This provides funding country names not in XML
			if d['id'] == ref:
				# for outputs
				donorShort.append(d['short_descr'])
				if d['donor_type_lvl1'] == 'PROG CTY' or d['donor_type_lvl1'] == 'NON_PROG CTY':
					donorCtyID.append(d['donor_type_lvl3'].replace(" ",""))
					donorCty.append(d['donor_type_lvl3_descr'])
				elif d['donor_type_lvl1'] == 'MULTI_AGY':
					donorCtyID.append(d['donor_type_lvl1'].replace(" ",""))
					donorCty.append(d['donor_type_lvl1_descr'])
				else:
					donorCtyID.append('OTH')
					donorCty.append('OTHERS')
				donorTypeID.append(d['donor_type_lvl1'])
				
				# for donor-index.json
				# Check for duplicates in donorCheck array
				if ref not in donorCheck:
					donorTemp = []
					donorCtryTemp = []
					donorCheck.append(ref)
					donorTemp.append(ref)
					donorTemp.append(donor.text)
					if d['donor_type_lvl1'] == 'PROG CTY' or d['donor_type_lvl1'] == 'NON_PROG CTY':
						donorTemp.append(d['donor_type_lvl3'].replace(" ",""))
					elif d['donor_type_lvl1'] == 'MULTI_AGY':
						donorTemp.append(d['donor_type_lvl1'].replace(" ",""))
					else:
						donorTemp.append('OTH')
					donor_index.append(dict(zip(donor_header,donorTemp)))
				if d['donor_type_lvl3'] not in donorCtryCheck:
					if d['donor_type_lvl1'] == 'PROG CTY' or d['donor_type_lvl1'] == 'NON_PROG CTY':
						donorCtryCheck.append(d['donor_type_lvl3'])
						donorCtryTemp.append(d['donor_type_lvl3'])
						donorCtryTemp.append(d['donor_type_lvl3_descr'])
						dctry_index.append(dict(zip(donorCtry_header,donorCtryTemp)))
	
	# Find budget information to later append to projectFY array
	outputBudgetTemp = {}
	budgets = o.findall("./budget")
	for budget in budgets: 
		for b in budget.iterchildren(tag='value'):
			date = b.get('value-date').split('-', 3)
			amt = b.text
			year = date[0]
			outputBudgetTemp[year] = float(amt)

			if year not in fiscalYears:
				# Append to global array for year-index.js
				fiscalYears.append(year) 
			if year not in outputFY:
				# Append to output array
				outputFY.append(year)	

	# Use transaction data to get expenditure and budget by donor
	donorBudget = []
	donorExpend = []
	outputExpendTemp = {}
	transactions = o.findall('transaction')
	b = []
	loop = 0
	for tx in transactions:
		for expen in tx.findall("./transaction-type[@code='E']"):
			loop = loop + 1
			eVal = []
			for sib in expen.itersiblings():
				if sib.tag == 'value':
					date = sib.get('value-date').split('-', 3)
					amt = sib.text
					year = date[0]
					outputExpendTemp[year] = []
					outputExpendTemp[year] = float(sib.text)
					eVal.append(float(sib.text))
					donorExpend = donorExpend + eVal
					if year not in fiscalYears:
						# Append to global array for year-index.js
						fiscalYears.append(year) 
					if year not in outputFY:
						# Append to output array
						outputFY.append(year)	

	outputBudget = []
	outputExpend = []
	for y in outputFY:
		try:
			outputExpend.append(outputExpendTemp[y])
		except KeyError:
			outputExpend.append(None)
		try:
			outputBudget.append(outputBudgetTemp[y])
		except KeyError:
			outputBudget.append(None)

	locs = []
	locHeader = ['awardID','lat','lon','precision','name','type']
	locations = o.findall('location')
	for location in locations:
		locTemp = []
		awardID = rltdProject
 		for loc in location.iterchildren():
			if loc.tag == 'coordinates':
				lat = loc.get('latitude')
				lon = loc.get('longitude')
				precision = loc.get('precision')
			if loc.tag == 'name':
				name = loc.text
			if loc.tag == 'location-type':
				locType = loc.get('code')
		locTemp.append(awardID)
		locTemp.append(lat)
		locTemp.append(lon)
		locTemp.append(precision)
		locTemp.append(name)
		locTemp.append(locType)
		locationsFull.append(dict(zip(locHeader,locTemp)))
	outputsHeader = ['output_id','award_id','output_title','output_descr','gender_id','gender_descr','focus_area','focus_area_descr','crs','crs_descr','fiscal_year','donor_budget','donor_expend','budget','expenditure','donor_id','donor_short','donor_name','donor_type_id','donor_country_id','donor_country']
	outputList.append(outputAward)
	outputList.append(outputTitle)
	outputList.append(outputDescr)
	outputList.append(outputGenID)
	outputList.append(outputGenDescr)
	outputList.append(outputFA)
	outputList.append(outputFAdescr)
	outputList.append(outputCRS)
	outputList.append(outputCRSdescr)
	outputList.append(outputFY)
	outputList.append(donorBudget)
	outputList.append(donorExpend)
	outputList.append(outputBudget)
	outputList.append(outputExpend)
	outputList.append(donorIDs)
	outputList.append(donorShort)
	outputList.append(donorNames)
	outputList.append(donorTypeID)
	outputList.append(donorCtyID)
	outputList.append(donorCty)
	outputsFull.append(dict(zip(outputsHeader,outputList))) # this returns a list of dicts of output informaiton for each output

# Global project arrays
projects = []
projectsFull = []
projectsSmallFull = []
projectsHeader = ['project_id','operating_unit','operating_unit_id','iati_op_id','project_title','project_descr','start','end','inst_id','inst_descr','inst_type_id','document_name']
units = csv.DictReader(open('download/undp_export/report_units.csv', 'rb'), delimiter = ',', quotechar = '"')
units_sort = sorted(units, key = lambda x: x['operating_unit'])
iati_regions = csv.DictReader(open('download/undp_export/iati_regions.csv', 'rb'), delimiter = ',', quotechar = '"')
iati_regions_sort = sorted(iati_regions, key = lambda x: x['code'])

def loopData(file_name, key):
	# Get IATI activities XML
	context = iter(etree.iterparse(file_name,tag='iati-activity'))
	# Loop through each IATI activity in the XML
	for event, p in context:
		docTemp = []
		# IATI hierarchy used to determine if output or input1
		hierarchy = p.attrib['hierarchy']
		current = p.attrib['default-currency']
		awardArray = p[1].text.split('-', 2)
		award = awardArray[2]
		implement = p.find("./participating-org[@role='Implementing']")
		if hierarchy == '2':
			# Send the outputs to a separate function, to be joined to their projects later in step 2 below.
			outputsLoop(p, award)
		# Check for projects		
		if hierarchy == '1':
			projectList = [award]
			docTemp = []
			subnationalTemp = []
			award_title = p.find("./title").text
			award_description = p.find("./description").text
			# Get document-links
			documents = p.findall("./document-link")
			docLinks = []
			docNames = []
			for doc in documents:
				docLinks.append(doc.get('url'))
				for d in doc.iterchildren(tag='title'):
					docNames.append(d.text)
			if docNames:
				docTemp.append(docNames)
				docTemp.append(docLinks)
			# Find start and end dates
			start_date = p.find("./activity-date[@type='start-planned']").text
			end_date = p.find("./activity-date[@type='end-planned']").text
			# Find operatingunit
			try: 
				op_unit = p.find("./recipient-country").attrib
				ou_descr = p.find("./recipient-country").text
				for r in units_sort:
					if op_unit.get('code') == r['iati_operating_unit']:
						operatingunit = r['operating_unit']
				projectList.append(ou_descr)
				projectList.append(operatingunit)
				projectList.append(op_unit.get('code'))						
			except: 
				region_unit = p.find("./recipient-region").attrib
				for r in units_sort:
					if region_unit.get('code') == r['iati_operating_unit']:
						operatingunit = r['operating_unit']
						ou_descr = r['ou_descr']
				projectList.append(ou_descr)
				projectList.append(operatingunit)
				projectList.append(r['iati_operating_unit'])
			# try: 
			# 	op_unit = p.find("./recipient-country").attrib
			# 	ou_descr = p.find("./recipient-country").text
			# 	for r in units_sort:
			# 		if op_unit.get('code') == r['iati_operating_unit']:
			# 			operatingunit = r['operating_unit']
			# 	projectList.append(ou_descr)
			# 	projectList.append(operatingunit)
			# 	projectList.append(op_unit.get('code'))			
			# except: 
			# 	operatingunit = []
			# 	ou_descr = []
			# 	region_unit = p.find("./recipient-region").attrib
			# 	op_unit = region_unit.get('code')
			# 	for r in iati_regions_sort:
			# 		if r['code'] == op_unit:
			# 			print "         "
			# 			print "this works"
			# 			print "           "
			# 			operatingunit = r['filter_unit']
			# 			ou_descr = r['name']
			# 	projectList.append(ou_descr)
			# 	projectList.append(operatingunit)
			# 	projectList.append('NA')
			# 	if award == '00069400':
			# 		print "first one", ou_descr, operatingunit, 	
			# Get regions
			regionTemp = p.find("./recipient-region").attrib
			region = p.find("./recipient-region").text
			regionID = regionTemp.get('code') 

			# Append the remaining items to the project Array				
			projectList.append(award_title)
			projectList.append(award_description)
			projectList.append(start_date)
			projectList.append(end_date)
			# Check for implementing organization 
			try: 
				inst = p.find("./participating-org[@role='Implementing']").attrib
				inst_descr = p.find("./participating-org[@role='Implementing']").text
				institutionid = inst.get('ref')
				inst_type_id = inst.get('type')
				projectList.append(institutionid)
				projectList.append(inst_descr)
				projectList.append(inst_type_id)
			except: 
				projectList.append("")
				projectList.append("")
				projectList.append("")
			projectList.append(docTemp)
			projectsFull.append(dict(zip(projectsHeader,projectList))) # this joins project information, output per project, and documents for each project

# This is the function that creates project summary files
# *******************************************
def createSummary():
	regionsList = ['PAPP','RBA','RBAP','RBAS','RBEC','RBLAC']
	row_count = 0
	yearList = []
	projectSumHeader = ['fiscal_year','id','name','operating_unit','region','budget','expenditure','crs','focus_area','donors','donor_types','donor_countries','donor_budget','donor_expend']

	for year in fiscalYears:
		projectSummary = []
		yearSummary = {'year':"",'summary':""} 
		for row in projectsFull:
			for y in row['fiscal_year']:
				if y == year:
					row_count = row_count + 1
					summaryList = [year]
					summaryList.append(row['project_id'] )
					projectFY = []
					docTemp = []
					summaryList.append(row['project_title'])
					summaryList.append(row['operating_unit_id'])
					if row['region_id'] not in regionsList:
						summaryList.append('global')
					else:
						summaryList.append(row['region_id'])
					crsTemp = []
					faTemp = []
					dTemp = []
					dtypeTemp = []
					dCtyTemp = []
					budgetT = []
					expendT = []
					dBudget = []
					dExpend = []
					for out in row['outputs']:
						for idx, yr in enumerate(out['fiscal_year']):
							if  yr == year:
								b = out['budget'][idx]
								e = out['expenditure'][idx]
								if b is not None:
									budgetT.append(b)
								if e is not None:
									expendT.append(e)
						if out['crs'] not in crsTemp:
						    crsTemp.append(out['crs'])
						if out['focus_area'] not in faTemp:
						    faTemp.append(out['focus_area'])
						for d in out['donor_id']:
							dTemp.append(d)
						for d in out['donor_type_id']:
							dtypeTemp.append(d)
						for d in out['donor_country_id']:
							dCtyTemp.append(d)
						for d in out['donor_budget']:
							dBudget.append(d)
						for d in out['donor_expend']:
							dExpend.append(d)

					summaryList.append(sum(budgetT))
					summaryList.append(sum(expendT))
					summaryList.append(crsTemp)
					summaryList.append(faTemp)
					summaryList.append(dTemp)
					summaryList.append(dtypeTemp)
					summaryList.append(dCtyTemp)
					summaryList.append(dBudget)
					summaryList.append(dExpend)
					projectSummary.append(dict(zip(projectSumHeader,summaryList))) # this joins the project summary information 

		yearSummary['year'] = year
		yearSummary['summary'] = projectSummary 
		yearList.append(yearSummary)

	print "Project Summary Process Count: %d" % row_count
	
	for y in yearList:
		jsvalue = "var SUMMARY = "
		jsondump = json.dumps(y['summary'], sort_keys=True, separators=(',',':'))
		writeout = jsvalue + jsondump
		f_out = open('../api/project_summary_%s.js' % y['year'], 'wb')
		f_out.writelines(writeout)
		f_out.close()
		f_out = open('../api/project_summary_%s.json' % y['year'], 'wb')
		f_out.writelines(jsondump)
		f_out.close()
	print 'Project Summary json files generated...'

# 1. Scipt starts here
# *****************
# Specify XML project file location
projects_file = 'download/undp_export/atlas_projects.xml'
loopData(projects_file,'document-link')

# 2. Joing outputs to projects
opUnits = []
for row in projectsFull:
	if row['operating_unit_id'] not in opUnits:
		opUnits.append(row['operating_unit_id'])
	row['outputs'] = []
	row['budget'] = []
	row['expenditure'] = []
	row['subnational'] = []
	row['fiscal_year'] = []
	budget = []
	expen = []
	for o in outputsFull:
		if row['project_id'] == o['award_id']:
			row['outputs'].append(o)
			for b in o['budget']:
				if b is not None:
					budget.append(b)
			for e in o['expenditure']:
				if e is not None:
					expen.append(e)
			for y in o['fiscal_year']:
				if y not in row['fiscal_year']:
					# Append to output array
					row['fiscal_year'].append(y)
	row['budget'].append(sum(budget))
	row['expenditure'].append(sum(expen))
	for l in locationsFull:
		if row['project_id'] == l['awardID']:
			row['subnational'].append(l)
	# join region information
	row['region_id'] = []
	for r in units_sort:
		if row['iati_op_id'] == r['iati_operating_unit']:
				row['region_id'] = r['bureau']

# 3. Run summary file function, on already joined project and output files
# ***********************
createSummary()

# 4. Generate JSONs
# ****************

# Generate JSONs for each project
file_count = 0
for row in projectsFull:
	file_count = file_count + 1
	writeout = json.dumps(row, sort_keys=True, separators=(',',':'))
	f_out = open('../api/projects/%s.json' % row['project_id'], 'wb')
	f_out.writelines(writeout)
	f_out.close()
print '%d project files generated...' % file_count

# Sort projects by operating unit
# ********************************
iso = csv.DictReader(open('download/undp_export/country_iso.csv', 'rb'), delimiter = ',', quotechar = '"')
iso_sort = sorted(iso, key = lambda x: x['iso3'])

unitFinal = []
unitHeader = ['op_unit','projects','iso_num']
for unit in opUnits:
	info = []
	listing = []
	info.append(unit)
	for proj in projectsFull:
		if unit == proj['operating_unit_id']:
			listingTemp = {}
			listingTemp['subnational'] = proj['subnational']
			listingTemp['id'] = proj['project_id']
			listingTemp['title'] = proj['project_title']
			listing.append(listingTemp)
	info.append(listing)   
	# Grab the iso number for each operating unit to match to TopoJSON
	for c in iso_sort:
		# Correct encoding for the match below
		numTemp = c['iso_num'].decode('utf-8')
		numDecode = numTemp.encode('ascii','ignore')
		isoTemp = c['iso3'].decode('utf-8')
		isoDecode = isoTemp.encode('ascii', 'ignore')
		if isoDecode == unit:
			if numDecode != "":
				info.append(numDecode)
	unitFinal.append(dict(zip(unitHeader,info))) # this joins project information, output per project, and documents for each project

# Generate JSONs for each operating unit
file_count = 0
for u in unitFinal:
	file_count = file_count + 1
	writeout = json.dumps(u, sort_keys=True, separators=(',',':'))
	f_out = open('../api/units/%s.json' % u['op_unit'], 'wb')
	f_out.writelines(writeout)
	f_out.close()
print '%d operating unit files generated...' % file_count

# Process CRS Index
# *****************
row_count = 0
print "CRS Index Process Count: %d" % row_count
writeout = json.dumps(crs_index, sort_keys=True, separators=(',',':'))
f_out = open('../api/crs-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()

# Process Donor Index
# *****************
print "Donor Index Process Count: %d" % row_count
writeout = json.dumps(donor_index, sort_keys=True, separators=(',',':'))
f_out = open('../api/donor-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()

# Process Donor Country Index
# *****************
print "Donor Country Index Process Count"
writeout = json.dumps(dctry_index, sort_keys=True, separators=(',',':'))
f_out = open('../api/donor-country-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()

# Make year index 
# ***************
yearJSvalue = "var FISCALYEARS ="
writeout = "%s %s" % (yearJSvalue, fiscalYears) 
f_out = open('../api/year-index.js', 'wb')
f_out.writelines(writeout)
f_out.close()

print "Donors by Output Process Count: %d"
donorOutputs = []
donorOutHeader = ['outputID','donorID','donorName','donorShort','donorTypeID','donorCtyID','donorCty','donorBudget','donorExpend']

# Top Donor Lists
# ************************
donor_gross = csv.DictReader(open('download/undp_export/donor_gross.csv', 'rb'), delimiter = ',', quotechar = '"')
donor_gross_sort = sorted(donor_gross, key = lambda x: x['donor'])
donor_local = csv.DictReader(open('download/undp_export/donor_local.csv', 'rb'), delimiter = ',', quotechar = '"')
donor_local_sort = sorted(donor_local, key = lambda x: x['donor'])

# Writeout donor gross list
# ************************
gross_list = []
for g in donor_gross_sort:
	gross = {}
	gross['name'] = g['donor']
	gross['country'] = g['abbrev']
	gross['regular'] = g['regular']
	gross['other'] = g['other']
	gross['total'] = g['total']
	for d in cntry_donors_sort:
		if d['donor_type_lvl3_descr'] == g['donor']:
			gross['donor_id'] = d['id']
	gross_list.append(gross)

writeout = json.dumps(gross_list, sort_keys=True, separators=(',',':'))
f_out = open('../api/top-donor-gross-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()

# Writeout donor local list
# ************************
local_list = []
for g in donor_local_sort:
	local = {}
	local['country'] = g['abbrev']
	local['name'] = g['donor']
	local['amount'] = g['amount']
	for d in cntry_donors_sort:
		if d['donor_type_lvl3_descr'] == g['donor']:
			local['donor_id'] = d['id']
	local_list.append(local)

writeout = json.dumps(local_list, sort_keys=True, separators=(',',':'))
f_out = open('../api/top-donor-local-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()

# Region Index 
# ************
exclude = ['PAPP','RBA','RBAP','RBAS','RBEC','RBLAC']
row_count = 0
region_index = []
regionHeader = ['id','name']
region_i = []
index = []
global_i = ['global','Global']
for r,region in groupby(units_sort, lambda x: x['bureau']): 
	row_count = row_count + 1
	if r in exclude:
		region_i = [r]
		for reg in region:
			if reg['bureau'] == 'PAPP':
				region_i.append(reg['ou_descr'])
				index.append(region_i)
			if reg['hq_co'] == 'HQ':
				if reg['ou_descr'] not in region_i:
					region_i.append(reg['ou_descr'])
					index.append(region_i)

index.append(global_i)
index_print = []
for i in index:
    index_print.append(dict(zip(regionHeader, i)))
    
print "Region Index Process Count: %d" % row_count
writeout = json.dumps(index_print, sort_keys=True, separators=(',',':'))
f_out = open('../api/region-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()

# Process Focus Area Index
# ************************
row_count = 0
index = []
for focus in focusAreas:
	row_count = row_count + 1
	index.append(focus)

print "Focus Area Index Process Count: %d" % row_count
writeout = json.dumps(index, sort_keys=True, separators=(',',':'))
f_out = open('../api/focus-area-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()

# Process HDI
# ************************
hdi = csv.DictReader(open('hdi/hdi-csv-clean.csv', 'rb'), delimiter = ',', quotechar = '"')
geo = csv.DictReader(open('process_files/country-centroids.csv', 'rb'), delimiter = ',', quotechar = '"')

hdi_sort = sorted(hdi, key = lambda x: x['hdi2011'], reverse = True)
country_sort = sorted(geo, key = lambda x: x['iso3'])

years = [1980,1985,1990,1995,2000,2005,2006,2007,2008,2011]
current_year = 2011

row_count = 0
rank = 0
hdi_index = []
hdi_dict = {}
for val in iter(hdi_sort):
	row_count = row_count + 1
	hdi_total = []
	hdi_health = []
	hdi_ed = []
	hdi_inc = []
	change = []
	change_year = {}
	for y in years:
		if val['hdi%d' % y] != '':
			hdi_total.append([y,float(val['hdi%d' % y])])
			hdi_health.append([y,float(val['health%d' % y])])
			hdi_ed.append([y,float(val['ed%d' % y])])
			hdi_inc.append([y,float(val['income%d' % y])])
			if y != current_year:
				change_year = float(val['hdi%d' % current_year]) - float(val['hdi%d' % y])
				if len(change) == 0:
					change.append(change_year)
	if len(change) == 0:
	    change.append("")
	for ctry in country_sort:
	    if ctry['name'] == val['country']:
			if val['hdi%d' % current_year] == "":
			    g = {
			        "id": ctry['iso3'],
			        "name": val['country'],
			        "hdi": "",
			        "health": "",
			        "income": "",
			        "education": "",
			        "change": change[0],
			        "rank": "n.a."
			    }
			else:
			    if ctry['iso3'].rfind("A-",0,2) == 0:
			        g = {
			            "id": ctry['iso3'],
			            "name": val['country'],
			            "hdi": hdi_total,
			            "health": hdi_health,
			            "income": hdi_inc,
			            "education": hdi_ed,
			            "change": change[0],
			            "rank": "n.a."
			        }
			    else:
			        rank = rank + 1
			        
			        g = {
			            "id": ctry['iso3'],
			            "name": val['country'],
			            "hdi": hdi_total,
			            "health": hdi_health,
			            "income": hdi_inc,
			            "education": hdi_ed,
			            "change": change[0],
			            "rank": rank
			        }
			hdi_index.append(g)
			uid = ctry['iso3']
			hdi_dict[uid] = copy.deepcopy(g)
			hdi_dict[uid].pop('id')
			hdi_dict[uid].pop('name')

hdi_dict['total'] = rank
hdi_index_sort = sorted(hdi_index, key = lambda x: x['rank'])
hdi_writeout = json.dumps(hdi_index_sort, sort_keys=True, separators=(',',':'))
hdi_out = open('../api/hdi.json', 'wb')
hdi_out.writelines(hdi_writeout)
hdi_out.close()

jsvalue = "var HDI = "
jsondump = json.dumps(hdi_dict, sort_keys=True, separators=(',',':'))
writeout = jsvalue + jsondump
f_out = open('../api/hdi.js', 'wb')
f_out.writelines(writeout)
f_out.close()

# Process Operating Unit Index
# ****************************
currentYear = fiscalYears[0]
opIndex = []
opIndexHeader =  ['id','name','project_count','funding_sources_count','budget_sum','expenditure_sum','lat','lon','iso_num']
for unit in opUnits:
	opTemp = {}
	donors = []
	budgetT = []
	expendT = []
	for ctry in country_sort:
		if ctry['iso3'] == unit:
			opTemp['name'] = ctry['name']
			if ctry['lat'] != "":
				opTemp['lat'] = float(ctry['lat'])
				opTemp['lon'] = float(ctry['lon'])
			for c in iso_sort:
				# Correct encoding for the match below
				numTemp = c['iso_num'].decode('utf-8')
				numDecode = numTemp.encode('ascii','ignore')
				isoTemp = c['iso3'].decode('utf-8')
				isoDecode = isoTemp.encode('ascii', 'ignore')
				if isoDecode == ctry['iso3']:
					opTemp['iso_num'] = numDecode
	projectCount = 0
	for row in projectsFull:
		if row['operating_unit_id'] == unit:
			projectCount = projectCount + 1;
			for o in row['outputs']:
				for d in o['donor_id']:
					if d not in donors:
						donors.append(d)
				for idx, y in enumerate(o['fiscal_year']):
					if y == currentYear:
						b = o['budget'][idx]
						e = o['expenditure'][idx]
						if b is not None:
							budgetT.append(b)
						if e is not None:
							expendT.append(e)
	opTemp['funding_sources_count'] = len(donors)
	opTemp['budget_sum'] = sum(budgetT)
	opTemp['expenditure_sum'] = sum(expendT)
	opTemp['id'] = unit
	opTemp['project_count'] = projectCount
	opIndex.append(opTemp)

writeout = json.dumps(opIndex, sort_keys=True, separators=(',',':'))
f_out = open('../api/operating-unit-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()
print "Operating Unit Index Process Count: %d" % row_count

# Subnational Locations Index
# ************************
refType = csv.DictReader(open('download/undp_export/ref_typeofproject.csv', 'rb'), delimiter = ',', quotechar = '"')
refType_sort = sorted(refType, key = lambda x: x['id'])
refPrec = csv.DictReader(open('download/undp_export/ref_precisioncodes.csv', 'rb'), delimiter = ',', quotechar = '"')
refPrec_sort = sorted(refPrec, key = lambda x: x['id'])
refScope = csv.DictReader(open('download/undp_export/ref_scopeofproject.csv', 'rb'), delimiter = ',', quotechar = '"')
refScope_sort = sorted(refScope, key = lambda x: x['id'])

ref = {}
ref['type'] = {}
ref['precision'] = {}
ref['scope'] = {}
row_count = 0
for x in refType_sort:
    ref['type'][x['id']] = x['description']
    row_count = row_count + 1
 
for x in refScope_sort:
    ref['scope'][x['id']] = x['description']
    row_count = row_count + 1
 
for x in refPrec_sort:
    ref['precision'][x['id']] = x['description']
    row_count = row_count + 1
    
print "Subnational Location Index Count: %d" % row_count
writeout = json.dumps(ref, sort_keys=True, separators=(',',':'))
f_out = open('../api/subnational-locs-index.json', 'wb')
f_out.writelines(writeout)
f_out.close()

# Calculate the total time and print to console. 
t1 = time.time()
total_time = t1-t0
print "Processing complete. Total Processing time = %d seconds" % total_time