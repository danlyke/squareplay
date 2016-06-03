#!/usr/bin/python3

import configparser
import os.path

class IniFile :
    def __init__(self):
        self.configfile = os.path.expanduser("~/.squareplay.ini")
        self.config = configparser.RawConfigParser()
        self.main_section = 'Squareplay'
        self.read()

    def read(self):
        if os.path.exists(self.configfile) :
            self.config.read(self.configfile)
    def write(self):
        with open(self.configfile, 'w') as f:
            self.config.write(f)

    def add_section(self,section) :
        try:
            self.config.add_section(section)
        except configparser.DuplicateSectionError :
            pass

    def get(self, attr, default = ''):
        value = default
        try:
            value = self.config.get(self.main_section, attr)
        except configparser.NoOptionError :
            pass
        return value
        
    def set(self, attr, value):
        self.add_section(self.main_section)
        return self.config.set(self.main_section, attr, value)

    def get_music(self, song, attr, default = ''):
        value = default
        try:
            value = self.config.get('Song - ' + song, attr)
        except configparser.NoOptionError :
            pass
        return value
        
    def set_music(self, song, attr, value):
        self.add_section('Song - ' + song)
        return self.config.set(self.main_section, attr, value)
    
    

if __name__ == "__main__":
    inifile = IniFile()
    inifile.set('Last Folder', '/foo/bar')
    print("Last folder ", inifile.get('Last Folder'))
    inifile.write()
    inifile = IniFile()
    print("Last folder ", inifile.get('Last Folder'))
    print("Should throw an error", inifile.get('Foo'))
    

