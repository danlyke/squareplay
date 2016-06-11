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
import fnmatch
import re
import inifiles
import time

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
        self.text_buffer.delete(self.text_buffer.get_start_iter(), self.text_buffer.get_end_iter())
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



( WEEKS_SINCE_PLAY_COLUMN,
  RECORD_LABEL_NAME_COLUMN,
  SONG_NAME_COLUMN,
  FILE_NAME_COLUMN ) = range(4)

class SquarePlayGTK:

    def __init__(self):
        self.player = instance.media_player_new()
        self.player.audio_output_set("Scaletempo")

        self.seconds_since_last_play = 0
        self.loop_start = None
        self.loop_end = None
        self.current_session_name_idx = -1
        self.current_session_name = ''
        
        self.gladefile = "Player.glade" 
        self.glade = Gtk.Builder()
        self.glade.add_from_file(self.gladefile)
        self.glade.connect_signals(self)
        self.glade.get_object("windowApplication").show_all()

        for control in (
                'labelCurrentSong',
                'labelSongLength',
                'scaleSongPosition',
                'togglebuttonLoop',
                'buttonLoopAuto',
                'entryLoopFrom',
                'entryLoopTo',
                'scaleSongTempo',
                'textviewCueSheet',
                'textviewNextCueSheet',
                'liststoreFolder1',
                'liststoreFolder2',
                'liststoreFolder3',
                'filechooserbuttonNextQueued',
                'filechooserbuttonFolder1',
                'filechooserbuttonFolder2',
                'filechooserbuttonFolder3',
                'treeviewFolder1',
                'treeviewFolder2',
                'treeviewFolder3',
                'comboboxSessionName',
        ) :
            setattr(self, control, self.glade.get_object(control))

        self.htmlrenderer = HTMLRender()
        self.htmlrenderer.initialize_textview(self.textviewCueSheet)
        self.htmlrenderer.initialize_textview(self.textviewNextCueSheet)
            
        self.entryCountdownTimer = self.glade.get_object('entryCountdownTimer')
        self.labelCountdownDisplay = self.glade.get_object('labelCountdownDisplay')
        self.countdown_seconds = parse_mmss_to_seconds(self.entryCountdownTimer.get_text())
        
        self.event_manager = self.player.event_manager()
        self.scaleSongPosition.set_range(0,1)
        self.scaleSongTempo.set_range(.5,1.5)
        self.scaleSongTempo.set_value(1)

        self.labelTimerDisplay = self.glade.get_object('labelTimerDisplay')
        self.inifile = inifiles.IniFile()

        default_directory = self.inifile.get('Last Directory', os.path.expanduser("~/Music"))
        if not os.path.exists(default_directory):
            default_directory = os.path.expanduser("~")
        
        self.filechooserbuttonNextQueued.set_current_folder(self.inifile.get('Last Directory', default_directory))

        self.initialize_file_liststore(self.liststoreFolder1)
        self.initialize_file_liststore(self.liststoreFolder2)
        self.initialize_file_liststore(self.liststoreFolder3)

        self.initialize_file_treeview(self.treeviewFolder1)
        self.initialize_file_treeview(self.treeviewFolder2)
        self.initialize_file_treeview(self.treeviewFolder3)

        self.new_session_name = self.comboboxSessionName.get_active_text()
        
        session_names = self.inifile.get('Session Names', self.new_session_name)
        for session in session_names.split('||') :
            self.comboboxSessionName.append_text(session)
        self.ensure_new_session_name_in_session_name_list()
        self.comboboxSessionName.set_active(0)
        self.set_current_session_name_from_control()

        self.filechooserbuttonFolder1.set_current_folder(self.inifile.get('Last Directory 1', default_directory))
        self.filechooserbuttonFolder2.set_current_folder(self.inifile.get('Last Directory 2', default_directory))       
        self.filechooserbuttonFolder3.set_current_folder(self.inifile.get('Last Directory 3', default_directory))
                                                         
        self.load_directory_into_liststore(self.filechooserbuttonFolder1, self.liststoreFolder1)
        self.load_directory_into_liststore(self.filechooserbuttonFolder2, self.liststoreFolder2)
        self.load_directory_into_liststore(self.filechooserbuttonFolder3, self.liststoreFolder3)
        

    def debug_log(self, text):
        print(text)

    def set_current_session_name_from_control(self):
        self.current_session_name = self.comboboxSessionName.get_active_text()
        self.current_session_name_idx = self.comboboxSessionName.get_active()

        if -1 == self.current_session_name_idx :
            model = self.comboboxSessionName.get_model()
            for i in range(0,len(model)) :
                if model[i][0] == self.current_session_name :
                    self.comboboxSessionName.set_active(i)
                    self.current_session_name_idx = i

    def ensure_new_session_name_in_session_name_list(self) :
        model = self.comboboxSessionName.get_model()
        if not any([True for x in model if x[0] == self.new_session_name]) :
            self.comboboxSessionName.append_text(self.new_session_name)
    

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
        self.inifile.set('Last Directory 1', self.filechooserbuttonFolder1.get_current_folder())
        self.inifile.set('Last Directory 2', self.filechooserbuttonFolder2.get_current_folder())
        self.inifile.set('Last Directory 3', self.filechooserbuttonFolder3.get_current_folder())
        model = self.comboboxSessionName.get_model()
        session_names = '||'.join([ x[0] for x in model ])
        self.inifile.set('Session Names', session_names)
        self.inifile.write()

    def read_config(self):
        current_song = self.labelCurrentSong.get_text()
        tempo = float(self.inifile.get_music(current_song, 'Tempo', '1'))
        self.player.set_rate(tempo)
        self.scaleSongTempo.set_value(tempo)
        self.togglebuttonLoop.set_active(int(self.inifile.get_music(current_song, 'Loop', '0')))
        self.entryLoopFrom.set_text(self.inifile.get_music(current_song, 'Loop From', '0:00'))
        self.entryLoopTo.set_text(self.inifile.get_music(current_song, 'Loop To', '0:00'))

        
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
        text = ""
        with open(path, 'r') as f:
            for line in f :
                text += line
        if text == '' :
            text = '<h1>No cuesheet found at ' + path + '</h1>'
        self.htmlrenderer.set_text(textview, text)

    def play_song(self,filename) :
        self.write_config()
        self.debug_log("Attempting to play: " + filename);
        media = instance.media_new(filename)
        self.player.set_media(media)
        print("Set media")
        current_song = os.path.basename(filename)
        self.labelCurrentSong.set_text(current_song)
        self.read_config()
        self.on_buttonPlay_clicked_cb(None)
        print("Setting ",filename,self.current_session_name, time.time())
        self.inifile.set_music(current_song, 'Session - ' + self.current_session_name, time.time())
        self.find_and_load_cuesheet(filename,self.textviewCueSheet)

    def find_and_load_cuesheet(self,filename,textview) :
        (root,ext) = os.path.splitext(filename)
        for alt_ext in ('.html', '.htm') :
            path = root + alt_ext
            if os.path.exists(path) :
                self.load_html_into_textview(path, textview)
                                    
                
    def get_current_song_name(self):
        return self.labelCurrentSong.get_text()

    def get_current_song_base_name(self):
        name = self.get_current_song_name()
        return re.sub(r'\s*\(.*?\)', '', name)

    def on_filechooserbuttonNextQueued_file_set_cb(self,event):
        filename = self.filechooserbuttonNextQueued.get_filename()
        self.find_and_load_cuesheet(filename, self.textviewNextCueSheet)
    
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


    def initialize_file_liststore(self, liststore):
#        liststore.set_column_types( ( GObject.TYPE_STRING,
#                                      GObject.TYPE_STRING,
#                                      GObject.TYPE_STRING ) )
        pass
    def initialize_file_treeview(self,treeview) :
        model = treeview.get_model()
        for col in (WEEKS_SINCE_PLAY_COLUMN, SONG_NAME_COLUMN, RECORD_LABEL_NAME_COLUMN) :
            model.set_sort_func(col, self.column_sort_func_method, col)

        renderer = Gtk.CellRendererText()
        renderer.set_property("xalign", 0.0)

        for (label, column_id) in (("Age", WEEKS_SINCE_PLAY_COLUMN), ("Name", SONG_NAME_COLUMN), ("Label", RECORD_LABEL_NAME_COLUMN)) :
            column = Gtk.TreeViewColumn(label, renderer, text=column_id)
            column.set_clickable(True)
            column.set_sort_column_id(column_id)
            treeview.append_column(column)

        
    def column_sort_func_method(self, model, iter1, iter2, data) :
        a = model.get_value(iter1, data)
        b = model.get_value(iter2, data)
        if a < b :
            return -1
        if a > b :
            return 1
        return 0        

    def file_row_from_name(self,name):
        current_song = os.path.basename(name)
        last_play = self.inifile.get_music(current_song, 'Session - ' + self.current_session_name, 0)
        now = time.time()
        age = now - float(last_play);
        weeks_since_last_play = int(age / (24 * 7 * 60 * 60))
        return ("   " if weeks_since_last_play > 999 else '%03.3d' % (weeks_since_last_play), name, 'Foo', name)
    
    def load_directory_into_liststore(self, filechooserbutton, liststore) :
        directory = filechooserbutton.get_filename()
        files = [self.file_row_from_name(f) for f in os.listdir(directory) if fnmatch.fnmatch(f, '*.mp3')]
        for f in sorted(files, key = lambda x: x[SONG_NAME_COLUMN]) :
            iter = liststore.append(None)
            liststore.set(iter,
                          WEEKS_SINCE_PLAY_COLUMN, f[0],
                          SONG_NAME_COLUMN, f[1],
                          RECORD_LABEL_NAME_COLUMN, f[2],
                          FILE_NAME_COLUMN, f[3]   )

        
    def on_filechooserbuttonFolder1_file_set_cb(self, event) :
        self.load_directory_into_liststore(self.filechooserbuttonFolder1, self.liststoreFolder1)
        self.treeviewFolder1.show_all()
        pass
    
    def on_filechooserbuttonFolder2_file_set_cb(self, event) :
        self.load_directory_into_liststore(self.filechooserbuttonFolder2, self.liststoreFolder2)
        pass
    
    def on_filechooserbuttonFolder3_file_set_cb(self, event) :
        self.load_directory_into_liststore(self.filechooserbuttonFolder3, self.liststoreFolder3)
        pass
    
    def on_windowApplication_delete_event(self, widget, event):
        self.write_config()
        Gtk.main_quit()


    def select_folder_line(self, treeview, liststore, filechooser) :
        (line, focus_column) = treeview.get_cursor()
        f = liststore[line]
        filename = f[3]
        folder = filechooser.get_current_folder()
        path = os.path.join(folder,filename)
        print("Selecting", filename, "in", folder)
        self.filechooserbuttonNextQueued.set_current_folder(folder)
        self.filechooserbuttonNextQueued.set_filename(path)
        self.find_and_load_cuesheet(path, self.textviewNextCueSheet)
        
        
    def on_treeviewFolder1_cursor_changed_cb(self, treeview):
        self.select_folder_line(treeview, self.liststoreFolder1, self.filechooserbuttonFolder1)

    def on_treeviewFolder2_cursor_changed_cb(self, treeview):
        self.select_folder_line(treeview, self.liststoreFolder2, self.filechooserbuttonFolder2)

    def on_treeviewFolder3_cursor_changed_cb(self, treeview):
        self.select_folder_line(treeview, self.liststoreFolder3, self.filechooserbuttonFolder3)

    def rename_session(self, from_name, to_name):
        print("Renaming session", from_name, "to", to_name) 
       

    def on_comboboxSessionName_text_entry_focus_out_event_cb(self,event, foo):
        model = self.comboboxSessionName.get_model()
        active = self.comboboxSessionName.get_active()
        new_name = self.comboboxSessionName.get_active_text()
        print("Focus out event", model, active, new_name)

        if new_name != self.current_session_name :
            if new_name == '' :
                model.remove(model.get_iter(self.current_session_name_idx))
                self.ensure_new_session_name_in_session_name_list()
                if self.current_session_name_idx >= len(model):
                    self.current_session_name_idx = len(model) - 1;
                self.comboboxSessionName.set_active(self.current_session_name_idx)
#                self.comboboxSessionName.set_active_text(model[self.current_session_name_idx])
            else :
                self.rename_session(self.current_session_name, new_name)
                model.set(model.get_iter(self.current_session_name_idx),0,new_name)

        self.ensure_new_session_name_in_session_name_list()
        self.set_current_session_name_from_control()
               
    def on_comboboxSessionName_changed_cb(self, event) :
        active = self.comboboxSessionName.get_active()
        if -1 != active and self.current_session_name_idx != active :
            print("Index changed")
            self.set_current_session_name_from_control()
            self.load_directory_into_liststore(self.filechooserbuttonFolder1, self.liststoreFolder1)
            self.load_directory_into_liststore(self.filechooserbuttonFolder2, self.liststoreFolder2)
            self.load_directory_into_liststore(self.filechooserbuttonFolder3, self.liststoreFolder3)
        pass




if __name__ == "__main__":
    try:
        a = SquarePlayGTK()
        Gtk.main()
    except KeyboardInterrupt:
        pass
