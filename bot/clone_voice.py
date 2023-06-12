# Script to clone a voice from a set of voice samples
# Remember to save the voice id

from elevenlabs import clone, generate, play, set_api_key
import config
import os


class VoiceClone:
    def __init__(self, voice_name, voice_description, voice_samples_path) -> None:
        set_api_key(config.voice_clone_api_key)
        self.voice_samples_path = voice_samples_path
        self.voice = clone(
            name=voice_name,
            description=voice_description,
            files=self.getVoiceSamplesFiles(),
        )
        print(f"{self.voice} is created, with description: {voice_description} and name: {voice_name}. Remeber to store the voice id!!!")
        
        # # low stability will make the voice fluctuate more, thus more emotional
        # self.voice.settings.stability = 0.23
        # self.voice.settings.similarity_boost = 0.9

    def getVoiceSamplesFiles(
        self,
    ) -> list:
        file_list = []

        # Check if the directory exists
        if os.path.exists(self.voice_samples_path):
            # Iterate over all files in the directory
            for file_name in os.listdir(self.voice_samples_path):
                file_path = os.path.join(self.voice_samples_path, file_name)
                if os.path.isfile(file_path):
                    file_list.append(file_path)
        else:
            print(
                "Directory path does not exist, and current directory is:" + os.getcwd()
            )
            raise

        return file_list
    

voice_clone = VoiceClone(voice_name="ibabyrainbow", voice_description="ibabyrainbow", voice_samples_path="voice_samples/ibabyrainbow")
