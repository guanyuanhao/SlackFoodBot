import os
import time
import re
from slackclient import SlackClient
from collections import Counter
import json
from yelpTest import query_api
import requests
from urllib.request import urlopen

# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
SEARCH_COMMAND = "check"
FIND_COMMAND = "find"
HELP_COMMAND = "help"
search_url = "http://techcheck-central.icheckuclaim.org/api/search_text/"
factcheck_url = "http://techcheck-central.icheckuclaim.org/api/factcheck/"
SearchCommands = [FIND_COMMAND, SEARCH_COMMAND, HELP_COMMAND]
HELP_MESSAGE = "You can try `check [*the claim you want to check*]`to find the matching claims, \nor you can try `find [*the food you want to eat*]` to find a restaurant you like"
EXCEPTION_MESSAGE = "Not sure what you mean. Try 'help'"
DEFAULT_MESSAGE = {
    "text": "*bold* `code` _italic_ ~strike~",
    "mrkdwn": False
}



MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def isSearchCommand(command):
    for c in SearchCommands:
        if command.startswith(c) and len(command.split()) > 1:
            return True
    return False

def parse_command(command, channel):
    if command.startswith(SEARCH_COMMAND):
        handle_search_command(command, channel)
    elif command.startswith(FIND_COMMAND):
        handle_find_command(command, channel)
    elif command.startswith(HELP_COMMAND):
        handle_help_command(channel)
    else:
        handle_exception(channel)


def handle_search_command(command, channel):
        text = "%20".join(command.split()[1:])
        print(text)
        search_result = json.load(urlopen(search_url + text))[0]
        fid = search_result["fid"]
        score = search_result["score"]
        response = json.load(urlopen(factcheck_url + str(fid)))
        print(response)

        DEFAULT_ATTACHMENTS = [
                {
                    # "fallback": "Required plain-text summary of the attachment.",
                    # "color": "#2eb886",
                    "pretext": "Here is the fact for you!",
                    "author_name": "Link to the article",
                    "author_link": response["article_url"],
                    # "author_icon": "http://flickr.com/icons/bobby.jpg",
                    # "title": "Slack API Documentation",
                    # "title_link": "https://api.slack.com/",
                    # "text": "Optional text that appears within the attachment",
                    "fields": [
                        {
                            "title": "Statement",
                            "value": response["statement"],
                            "short": False
                        }
                    ],
                    "image_url": response["imageurl"],

                }
            ]
        slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            # text=DEFAULT_MESSAGE,
            attachments = DEFAULT_ATTACHMENTS
        )

def handle_find_command(command, channel):
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    none_response = "Not sure what you mean. Try 'help'"
    regular_response = None
    attachments = []
    # Finds and executes the given command, filling in response
    response = None
    # This is where you start to implement more commands!
    if isSearchCommand(command):
        response = None
        command_seg = command.split()
        if len(command_seg) < 2 or len(command_seg) > 3:
            slack_client.api_call(
                "chat.postMessage",
                channel=channel,
                text= none_response
            )
            return
        elif len(command_seg) == 2:
            response = query_api(command_seg[1], "Durham, NC")
        else:
            response = query_api(command_seg[1], command_seg[2])

        regular_response = "Here is the restaurant for you!"
        if response is not None:
            name = "N/A"
            price = "N/A"
            phone = "N/A"
            rating = "N/A"
            address = "N/A"
            image_url = "N/A"
            try:
                name = response["name"]
            except:
                pass
            try:
                price = response["price"]
            except:
                pass
            try:
                phone = response["phone"]
            except:
                pass
            try:
                rating = response["rating"]
            except:
                pass
            try:
                address = response['location']['address1']
            except:
                pass
            try:
                image_url = response['image_url']
            except:
                pass
            attachments = [{"title": "Image",
            "image_url": image_url,
            },{
                "title": "Name",
                "text": name
            },
            {
                "title": "Price",
                "text": price
            },
            {
                "title": "Phone",
                "text": phone
            },
            {
                "title": "Rating",
                "text": rating
            },
            {
                "title": "Address",
                "text": address
            },]
    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text= regular_response,
        attachments = attachments
    )

def handle_help_command(channel):
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text= HELP_MESSAGE
        )

def handle_exception(channel):
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text= EXCEPTION_MESSAGE
        )

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                parse_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
