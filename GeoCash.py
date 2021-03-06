from flask import Flask, render_template, request, session, redirect, url_for
from pymongo import Connection
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import urllib
import json
import os
import smtplib
from jinja2 import Environment, PackageLoader
from werkzeug import ImmutableMultiDict
import pdb

env = Environment(loader=PackageLoader('GeoCash', 'templates'))

app = Flask(__name__)
app.config['DEBUG'] = True

try:
	APP_SECRET = os.environ['APP_SECRET']
	FOURSQUARE_CLIENT_ID = os.environ['FOURSQUARE_CLIENT_ID']
	FOURSQUARE_CLIENT_SECRET = os.environ['FOURSQUARE_CLIENT_SECRET']
	VENMO_CLIENT_ID = os.environ['VENMO_CLIENT_ID']
	VENMO_SECRET = os.environ['VENMO_SECRET']
	MONGOHQ_USER = os.environ['MONGOHQ_USER']
	MONGOHQ_PWD = os.environ['MONGOHQ_PWD']
	base_url = 'https://geocash.herokuapp.com'

except:
	# For local testing:
	from geocash_constants import APP_SECRET, FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET, VENMO_CLIENT_ID,VENMO_SECRET, MONGOHQ_USER, MONGOHQ_PWD
	base_url = 'http://www.stupid.com:5000'


did_just_finish = False
mongo_connected = False
user_collection = None
pending_gift_collection = None

AKS = ['66007446','38321450','17788273', '66007856']
# adam: 383...
# AKS = []

foursq_grant_access_base_url = 'https://foursquare.com/oauth2/authenticate?'
foursq_access_token_base_url = 'https://foursquare.com/oauth2/access_token?'
foursq_get_user_id_base_url = 'https://api.foursquare.com/v2/users/self?'
foursq_get_friends_base_url = 'https://api.foursquare.com/v2/users/self/friends?'

new_user_redirect_uri = base_url+'/newuser/'
home_redirect_uri = base_url+'/home/'

add_venmo_redirect_uri = 'https://geocash.herokuapp.com/venmoauth/'

venmo_access_token_base_url = 'https://api.venmo.com/oauth/access_token?'

from_email = 'GetGeoCash@gmail.com'

@app.route('/')
def index():
	if not mongo_connected:
		mongo_connect()

	if ('4sqid' in session) and (session['4sqid'] not in AKS):
		return redirect(url_for('mailing_list'))

	if '4sqid' in session:
		return redirect(url_for('home'))
	else:
		args = {'client_id':FOURSQUARE_CLIENT_ID,
				'response_type':'code',
				'redirect_uri':new_user_redirect_uri}

		auth_url = foursq_grant_access_base_url+urllib.urlencode(args)
		return render_template('index.html', base_url = base_url, foursquare_auth_url=auth_url)

@app.route('/newuser/')
def new_user():
	

	if not mongo_connected:
		mongo_connect()

	if ('4sqid' in session) and (session['4sqid'] not in AKS):
		return redirect(url_for('mailing_list'))

	code = request.args.get('code', '')

	args = {'client_id':FOURSQUARE_CLIENT_ID, 
		'client_secret':FOURSQUARE_CLIENT_SECRET, 
		   'grant_type':'authorization_code', 
		 'redirect_uri':home_redirect_uri,
		 'code':code}
	# return foursq_access_token_base_url+urllib.urlencode(args)
	user_access_token = requests.get(foursq_access_token_base_url+urllib.urlencode(args)).json()['access_token']

	# return foursq_get_user_id_base_url+'oauth_token='+user_access_token+'&v=20130907'

	response = requests.get(foursq_get_user_id_base_url+'oauth_token='+user_access_token+'&v=20130907').json()
	
	firstname =  str(response['response']['user']['firstName'])
	try:
		lastname = str(response['response']['user']['lastName'])
	except:
		lastname = ''
	user_id = response['response']['user']['id']

	session['4sqid']=user_id
	session['4sqtoken']=user_access_token
	session['user_name']=firstname+''+lastname
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

	if ('4sqid' in session) and (session['4sqid'] not in AKS):
		return redirect(url_for('mailing_list'))
	# if 'user_name' not in session:


	#if venmo isn't connected
	if not user_collection.find_one({'4sq_id':session['4sqid']})['venmo_id']:
		args = {'client_id':VENMO_CLIENT_ID, 
					'scope':'make_payments', 
		   	   'response_type':'code'}

		url = venmo_access_token_base_url+urllib.urlencode(args)
		return render_template('venmo-login.html', base_url = base_url, venmo_auth_url=url)

	if 'friend_email' not in session:
		friends = requests.get(foursq_get_friends_base_url+'oauth_token='+session['4sqtoken']+'&v=20130907')
		friends = friends.json()['response']['friends']['items']
		# pdb.set_trace()
		global did_just_finish
		template = env.get_template('pick-friend.html')
		if did_just_finish:
			return template.render(base_url=base_url, friends=friends, showOrNot='block')
			
			did_just_finish = False
		else:
			return template.render(base_url=base_url, friends=friends,showOrNot='none')
	
	elif 'chosen_venue' not in session:
		return render_template('pick-venue.html', base_url=base_url)

	else:
		return render_template('create-payment.html', base_url=base_url)

@app.route('/add_friend',methods=['GET'])
def add_friend():
	if ('4sqid' in session) and (session['4sqid'] not in AKS):
		return redirect(url_for('mailing_list'))

	friend_id = request.args.get('friend_4sq_id', '')
	friend_name = request.args.get('friend_name', '')
	friend_email = request.args.get('friend_email','')

	# pdb.set_trace()

	session['friend_4sq_id']=friend_id
	session['friend_name']=friend_name
	session['friend_email']=friend_email
	return redirect(url_for('home'))

@app.route('/add_venue/',methods=['GET'])
def add_venue():
	if ('4sqid' in session) and (session['4sqid'] not in AKS):
		return redirect(url_for('mailing_list'))
	venue_id = request.args.get('venue_id', '')
	session['chosen_venue']=venue_id
	return redirect(url_for('home'))

@app.route('/add_pending_payment/', methods=['GET'])
def add_pending_payment():
	if ('4sqid' in session) and (session['4sqid'] not in AKS):
		return redirect(url_for('mailing_list'))
	
	note = request.args.get('note', '')
	
	print 'THIS BE MY NOTE: '+str(note)


	amount = request.args.get('amount', '')

	
	payment_info= 'NEW PAYMENT: '+session['friend_name']+'  '+session['friend_email']+' '+session['chosen_venue']+'  '+note+' '+amount

	pending_payment = {'recipient_id':session['friend_4sq_id'], 
						  'sender_id':session['4sqid'],
						   'venue_id':session['chosen_venue'],
						   'amount':amount,
						   'note':note}

	pending_gift_collection.insert(pending_payment)

	send_notification_email(session['user_name'],session['friend_name'],session['friend_email'], session['chosen_venue'], note, amount)

	session.pop('chosen_venue', None)
	session.pop('friend_4sq_id', None)
	session.pop('friend_name', None)
	session.pop('user_name', None)
	session.pop('friend_email',None)
	
	global did_just_finish
	did_just_finish = True
	return redirect(url_for('home'))

def send_notification_email(sender_name, toName, recipient_email, venue_id, note, amount):
	if ('4sqid' in session) and (session['4sqid'] not in AKS):
		return redirect(url_for('mailing_list'))

	msg = MIMEMultipart('alternative')
	msg['Subject'] = "You've received a GeoCash from a Foursquare friend!"
	msg['From'] = from_email
	msg['To'] = recipient_email
	venue_response = requests.get('https://api.foursquare.com/v2/venues/'+venue_id+'?oauth_token='+session['4sqtoken']+'&v=20130907').json()
	venue_name = venue_response['response']['venue']['name']

	text = "Hi " + toName + ",\n Your \
		friend " + sender_name + " sent you a GeoCash gift! It's waiting for you \
		at " + venue_name + ".\n" + sender_name + ": " + note + "\n\n" + "Go to http://geoca.sh \
		to authenticate GeoCash with Foursquare so you can claim the payment on Venmo when you \
		check in there.\n Authenticating will let GeoCash know when you check in at a place \
		where a friend has left you a payment. Once you check in on Foursquare, we'll pass \
		along " +sender_name + "'s gift on Venmo.\n"

	html = """\n
		<html>
			<head></head>
			<body>
				Hi %s,<br>
				Your friend %s sent you a GeoCash gift!<br>
				It's waiting for you at %s.<br>
				<p style="font-size:large;">%s: <b>%s</b></p>
				Click <a target="_blank" href="http://geoca.sh/">here</a> to let GeoCash know
				when you check in at a place where a friend has left you a payment. Once
				you check in on <a target="_blank" href="http://www.foursquare.com">Foursquare</a>, we'll
				pass along %s's gift on <a target="_blank" href="http://www.venmo.com">
				Venmo</a>.<br>
			</body>
		</html>
		""" %(toName, sender_name, venue_name, sender_name, note, sender_name)

	# Login creds
	username = 'GeoCash'
	password = "pennappscolumbia1"

	# Record the MIME types of both part - text/plain and text/html
	part1 = MIMEText(text, 'plain')
	part2 = MIMEText(html, 'html')

	# Attach parts into message container
	msg.attach(part1)
	msg.attach(part2)

	s = smtplib.SMTP('smtp.sendgrid.net', 587)
	s.login(username, password)


	s.sendmail(from_email, recipient_email, msg.as_string())

	s.quit()


@app.route('/mailing_list/', methods=['GET'])
def mailing_list(): 
	add = str(request.args.get('add',''))

	template = env.get_template('mailing_list.html')

	if add=='true':
		user_collection.update({'4sq_id':session['4sqid']},{'$set':{'email_me':'True'}})
		return template.render(base_url=base_url, showOrNot='block')
	else:
		return template.render(base_url=base_url, showOrNot='none')



@app.route('/venmoauth/', methods=['GET'])
def add_venmo_token():
	if ('4sqid' in session) and (session['4sqid'] not in AKS):
		return redirect(url_for('mailing_list'))

	code = str(request.args.get('code', ''))


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
	session.pop('friend_4sq_id', None)
	session.pop('friend_name', None)
	session.pop('user_name', None)
	session.pop('friend_email',None)

	print 'Logged out!'
	return redirect(url_for('index'))

@app.route('/faq/', methods = ['GET'])
def faq():
	return render_template('faq.html')

@app.route('/push/', methods=['POST'])
def dummy_push():
	if not mongo_connected:
		mongo_connect()
	recip_id = str(json.loads(request.form['user'])['id'])
	venue_id = str(json.loads(request.form['checkin'])['venue']['id'])

	gift_to_process = pending_gift_collection.find_one({'recipient_id':recip_id,'venue_id':venue_id})

	if(gift_to_process):
		sender_venmo_token = user_collection.find_one({'4sq_id':gift_to_process['sender_id']})['venmo_token']


		recip_4sq_token = user_collection.find_one({'4sq_id':recip_id})['4sq_token']


		response = requests.get(foursq_get_user_id_base_url+'oauth_token='+recip_4sq_token+'&v=20130907').json()

		recip_email = response['response']['user']['contact']['email']

		note = gift_to_process['note']
		amount = gift_to_process['amount']


		pending_gift_collection.remove(gift_to_process)
		initiate_payment(sender_venmo_token, recip_email, note, amount)
	else:
		return '200 okay'

def initiate_payment(sender_token, recip_email, note, amount):

	data = {
		'access_token':sender_token,
		'email':recip_email,
		'note':note,
		'amount':amount
	}

	url = 'https://api.venmo.com/payments'
	response = requests.post(url,data)


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