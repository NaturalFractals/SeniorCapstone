import pandas as pd
import os
import json
import re
from io import StringIO
from datetime import datetime
from watson_developer_cloud import ToneAnalyzerV3
from watson_developer_cloud import WatsonException
from watson_developer_cloud import WatsonInvalidArgument
# install with - from watson_developer_cloud import ToneAnalyzerV3


class MyToneAnalyzer:

    def create_connection(self, version_num):
        try:
            tone_analyzer = ToneAnalyzerV3(
                username=os.environ['TONE_U'],
                password=os.environ['TONE_P'],
                version=version_num)
        except WatsonInvalidArgument as e:
            print(e)
            exit(0)
        return tone_analyzer

    def analyze_json_file(self, analyzer, filename):
        with open(filename) as tone_json:
            try:
                tone_resp = analyzer.tone(tone_json.read())
            except WatsonException as e:
                print("WatsonException", e)
                exit(0)
        return tone_resp

    def write_only_sentence_tone_to_file(self, resp, output_file):
        # Load the data and create a new string with only the sentence_tones not the document_tone
        data = json.loads(json.dumps(resp))
        try:
            io = StringIO()
            str = "["
            for i in data["sentences_tone"]:
                json.dump(i, io)
            str += io.getvalue()
            new = str.replace("}{", "},{")
            new += "]"
            self.dump_json_to_file(json.loads(new), output_file)
        except Exception as e:
            print(e)


    # analyzes all the tweet_text files in /data/tweets_text/ and saves the
    # analysis files to /data/analysis/
    def analyze_all_tweets_text_folder(self, analyzer):
        tweets_path = os.path.dirname(__file__) + "/../data/tweets_text/"
        for filename in os.listdir(tweets_path):
            num = filename.split('tweet_text_')[1].split('.')[0]
            print("analyzing : " + num.zfill(4))
            tone_resp = self.analyze_json_file(analyzer, tweets_path + filename)
            output_file = tweets_path + "/../analysis/tone_tweet_" + str(num).zfill(4) + ".json"
            self.write_only_sentence_tone_to_file(tone_resp, output_file)


    # Tone analyzer only reads first 100 sentences for tone analysis and only first
    # 1000 sentences for document level analysis. Max filesize = 128KB
    def clean_text_write_to_json(self, tweet_text, newfilename):
        ninety_tweets = ""
        for tweet in tweet_text:
            s_tweet = re.sub(r'http\S+', '[link]', tweet, flags=re.MULTILINE)
            s_tweet = s_tweet.strip().replace('\n', ' ').replace('\r', ' ').replace('.', ' ').replace('!', ' ').replace('?', ' ') + ".\\n"
            ninety_tweets += " " + s_tweet
        d = {'text': [ninety_tweets]}
        new_df = pd.DataFrame(data=d).to_json(orient='records')[1:-1]
        with open(newfilename, 'w') as f:
            f.write(new_df)

    # Creates a new tone analysis ready json file of 90 tweets per file
    # Saves it in /data/tweets_text
    def send_all_tweets_to_text_json(self, input_filename):
        num = 0
        start = 0
        stop = 99
        increment = 99
        df = pd.read_json(input_filename)
        while start < (len(df)):
            newfilename = self.path_name("/../data/tweets_text/tweet_text" + "_" + str(num).zfill(4) + ".json")
            subset = df[start:stop]['text']
            self.clean_text_write_to_json(subset, newfilename)
            start += increment
            stop += increment
            num += 1


    def single_file_tone_analysis(self):
        count = 0
        output_file = self.path_name("/../data/all_analysis.json")
        dirFiles = os.listdir(self.path_name("/../data/analysis/"))
        dirFiles.sort()
        print(dirFiles)

        with open(output_file, 'w') as outfile:
            first = True
            for file in dirFiles:
                if first:
                    outfile.write('[')
                    first = False
                else:
                    outfile.write(',')

                path = self.path_name("/../data/analysis/" + file)
                data = pd.read_json(path)
                data['sentence_id'] = range(count, count+len(data))
                count += len(data)
                outfile.write(data.to_json(orient='records').strip()[1:-1])
            outfile.write(']')

    def temp_file_cleanup(self):
        analysis_path = self.path_name("/../data/analysis/")
        tweets_text_path = self.path_name("/../data/tweets_text/")
        for the_file in os.listdir(analysis_path):
            file_path = os.path.join(analysis_path, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)
        for the_file in os.listdir(tweets_text_path):
            file_path = os.path.join(tweets_text_path, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    # elif os.path.isdir(file_path): shutil.rmtree(file_path)
            except Exception as e:
                print(e)

    def attach_analysis_to_tweet(self):
        analysis_path = os.path.dirname(__file__) + "/../data/all_analysis.json"
        tweets_path = os.path.dirname(__file__) + "/../data/tweets.json"

        analysis = pd.read_json(analysis_path)
        tweets = pd.read_json(tweets_path)
        tweets['sentence_id'] = range(0, len(tweets))

        merged = pd.merge(left=tweets, right=analysis, left_on='sentence_id', right_on='sentence_id')
        cols = list(merged.columns)
        print(cols)
        print("text_y: ", cols[-2])
        cols[-2] = 'processed_text'
        print("text_x: ", cols[-9])
        cols[-9] = 'text'
        merged.columns = cols
        print(merged.columns)
        output_file_path = os.path.dirname(__file__) + "/../data/merged_analysis.json"
        with open(output_file_path, 'w') as file:
            file.write(merged.to_json(orient='records'))

    def dump_json_to_file(self, data, filename):
        with open(filename, 'w') as out:
            json.dump(data, out)

    def path_name(self, filename):
        return os.path.dirname(__file__) + filename

def main():
    ta = MyToneAnalyzer()
    analyzer = ta.create_connection('2018-02-24')

    # Uncomment to read in a tweets.json file with all of your tweets and seperate them into
    # files with just the text and then analyze each tweet.
    ta.send_all_tweets_to_text_json(ta.path_name("/../data/tweets.json"))
    ta.send_all_tweets_to_text_json(ta.path_name("/../data/tweets.json"))
    ta.analyze_all_tweets_text_folder(analyzer)
    ta.single_file_tone_analysis()
    ta.temp_file_cleanup()
    ta.attach_analysis_to_tweet()

    '''
    resp = ta.analyze_json_file(analyzer, ta.path_name("/../data/tweets_text/tweet_text_0000.json"))
    ta.write_only_sentence_tone_to_file(resp, ta.path_name("/../data/hi.json"))
    '''

if __name__ == "__main__":
    main()