from gi.repository import Gtk
from gi.repository import Pango

from html.parser import HTMLParser

class HTMLRender(HTMLParser):
    __inline = [ "b", "i", "strong", "em", "cite" ]
    __block = [ "h1", "h2", "h3", "h4", "h5", "h6", "p", "dl", "dt", "dd", "br",
                    "hr" ]
    __ignore = [ "body", "html", "div", "span",
                     "font", "a", "img", "u", "nobr", "l" ]
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
         'hr': { 'font': "sans 14",
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
