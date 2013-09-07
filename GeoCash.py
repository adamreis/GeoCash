from flask import Flask, render_template, request, session, redirect, url_for
from pymongo import Connection
# from geocash_constants import APP_SECRET, FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET 
import requests
import urllib
import os

app = Flask(__name__)

APP_SECRET = os.environ['APP_SECRET']

FOURSQUARE_CLIENT_ID = os.environ['FOURSQUARE_CLIENT_ID']
FOURSQUARE_CLIENT_SECRET = os.environ['FOURSQUARE_CLIENT_SECRET']
MONGOHQ_USER = os.environ['MONGOHQ_USER']
MONGOHQ_PWD = os.environ['MONGOHQ_PWD']

mongo_connected = False
user_collection = None
pending_gift_collection = None

foursq_access_token_base_url = 'https://foursquare.com/oauth2/access_token?'
foursq_grant_access_base_url = 'https://foursquare.com/oauth2/authenticate?'
foursq_get_user_id_base_url = 'https://api.foursquare.com/v2/users/self?'
home_redirect_uri = 'https://geocash.herokuapp.com/home/'
new_user_redirect_uri = 'https://geocash.herokuapp.com/newuser/'

@app.route('/')
def index():
	if not mongo_connected:
		mongo_connect()

	if '4sqid' in session:
		return redirect(url_for('home'))
	else:
		args = {'client_id':FOURSQUARE_CLIENT_ID,
				'response_type':'code',
				'redirect_uri':new_user_redirect_uri}

		auth_url = foursq_grant_access_base_url+urllib.urlencode(args)
		return render_template('index.html', foursquare_auth_url=auth_url)

@app.route('/newuser/')
def new_user():
	if not mongo_connected:
		mongo_connect()

	code = request.args.get('code', '')
	print 'CODE: '+str(code)
	args = {'client_id':FOURSQUARE_CLIENT_ID, 
		'client_secret':FOURSQUARE_CLIENT_SECRET, 
		   'grant_type':'authorization_code', 
		 'redirect_uri':home_redirect_uri,
		 'code':code}
	# return foursq_access_token_base_url+urllib.urlencode(args)
	user_access_token = requests.get(foursq_access_token_base_url+urllib.urlencode(args)).json()['access_token']
	
	print 'ACCESS TOKEN: '+user_access_token
	# return foursq_get_user_id_base_url+'oauth_token='+user_access_token+'&v=20130907'

	response = requests.get(foursq_get_user_id_base_url+'oauth_token='+user_access_token+'&v=20130907').json()
	user_id = response['response']['user']['id']

	session['4sqid']=user_id
	session['4sqtoken']=user_access_token
	print 'Logged in!'
#TODO: add them to our database of users

	return redirect(url_for('home'))

@app.route('/home/', methods=['GET'])
def home():
	if not mongo_connected:
		mongo_connect()

	if '4sqid' not in session:
		return redirect(url_for('index'))

	return render_template('home.html')

@app.route('/logout/', methods=['GET'])
def logout():
	session.pop('4sqid', None)
	session.pop('4sqtoken', None)
	print 'Logged out!'
	return redirect(url_for('index'))

@app.route('/push/', methods=['POST'])
def dummy_push():
	if not mongo_connected:
		mongo_connect()

	print 'request:'
	print request.form
	return '200 OK'

def mongo_connect():
	print 'mongo connect called'
	global mongo_connected, user_collection, pending_gift_collection
	host = 'paulo.mongohq.com'
	port = 10014
	dbName = 'GeoCash'

	connection = Connection(host,port)
	db = connection[dbName]

	db.authenticate(MONGOHQ_USER, MONGOHQ_PWD)

	user_collection = db.users
	pending_gift_collection = db.pending_gifts
	test_data = {'one plus one':'two', 'two plus two':'four'}
	pending_gift_collection.insert(test_data)
	mongo_connected = True

# app.wsgi_app = ProxyFix(app.wsgi_app)

app.secret_key = APP_SECRET


if __name__ == '__main__':
	app.run(port=5000,debug=True)