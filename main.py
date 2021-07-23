import tweepy
import json
import time
import os
from datetime import datetime
import requests

config = None
api = None
users = None
following_old = None
watchlist = None


def main():
    while True:
        # cleanup irrelevant accounts from watchlist
        if watchlist is not None:
            for user in list(watchlist):
                if datetime.strptime(
                    watchlist[user]["since"], "%Y-%m-%d %H:%M:%S"
                ) < datetime.now() - datetime.timedelta(
                    days=config["relevant_interval_days"]
                ):
                    del watchlist[user]

        # fetch and update info
        following = {}
        variations = {}
        for username in users:
            user = api.get_user(username)
            friend_count = user.friends_count
            if (
                username not in following_old
                or friend_count != following_old[username]["num"]
            ):
                following[username] = {"num": friend_count, "friends": {}}
                for friend in user.friends():
                    following[username]["friends"][friend.screen_name] = {
                        "name": friend.name,
                        "screen_name": friend.screen_name,
                        "since": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if (
                            username not in following_old
                            or friend not in following_old[username]["friends"]
                        )
                        else following_old[username]["friends"][friend]["since"],
                    }
                if username in following_old:
                    variations[username] = {
                        "new_num": following[username]["num"],
                        "old_num": following_old[username]["num"],
                        "new_friends": following[username]["friends"],
                        "old_friends": following_old[username]["friends"],
                    }
                else:
                    variations[username] = {
                        "new_num": following[username]["num"],
                        "old_num": 0,
                        "new_friends": following[username]["friends"],
                        "old_friends": {},
                    }
            else:
                following[username] = following_old[username]
        following_old = following

        # backup following
        with open("following.json", "w") as f:
            json.dump(following_old, f, indent=4)

        # computation of accounts in watchlist
        for username in variations:
            if variations[username]["new_num"] > variations[username]["old_num"]:
                diff = list(
                    set(variations[username]["new_friends"])
                    - set(variations[username]["old_friends"])
                )
                if diff is not None:
                    for friend in diff:
                        if friend in watchlist:
                            watchlist[friend]["num"] += 1
                            watchlist[friend]["followed_by"].append(username)
                        else:
                            watchlist[friend] = {
                                "since": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "num": 1,
                                "announced": False,
                                "followed_by": [username],
                            }

        # send notification
        for usr in watchlist:
            if watchlist[usr]["num"] >= config["min_relevant_followers"]:
                if not watchlist[user]["announced"]:
                    data = {
                        "content": f"@{', @'.join(watchlist[usr]['followed_by'])} started following user @{usr}."
                        f"https://twitter.com/{usr}",
                        "username": "NFT Alpha Bot",
                    }
                    requests.post(config["discord"], json=data)
                    watchlist[usr]["announced"] = True

        # backup watchlist
        with open("watchlist.json", "w") as f:
            json.dump(watchlist, f, indent=4)

        # check again in check_interval seconds
        time.sleep(config["check_interval"])


if __name__ == "__main__":
    config = json.load(open("config.json"))
    auth = tweepy.OAuthHandler(config["api_key"], config["api_secret"])
    auth.set_access_token(config["access_token"], config["access_token_secret"])
    api = tweepy.API(auth, wait_on_rate_limit=True)
    users = json.load(open("config.json"))["twitter"]
    following_old = (
        json.load(open("following.json")) if os.path.exists("following.json") else {}
    )
    watchlist = (
        json.load(open("watchlist.json")) if os.path.exists("watchlist.json") else {}
    )

    main()
