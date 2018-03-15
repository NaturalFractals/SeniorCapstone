import tweepy
import os
import json

class TweepyGrabber:

    def api_connect(self, consumer_key, consumer_secret):
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        api = tweepy.API(auth)
        return api

    def get_users_timeline(self, api, screen_name):
        all_tweets = []
        new_tweets = api.user_timeline(screen_name=screen_name, count=200)
        all_tweets.extend(new_tweets)
        # get the tweet id of the last tweet grabbed to know where to start grabbing
        # the next 200 tweets
        oldest = all_tweets[-1].id - 1
        print("Downloaded ", len(all_tweets), " so far =)")

        while len(new_tweets) > 0:
            new_tweets = api.user_timeline(screen_name=screen_name, count=200, max_id=oldest)
            all_tweets.extend(new_tweets)
            oldest = all_tweets[-1].id - 1
            print("Downloaded ", len(all_tweets), " so far =)")

        json_filename = os.path.dirname(__file__) + "/../data/tweets.json"

        with open(json_filename, 'w') as file:
            json.dump([status._json for status in all_tweets], file)


def main():
    grabber = TweepyGrabber()
    api = grabber.api_connect(os.environ['TWEET_PUB'], os.environ['TWEET_PRI'])
    grabber.get_users_timeline(api, "patrickbeekman")

if __name__ == "__main__":
    main()