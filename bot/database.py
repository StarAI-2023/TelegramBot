from datetime import datetime
from typing import Any

import motor.motor_asyncio

import config

# class Database:
#     def __init__(self):
#         self.client = pymongo.MongoClient(config.mongodb_uri_second)
#         self.db = self.client["chatgpt_telegram_bot"]
#         self.user_collection = self.db["user"]

#     def check_if_user_exists(self, user_id: int, raise_exception: bool = False):
#         if self.user_collection.count_documents({"_id": user_id}) > 0:
#             return True
#         else:
#             if raise_exception:
#                 raise ValueError(f"User {user_id} does not exist")
#             else:
#                 return False

#     def add_new_user(
#         self,
#         user_id: int,
#         chat_id: int,
#         username: str = "",
#         first_name: str = "",
#         last_name: str = "",
#     ):
#         user_dict: dict = {
#             "_id": user_id,
#             "chat_id": chat_id,
#             "username": username,
#             "first_name": first_name,
#             "last_name": last_name,
#             "first_seen": datetime.now(),
#             "n_used_tokens": {
#                 "n_input_tokens": 0,
#                 "n_output_tokens": 0,
#                 "n_remaining_output_tokens": config.available_token_new_user,
#             },
#         }

#         if not self.check_if_user_exists(user_id):
#             self.user_collection.insert_one(user_dict)

#     def get_user_attribute(self, user_id: int, key: str) -> str:
#         self.check_if_user_exists(user_id, raise_exception=True)
#         user_dict = self.user_collection.find_one({"_id": user_id})

#         if key not in user_dict:
#             return None

#         return user_dict[key]

#     def set_user_attribute(self, user_id: int, key: str, value: Any):
#         self.check_if_user_exists(user_id, raise_exception=True)
#         self.user_collection.update_one({"_id": user_id}, {"$set": {key: value}})

#     def update_n_used_tokens(
#         self,
#         user_id: int,
#         n_input_tokens: int,
#         n_output_tokens: int,
#     ) -> int:
#         """
#         Updates the count of used tokens for a specific user and model. If user used all the remaining tokens and the tokens go negative, set to 0.

#         Args:
#             user_id (int): The ID of the user.
#             model (str): The name of the model.
#             n_input_tokens (int): The number of input tokens used.
#             n_output_tokens (int): The number of output tokens used.

#         Returns:
#             int: The remaining number of available output tokens for the model.

#         Raises:
#             ValueError: If the user does not exist in the database.

#         """
#         n_used_tokens_dict = self.get_user_attribute(user_id, "n_used_tokens")

#         n_used_tokens_dict["n_input_tokens"] += n_input_tokens
#         n_used_tokens_dict["n_output_tokens"] += n_output_tokens
#         n_used_tokens_dict["n_remaining_output_tokens"] = max(
#             n_used_tokens_dict["n_remaining_output_tokens"] - n_output_tokens, 0
#         )

#         self.set_user_attribute(user_id, "n_used_tokens", n_used_tokens_dict)
#         return n_used_tokens_dict["n_remaining_output_tokens"]

#     def get_remaining_tokens(self, user_id: int) -> int:
#         n_used_tokens_dict = self.get_user_attribute(
#             user_id=user_id, key="n_used_tokens"
#         )
#         return n_used_tokens_dict["n_remaining_output_tokens"]

#     def increase_remaining_tokens(self, user_id: int, tokens_added: int) -> int:
#         """
#         increase the remaining number of available output tokens for the model, e.g. gpt-turbo.
#         """
#         n_used_tokens_dict = self.get_user_attribute(user_id, "n_used_tokens")
#         n_used_tokens_dict["n_remaining_output_tokens"] += tokens_added
#         self.set_user_attribute(user_id, "n_used_tokens", n_used_tokens_dict)
#         return n_used_tokens_dict["n_remaining_output_tokens"]


class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(config.mongodb_uri_second)
        self.db = self.client["chatgpt_telegram_bot"]
        self.user_collection = self.db["user"]

    async def check_if_user_exists(self, user_id: int, raise_exception: bool = False):
        if await self.user_collection.count_documents({"_id": user_id}) > 0:
            return True
        else:
            if raise_exception:
                raise ValueError(f"User {user_id} does not exist")
            else:
                return False

    async def add_new_user(
        self,
        user_id: int,
        username: str = "",
        first_name: str = "",
        last_name: str = "",
    ):
        user_dict: dict = {
            "_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "first_seen": datetime.now(),
            "n_used_tokens": {
                "n_input_tokens": 0,
                "n_output_tokens": 0,
                "n_remaining_output_tokens": config.available_token_new_user,
            },
        }

        if not await self.check_if_user_exists(user_id):
            await self.user_collection.insert_one(user_dict)

    async def get_user_attribute(self, user_id: int, key: str) -> str:
        await self.check_if_user_exists(user_id, raise_exception=True)
        user_dict = await self.user_collection.find_one({"_id": user_id})

        if key not in user_dict:
            return None

        return user_dict[key]

    async def set_user_attribute(self, user_id: int, key: str, value: Any):
        await self.check_if_user_exists(user_id, raise_exception=True)
        await self.user_collection.update_one({"_id": user_id}, {"$set": {key: value}})

    async def update_n_used_tokens(
        self,
        user_id: int,
        n_input_tokens: int,
        n_output_tokens: int,
    ) -> int:
        """
        Updates the count of used tokens for a specific user and model. If user used all the remaining tokens and the tokens go negative, set to 0.

        Args:
            user_id (int): The ID of the user.
            n_input_tokens (int): The number of input tokens used.
            n_output_tokens (int): The number of output tokens used.

        Returns:
            int: The remaining number of available output tokens for the model.

        Raises:
            ValueError: If the user does not exist in the database.

        """
        n_used_tokens_dict = await self.get_user_attribute(user_id, "n_used_tokens")

        n_used_tokens_dict["n_input_tokens"] += n_input_tokens
        n_used_tokens_dict["n_output_tokens"] += n_output_tokens
        n_used_tokens_dict["n_remaining_output_tokens"] = max(
            n_used_tokens_dict["n_remaining_output_tokens"] - n_output_tokens, 0
        )

        await self.set_user_attribute(user_id, "n_used_tokens", n_used_tokens_dict)
        return n_used_tokens_dict["n_remaining_output_tokens"]

    async def get_remaining_tokens(self, user_id: int) -> int:
        n_used_tokens_dict = await self.get_user_attribute(
            user_id=user_id, key="n_used_tokens"
        )
        return n_used_tokens_dict["n_remaining_output_tokens"]

    async def increase_remaining_tokens(self, user_id: int, tokens_added: int) -> int:
        """
        increase the remaining number of available output tokens for the model, e.g. gpt-turbo.
        """
        n_used_tokens_dict = await self.get_user_attribute(user_id, "n_used_tokens")
        n_used_tokens_dict["n_remaining_output_tokens"] += tokens_added
        await self.set_user_attribute(user_id, "n_used_tokens", n_used_tokens_dict)
        return n_used_tokens_dict["n_remaining_output_tokens"]
