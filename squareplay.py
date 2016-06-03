#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0');
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Pango
from html.parser import HTMLParser
import sys
import vlc
import os
import re
import inifiles


class HTMLRender(HTMLParser):
    __inline = [ "b", "i", "strong", "em", "cite" ]
    __block = [ "h1", "h2", "h3", "h4", "h5", "h6", "p", "dl", "dt", "dd", "br" ]
    __ignore = [ "body", "html", "div", "span" ]
    __open = [ "dt", "dd", "p" ]
    __remove = [ "head", "script", "style" ]

    # Formatos e fontes aplicadas às tags
    __formats = {
         'h1': { 'font': "sans bold 20",
                 'justification': Gtk.Justification.CENTER,
                 'pixels-above-lines': 8,
                 'pixels-below-lines': 4 },
         'h2': { 'font': "sans bold 18",
                 'justification': Gtk.Justification.CENTER,
                 'pixels-above-lines': 6,
                 'pixels-below-lines': 3 },
         'h3': { 'font': "sans bold italic 16",
                 'pixels-above-lines': 4,
                 'pixels-below-lines': 0 },
         'h4': { 'font': "sans bold italic 16",
                 'pixels-above-lines': 4,
                 'pixels-below-lines': 0 },
         'h5': { 'font': "sans bold italic 16",
                 'pixels-above-lines': 4,
                 'pixels-below-lines': 0 },
         'h6': { 'font': "sans bold italic 16",
                 'pixels-above-lines': 4,
                 'pixels-below-lines': 0 },
         'dl': { 'font': "sans 14" },
         'dd': { 'font': "sans 14",
                 'left-margin': 10, 'right-margin': 10,
                 'pixels-above-lines': 2,
                 'pixels-below-lines': 2 },
         'dt': { 'font': "sans bold 14",
                 'pixels-above-lines': 3,
                 'pixels-below-lines': 2 },
         'p': { 'font': "sans 14",
                'pixels-above-lines': 4,
                'pixels-below-lines': 4 },
         'br': { 'font': "sans 14",
                'pixels-above-lines': 0,
                'pixels-below-lines': 0 },
         'b': { 'font': "sans bold 14", },
         'i': { 'font': "sans italic 14", },
         'em': { 'font': "sans italic 14", },
         'cite': { 'font': "sans italic 14", },
         'strong': { 'font': "sans bold italic 14" },
         'code': { 'font': "monospace 14" }
    }

    def __init__(self):
        HTMLParser.__init__(self)
        self.__last = None
        self.__tags = { }
        self.remove_stack = []

    def initialize_textview(self,textview) :
        text_buffer = textview.get_buffer()
        textview.set_editable(False)
        font_desc = Pango.font_description_from_string ("Serif 15");
        textview.modify_font(font_desc);
        for tag in self.__formats:
            text_buffer.create_tag(tag, **self.__formats[tag])


    def set_text(self, textview, txt):
        self.text_buffer = textview.get_buffer()
        self.feed(txt)

    def handle_starttag(self, tag, attr):
        if tag in self.__ignore:
            pass
        if tag in self.__remove:
            self.remove_stack.append(tag)
            return

        elif tag in self.__block:
            if self.__last in self.__open:
                self.handle_endtag(self.__last)
            self.__last = tag
            end_iter = self.text_buffer.get_end_iter()
            self.text_buffer.insert(end_iter, "\n")

        end_iter = self.text_buffer.get_end_iter()
        mark = self.text_buffer.create_mark(None, end_iter, True)
        if tag in self.__tags:
            self.__tags[tag].append(mark)
        else:
            self.__tags[tag] = [ mark ]


    def handle_data(self, data):
        if (len(self.remove_stack)) :
            return
        
        data = ' '.join(data.split()) + ' '
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, data)


    def handle_endtag(self, tag):
        if len(self.remove_stack) > 0 :
            top_tag = self.remove_stack.pop()
            if top_tag != tag :
                self.remove_stack.append(top_tag)
            return
               
        try:
            if tag not in self.__ignore:
                if len(self.__tags[tag]) > 0 :
                    start_mark = self.__tags[tag].pop()
                    start = self.text_buffer.get_iter_at_mark(start_mark)
                    end = self.text_buffer.get_end_iter()
                    self.text_buffer.apply_tag_by_name(tag, start, end)
                return
        except KeyError:
            pass





instance = vlc.Instance()

def seconds_to_formatted(seconds_in):
    minutes = int(seconds_in / 60);
    seconds = seconds_in % 60
    return '%d:%02.2d' % (minutes, seconds)

mmss_regex = re.compile(r'^\s*(\d+)\:(\d+)\s*$')

def parse_mmss_to_seconds(mmss) :
    match = mmss_regex.match( mmss )
    if  match != None:
        return int(match.group(1)) * 60 + int(match.group(2))
    return None

class HellowWorldGTK:

    def __init__(self):
        self.player = instance.media_player_new()
        self.player.audio_output_set("Scaletempo")
        
        self.gladefile = "Player.glade" 
        self.glade = Gtk.Builder()
        self.glade.add_from_file(self.gladefile)
        self.glade.connect_signals(self)
        self.glade.get_object("windowApplication").show_all()
        self.filechooserbuttonNextQueued = self.glade.get_object("filechooserbuttonNextQueued")

        for control in (
                'labelCurrentSong',
                'labelSongLength',
                'scaleSongPosition',
                'togglebuttonLoop',
                'buttonLoopAuto',
                'entryLoopFrom',
                'entryLoopTo',
                'scaleSongTempo',
                'textviewCueSheet'
        ) :
            setattr(self, control, self.glade.get_object(control))
        
        self.entryCountdownTimer = self.glade.get_object('entryCountdownTimer')
        self.labelCountdownDisplay = self.glade.get_object('labelCountdownDisplay')
        self.countdown_seconds = parse_mmss_to_seconds(self.entryCountdownTimer.get_text())
        
        self.event_manager = self.player.event_manager()
        self.scaleSongPosition.set_range(0,1)
        self.scaleSongTempo.set_range(.5,1.5)
        self.seconds_since_last_play = 0
        self.loop_start = None
        self.loop_end = None
        self.scaleSongTempo.set_value(1)

        self.labelTimerDisplay = self.glade.get_object('labelTimerDisplay')
        self.inifile = inifiles.IniFile()

        default_directory = os.path.expanduser("~/Music")
        if not os.path.exists(default_directory):
            default_directory = os.path.expanduser("~")
        
        self.filechooserbuttonNextQueued.set_current_folder(self.inifile.get('Last Directory', default_directory))
        
    def debug_log(self, text):
        print(text)

    def on_scaleSongPosition_change_value_cb(self, scale_object, scroll_type, position):
        self.player.set_position(position)

    def on_scaleSongTempo_change_value_cb(self, scale_object, scroll_type, position):
        self.player.set_rate(position);

    def update_timer_display(self):
        self.labelTimerDisplay.set_text( seconds_to_formatted(self.seconds_since_last_play) )
        
    def timer_tick(self):
        song_position = self.player.get_position()
        self.scaleSongPosition.set_value(song_position)
        self.seconds_since_last_play += 1
        self.update_timer_display()

        if self.loop_start == None :
            self.loop_start = parse_mmss_to_seconds(self.entryLoopFrom.get_text())
        if self.loop_end == None :
            self.loop_end = parse_mmss_to_seconds(self.entryLoopTo.get_text())
        if self.loop_start != None and self.loop_end != None and self.togglebuttonLoop.get_active() :
            length = self.player.get_length();
            song_position_in_seconds = length * song_position / 1000
            if song_position_in_seconds > self.loop_end :
                self.player.set_position(self.loop_start / (length / 1000))
                
        return self.player.get_state() == vlc.State.Playing

    def write_config(self):
        current_song = self.labelCurrentSong.get_text()
        self.inifile.set_music(current_song, 'Tempo', self.player.get_rate() )
        self.inifile.set_music(current_song, 'Loop', '1' if self.togglebuttonLoop.get_active() else '0' )
        self.inifile.set_music(current_song, 'Loop From', self.entryLoopFrom.get_text() )
        self.inifile.set_music(current_song, 'Loop To', self.entryLoopTo.get_text() )
        self.inifile.set('Last Directory', self.filechooserbuttonNextQueued.get_current_folder())
        self.inifile.write()

    def read_config(self):
        current_song = self.labelCurrentSong.get_text()
        tempo = self.inifile.get_music(current_song, 'Tempo', '1')
        self.player.set_rate(tempo)
        self.scaleSongTempo.set_value(tempo)
        self.togglebuttonLoop.set_active(int(self.inifile.get_music(current_song, 'Loop', '0')))
        self.entryLoopFrom.get_text(int(self.inifile.get_music(current_song, 'Loop From', '0:00')))
        self.entryLoopTo.get_text(int(self.inifile.get_music(current_song, 'Loop To', '0:00')))

        
    def on_buttonLoopAuto_clicked_cb(self, event) :
        self.loop_start = None
        self.loop_end = None
        length = self.player.get_length();
        self.entryLoopFrom.set_text('0:20');
        self.entryLoopTo.set_text( seconds_to_formatted( length / 1000 - 20) )
        self.togglebuttonLoop.set_active(1)
        print("buttonLoopAuto clicked: ", event)

    def on_togglebuttonLoop_toggled_cb(self, event) :
        print("Togglebutton pressed: ", event)

        
    def on_buttonPlay_clicked_cb(self, event) :
        self.player.play()
        self.seconds_since_last_play = 0
        self.update_timer_display()
        GObject.timeout_add_seconds(1,self.timer_tick)
        GObject.timeout_add_seconds(1,self.timer_set_duration_labels)

    def on_buttonStop_clicked_cb(self, event) :
        self.player.stop()
        self.player.set_position(0)

    def on_buttonPause_clicked_cb(self, event) :
        self.player.pause()

    def timer_set_duration_labels(self):
        length = self.player.get_length();
        if length < 0 :
            length = 0
        length_in_seconds = length / 1000;
        self.labelSongLength.set_text( seconds_to_formatted(length_in_seconds) )
        return False

    def load_html_into_textview(self, path, textview):
        htmlrenderer = HTMLRender()
        htmlrenderer.initialize_textview(textview)
        text = ""
        with open(path, 'r') as f:
            for line in f :
                text += line
        htmlrenderer.set_text(textview, text)

    def play_song(self,filename) :
        self.debug_log("Attempting to play: " + filename);
        media = instance.media_new(filename)
        self.player.set_media(media)
        print("Set media")
        self.labelCurrentSong.set_text(os.path.basename(filename))
        self.on_buttonPlay_clicked_cb(None)
        (root,ext) = os.path.splitext(filename)
        for alt_ext in ('.html', '.htm') :
            path = root + alt_ext
            if os.path.exists(path) :
                self.load_html_into_textview(path, self.textviewCueSheet)
                
    def get_current_song_name(self):
        return self.labelCurrentSong.get_text()

    def get_current_song_base_name(self):
        name = self.get_current_song_name()
        return re.sub(r'\s*\(.*?\)', '', name)
        
    def on_buttonPlayNextSong_clicked_cb(self,event) :
        filename = self.filechooserbuttonNextQueued.get_filename()
        if filename != None :
            self.play_song(filename)
                    
    def timer_countdown(self):
        self.countdown_seconds -= 1
        self.labelCountdownDisplay.set_text(seconds_to_formatted(self.countdown_seconds))
        if 0 >= self.countdown_seconds :
            # Play alarm
            return False
        return True
                    
    def on_buttonResetCountdownTimer_clicked_cb(self, event):
        self.countdown_seconds = parse_mmss_to_seconds(self.entryCountdownTimer.get_text())
        self.labelCountdownDisplay.set_text(seconds_to_formatted(self.countdown_seconds))

    def on_buttonStartCountdownTimer_clicked_cb(self, event):
        GObject.timeout_add_seconds(1,self.timer_countdown)
        
    
    def on_windowApplication_delete_event(self, widget, event):
        Gtk.main_quit()


















if __name__ == "__main__":
    try:
        a = HellowWorldGTK()
        Gtk.main()
    except KeyboardInterrupt:
        pass
