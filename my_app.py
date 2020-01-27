from flask import Flask, jsonify, request, make_response
import requests as r
from collections import Counter
import os
from tabulate import tabulate
from datetime import datetime, timedelta
import re

try:
    from passwords import BEARER, SLACK_TOKEN, SLACK_OAUTH_ACESS_TOKEN
except:
    BEARER = os.environ['BEARER']
    SLACK_TOKEN = os.environ['SLACK_TOKEN']
    SLACK_OAUTH_ACESS_TOKEN = os.environ['SLACK_OAUTH_ACESS_TOKEN']


class Airtable(object):
    def __init__(self):
        self.headers = {'Authorization': BEARER,
                        'Content-Type': 'application/json'}
        self.base_url = "https://api.airtable.com/v0/apphBP3YhZKaBIYti/donuts"
        self.entries = self.get_all()

    def get_all(self):
        params = {'view': 'sorted'}
        return r.get(self.base_url, headers=self.headers, params=params).json()['records']

    def last_entry_per_donut(self):
        latest = {}
        for entry in self.entries:
            donut = entry['fields']['donut']
            try:
                latest[donut]
            except KeyError:
                latest[donut] = entry
        return latest

    def get_owe(self):
        owes = []
        for entry in self.last_entry_per_donut().values():  # TODO should I keep the user_id as a dict to make it easy to find if someone owes?
            fields = entry['fields']
            if fields['event_type'] == 'donutted':
                owes += [(fields['donut'], fields['user_name'], fields['created'])]
        return owes

    def create_entry(self, donut, user_name='', event_type='donutted'):
        """
        event_type can be either 'donutted' or 'brought' everything else will error from Airtable
        """
        self._validate_entry(donut, user_name, event_type)
        payload = {
            "records": [{'fields': {'donut': donut, 'user_name': user_name, 'event_type': event_type}}]
        }
        return r.post(self.base_url, headers=self.headers, json=payload).json()

    def donuts(self):
        names = [entry['fields']['display_name'] for entry in self.entries]
        return names

    def latest(self):
        names = self.donuts()
        return names[0]

    def hall_of_shame(self):
        names = self.donuts()
        return Counter(names).most_common()

    def _validate_entry(self, donut, user_name, event_type):
        if event_type == 'donutted':
            match_time = False
            for d in self.entries:
                if d['fields']['donut'] == donut:
                    match_time = datetime.fromisoformat(d['createdTime'][:-1])
                    break
            if match_time:
                acceptable_start = datetime.utcnow() - timedelta(minutes=5)
                if match_time > acceptable_start:
                    raise ValueError('User donutted too soon')

        elif event_type == 'brought':
            for owe_donut, owe_user_name, _ in self.get_owe():
                if (donut == owe_donut) and (user_name == owe_user_name):
                    break
            else:
                raise ValueError('Person reported does not seem to owe donuts')

        else:
            raise Exception('Invalid event_type')


a = Airtable()

app = Flask(__name__)


@app.route("/")
def home():
    return 'hello from the app'


@app.route("/donut", methods=['GET', 'POST'])
def donut_api():
    if request.headers['Authorization'] != a.headers['Authorization']:
        return jsonify({"message": "No"}), 401

    if request.method == 'GET':
        response = a.get_owe()

    elif request.method == 'POST':
        body = request.get_json()
        try:
            response = a.create_entry(**body)
        except ValueError:
            response = {'message': 'Nah'}

    else:
        response = a.hall_of_shame()
    return jsonify(response)


@app.route("/slack", methods=['POST'])
def donut():
    if request.form['token'] != SLACK_TOKEN:
        return jsonify({'message': 'Nope'}), 401

    text = request.form['text']
    user_id = f'<@{request.form["user_id"]}>'
    user_name = request.form["user_name"]

    bringer_id = re.search(r'<@[^|>]*|$', text).group()
    if bringer_id:
        bringer_id += '>'
    bringer_name = re.search(r'\|[^>]*>|$', text).group()[1:-1]

    if text == 'me':
        try:
            a.create_entry(user_id, user_name)
            out = f'''{":doughnut:" * 11}\n:doughnut:{user_id} has been donutted!!:doughnut:\n{":doughnut:" * 11}'''
        except ValueError:
            out = 'Please wait a bit before donutting again'

    elif text == 'shame':
        latest = a.latest()
        shame = a.hall_of_shame()
        # TODO owe = a.get_owe() add to out if len(owe) > 0. maybe give how long its been outstanding?
        table = tabulate(shame, tablefmt="simple", headers=['Donut', '#'])
        out = f'''```Welcome to the Hall of Shame!\n\nThe last person to get donutted was {latest}.\n\n{table}```'''

    elif bringer_id:
        if request.form['user_id'] in bringer_id:
            out = "Are you sure that you brought donuts? Maybe ask someone else to vouch for you :p"
        else:
            try:
                a.create_entry(bringer_id, bringer_name, 'brought')
                out = f'''{user_id} reports that {bringer_id} has brought donuts!'''
            except ValueError:
                out = 'It doesnt seem like that person owes donuts'

    else:
        out = ''':wave: Hi there, here is how you can use Donut Bot\n>`/donut me` to donut someone\n>`/donut shame` to see the Donut Hall of Shame'''

    payload = {
        "channel": "CLDHP8ZU7",
        "text": out
    }
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {SLACK_OAUTH_ACESS_TOKEN}"
    }
    r.post(url, headers=headers, json=payload)

    response = {
        "response_type": "ephemeral",
        "text": "check #random for response"
    }
    return jsonify(response)
