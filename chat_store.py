"""Where a conversation lives. DbStore saves to the user's private history; SessionStore keeps it only in memory
(used when the farmer turned off 'Save my conversations'). Both expose the same small interface."""

import database as db


class DbStore:
    persistent = True

    def __init__(self, user_id, state):
        self.user_id, self.state = user_id, state

    @property
    def conv_id(self):
        return self.state.get("ask_conv_id")

    def messages(self):
        cid = self.conv_id
        return db.get_messages(self.user_id, cid) if cid else []

    def add(self, role, content, lang, input_mode="text", raw=None, title=None):
        cid = self.conv_id
        if cid is None:
            cid = db.create_conversation(self.user_id, title or content, lang.name, lang.stt_code or lang.tts_code or "")
            self.state["ask_conv_id"] = cid
        return db.add_message(self.user_id, cid, role, content, language=lang.id, input_mode=input_mode, raw_transcript=raw)

    def feedback(self, message_id, value):
        return db.set_feedback(self.user_id, message_id, value)

    def drop_last_assistant(self):
        if self.conv_id:
            db.delete_last_assistant_message(self.user_id, self.conv_id)

    def delete(self):
        if self.conv_id:
            db.delete_conversation(self.user_id, self.conv_id)
        self.state.pop("ask_conv_id", None)


class SessionStore:
    persistent = False
    KEY = "ask_mem"

    def __init__(self, user_id, state):
        self.user_id, self.state = user_id, state

    @property
    def conv_id(self):
        return "temp" if self.state.get(self.KEY) else None

    def messages(self):
        return list(self.state.get(self.KEY, []))

    def add(self, role, content, lang, input_mode="text", raw=None, title=None):
        mem = self.state.setdefault(self.KEY, [])
        new_id = -(len(mem) + 1)
        mem.append({"id": new_id, "role": role, "content": content, "language": lang.id, "input_mode": input_mode,
                    "raw_transcript": raw, "feedback": None, "created_at": ""})
        return new_id

    def feedback(self, message_id, value):
        for msg in self.state.get(self.KEY, []):
            if msg["id"] == message_id:
                msg["feedback"] = value
                return True
        return False

    def drop_last_assistant(self):
        mem = self.state.get(self.KEY, [])
        for i in range(len(mem) - 1, -1, -1):
            if mem[i]["role"] == "assistant":
                del mem[i]
                return

    def delete(self):
        self.state.pop(self.KEY, None)


def get_store(user, state):
    return DbStore(user["id"], state) if user["save_history"] else SessionStore(user["id"], state)
