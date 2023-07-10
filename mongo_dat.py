import persist

DEBUG = False

PersistKV = persist.persistKV('data.sqlite3')
mock_data = {
    'data': PersistKV('data'),
    'get_keyword_row': dict(PersistKV('get_keyword_row')),
    'keyword_log_search': dict(PersistKV('keyword_log_search')),
    'adreport_search': dict(PersistKV('adreport_search')),
    'amazon_keyword_search': dict(PersistKV('amazon_keyword_search')),
    'amazon_adreport_search': dict(PersistKV('amazon_adreport_search')),
    'cid_gross_profit': dict(PersistKV('cid_gross_profit'),)
}

import pymongo

myclient = pymongo.MongoClient('mongodb://localhost:27017/')

mydb = myclient['AdLog']

# mycol = mydb["cid_gross_profit"]

# for key in mock_data['cid_gross_profit'].keys():
#     mycol.insert_one({
#         'cid': key,
#         'gross_profit': mock_data['cid_gross_profit'][key],
#         'amazon_keyword_search': mock_data['amazon_keyword_search'][key],
#         'amazon_adreport_search': mock_data['amazon_adreport_search'][key],
#     })
mycol = mydb["amazon_adreport_search"]
# for key in mock_data['cid_gross_profit'].keys():
#     for entry in mock_data['amazon_adreport_search'][key]:
#         temp = entry
#         temp['cid'] = key
#         temp['cid_gross_profit'] = mock_data['cid_gross_profit'][key]
#         mycol.insert_one(temp)
        

print()
