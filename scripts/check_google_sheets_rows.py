import requests
url = 'https://script.google.com/macros/s/AKfycbxzWKi1dNiGUiF15Ysl_69Pe2dt2vUpe1UBQ9xadPenmnsH68VOk6W1ZMwhRQkRpkBX/exec'
r = requests.get(url, timeout=20)
items = r.json()
print('Total rows in sheet:', len(items))
for idx, it in enumerate(items):
    print(f"Row {idx+2}: {it.get('data')} | {it.get('partida')} | {it.get('canal')}")
