from pathlib import Path

import dotenv
import yaml

config_dir = Path(__file__).parent.parent.resolve() / "config"

# load yaml config
with open(config_dir / "config.yml", "r") as f:
    config_yaml = yaml.safe_load(f)

# load .env config
config_env = dotenv.dotenv_values(config_dir / "config.env")

# config parameters
telegram_token = config_yaml["telegram_token"]
openai_api_key = config_yaml["openai_api_key"]
stripe_token_live = config_yaml["stripe_token_live"]
stripe_token_test = config_yaml["stripe_token_test"]
use_chatgpt_api = config_yaml.get("use_chatgpt_api", True)
allowed_telegram_usernames = config_yaml["allowed_telegram_usernames"]
new_dialog_timeout = config_yaml["new_dialog_timeout"]
enable_message_streaming = config_yaml.get("enable_message_streaming", True)
return_n_generated_images = config_yaml.get("return_n_generated_images", 1)
n_chat_modes_per_page = config_yaml.get("n_chat_modes_per_page", 5)
mongodb_uri_remote = "mongodb+srv://will:Wkf0OkXsWcmt10U1@bot.usvocwk.mongodb.net/?retryWrites=true&w=majority"
mongodb_uri_second = "mongodb+srv://me:F595YW6HduqCjNyN@cluster0.9gg56ry.mongodb.net/?retryWrites=true&w=majority"
available_token_new_user = config_yaml["available_output_token_new_user"]
voice_clone_api_key = config_yaml["11_labs_api_key"]
voice_clone_id = config_yaml["11_labs_voice_id"]
pinecone_api_key = config_yaml["pinecone_api_key"]
pinecone_environment = config_yaml["pinecone_environment"]
pinecone_index_name = config_yaml["pinecone_index_name"]
# chat_modes
with open(config_dir / "chat_modes.yml", "r") as f:
    chat_modes = yaml.safe_load(f)

# models
with open(config_dir / "models.yml", "r") as f:
    models = yaml.safe_load(f)

# files
help_group_chat_video_path = (
    Path(__file__).parent.parent.resolve() / "static" / "help_group_chat.mp4"
)
