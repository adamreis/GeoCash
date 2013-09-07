from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def main_page():
	return render_template('index.html')


# app.wsgi_app = ProxyFix(app.wsgi_app)

if __name__ == '__main__':
	app.run(port=7777,debug=True)