import tweepy
import json
import time
import os
from datetime import datetime

config = None
api = None
users = None
following_old = None
relevant = None


def main():
    while True:
        # cleanup irrelevant accounts from watchlist
        if relevant is not None:
            for user in list(relevant):
                if datetime.strptime(
                    relevant[user]["since"], "%Y-%m-%d %H:%M:%S"
                ) < datetime.now() - datetime.timedelta(
                    days=config["relevant_interval_days"]
                ):
                    del relevant[user]

        # update info
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

        with open("following.json", "w") as f:
            json.dump(following, f, indent=4)

        # computation of relevant accounts
        for usr in variations:
            if variations[usr]["new_num"] > variations[usr]["old_num"]:
                diff = list(
                    set(variations[usr]["new_friends"])
                    - set(variations[usr]["old_friends"])
                )
                if diff is not None:
                    for friend in diff:
                        if friend in relevant:
                            relevant[friend]["num"] += 1
                            relevant[friend]["followed_by"].append(usr)
                        else:
                            relevant[friend] = {
                                "since": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "num": 1,
                                "announced": False,
                                "followed_by": [usr],
                            }

        # announcement
        for usr in relevant:
            if relevant[usr]["num"] >= config["min_relevant_followers"]:
                if not relevant[user]["announced"]:
                    print(
                        f"{relevant[usr]['followed_by']} started following user {usr}"
                    )
                    relevant[usr]["announced"] = True

        with open("relevant.json", "w") as f:
            json.dump(relevant, f, indent=4)

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
    following_old = (
        json.load(open("relevant.json")) if os.path.exists("relevant.json") else {}
    )

    main()
