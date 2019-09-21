from flask import Flask, jsonify, request, make_response
import requests as r
from collections import Counter
import os
from tabulate import tabulate

try:
    from passwords import BEARER
except:
    BEARER = os.environ['BEARER']

class Airtable(object):
    def __init__(self):
        self.headers = {'Authorization': BEARER,
                       'Content-Type': 'application/json'}
        self.base_url = "https://api.airtable.com/v0/apphBP3YhZKaBIYti/donuts"

    def get_all(self):
        params = {'view':'sorted'}
        return r.get(self.base_url, headers=self.headers, params=params).json()

    def create_entry(self, donut, user_name=''):
        payload = {
            "records":[{'fields':{'donut':donut, 'user_name':user_name}}]
        }
        return r.post(self.base_url, headers=self.headers, json=payload).json()

    def donuts(self):
         entries = self.get_all()
         names = [entry['fields']['display_name'] for entry in entries['records']]
         return names

    def latest(self):
         names = self.donuts()
         return names[0]

    def hall_of_shame(self):
         names = self.donuts()
         return Counter(names).most_common()

a = Airtable()

app = Flask(__name__)

@app.route("/")
def home():
    return 'hello from the app'

@app.route("/donut", methods=['GET', 'POST'])
def donut_api():
    if request.method == 'POST':
        body = request.get_json()
        response = a.create_entry(**body)
    else:
        response = a.hall_of_shame()
    return jsonify(response)

@app.route("/slack", methods=['POST'])
def donut():
    text = request.form['text']
    user_id = f'<@{ request.form["user_id"] }>'
    user_name = request.form["user_name"]

    if text == 'me':
        a.create_entry(user_id, user_name)
        out = f'''{":doughnut:" * 11}\n:doughnut:{user_id} has been donutted!!:doughnut:\n{":doughnut:" * 11}'''
    elif text == 'shame':
        latest = a.latest()
        shame = a.hall_of_shame()
        table = tabulate(shame, tablefmt="simple", headers=['Donut', '#'])
        out = f'''```Welcome to the Hall of Shame!\nThe last person to get donutted was {latest}.\n{table}```'''
    else:
        out = ''':wave: Hi there, here is how you can use Donut Bot\n>`/donut me` to donut someone\n>`/donut shame` to see the Donut Hall of Shame'''

    response = {
            "response_type": "in_channel",
            "text": out
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
