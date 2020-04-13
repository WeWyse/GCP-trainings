import datetime
import json
import time
import tweepy

from google.cloud import pubsub_v1
from tweepy.streaming import StreamListener
from tweepy.auth import OAuthHandler


#######################################    
#########   USEFUL METHODS   ##########
#######################################

def reformat_tweet(tweet):
	""" A method to format a tweet from tweepy
    """
    
    x = tweet
    processed_doc = {
        "id"					: x["id"],
        "lang"					: x["lang"],
        "retweeted_id"			: x["retweeted_status"]["id"] if "retweeted_status" in x else None,
        "favorite_count" 		: x["favorite_count"] if "favorite_count" in x else 0,
        "retweet_count"			: x["retweet_count"] if "retweet_count" in x else 0,
        "coordinates_latitude"	: x["coordinates"]["coordinates"][0] if x["coordinates"] else 0,
        "coordinates_longitude"	: x["coordinates"]["coordinates"][0] if x["coordinates"] else 0,
        "place"					: x["place"]["country_code"] if x["place"] else None,
        "user_id"				: x["user"]["id"],
        "created_at"			: time.mktime(time.strptime(x["created_at"], "%a %b %d %H:%M:%S +0000 %Y"))
    }

    if x["entities"]["hashtags"]:
        processed_doc["hashtags"] 		= [{"text": y["text"], "startindex": y["indices"][0]} for y in
                                     	x["entities"]["hashtags"]]
    else:
        processed_doc["hashtags"] 		= []

    if x["entities"]["user_mentions"]:
        processed_doc["usermentions"] 	= [{"screen_name": y["screen_name"], "startindex": y["indices"][0]} for y in
                                        x["entities"]["user_mentions"]]
    else:
        processed_doc["usermentions"]	= []

    if "extended_tweet" in x:
        processed_doc["text"] 			= x["extended_tweet"]["full_text"]
    elif "full_text" in x:
        processed_doc["text"] 			= x["full_text"]
    else:
        processed_doc["text"]			= x["text"]

    return processed_doc
    
    
##################################################    
##########    PUB / SUB CONFIGURATION   ##########
##################################################

# Pub/Sub topic configuration
publisher 	= pubsub_v1.PublisherClient()
topic_path 	= publisher.topic_path("rare-result-248415","got_tweets_topic_alexis_g")

# Method to push messages to pub/sub
def write_to_pubsub(tweet):
	""" A method to push tweet messages to pub/sub.
	The method needs to specify the JSON format according the to BigQuery table.
    """
    try:
        if tweet["lang"] == "fr":
            publisher.publish(topic_path, data=json.dumps({
                "text"	    : 	tweet["text"],
                "user_id"   : 	tweet["user_id"],
                "id"        : 	tweet["id"],
                "created_at": 	datetime.datetime.fromtimestamp(tweet["created_at"]).strftime('%Y-%m-%d %H:%M:%S')
            }).encode("utf-8"), tweet_id=str(tweet["id"]).encode("utf-8"))
    except Exception as e:
        raise
        
##################################################    
######    TWITTER CUSTOM LISTENER CLASS    #######
##################################################

class StdOutListener(StreamListener):
    """ A listener object handles tweets that are received from the stream.
    This is a basic listener that just pushes tweets to pubsub.
    """

    def __init__(self):
        super(StdOutListener, self).__init__()
        self._counter = 0


    def on_status(self, data):
        write_to_pubsub(reformat_tweet(data._json))
        self._counter += 1
        return True


    def on_error(self, status):
        if status == 420:
            print("rate limit active")
            return False

#################################################    
####    TWITTER AUTHENTICATION PARAMETERS   #####
#################################################

auth 		= tweepy.OAuthHandler('Q3AGu9g3qrnEJ7LPfoqcN8c22', 'VXi4c6aRxJU9dA3yi89WF2bkEHsdL6T6TnWoH121My0isBRWAm')
auth.set_access_token('353644828-pyCggbPYbcWOkVUMeBw7iJUXMCt9mkaO7RqNN5mD', '1VR8THzl6M7t2zcGrMzKlSqwXAAqC5cwcNyK0z3Y8S3Qh')
api 		= tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=False)


#################################################    
############      MAIN FUNCTION       ###########
#################################################

if __name__ == "__main__":
	# Filter tweets based on hashtags
	lst_hashtags = ["#coronavirus"]
	# Create a listener object
	l 		= StdOutListener()
	# Start listening with the listener object and the credentials
	stream 	= tweepy.Stream(auth, l, tweet_mode='extended')
	stream.filter(track=lst_hashtags)
