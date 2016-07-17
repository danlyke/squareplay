#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0');
from gi.repository import Gtk
from gi.repository import GObject

import sys
import os
import fnmatch
import re
import inifiles
import time

import vlcplayer
import htmlrender
import displaytimer

        

( WEEKS_SINCE_PLAY_COLUMN,
  RECORD_LABEL_NAME_COLUMN,
  SONG_NAME_COLUMN,
  FILE_NAME_COLUMN ) = range(4)

class SquarePlayGTK:

    def __init__(self):
        self.player = vlcplayer.VLCPlayer()

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
                'entryCountdownTimer',
                'labelCountdownDisplay',
                'labelTimerDisplay',
                'entryIntroCountdown',
                'labelIntroTimer',
        ) :
            setattr(self, control, self.glade.get_object(control))

        self.htmlrenderer = htmlrender.HTMLRender()
        self.htmlrenderer.initialize_textview(self.textviewCueSheet)
        self.htmlrenderer.initialize_textview(self.textviewNextCueSheet)
            
        self.countdown_timer = \
          displaytimer.DisplayTimer(lambda t: \
                                    self.labelCountdownDisplay.set_text(t))
        self.countup_timer = \
          displaytimer.DisplayTimer(lambda t: \
                                        self.labelTimerDisplay.set_text(t))
        self.intro_timer = \
          displaytimer.DisplayTimer(lambda t: \
                                        self.labelIntroTimer.set_text(t),
                                    .1)

        self.scaleSongPosition.set_range(0,1)
        self.scaleSongTempo.set_range(.5,1.5)
        self.scaleSongTempo.set_value(1)

        self.inifile = inifiles.IniFile()

        default_directory = self.inifile.get('Last Directory', os.path.expanduser("~/Music"))
        if not os.path.exists(default_directory):
            default_directory = os.path.expanduser("~")
        
        self.filechooserbuttonNextQueued.set_current_folder(self.inifile.get('Last Directory', default_directory))


        self.reloading_music_lists = False
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
        
        self.next_queued_liststore = None
        self.next_queued_line = None
            
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

    def on_buttonIntroSet_clicked_cb(self, event) :
        now = self.player.get_position()
        formatted_now = self.intro_timer.seconds_to_formatted(now * self.player.get_length())
        print("Got position ",now, " formatted as ", formatted_now, " length ", self.player.get_length())
        self.entryIntroCountdown.set_text(formatted_now)
    
    def on_scaleSongPosition_change_value_cb(self, scale_object, scroll_type, position):
        self.player.set_position(position * self.player.get_length())

    def on_scaleSongTempo_change_value_cb(self, scale_object, scroll_type, position):
        self.player.set_tempo(position)

    def intro_timer_tick(self) :
        self.intro_timer.tick()
        GObject.timeout_add(1000*self.intro_timer.next_tick(),self.intro_timer_tick)
        return False;
        
    def timer_tick(self):
        song_position = self.player.get_position()
        self.scaleSongPosition.set_value(song_position)
        self.countup_timer.tick()

        if self.togglebuttonLoop.get_active() :
            if self.loop_start == None :
                self.loop_start = \
                  self.countup_timer.parse_mmss_to_seconds(
                      self.entryLoopFrom.get_text()
                      )
            if self.loop_end == None :
                self.loop_end = \
                  self.countup_timer.parse_mmss_to_seconds(
                      self.entryLoopTo.get_text()
                      )
            if self.loop_start != None and self.loop_end != None :
                length = self.player.get_length();
                song_position_in_seconds = length * song_position
                print("Timer tick ", length, " ", song_position, " ", song_position_in_seconds, " ", self.loop_start, " ", self.loop_end)
                if song_position_in_seconds > self.loop_end :
                    self.player.set_position(self.loop_start)
                
        return self.player.is_playing()

    def write_config(self):
        current_song = self.labelCurrentSong.get_text()
        self.inifile.set_music(current_song, 'Tempo', self.player.get_tempo() )
        self.inifile.set_music(current_song, 'Loop', '1' if self.togglebuttonLoop.get_active() else '0' )
        self.inifile.set_music(current_song, 'Loop From', self.entryLoopFrom.get_text() )
        self.inifile.set_music(current_song, 'Loop To', self.entryLoopTo.get_text() )
        self.inifile.set_music(current_song, 'Intro', self.entryIntroCountdown.get_text())

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
        self.player.set_tempo(tempo)
        self.scaleSongTempo.set_value(tempo)
        self.togglebuttonLoop.set_active(int(self.inifile.get_music(current_song, 'Loop', '0')))
        self.entryLoopFrom.set_text(self.inifile.get_music(current_song, 'Loop From', '0:00'))
        self.entryLoopTo.set_text(self.inifile.get_music(current_song, 'Loop To', '0:00'))
        self.entryIntroCountdown.set_text(self.inifile.get_music(current_song, 'Intro', '0:08.0'))

        
    def on_buttonLoopAuto_clicked_cb(self, event) :
        self.loop_start = None
        self.loop_end = None
        length = self.player.get_length();
        self.entryLoopFrom.set_text('0:20');
        self.entryLoopTo.set_text( self.countup_timer.seconds_to_formatted( length - 20) )
        self.togglebuttonLoop.set_active(1)

    def on_togglebuttonLoop_toggled_cb(self, event) :
        pass

        
    def on_buttonPlay_clicked_cb(self, event) :
        self.player.play()
        self.seconds_since_last_play = 0
        self.countup_timer.reset()
        self.intro_timer.reset(self.entryIntroCountdown.get_text())
        GObject.timeout_add(1000*1,self.timer_tick)
        GObject.timeout_add(1000*1,self.intro_timer_tick)
        GObject.timeout_add(1000*1,self.timer_set_duration_labels)

    def on_buttonStop_clicked_cb(self, event) :
        self.player.stop()
        self.player.set_position(0)

    def on_buttonPause_clicked_cb(self, event) :
        self.player.pause()

    def timer_set_duration_labels(self):
        length = self.player.get_length();
        if length < 0 :
            length = 0
        self.labelSongLength.set_text(
            self.countup_timer.seconds_to_formatted(length) )
        return False

    def load_html_into_textview(self, path, textview):
        text = ""
        with open(path, 'r') as f:
            for line in f :
                text += line
        if text == '' :
            text = '<h1>No cuesheet found at ' + path + '</h1>'
        self.htmlrenderer.set_text(textview, text)

    def play_song(self,filename, play_immediately = True) :
        self.write_config()
        self.player.load_song(filename)
        current_song = os.path.basename(filename)
        self.labelCurrentSong.set_text(current_song)
        self.read_config()
        if play_immediately :
            self.on_buttonPlay_clicked_cb(None)
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
        self.next_queued_liststore = None
        self.next_queued_line = None
    
    def on_buttonPlayNextSong_clicked_cb(self,event) :
        filename = self.filechooserbuttonNextQueued.get_filename()
        if filename != None :
            self.play_song(filename)
        if self.next_queued_liststore != None and self.next_queued_line != None :
            iter = self.next_queued_liststore.get_iter(self.next_queued_line)
            self.next_queued_liststore.set(iter, WEEKS_SINCE_PLAY_COLUMN, '***')
                    
    def on_buttonQueueNextSong_clicked_cb(self, event) :
        filename = self.filechooserbuttonNextQueued.get_filename()
        if filename != None :
            self.play_song(filename, False)
        if self.next_queued_liststore != None and self.next_queued_line != None :
            iter = self.next_queued_liststore.get_iter(self.next_queued_line)
            self.next_queued_liststore.set(iter, WEEKS_SINCE_PLAY_COLUMN, '***')
        
    def timer_countdown(self):
        self.countdown_timer.tick()
        GObject.timeout_add(1000*self.countdown_timer.next_tick(),self.timer_countdown)
        return False
                    
    def on_buttonResetCountdownTimer_clicked_cb(self, event):
        self.countdown_timer.reset(self.entryCountdownTimer.get_text())

    def on_buttonStartCountdownTimer_clicked_cb(self, event):
        GObject.timeout_add(1000*self.countdown_timer.next_tick(),self.timer_countdown)


    def initialize_file_liststore(self, liststore):
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
        liststore.clear()
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
        if not self.reloading_music_lists :
            (line, focus_column) = treeview.get_cursor()
            f = liststore[line]
            filename = f[3]
            folder = filechooser.get_current_folder()
            path = os.path.join(folder,filename)
            self.filechooserbuttonNextQueued.set_current_folder(folder)
            self.filechooserbuttonNextQueued.set_filename(path)
            self.find_and_load_cuesheet(path, self.textviewNextCueSheet)

            self.next_queued_liststore = liststore
            self.next_queued_line = line
        
        
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
        
    def reload_song_folders(self):
        self.reloading_music_lists = True
        self.load_directory_into_liststore(self.filechooserbuttonFolder1,
                                            self.liststoreFolder1)
        self.load_directory_into_liststore(self.filechooserbuttonFolder2,
                                            self.liststoreFolder2)
        self.load_directory_into_liststore(self.filechooserbuttonFolder3,
                                            self.liststoreFolder3)
        self.reloading_music_lists = False
        
               
    def on_comboboxSessionName_changed_cb(self, event) :
        active = self.comboboxSessionName.get_active()
        if -1 != active and self.current_session_name_idx != active :
            self.set_current_session_name_from_control()
            self.reload_song_folders()
        pass




if __name__ == "__main__":
    try:
        a = SquarePlayGTK()
        Gtk.main()
    except KeyboardInterrupt:
        pass
