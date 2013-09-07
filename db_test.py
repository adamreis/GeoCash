from geocash_constants import MONGOHQ_USER, MONGOHQ_PWD
from pymongo import Connection


host = 'paulo.mongohq.com'
port = 10014
dbName = 'GeoCash'

connection = Connection(host,port)
db = connection[dbName]

db.authenticate(MONGOHQ_USER, MONGOHQ_PWD)

test_collection = db.test

test_data = {'one plus one':'two', 'two plus two':'four'}
test_collection.insert(test_data)

test_collection.find_one({'two plus two':'four'})