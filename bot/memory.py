import asyncio
from datetime import datetime

import database


class Memory:
    """
    dialog_dict = {
           "chat_mode": chat_mode,
           "start_time": datetime.now(), # when the user started the conversation
           "messages": str,
           "last_time_used": datetime.now() # last time user interacted with the bot
       }
    """

    def __init__(
        self,
        mongoDb: database.Database,
        default_chat_mode: str = "sweet",
    ):
        self.default_chat_mode: str = default_chat_mode
        self.db: database.Database = mongoDb
        self.memory: dict = self.load_memory_from_db_sync()

    def get_dialog(self, user_id: int):
        if user_id not in self.memory:
            self.create_dialog(
                user_id=user_id,
            )
        return self.memory[user_id]

    def get_chat_mode(self, user_id: int):
        dialog = self.get_dialog(user_id)
        return dialog["chat_mode"]

    def create_dialog(self, user_id: int, chat_mode: str = None):
        if chat_mode is None:
            chat_mode = self.default_chat_mode
        dialog_dict = {
            "chat_mode": chat_mode,
            "start_time": datetime.now(),
            "last_time_used": datetime.now(),
            "messages": "",
        }
        self.memory[user_id] = dialog_dict

    def add_message(self, user_id: int, human_message: str, bot_response: str):
        dialog: dict = self.get_dialog(user_id)
        human_message = f"I said: {human_message}\n"
        bot_response = f"You said: {bot_response}\n"

        dialog["messages"] = "".join([dialog["messages"], human_message, bot_response])
        dialog["last_time_used"] = datetime.now()  # update last time used

    # Called when the bot memory get reset. The first half of the short term memory will be written to the long term memory in pinecone
    def write_to_long_term(self, user_id: int) -> None:
        if user_id in self.memory:
            message = self.memory[user_id]["messages"]
            half = len(message) // 2
            self.memory[user_id]["messages"] = message[half:]
            self.memory[user_id]["start_time"] = datetime.now()
            return message[:half]
        else:
            self.create_dialog(user_id=user_id)

    # Delete last 10 new line messages from the short term memory
    def delete_memory(self, user_id: int) -> None:
        if user_id in self.memory:
            message = self.memory[user_id]["messages"]
            new = message.rsplit("\n", 10)
            if len(new) == 11:
                self.memory[user_id]["messages"] = new[0]
            else:
                self.memory[user_id]["messages"] = ""

    def set_chat_mode(self, user_id: int, chat_mode: str):
        if user_id in self.memory:
            self.memory[user_id]["chat_mode"] = chat_mode
        else:
            self.create_dialog(user_id=user_id)

    def get_conversation_history(self, user_id: int) -> str:
        if user_id not in self.memory:
            self.create_dialog(
                user_id=user_id,
            )
        return self.memory[user_id]["messages"]

    def get_all_users(self) -> list:
        return list(self.memory.keys())

    # this function is made syncronous so that we can use in within constructor
    def load_memory_from_db_sync(self):
        try:
            memory_from_db = asyncio.run(self.db.load_short_term_memory())
            print(f"memory loading from db successed{str(self.memory)}")
            return memory_from_db
        except Exception as e:
            print("Error loading memory from db:", e)
            return {}

    async def backup_memory_to_db(self):
        try:
            await self.db.backup_short_term_memory(short_term_memory=self.memory)
            print(f"memory backup to db successed{str(self.memory)}")
        except Exception as e:
            print("Error backing up memory to db:", e)
