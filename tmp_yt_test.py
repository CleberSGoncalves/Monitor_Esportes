import requests
import json
import os

def test_yt_api():
    cfg_path = r"E:\desenvolvimento\Monitor_Esportes\config\google_ai.json"
    with open(cfg_path, "r") as f:
        cfg = json.load(f)
    
    api_key = cfg.get("api_key")
    handle = "@CazeTV"
    
    # 1. Get Channel ID
    url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={handle}&key={api_key}"
    res = requests.get(url)
    print(f"Channels Response: {res.status_code}")
    print(res.text)
    
    if res.status_code == 200:
        data = res.json()
        if "items" in data and len(data["items"]) > 0:
            channel_id = data["items"][0]["id"]
            print(f"Found Channel ID: {channel_id}")
            
            # 2. Search for videos (including past streams)
            # This is just a test for the key
            url_search = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&maxResults=5&order=date&type=video&key={api_key}"
            res_search = requests.get(url_search)
            print(f"Search Response: {res_search.status_code}")
            # print(res_search.text)

if __name__ == "__main__":
    test_yt_api()
