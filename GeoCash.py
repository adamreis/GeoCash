from flask import Flask, render_template, request, session, redirect, url_for
# from geocash_constants import APP_SECRET, FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET 
import requests
import urllib
import os

app = Flask(__name__)

APP_SECRET = os.environ['APP_SECRET']
print 'app secret: '+APP_SECRET
FOURSQUARE_CLIENT_ID = os.environ['FOURSQUARE_CLIENT_ID']
FOURSQUARE_CLIENT_SECRET = os.environ['FOURSQUARE_CLIENT_SECRET']



foursq_access_token_base_url = 'https://foursquare.com/oauth2/access_token?'
foursq_grant_access_base_url = 'https://foursquare.com/oauth2/authenticate?'
home_redirect_uri = 'https://geocash.herokuapp.com/home/'
new_user_redirect_uri = 'https://geocash.herokuapp.com/newuser/'

@app.route('/')
def index():
	print 'test point 1'
	if '4sqid' in session:
		print 'shouldn\'t be here'
		return redirect(url_for('home'))
	else:
		args = {'client_id':FOURSQUARE_CLIENT_ID,
				'response_type':'code',
				'redirect_uri':new_user_redirect_uri}

		auth_url = foursq_grant_access_base_url+urllib.urlencode(args)
		print 'this is the auth url.  we havent crashed yet: '+auth_url
		return render_template('index.html', foursquare_auth_url=auth_url)

@app.route('/newuser/')
def new_user():
	code = request.args.get('code', '')
	print 'CODE: '+str(code)
	args = {'client_id':FOURSQUARE_CLIENT_ID, 
		'client_secret':FOURSQUARE_CLIENT_SECRET, 
		   'grant_type':'authorization_code', 
		 'redirect_uri':home_redirect_uri,
		 'code':code}
	return foursq_access_token_base_url+urllib.urlencode(args)
	# token = json.loads(requests.get(foursq_access_token_base_url+urllib.urlencode(args)))['access_token']

	# return 'TOKEN: '+token


@app.route('/home/', methods=['GET'])
def home():
	if '4sqid' not in session:
		return redirect(url_for('index'))




@app.route('/push/', methods=['POST'])
def dummy_push():
	print 'request:'
	print request.form
	return '200 OK'


# app.wsgi_app = ProxyFix(app.wsgi_app)

app.secret_key = APP_SECRET


if __name__ == '__main__':
	app.run(port=7777,debug=True)