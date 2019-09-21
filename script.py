import requests as r

r.get('https://donut-bot.herokuapp.com/donut')

print(r.json())
