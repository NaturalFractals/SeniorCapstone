import tweepy
import pandas as pd
import time
import sys
import os
import json

class TweepyGrabber:
    api = None

    def __init__(self):
        self.api = self.api_connect(os.environ['TWEET_PUB'], os.environ['TWEET_PRI'])

    def api_connect(self, consumer_key, consumer_secret):
        try:
            auth = tweepy.AppAuthHandler(consumer_key, consumer_secret)
        except tweepy.TweepError as e:
            print(e)
            exit(1)
        api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, compression=True)
        return api

    def get_users_timeline(self, screen_name, output_file_name):
        all_tweets = []
        try:
            new_tweets = self.api.user_timeline(screen_name=screen_name, count=200)
        except Exception as e:
            print("Error accessing usertimeline:", e.message)
        all_tweets.extend(new_tweets)
        # get the tweet id of the last tweet grabbed to know where to start grabbing
        # the next 200 tweets
        oldest = all_tweets[-1].id - 1
        print("Downloaded ", len(all_tweets), " so far =)")

        while len(new_tweets) > 0:
            new_tweets = self.api.user_timeline(screen_name=screen_name, count=200, max_id=oldest)
            all_tweets.extend(new_tweets)
            oldest = all_tweets[-1].id - 1
            print("Downloaded ", len(all_tweets), " so far =)")

        json_file_path = os.path.dirname(__file__) + "/../data/" + output_file_name

        with open(json_file_path, 'w') as file:
            json.dump([status._json for status in all_tweets], file)

    def get_users_followers(self, screen_name):
        users = []
        try:
            ids = []
            for page in tweepy.Cursor(self.api.followers_ids, screen_name=screen_name).pages():
                ids.extend(page)
        except tweepy.TweepError:
            print("tweepy.TweepError=")
        except:
            e = sys.exc_info()[0]
            print("Error: %s" % e)

        for start in range(0, len(ids), 100):
            end = start + 100

            try:
                users.extend(self.api.lookup_users(ids[start:end]))

            except tweepy.RateLimitError:
                print("RateLimitError...waiting 900 seconds to continue")
                time.sleep(900)
                users.extend(self.api.lookup_users(ids[start:end]))

        return users

    def get_followers_of_followers(self, users, output_path):

        if not os.path.exists(output_path):
            os.makedirs(output_path)
        folder_files = os.listdir(output_path)

        large_users = []
        for user in users:
            sn = user['screen_name']

            # Dont get private users and don't get if json file already saved
            if user['protected'] is True:
                continue
            for f in folder_files:
                if f[1:f.find('_')] == sn:
                    should_continue = True
                    break
            if should_continue:
                should_continue = False
                continue

            print("collecting users from ", sn)
            this_users = self.get_users_followers(sn)
            out_filename = output_path + "@" + sn + "_followers.json"
            with open(out_filename, 'w') as file:
                json.dump([u._json for u in this_users], file)
        return large_users

    def get_search_results(self, search_term, output_file, max_tweets=10000):
        # Searching based on https://www.karambelkar.info/2015/01/how-to-use-twitters-search-rest-api-most-effectively./
        tweets_per_query = 100
        since_id = None
        max_id = -1
        tweet_count = 0
        all_tweets = []

        print("Downloading max {0} tweets".format(max_tweets))
        with open(output_file, 'w+') as f:
            while tweet_count < max_tweets:
                try:
                    if max_id <= 0:
                        if not since_id:
                            new_tweets = self.api.search(q=search_term, count=tweets_per_query)
                        else:
                            new_tweets = self.api.search(q=search_term, count=tweets_per_query,
                                                    since_id=since_id)
                    else:
                        if not since_id:
                            new_tweets = self.api.search(q=search_term, count=tweets_per_query,
                                                    max_id=str(max_id - 1))
                        else:
                            new_tweets = self.api.search(q=search_term, count=tweets_per_query,
                                                    max_id=str(max_id - 1),
                                                    since_id=since_id)
                    if not new_tweets:
                        print("No more tweets found")
                        break
                    all_tweets.extend(new_tweets)
                    tweet_count += len(new_tweets)
                    print("Downloaded {0} tweets out of {1}".format(tweet_count, max_tweets))
                    max_id = new_tweets[-1].id
                except tweepy.TweepError as e:
                    # Just exit if any error
                    print("some error : " + str(e))
                    break
        with open(output_file, 'w+') as file:
            json.dump([tweet._json for tweet in all_tweets], file)
        os.chmod(output_file, 0o777)

def main():
    grabber = TweepyGrabber()
    twitter_handle = "patrickbeekman"
    #grabber.get_users_timeline(twitter_handle, "@" + twitter_handle + "_tweets.json")
    # followers = grabber.get_users_followers(twitter_handle)
    search_term = "North Carolina"
    outfile = os.path.dirname(__file__) + "/../data/us_states/" + search_term.replace(' ', '_') + "_tweets.json"
    grabber.get_search_results(search_term, outfile)


if __name__ == "__main__":
    main()