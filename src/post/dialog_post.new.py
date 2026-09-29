
import os
import sys

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from ..gui.def_dialog import common


class dialog_post(common):

    """ >>>>>>>>>>>>>------------------------------------------------
    1. dialog_post
         called by: window_main
                                                     
    """

    # act ==============================

    def act_forward(self):
        self.plot_idx += 1
        if(self.plot_idx >= len(self.plotfilenames)):
            self.plot_idx = 0
        self.update_img()

    def act_backward(self):
        self.plot_idx -= 1
        if(self.plot_idx < 0):
            self.plot_idx = len(self.plotfilenames) - 1
        self.update_img()

    def update_img(self):
        from PyQt5.QtGui import QPixmap
        pixmap = QPixmap(self.plotfilenames[self.plot_idx])
        self.w.plot_label.setVisible(True)
        self.w.plot_label.setPixmap(pixmap)

    # init ============================

    def __init__(self, parent):

        self.parent = parent

        # set connection ====================
        self.w = QDialog()
        outer = QVBoxLayout()
        
        self.w.plot_label = QLabel()
        outer.addWidget(self.w.plot_label)
        buttons = QHBoxLayout()
        self.w.backward= QPushButton("<-")
        self.w.forward = QPushButton("->")
        buttons.addWidget(self.w.backward)
        buttons.addWidget(self.w.forward)
        outer.addLayout(buttons)
        self.w.setLayout(outer)
        self.w.setWindowTitle("GPS Testing Plots")

        self.w.forward.clicked.connect(self.act_forward)
        self.w.backward.clicked.connect(self.act_backward)

        # set variables ==============================

        self.plotfilenames = parent.plotfilenames
        self.plot_idx = 0
        self.update_img()
        
        # exec ==============================

        self.w.exec_()

