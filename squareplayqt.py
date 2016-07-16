#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import QtGui

class MyWidget(QtGui.QMainWindow):
    def __init__(self, *args):  
        QtGui.QMainWindow.__init__(self, *args)

        loader = QtUiTools.QUiLoader()
        file = QtCore.QFile("Player.ui")
        file.open(QtCore.QFile.ReadOnly)
        self.myWidget = loader.load(file, self)
        file.close()

        self.setCentralWidget(self.myWidget)

#        btn = self.myWidget.findChild(QtGui.QPushButton, "HelloWorldButton")
#        btn.clicked.connect(self.slot1)        
#
#    def slot1(self):
#        print "Received"
