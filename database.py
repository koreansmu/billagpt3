import json

from datetime import datetime
from os.path import exists
from typing import Optional, List, Union

from const import pricing

class Message(dict):
    def __init__(self, role: str, content: Optional[str], tool_calls: Optional[List[dict]] = None, tool_call_id: Optional[str] = None, name: Optional[str] = None) -> None:
        if tool_calls:
            super().__init__({"role": role, "content": content, "tool_calls": tool_calls})
        elif tool_call_id and name:
            super().__init__({"role": role, "content": content, "tool_call_id": tool_call_id, "name": name})
        else:
            super().__init__({"role": role, "content": content})


    @property
    def role(self) -> Optional[str]:
        return self["role"]


    @property
    def content(self) -> Optional[str]:
        return self["content"]


    @property
    def tool_calls(self) -> Optional[List[dict]]:
        return self["tool_calls"]


class Chat(dict): 
    def __init__(self, uid: int, owner: int, title: str, model: Optional[str] = "gpt-3.5-turbo", created_at: Union[int, datetime] = datetime.now(), last_accessed: Union[int, datetime] = datetime.now(), messages: List[Union[dict, Message]] = None) -> None:
        if messages is not None and len(messages) > 0 and not isinstance(messages[0], Message):
            messages = list(map(lambda m: Message(**m), messages))
        if isinstance(created_at, datetime):
            created_at = int(created_at.timestamp())
        if isinstance(last_accessed, datetime):
            last_accessed = int(last_accessed.timestamp())
        super().__init__({"uid": uid, "owner": owner, "title": title, "created_at": created_at, "last_accessed": last_accessed, "messages": messages or []})


    @property
    def uid(self) -> int:
        return self["uid"]


    @property
    def owner(self) -> int:
        return self["owner"]


    @property
    def title(self) -> str:
        return self["title"]


    @property
    def messages(self) -> List[Message]:
        return self["messages"]
    

    @property
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self["created_at"])


    @property
    def last_accessed(self) -> datetime:
        return datetime.fromtimestamp(self["last_accessed"])


class User(dict): # Create more settings
    def __init__(self, uid: int, model: str = "gpt-3.5-turbo", has_gpt4: bool = False):
        super().__init__({"uid": uid, "model": model, "has_gpt4": has_gpt4})
    
    
    @property
    def uid(self):
        return self["uid"]


    @property
    def model(self):
        return self["model"]


    @property
    def has_gpt4(self):
        return self["has_gpt4"]


class Database():
    chats: List[Chat] = []
    users: List[User] = []
    path = ""

    def __init__(self, path: str = "messages.json") -> None:
        self.path = path
        if not exists(path):
            with open(path, "w") as f:
                json.dump({"users": [], "chats": []}, f)
        with open(path) as f:
            data = json.load(f)
            self.chats = list(map(lambda c: Chat(**c), data["chats"]))
            self.users = list(map(lambda u: User(**u), data["users"]))


    def commit(self) -> None:
        with open(self.path, "w") as f:
            json.dump({"users": self.users, "chats": self.chats}, f, indent=2)


    def user_exists(self, uid: int) -> bool:
        return len(list(filter(lambda u: u.uid == uid, self.users))) > 0


    def create_user(self, uid: int, model: str = "gpt-3.5-turbo", has_gpt4: bool = False) -> User:
        if model not in pricing.keys():
            raise ValueError(f"Model {model} not found")
        if len(list(filter(lambda u: u.uid == uid, self.users))) > 0:
            raise ValueError(f"User {model} already exists")
        new_user = User(uid, model, has_gpt4)
        self.users.append(new_user)
        return new_user


    def get_user(self, uid: int) -> Optional[User]:
        result = list(filter(lambda u: u.uid == uid, self.users))
        if len(result) > 0:
            return result[0]
        else:
            return None


    def chat_exists(self, uid: int) -> bool:
        return len(list(filter(lambda c: c.owner == uid, self.chats))) > 0


    def create_chat(self, title: str, owner: int, model: str = "gpt-3.5-turbo") -> Chat:
        if model not in pricing.keys():
            raise ValueError(f"Model {model} not found")
        new_id = 0
        if len(self.chats) > 0:
            new_id = max(map(lambda c: c.uid, self.chats)) + 1
        new_chat = Chat(new_id, owner, title, model)
        self.chats.append(new_chat)
        self.commit()
        return new_chat


    def get_chat(self, uid: int) -> Optional[Chat]:
        result = list(filter(lambda c: c.uid == uid, self.chats))
        if len(result) > 0:
            return result[0]
        else:
            return None


    def get_chats(self, owner: int) -> List[Chat]:
        return sorted(filter(lambda c: c.owner == owner, self.chats), key=lambda c: c.last_accessed, reverse=True)


    def delete_chat(self, uid: int) -> None:
        if not self.chat_exists(uid):
            raise ValueError(f"Chat with uid {uid} does not exist")
        self.chats = list(filter(lambda c: c.uid != uid, self.chats))
        self.commit()


    def create_message(self, chat_id: int, role: str, *, content: Optional[Union[str, dict]] = None, tool_calls: Optional[List[dict]] = None, call_id: Optional[str] = None, function_name: Optional[str] = None) -> Message:
        message = Message(role, content, tool_calls, call_id, function_name)
        chat = self.get_chat(chat_id)
        chat.messages.append(message)
        chat["last_accessed"] = int(datetime.now().timestamp())
        self.commit()
        return message


    def get_messages(self, chat_id: int) -> List[Message]:
        if chat := self.get_chat(chat_id):
            return chat.messages
        else:
            return []
