import time
import re

class DisplayTimer :
    def __init__(self, update, resolution = 1) :
        self.update = update
        self.start_time = time.time()
        self.mmss_regex = re.compile(r'^\s*(\d+)\:(\d+(\.\d+)?)\s*$')
        self.ss_regex = re.compile(r'^\s*(\d+(\.\d+)?)\s*$')
        self.last_frac_seconds = 0;
        self.resolution = resolution;

    def reset(self, offset = None):
        offset_seconds = 0
        if offset != None :
            offset_seconds = self.parse_mmss_to_seconds(offset)
        self.start_time = time.time() + offset_seconds

    def parse_mmss_to_seconds(self,mmss) :
        match = self.mmss_regex.match( mmss )
        if  match != None:
            return int(match.group(1)) * 60 + float(match.group(2))
        match = self.ss_regex.match( mmss )
        if match != None :
            return float(match.group(1))
        return 0

    def seconds_to_formatted(self,seconds_in):
        sign = '';
        if seconds_in < 0:
            sign = '-'
            seconds_in = -seconds_in 
        minutes = int(seconds_in / 60);
        seconds = int(seconds_in % 60)
        fracseconds = int(100 * (seconds_in - int(seconds_in)))
        self.last_frac_seconds = fracseconds;
        return '%s%d:%02.2d.%02.2d' % (sign, minutes, seconds, fracseconds)


    def tick(self) :
        now = time.time()
        offset = now - self.start_time;
        formatted_offset = self.seconds_to_formatted(offset)
        self.update(formatted_offset)

    def next_tick(self) :
        next_tick = self.resolution;
        if self.last_frac_seconds < next_tick :
            next_tick = next_tick * 2 - self.last_frac_seconds
        return next_tick
