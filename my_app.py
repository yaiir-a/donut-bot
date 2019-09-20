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
        self.resp = r.get(self.base_url, headers=self.headers, params=params)
        return self.resp.json()

    def create_entry(self, donut):
        payload = {
            "records":[{'fields':{'donut':donut}}]
        }
        self.resp = r.post(self.base_url, headers=self.headers, json=payload)
        return self.resp.json()

    def donuts(self):
         entries = self.get_all()
         names = [entry['fields']['donut'] for entry in entries['records']]
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

@app.route("/donut_api", methods=['GET', 'POST'])
def donut_api():
    if request.method == 'POST':
        body = request.get_json()
        resp = a.create_entry(body['donut'])
        return jsonify(resp)
    else:
        return jsonify(a.hall_of_shame())

@app.route("/donut", methods=['POST'])
def donut():
    text = request.form['text']
    user_id = f'<@{ request.form["user_id"] }>'

    if text == 'me':
        a.create_entry(user_id)
        out = f'{user_id} has been donutted!!'
    elif text == 'shame':
        shame = a.hall_of_shame()
        out = f'```{tabulate(shame, tablefmt="simple")}```'
    else:
        out = 'use /donut me to donut someone or /donut shame to see the shame board'

    response = {
            "response_type": "in_channel",
            "text": out
    }
    return jsonify(response)






if __name__ == "__main__":
    app.run(debug=True)
