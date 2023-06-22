import asyncio
import os

from bot.long_term import LongTermMemory


async def process_transcripts(
    folder: str, user_namespace: str, long_term_memory: LongTermMemory
):
    """
    Processes transcripts in a folder and adds them to long term memory pinecone db.
    Also keeps track of processed files to avoid re-processing.

    Parameters
    ----------
    folder : str
        The path to the folder containing the transcript text files.
    user_namespace : str
        The namespace for the long term memory additions.
    long_term_memory : LongTermMemory
        The long term memory object.
    """
    # Name of the file where we keep track of processed files
    log_file = os.path.join(folder, "log_files.txt")

    # Read the processed files if the log file exists
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            processed_files = f.read().splitlines()
    else:
        processed_files = []

    for filename in os.listdir(folder):
        if filename == "log_files.txt":
            continue

        file_path = os.path.join(folder, filename)
        if filename.endswith(".txt") and filename not in processed_files:
            with open(file_path, "r") as f:
                text = f.read()
            response = await long_term_memory.add_text(
                user_namespace=user_namespace, text=text, chunkSize=2048
            )
            print(response)
            processed_files.append(filename)

            # Update the log file
            with open(log_file, "w") as f:
                f.write("\n".join(processed_files))
            print(f"Successfully inserted {filename} into pinecone.")

        # Delete the processed file
        os.remove(file_path)

    print(f"Processed all unprocessed transcripts in {folder}.")


long_term_memory = LongTermMemory()
folder = "eugeniacooney_youtube_transcriptions"
celebrity_name = "eugeniacooney_telegram_bot"

# Call process_transcripts function in an event loop
loop = asyncio.get_event_loop()
loop.run_until_complete(
    process_transcripts(
        folder, user_namespace=celebrity_name, long_term_memory=long_term_memory
    )
)
