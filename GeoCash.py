from flask import Flask, render_template, request, session, redirect, url_for
from pymongo import Connection
# from geocash_constants import APP_SECRET, FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET 
import requests
import urllib
import os
# from jinja import Template, Context, FileSystemLoader
from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('GeoCash', 'templates'))

app = Flask(__name__)

APP_SECRET = os.environ['APP_SECRET']

FOURSQUARE_CLIENT_ID = os.environ['FOURSQUARE_CLIENT_ID']
FOURSQUARE_CLIENT_SECRET = os.environ['FOURSQUARE_CLIENT_SECRET']
VENMO_CLIENT_ID = os.environ['VENMO_CLIENT_ID']
VENMO_SECRET = os.environ['VENMO_SECRET']
MONGOHQ_USER = os.environ['MONGOHQ_USER']
MONGOHQ_PWD = os.environ['MONGOHQ_PWD']

mongo_connected = False
user_collection = None
pending_gift_collection = None

foursq_grant_access_base_url = 'https://foursquare.com/oauth2/authenticate?'
foursq_access_token_base_url = 'https://foursquare.com/oauth2/access_token?'
foursq_get_user_id_base_url = 'https://api.foursquare.com/v2/users/self?'
foursq_get_friends_base_url = 'https://api.foursquare.com/v2/users/self/friends?'

home_redirect_uri = 'https://geocash.herokuapp.com/home/'
new_user_redirect_uri = 'https://geocash.herokuapp.com/newuser/'
add_venmo_redirect_uri = 'https://geocash.herokuapp.com/venmoauth/'
venmo_grant_access_base_url = 'https://api.venmo.com/oauth/authorize?'
venmo_access_token_base_url = 'https://api.venmo.com/oauth/access_token?'

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
	print "FIND NAME:"
	return response['response']['user']
	user_id = response['response']['user']['id']

	session['4sqid']=user_id
	session['4sqtoken']=user_access_token
	print 'Logged in!'
	
	existing_user = user_collection.find_one({'4sq_id':user_id})
	
	if not existing_user:
		# add user to database
		user = {'4sq_id':user_id, 
			 '4sq_token':user_access_token, 
			  'venmo_id':None, 
		   'venmo_token':None,
		   'pending_gifts':[]}

		user_collection.insert(user)

	return redirect(url_for('home'))

@app.route('/home/', methods=['GET'])
def home():
	if not mongo_connected:
		mongo_connect()

	if '4sqid' not in session:
		return redirect(url_for('index'))

	# if 'user_name' not in session:


	#if venmo isn't connected
	if not user_collection.find_one({'4sq_id':session['4sqid']})['venmo_id']:
		args = {'client_id':VENMO_CLIENT_ID, 
					'scope':'make_payments', 
		   	   'response_type':'code'}

		url = venmo_grant_access_base_url+urllib.urlencode(args)
		return render_template('venmo-login.html', venmo_auth_url=url)

	if 'friend_email' not in session:
		friends = requests.get(foursq_get_friends_base_url+'oauth_token='+session['4sqtoken']+'&v=20130907')
		friends = friends.json()['response']['friends']['items']

		template = env.get_template('pick-friend.html')
		return template.render(friends=friends)
	
	elif 'chosen_venue' not in session:
		return render_template('pick-venue.html')

	else:
		return render_template('create-payment.html')

@app.route('/add_friend',methods=['GET'])
def add_friend():
	friend_email = request.args.get('friend_email', '')
	friend_name = request.args.get('friend_name', '')
	session['friend_email']=friend_email
	session['friend_name']=friend_name
	return redirect(url_for('home'))

@app.route('/add_venue/',methods=['GET'])
def add_venue():
	venue_id = request.args.get('venue_id', '')
	session['chosen_venue']=venue_id
	return redirect(url_for('home'))

@app.route('/add_pending_payment/', methods=['GET'])
def add_pending_payment():
	note = request.args.get('note', '')
	amount = request.args.get('amount', '')

	payment_info ='NEW PAYMENT: '+session['friend_name']+'  '+session['friend_email']+'  '+session['chosen_venue']+'  '+note+' '+amount

	return payment_info



@app.route('/venmoauth/', methods=['GET'])
def add_venmo_token():
	code = str(request.args.get('code', ''))
	print 'CODE: '+code

	args = {'client_id':VENMO_CLIENT_ID, 
		'client_secret':VENMO_SECRET, 
		 		 'code':code}
	# return str(args)
	# return venmo_access_token_base_url+urllib.urlencode(args)

	response= requests.post(venmo_access_token_base_url+urllib.urlencode(args)).json()
	user_venmo_access_token = response['access_token']
	venmo_user_id = response['user']['id']

	session['venmoid']=venmo_user_id
	session['venmotoken']=user_venmo_access_token

	user_4sq_id = session['4sqid']

	user_collection.update({'4sq_id':user_4sq_id},
				 {'$set':{'venmo_id':venmo_user_id, 
					   'venmo_token':user_venmo_access_token}})

	return redirect(url_for('home'))

@app.route('/logout/', methods=['GET'])
def logout():
	session.pop('4sqid', None)
	session.pop('4sqtoken', None)
	session.pop('chosen_venue', None)
	session.pop('friend_email', None)
	session.pop('friend_name', None)

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
	mongo_connected = True

# app.wsgi_app = ProxyFix(app.wsgi_app)

app.secret_key = APP_SECRET


if __name__ == '__main__':
	app.run(port=5000,debug=True)