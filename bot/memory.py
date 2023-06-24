from datetime import datetime

import config


class Memory:
    """
    dialog_dict = {
           "chat_mode": chat_mode,
           "start_time": datetime.now(),
           "messages": str,
       }
    """

    def __init__(self, default_chat_mode: str = "Eugenia"):
        self.memory: dict = {}
        self.default_chat_mode: str = default_chat_mode

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
            "messages": "",
        }
        self.memory[user_id] = dialog_dict

    def add_message(self, user_id: int, human_message: str, bot_response: str):
        dialog: dict = self.get_dialog(user_id)
        human_message = f"I said: {human_message}\n"
        bot_response = f"You said: {bot_response}\n"

        dialog["messages"] = "".join([dialog["messages"], human_message, bot_response])

    # reset when mode change
    def write_to_long_term(self, user_id: int) -> None:
        if user_id in self.memory:
            message =  self.memory[user_id]["messages"]
            half = len(message)//2
            self.memory[user_id]["messages"] = message[half:]
            self.memory[user_id]["start_time"] = datetime.now()
            return message[:half]
        else:
            self.create_dialog(user_id=user_id)

    def delete_memory(self,user_id: int) -> None:
        if user_id in self.memory:
            message = self.memory[user_id]["messages"]
            new = message.rsplit('\n', 10)
            if len(new)==11:
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

    # def get_dialog_into_str(self, user_id):
    # current_dialog = self.get_dialog(user_id)
    # dialog_messages = current_dialog["messages"]
    # chat_mode = current_dialog["chat_mode"]
    # prompt = config.chat_modes[chat_mode]["prompt_start"]
    # prompt += "\n\n"
    # # add chat context
    # if len(dialog_messages) > 0:
    #     prompt += "Chat:\n"
    #     for user_message, ai_response in dialog_messages:
    #         prompt += f"{user_message}\n"
    #         prompt += f"{ai_response}\n"

    # return prompt
