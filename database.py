import json

from os.path import exists
from typing import Optional, List, Union


class Function(dict):
    def __init__(self, name: str, arguments: str):
        super().__init__({"name": name, "arguments": arguments})


    @property
    def name(self) -> str:
        return self["name"]


    @property
    def arguments(self) -> dict:
        return json.loads(self["arguments"])


class ToolCall(dict):
    def __init__(self, id: str, type: str, function: Union[dict, Function]) -> None:
        if not isinstance(function, Function):
            function = Function(**function)
        super().__init__({"id": id, "type": type, "function": function})


    @property
    def id(self) -> str:
        return self["id"]


    @property
    def type(self) -> str:
        return self["type"]


    @property
    def function(self) -> Function:
        return self["function"]


class Message(dict): # ToolCall and Function probably were unnecessary 
    def __init__(self, role: str, content: Optional[str], tool_calls: Optional[List[Union[dict, ToolCall]]] = None, tool_call_id: Optional[str] = None, name: Optional[str] = None) -> None:
        if tool_calls is not None and len(tool_calls) > 0 and not isinstance(tool_calls[0], ToolCall):
            tool_calls = list(map(lambda t: ToolCall(**t), tool_calls))

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
    def tool_calls(self) -> Optional[List[ToolCall]]:
        return self["tool_calls"]


class Chat(dict):  # TODO: created_at, accessed_at, model
    def __init__(self, uid: int, owner: int, title: Optional[str], messages: List[Union[dict, Message]] = []) -> None:
        if len(messages) > 0 and not isinstance(messages[0], Message):
            messages = list(map(lambda m: Message(**m), messages))
        super().__init__({"uid": uid, "owner": owner, "title": title, "messages": messages})


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


class Database():
    chats: List[Chat] = []
    path = ""

    def __init__(self, path: str = "messages.json") -> None:
        self.path = path
        if not exists(path):
            with open(path, "w") as f:
                f.write("[]")
        with open(path) as f:
            self.chats = list(map(lambda c: Chat(**c), json.load(f)))


    def commit(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self.chats, f, indent=4)


    def chat_exists(self, uid: int) -> bool:
        return len(len(filter(lambda c: c.owner == uid, self.chats))) > 0


    def create_chat(self, title: str, owner: int) -> Chat:
        new_id = 0
        if len(self.chats) > 0:
            new_id = max(map(lambda c: c.uid, self.chats)) + 1
        new_chat = Chat(new_id, owner, title)
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
        return list(filter(lambda c: c.owner == owner, self.chats))


    def delete_chat(self, uid: int) -> None:
        if not self.chat_exists(uid):
            raise ValueError(f"Chat with uid {uid} does not exist")
        self.chats = list(filter(lambda c: c.uid != uid, self.chats))
        self.commit()


    def create_message(self, chat_id: int, role: str, *, content: Optional[Union[str, dict]] = None, tool_calls: Optional[List[ToolCall]] = None, call_id: Optional[str] = None, function_name: Optional[str] = None) -> Message:
        message = Message(role, content, tool_calls, call_id, function_name)
        self.get_chat(chat_id).messages.append(content)
        self.commit()
        return message


    def get_messages(self, chat_id: int) -> List[Message]:
        if chat := self.get_chat(chat_id):
            return chat.messages
        else:
            return []
