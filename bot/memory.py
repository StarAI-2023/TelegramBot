from datetime import datetime


class Memory:
    """
    dialog_dict = {
           "chat_mode": chat_mode,
           "start_time": datetime.now(),
           "messages": [],
       }
    """

    def __init__(self, default_chat_mode: str = "sweet"):
        self.memory: dict = {}
        self.default_chat_mode: str = default_chat_mode

    def get_dialog(self, user_id: int):
        if user_id not in self.memory:
            self.create_dialog(
                user_id=user_id,
            )
        return self.memory.get(user_id)

    def get_chat_mode(self, user_id: int):
        dialog = self.get_dialog(user_id)
        return dialog["chat_mode"]

    def create_dialog(self, user_id: int, chat_mode: str = None):
        if chat_mode is None:
            chat_mode = self.default_chat_mode
        dialog_dict = {
            "chat_mode": chat_mode,
            "start_time": datetime.now(),
            "messages": [],
        }
        self.memory[user_id] = dialog_dict

    def add_message(self, user_id: int, human_message: str, bot_response: str):
        dialog: dict = self.get_dialog(user_id)
        human_message = "User said:" + human_message
        bot_response = "You said:" + bot_response
        if dialog:
            dialog["messages"].append((human_message, bot_response))
        else:
            raise Exception(
                f"Failed to add message. No dialog found for user {user_id}"
            )

    # reset when mode change
    def reset_dialog(self, user_id: int) -> None:
        if user_id in self.memory:
            self.memory[user_id]["messages"] = []
            self.memory[user_id]["start_time"] = datetime.now()
        else:
            self.create_dialog(user_id=user_id)

    def set_chat_mode(self, user_id: int, chat_mode: str):
        if user_id in self.memory:
            self.memory[user_id]["chat_mode"] = chat_mode
        else:
            raise Exception(f"Failed to reset. No dialog found for user {user_id}")
