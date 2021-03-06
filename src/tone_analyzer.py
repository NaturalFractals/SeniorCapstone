import pandas as pd
import os
import json
import re
from io import StringIO
import datetime
from watson_developer_cloud import ToneAnalyzerV3
from watson_developer_cloud import WatsonException
from watson_developer_cloud import WatsonInvalidArgument
# install with - from watson_developer_cloud import ToneAnalyzerV3

'''
    Utilizes IBM Watsons tone analyzer to determine tone and save the analysis to multiple files.
    This class also handles merges the analysis with the saved tweets object from TweepyGrabber.
'''
class MyToneAnalyzer:
    analyzer = None

    def __init__(self, username=os.environ['TONE_U'], password=os.environ['TONE_P']):
        self.analyzer = self.create_connection(username, password, '2018-02-24')

    '''
        Creates a connection with IBM Watson's Tone analyzer.
        https://www.ibm.com/watson/services/tone-analyzer/
    '''
    def create_connection(self, username, password, version_num):
        try:
            tone_analyzer = ToneAnalyzerV3(
                username=username,
                password=password,
                version=version_num)
        except WatsonInvalidArgument as e:
            return None
        return tone_analyzer

    '''
        Directly interacts with the tone analyzer API to analyze a tone and return the response.
    '''
    def analyze_json_file(self, file_path):
        if not os.path.isfile(file_path):
            raise FileNotFoundError("File does not exist.")
        with open(file_path) as tone_json:
            try:
                tone_resp = self.analyzer.tone(tone_json.read(), content_type='application/json')
            except WatsonException as e:
                raise WatsonException(e)
        return tone_resp

    '''
        Helper function that parses the tone response to only grab the sentence tones and exclude
        the document tone. Dumps to the specified output_file
    '''
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

    def dump_json_to_file(self, data, filename):
        with open(filename, 'w') as out:
            json.dump(data, out)

    '''
        analyzes all the tweet_text files in /data/tweets_text/ and saves the
        analysis files to /data/analysis/
    '''
    def analyze_all_tweets_text_folder(self, tweet_text_path):
        if self.analyzer is None:
            raise ConnectionError("Analyzer not connected")
            return
        #tweets_path = os.path.dirname(__file__) + "/../data/tweets_text/"
        for filename in os.listdir(tweet_text_path):
            num = filename.split('tweet_text_')[1].split('.')[0]
            print("analyzing : " + num.zfill(4))
            try:
                tone_resp = self.analyze_json_file(tweet_text_path + filename)
            except WatsonException as e:
                raise WatsonException(e)
            except FileNotFoundError as e2:
                print(e2)
                return
            output_file = tweet_text_path + "../analysis/tone_tweet_" + str(num).zfill(4) + ".json"
            self.write_only_sentence_tone_to_file(tone_resp, output_file)

    '''
        Parses each tweets text and cleans it up for analysis. Removes links and end of sentence
        markers such as [. ! ? \\r \\n]. I add my own end of sentence marker at the end of each tweet,
        this ensures I get the tone of the whole tweet and not each sentence of the tweet.
    '''
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

    '''
        Creates a new tone analysis ready json file of 99 tweets per file and
        saves it in /data/tweets_text. Tone analyzer only reads first 100 sentences 
        for tone analysis and only first 1000 sentences for document level analysis.
        Max filesize = 128KB tweet_text is a iterable list of text from the tweets.
    '''
    def incremental_send_all_tweets_to_text_json(self, input_filename, data_path):
        num = 0
        start = 0
        stop = 99
        increment = 99

        if not os.path.exists(input_filename):
            raise FileNotFoundError()
        if not os.path.exists(data_path):
            os.mkdir(data_path)

        df = pd.read_json(input_filename)

        while start < (len(df)):
            #newfilename = self.path_name("/../data/tweets_text/tweet_text" + "_" + str(num).zfill(4) + ".json")
            newfilename = data_path + "tweet_text_" + str(num).zfill(4) + ".json"
            subset = df[start:stop]['text']
            self.clean_text_write_to_json(subset, newfilename)
            start += increment
            stop += increment
            num += 1


    '''
        Aggregates all of the tone analysis from the /data/analysis/ folder. This needs to 
        happen because the clean_text_write_to_json method writes each chunk of 99 tweets to a
        new file.
    '''
    def create_single_file_tone_analysis(self, analysis_folder, output_path):
        if not os.path.isdir(analysis_folder):
            os.mkdir(analysis_folder)
        count = 0
        #output_file = self.path_name("/../data/all_analysis.json")
        #dirFiles = os.listdir(self.path_name("/../data/analysis/"))
        dirFiles = os.listdir(analysis_folder)
        if len(dirFiles) == 0:
            raise FileNotFoundError
        dirFiles.sort()
        print(dirFiles)

        with open(output_path, 'w') as outfile:
            first = True
            for file in dirFiles:
                if first:
                    outfile.write('[')
                    first = False
                else:
                    outfile.write(',')

                #path = self.path_name("/../data/analysis/" + file)
                path = analysis_folder + file
                data = pd.read_json(path)
                data['sentence_id'] = range(count, count+len(data))
                count += len(data)
                outfile.write(data.to_json(orient='records').strip()[1:-1])
            outfile.write(']')

    '''
        Cleans up any unnecessary files that were created during intermediary processes.
    '''
    def temp_file_cleanup(self, analysis_path, tweets_text_path):
        #analysis_path = self.path_name("/../data/analysis/")
        #tweets_text_path = self.path_name("/../data/tweets_text/")
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
            except Exception as e:
                print(e)

    '''
        Attaches the analysis to the the actual tweet object downloaded using the 
        tweepy grabber class. This merged analysis is saved to a merged folder.
    '''
    def attach_analysis_to_tweet(self, analysis_path, tweets_path, merged_path):
        #analysis_path = self.path_name("/../data/all_analysis.json")
        #tweets_path = self.path_name("/../data/tweets.json")

        try:
            analysis = pd.read_json(analysis_path)
            tweets = pd.read_json(tweets_path)
        except FileNotFoundError as e:
            print(e, analysis_path, tweets_path)
            return
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
        #output_file_path = self.path_name("/../data/merged_analysis.json")
        with open(merged_path, 'w+') as file:
            file.write(merged.to_json(orient='records'))
        os.chmod(merged_path, 0o777)
        print("Merged analysis created!")


    def path_name(self, filename):
        return os.path.dirname(__file__) + filename

def main():
    ta = MyToneAnalyzer()

    twitter_handle = "us_states/North_Carolina"

    # Uncomment to read in a tweets.json file with all of your tweets and seperate them into
    # files with just the text and then analyze each tweet.
    ta.incremental_send_all_tweets_to_text_json(ta.path_name("/../data/" + twitter_handle + "_tweets.json"),
                                                ta.path_name("/../data/tweets_text/"))
    ta.analyze_all_tweets_text_folder(ta.path_name("/../data/tweets_text/"))
    ta.create_single_file_tone_analysis(ta.path_name("/../data/analysis/"),
                                        ta.path_name("/../data/all_analysis.json"))
    ta.temp_file_cleanup(ta.path_name("/../data/analysis/"),
                         ta.path_name("/../data/tweets_text/"))
    ta.attach_analysis_to_tweet(ta.path_name("/../data/all_analysis.json"),
                                ta.path_name("/../data/" + twitter_handle + "_tweets.json"),
                                ta.path_name("/../data/" + twitter_handle + "_merged_analysis.json"))

    '''
    resp = ta.analyze_json_file(analyzer, ta.path_name("/../data/tweets_text/tweet_text_0000.json"))
    ta.write_only_sentence_tone_to_file(resp, ta.path_name("/../data/hi.json"))
    '''

if __name__ == "__main__":
    main()