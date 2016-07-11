import vlc

instance = vlc.Instance()

class VLCPlayer:
    def __init__(self):
        self.player = instance.media_player_new()
        self.player.audio_output_set("Scaletempo")
        self.length = 0
        
    def set_position(self,position) :
        self.player.set_position(position / self.get_length())

    def get_position(self) :
        return self.player.get_position()

    def get_length(self) :
        self.length = self.player.get_length() / 1000
        return self.length

    def is_playing(self) :
        return self.player.get_state() == vlc.State.Playing;

    def set_tempo(self,tempo) :
        self.player.set_rate(tempo);
 
    def get_tempo(self) :
        return self.player.get_rate()

    def play(self) :
        self.player.play()

    def stop(self) :
        self.player.stop()
        
    def pause(self) :
        self.player.pause()

    def load_song(self,filename) :
        media = instance.media_new(filename)
        self.player.set_media(media)
