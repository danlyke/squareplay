== squareplay - a simple square dance oriented music player ==

SquarePlay is a music player for playing square dance music under
Linux, and hopefully the Mac. It requires Python3, VLC and GTK.

![screen shot](https://github.com/danlyke/squareplay/raw/master/src/images/squareplay_screenshot.png)

I was struggling to get SqView running under Wine on Linux, so I
started slinging code, and then I started adding features. This is
still kind of rough, but getting somewhere.

A few things require explanation:

![screen shot](https://github.com/danlyke/squareplay/raw/master/src/images/squareplay_screenshot_numbered.png)

1. The music tab, the tab you're currently looking at.

2. The cue sheet tab, loaded from HTML with the same name as the
   currently playing MP3 file but with a '.htm' or '.html' extension,
   and a very simplistic HTML with sizes that's supposed to be
   readable. Yes, this means that if you have multiple versions of the
   same song you need multiple cue sheet files. Still thinking about
   this.
   
3. The cue sheet tab for the song that's queued and "on deck", see #10.

4. Figures. Currently not used.

5. The progress bar, draggable. I really want to put in some notion of
   markers so that you can jump to the opener / rotations / break /
   closer. Not there yet.
   
6. Loop. The "Auto" button just chooses 20 seconds from either end of
   the currently playing song.
   
7. Session. This is to try to keep track of who I've played music for
   recently, and shows up as weeks old udner the "Label" button (which
   needs to get changed to "Age") down in the #15 music selection
   area.
   
8. The main players.

9. Tempo. Middle is whatever the song is.

10. The on-deck song and the button to play it. You can click here to
    load a song from the filesystem, or use the music selection
    area below.

11. Plays the on-deck song.

12. The songs tab, what you see.

13. A count-up timer from the last time you played the on-deck song.

14. A count-down timer, because we need to not have breaks that are
    too long.

15. The music selection area. Use as you wish, I like Patter on the
    left, Singers in the middle, singers with vocal on the right,
    though my plan is to use that more for sound effects and novelties
    (Fanfare for announcements, Happy Birthday, etc). The bars at the
    top let you select a directory, click on any song to put it
    on-deck. Note the "00" on FT-161-Time Marches On..., that's 'cause
    I played it today.
    
Options should get saved and restored to ~/.squareplay.ini

