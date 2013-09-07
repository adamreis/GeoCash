from flask import Flask, render_template, request, session, redirect, url_for
from geocash_constants import APP_SECRET, FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET 
import requests
import urllib

app = Flask(__name__)

foursq_access_base_url = 'https://foursquare.com/oauth2/access_token/?'
redirect_uri = 'https://geocash.herokuapp.com/home/'

@app.route('/')
def index():
	if '4sqid' in session:
		return redirect(url_for('home'))
	else:
	# return render_template('index.html')

@app.route('/newuser/')
def new_user():
	code = request.args.get('code', '')
	print 'CODE: '+str(code)
	args = {'client_id':FOURSQUARE_CLIENT_ID, 
		'client_secret':FOURSQUARE_CLIENT_SECRET, 
		   'grant_type':'authorization_code', 
		 'redirect_uri':redirect_uri,
		 'code':code}

	token = json.loads(requests.get(foursq_access_base_url+urllib.urlencode(args)))['access_token']

	return 'TOKEN: '+token


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