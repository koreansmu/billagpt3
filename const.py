from logger import Logger
from yaml import load, Loader

config = load(open("config.yml"), Loader=Loader)
log = Logger()

commands = {
    "help": "Help message",
    "start": "Start message",
    "reset": "Clear current chat",
    # "delete": "Delete last two messages",
    # "regen": "Regenerate last message",
    "chats": "Show all your chats",
    "model": "Select default GPT model"
}

models = {
    "gpt-3.5": "gpt-3.5-turbo",
    "gpt-4": "gpt-4-turbo"
}

# model -> [in, out]
pricing = { 
    "gpt-3.5-turbo": [0.0005, 0.0015], 
    "gpt-4-turbo": [0.01, 0.03],
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0"
}

system_message = """You are very helpful AI assistant that provides comprehensive answers.
You have ability to search online and ask another GPT 'agent' about content of specified URL. 
Search a lot of things to get many details. Search engine is Google.
So when you're doing research better SEND ALL OR SOME OF THE LINKS into ask_webpage to get more knowledge and to know the topic deeper!
Addionally while using WolframAlpha API add pictures of charts, maps etc etc even if the user didn't ask.
DON'T USE MARKDOWN IMAGES AS THE END CLIENT DOESN'T SUPPORT IT, rather them with add_image function as.
For scientific, geographical etc better use Wolfram as it provides better and clearer results"""

