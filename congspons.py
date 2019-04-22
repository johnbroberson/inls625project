import requests
from bs4 import BeautifulSoup as BS
import pandas
import re
from dateutil.relativedelta import relativedelta
from nltk.corpus import stopwords

##############################################################################################################################################
##1: GET PROPUBLICA API BILL-ENDPOINT DATA (ppabe_)

def ppabe_get_bill_batch(cong_num, chamber, bill_type, offset = 0):
#	pulls a batch of 20 bills through a propublica api call;
#	returns: df 
	global base_url, headers
	#https://api.propublica.org/congress/v1/{congress}/{chamber}/bills/{type}.json
	this_batch_url = base_url + str(cong_num) + "/" + chamber + "/bills/" + bill_type + ".json?offset=" + str(offset)
	this_batch = requests.get(this_batch_url, headers = headers)
	print(this_batch)
	#handling exceptional cases, in which the returned json file has bad characters
	if ((cong_num == 113) & (chamber == 'house') & (bill_type == 'passed') & (offset == 260)):
		return pandas.DataFrame(json.loads(this_batch.text.replace("\\ "," "))['results'][0]['bills'])
	if ((cong_num == 112) & (chamber == 'house') & (bill_type == 'passed')):
		if offset == 140:
			return pandas.DataFrame(json.loads(this_batch.text.replace("(1)\tthe","(1) the"))['results'][0]['bills'])
		if offset == 480:
			return pandas.DataFrame(json.loads(this_batch.text.replace("\r\r"," "))['results'][0]['bills'])
	return pandas.DataFrame(json.loads(this_batch.text)['results'][0]['bills'])

def ppabe_get_sponsors(number, chamber, bill_type):
#	iteratively calls ppabe_get_bill_batch for all sets of 20 bills for the given congress;
#	returns: None (writes df to csv)
	offset = 0
	full_20 = True
	bill_data = ppabe_get_bill_batch(number, chamber, bill_type, offset)
	offset = 20
	while full_20 == True:
		print(offset)
		batch = ppabe_get_bill_batch(number, chamber, bill_type, offset)
		offset += 20
		bill_data = bill_data.append(batch)
		bill_data = bill_data.drop_duplicates(subset = 'bill_id')
		full_20 = (len(batch.index) == 20)
	bill_data.drop("summary", axis = 1).to_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/API Source Data/{}_Sponsors.csv".format(str(number)))

def ppabe_get_cong_num(row):
#	extracts the congress number (e.g. 114) from a bill's ID
#	returns: int
	return int((row['bill_id'].split("-"))[1])

def ppabe_merge_cong_dfs():
#	reads in separate dfs for each congress (created by ppabe_get_sponsors), then merges them and cleans them up a bit
#	returns: df
	df_112 = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/API Source Data/112_Sponsors.csv")
	df_113 = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/API Source Data/113_Sponsors.csv")
	df_114 = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/API Source Data/114_Sponsors.csv")
	df_115 = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/API Source Data/115_Sponsors.csv")

	df_112.set_index('bill_id',drop = False, inplace = True)
	df_113.set_index('bill_id',drop = False, inplace = True)
	df_114.set_index('bill_id',drop = False, inplace = True)
	df_115.set_index('bill_id',drop = False, inplace = True)

	merged = (df_115.append(df_114.append(df_113.append(df_112)))) \
		.drop(labels = ["Unnamed: 0", "Unnamed: 0.1", "active", "committee_codes", "enacted", "vetoed"], axis = 1, inplace = True)

	merged['congress'] = merged.apply(ppabe_get_cong_num, axis = 1)

	return merged

def ppabe_main():
	ppabe_get_sponsors(112, 'house', 'passed')
	ppabe_get_sponsors(113, 'house', 'passed')
	ppabe_get_sponsors(114, 'house', 'passed')
	ppabe_get_sponsors(115, 'house', 'passed')

	ppabe_merge_cong_dfs().to_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 1 - Merged API Bill-Point Data", index = False)

##############################################################################################################################################
##2: GET GOVTRACK DATA (gt_)

def gt_get_text(row):
#	collects the text of the given bill
#	returns: string
	bill_list = row['bill_id'].split("-")
	bill_id = bill_list[0]
	cong_num = bill_list[1]
	url = "https://www.govtrack.us/congress/bills/{}/{}/text".format(str(cong_num), bill_id)
	soup = BS(requests.get(url).content, "lxml")
	bill_text = ""
	for section in soup.find_all("p", ["header","text"]):
		bill_text += (section.text + " ")
	return (re.sub(r"[^\s\w:()?!$%&]", "", bill_text)) \
		.replace("\r\n\t\t", " ").replace("\r\n\t", " ").replace("\r\n", " ") \
		.replace("\\n"," ").replace("\\r", " ").replace("\\t", " ")

def gt_main():
	data = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 1 - Merged API Data.csv")
	data['bill_text'] = merged_api_data.apply(gt_get_text, axis = 1) 
	data.to_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 2 - Added Bill Text.csv", index = False)

##############################################################################################################################################
##3: GET DW_NOMINATE DATA (dwn_)

def dwn_main():
	#data available for download here: https://voteview.com/data
	dw_data = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/HSall_members.csv")
	dw_nom_df = pandas.DataFrame()
	dw_nom_df['sponsor_id'] = dw_data['bioguide_id']
	dw_nom_df['dw_nom_1'] = dw_data['nominate_dim1'] 
	dw_nom_df['dw_nom_2'] = dw_data['nominate_dim2']
	dw_nom_df.drop_duplicates(inplace = True)
	(pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 2 - Added Bill Text.csv")) \
		.merge(dw_nom_df) \
		.to_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 3 - Added DW_Nom.csv", index = False) 

##############################################################################################################################################
##4: GET PROPUBLICA API MEMBER-ENDPOINT DATA (ppame_)

def ppame_get_data(row):
#	fetches api data from the member endpoint
#	returns: dict
	global headers
	print(row['sponsor_id'])
	the_goods = (requests.get("https://api.propublica.org/congress/v1/members/{}.json".format(row['sponsor_id']), headers = headers)) \
		.json()['results'][0]
	output = {'dob':the_goods['date_of_birth'],
			  'gender':the_goods['gender'],
			  'twitter':the_goods['twitter_account']}
	for congress in the_goods['roles']:
		if (int(congress['congress']) == int(row['congress'])):
			output['leadership'] = congress['leadership_role']
			output['seniority'] = congress['seniority']
			output['party_loyalty'] = congress['votes_with_party_pct']
			if ((congress['short_title'] == "Rep.") and (congress['at_large'] == False)):
				output['district'] = congress['district']
			else:
				output['district'] = "At_Large"
	return output			 

def ppame_break_out(df):
#	Takes the dict of info from ppame_get_data, break it into a df of its own, then join back
#	returns: df
	member_info_df = df['member_info'].apply(pandas.Series)
	return pandas.concat([df, member_info_df], axis = 1) \
		.drop('member_info', axis = 1)	

def ppame_main():
	data = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 3 - Added DW_Nom.csv")
	data['member_info'] = data.apply(ppame_get_data, axis = 1)
	ppame_break_out(data).to_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 4 - Added API Member-Point Data.csv", index = False) 

##############################################################################################################################################
##5: OTHER PREPROCESSING (opp_)

def opp_make_district(row):
	return "{}-{}".format(row['sponsor_state'], row['district'])

def opp_recog_as_dict(row):
	return eval(row['cosponsors_by_party'])

def opp_calc_age(row):
	return relativedelta(row['introduced_date'], row['dob']).years

def opp_break_out_cosponsors_by_party(df):
	cospon_info_df = df['cosponsors_by_party'].apply(pandas.Series)
	return pandas.concat([df, cospon_info_df], axis = 1) \
		.drop('cosponsors_by_party', axis = 1)

def opp_main():
	data = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 4 - Added API Member-Point Data.csv", index_col = [0]) 
	data['sponsor_district'] = data.apply(opp_make_district, axis = 1)
	data['introduced_date'] = pandas.to_datetime(data['introduced_date'])
	data['dob'] = pandas.to_datetime(data['dob'])
	data['sponsor_age'] = data.apply(opp_calc_age, axis = 1)
	data['cosponsors_by_party'] = data.apply(opp_recog_as_dict, axis = 1)
	data_with_cospons_by_party = opp_break_out_cosponsors_by_party(data)
	data_with_cospons_by_party.rename(columns = {"R":"cospons_r","D":"cospons_d","I":"cospons_i"}) \
		.drop(labels = ["bill_uri", "congressdotgov_url", "gpo_pdf_uri", "sponsor_uri"], axis = 1) \
		.to_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 5 - Additional Preprocessing.csv", index = False)

##############################################################################################################################################
##6: TEXT PROCESSING (tp_)
##https://www.analyticsvidhya.com/blog/2018/02/the-different-methods-deal-text-data-predictive-python/

def tp_convert_floats_to_empty_strings(text):
	if type(text) == float:
		return ""
	return str(text)

def tp_avg_word_len(text):
	if len(text) == 0:
		return 0
	words = text.split()
	return (sum(len(word) for word in words) / len(words))

def tp_us_code_refs(row):
	usc_regex_1 = re.compile(r'\d\susc\s\d')
	usc_regex_2 = re.compile(r'\d\sU\.S\.C\.\s\d')
	usc_regex_3 = re.compile(r'section\s\d*\sof\stitle\s\d*, United States Code')
	usc_regex_4 = re.compile(r'section\s\d*\sof\stitle\s\d*, US Code')
	usc_regex_5 = re.compile(r'section\s\d*\sof\stitle\s\d*, U\.S\. Code')
	usc_regex_6 = re.compile(r'Chapter\s\d*\sof\stitle\s\d*, United States Code')
	usc_regex_7 = re.compile(r'Chapter\s\d*\sof\stitle\s\d*, US Code')
	usc_regex_8 = re.compile(r'Chapter\s\d*\sof\stitle\s\d*, U\.S\. Code')
	usc_regex_9 = re.compile(r'section\s\d*\sof\stitle\s\d*\.')
	usc_regex_10 = re.compile(r'section\s\d*(\w*)\sstitle\s\d')

	ref_list = []

	for regex in [usc_regex_1, usc_regex_2, usc_regex_3, usc_regex_4, usc_regex_5,
				  usc_regex_6, usc_regex_7, usc_regex_8, usc_regex_9, usc_regex_10]:
		this_list = regex.findall(row['bill_text'])
		if (this_list != []):
			ref_list.extend(this_list)

	return len(ref_list)

def tp_main():
	data = pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 5 - Additional Preprocessing.csv", index_col = [0])
	data['bill_text'] = data['bill_text'].apply(tp_convert_floats_to_empty_strings)

	#simple stats
	data['bill_text_simple_word_count'] = data['bill_text'].apply(lambda x: len(str(x).split(" ")))
	data['bill_text_simple_avg_word_len'] = data['bill_text'].apply(lambda x: tp_avg_word_len(x))
	stops = stopwords.words('english')
	data['bill_text_num_stopwords'] = data['bill_text'].apply(lambda x: len([a for a in x.split() if a in stops]))
	data['bill_text_num_numerics'] = data['bill_text'].apply(lambda x: len([a for a in x.split() if a.isdigit()]))

	#make lower and remove stopwords
	data['bill_text'] = data['bill_text'].apply(lambda x: " ".join(a.lower() for a in x.split() if a not in stops)) #might want to consider leaving uppercases?

	#calculate number of direct references to existing us code
	data['bill_text_us_code_refs'] = data.apply(tp_us_code_refs, axis = 1)

	data.to_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 6 - Text Processing.csv", index = False)

#	tf1 = (data['bill_text'][1:2]).apply(lambda x: pandas.value_counts(x.split(" "))) \
#		.sum(axis = 0).reset_index()
#	tf1.columns = ['words', 'tf']

##############################################################################################################################################
##7: OTHER PREPROCESSING ROUND 2 (opp2_)

def opp2_recode_latest_major_action(row):
	res = row['latest_major_action'].lower()
	dlc_substrs = ["hearings held","laid on the table","indefinitely postponed","held at desk","motion to table"]
	if ("became public law" in res) or ("presented to president" in res) or ("signed by president" in res) or ("became private law" in res):
		return "Became law"
	elif "on agreeing to the resolution agreed to by" in res:
		return "Passed; not law (e.g. CR)"
	elif ("placed on senate legislative calendar" in res) or ("received in the senate" in res):
		return "Went to senate"
	elif any(x in res for x in dlc_substrs) or (("referred to the" in res) and ("committee" in res)) or (("motion to proceed" in res) and ("rejected" in res)):
		return "Didn't leave Congress"
	elif ("vetoed by President" in res) or ("veto message" in res):
		return "Vetoed"
	else:
		return "Other"

def opp2_main():
	this = (pandas.read_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Step 6 - Text Processing.csv")).drop("bill_text", axis = 1) \

	this['result'] = this.apply(opp2_recode_latest_major_action, axis = 1)

	this.drop(labels = ["govtrack_url","number","short_title","summary_short","title","dob","district","latest_major_action","latest_major_action_date"], axis = 1) \
		.to_csv("C:/Users/johnr/OneDrive/Spring 2019/INLS 625/Project/Processed with No Text.csv")

def main():
	global headers
	headers = {"X-API-Key":"##censored##"}
#	ppabe_main()	#1: GET PROPUBLICA API BILL-ENDPOINT DATA
#	gt_main()		#2: GET GOVTRACK DATA
#	dwn_main()		#3: GET DW_NOMINATE DATA
#	ppame_main()	#4: GET PROPUBLICA API MEMBER-ENDPOINT DATA
#	opp_main()		#5: OTHER PREPROCESSING
#	tp_main()		#6: TEXT PROCESSING
	opp2_main()		#7: OTHER PREPROCESSING ROUND 2

if __name__ == '__main__':
	main()


