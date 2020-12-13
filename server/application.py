from flask import Flask
from Checker import Checker
from Fixer import Fixer
import requests
from flask import request

app = Flask(__name__)

@app.route('/find-errors/<url>')
def find_errors(url):

    checker = Checker()
    
    return "finding errors! for %s" % url
    
@app.route('/')
def index():
    return "hello world!"
    
@app.route('/find-and-fix')
def find_and_fix():
    
    url = request.args.get('url')
    
    checker = Checker()
    fixer   = Fixer()
    
    # get the errors
    # TODO: THIS IS JUST FOR TESTING
    errors = checker.check_with_save(url)
    
    id = errors[0]['site_id']
    filename = 'data/%d.html' % id
    with open(filename, 'r', encoding='utf-8') as fo:
        html = fo.read()
    
    # END TESTING
    # errors = checker.check(url)
    # html = requests.get(url)
    
    # fix as many errors as possible
    better_html = fixer.fix_all(errors, html)

    return better_html


@app.route('/fix')
def fix():
    return "fixing this one issue!"
    
    
if __name__ == "__main__":
    
    app.run(debug=True)