#from fuzzymatcher import link_table, fuzzy_left_join
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import pandas as pd

#with open('Alaska Center - PMC Data.csv', 'r') as file:
#    alaska_pmc = file.readlines()
#
#with open('Alaska Center - Property Data.csv', 'r') as file:
#    alaska_property = file[1:].readlines()
#

def fuzzy_merge(df_1, df_2, key1, key2, threshold=90, limit=2):
    """
    :param df_1: the left table to join
    :param df_2: the right table to join
    :param key1: key column of the left table
    :param key2: key column of the right table
    :param threshold: how close the matches should be to return a match, based on Levenshtein distance
    :param limit: the amount of matches that will get returned, these are sorted high to low
    :return: dataframe with boths keys and matches
    """
    s = df_2[key2].tolist()
    
    m = df_1[key1].apply(lambda x: process.extract(x, s, limit=limit))    
    df_1['matches'] = m
    
    m2 = df_1['matches'].apply(lambda x: ', '.join([i[0] for i in x if i[1] >= threshold]))
    df_1['matches'] = m2
    
    return df_1

alaska_pmc = pd.read_csv('Alaska Center - PMC Data.csv', skiprows=1)
alaska_property = pd.read_csv('Alaska Center - Property Data.csv', skiprows=1)

#print(alaska_pmc)
#print(alaska_property)
match = fuzzy_merge(alaska_pmc, alaska_property, 'Combined', 'Reference', threshold=90, limit=2)
print(match)

for thresh in [80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99]:
    num_matches = 0
    match = fuzzy_merge(alaska_pmc, alaska_property, 'Combined', 'Reference', threshold=thresh, limit=2)
    for x in match['matches']:
        if x != '':
            num_matches+=1
    print('Threshold: '+str(thresh)+' Number Matches: '+str(num_matches))

#match.to_csv('fuzzy_match.csv', index=False)