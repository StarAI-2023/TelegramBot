# # # Concatenate text objects into paragraphs of one minute each
# # minute = 0
# # current_paragraph = ""
# # paragraphs = []
# # for obj in data:
# #     duration = obj['duration']
# #     text = obj['text']
# #     current_paragraph += text + " "
# #     if len(current_paragraph) > 50 or duration > 60:
# #         paragraphs.append({'minute': minute, 'text': current_paragraph})
# #         current_paragraph = ""
# #         minute += 1

# # # Output the result to a new text file
# # with open(f'{video_id}.txt', 'w') as f:
# #     for paragraph in paragraphs:
# #         f.write(f"Minute {paragraph['minute']}: {paragraph['text']}\n\n")

# # print(f"Transcript saved to {video_id}.txt")


import json
import os

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter, TextFormatter


class TranscriptFetcher:
    """
    A class used to fetch and format transcripts from YouTube videos.
    """

    def __init__(self, video_id: str, folder_name: str):
        """
        Parameters
        ----------
        video_id : str
            The ID of the YouTube video to fetch the transcript from.
        folder_name : str
            The name of the folder where the transcript text file will be saved.
        """
        self.video_id = video_id
        self.folder_name = folder_name
        self.file_path = os.path.join(folder_name, f"{video_id}.txt")
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

    def generate_concatenated_transcript(self) -> bool:
        """
        Writes the formatted transcript directly to a text file, without writing to a JSON file first.
        """
        try:
            if os.path.exists(self.file_path):
                print(f"Transcript for {self.video_id} already exists! Skipping...")
                return True

            # Fetches the transcript from the YouTube video.
            youtube_transcript = YouTubeTranscriptApi.get_transcript(self.video_id)

            with open(self.file_path, "w", encoding="utf-8") as f_txt:
                for individual_sentence in youtube_transcript:
                    text = individual_sentence["text"]
                    f_txt.write(f"{text} ")
                print(f"Transcript for {self.video_id} saved to {self.file_path}")
                return True

        except Exception as e:
            print(f"Fail to generate transcript with error: {e}")
            return False


import time

from pytube import Playlist
from youtube_video_transcription import TranscriptFetcher

if __name__ == "__main__":
    playlist_urls = [
        "https://www.youtube.com/playlist?list=PLLCqY3eG8BmQR1pdqJn_oyUjkk1Sp1xEi",
        "https://www.youtube.com/playlist?list=PLLCqY3eG8BmRvd3ZncrOvrkGR9mU9HEjJ",
        "https://www.youtube.com/playlist?list=PLLCqY3eG8BmQybkfc6E_FTpxarHGS5Knt",
    ]

    youtube_folder_name = "eugeniacooney_youtube_transcriptions"

    for playlist_url in playlist_urls:
        playlist = Playlist(playlist_url)
        for url in playlist.video_urls:
            video_id = url.split("=")[-1]
            transcript_fetcher = TranscriptFetcher(video_id, youtube_folder_name)
            try:
                transcript_fetcher.generate_concatenated_transcript()
                time.sleep(secs=1)

            except Exception as e:
                print(
                    f"An error occurred while processing video ID {video_id}: {str(e)}"
                )
