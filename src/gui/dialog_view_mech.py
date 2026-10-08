
import sys
from PyQt5.QtWidgets import *
import os
import cantera as ct
import json
import time
import shutil
import copy

from PyQt5 import uic
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from src.ct.def_lwsoln import get_lwsoln

class dialog_view_mech(object):
	def set_summary(self):
		self.w.txt_n_e.setText(': ' + str(self.soln.n_elements))
		self.w.txt_n_sp.setText(': ' + str(self.soln.n_species))
		self.w.txt_n_rxn.setText(': ' + str(self.soln.n_reactions))

	def set_lists(self):
		for e in self.soln.element_names:
			self.w.cb_e.addItem(e)
		for sp in self.soln.species_names:
			self.w.cb_sp.addItem(sp)
		for rxn in self.soln.reaction_equations():
			self.w.cb_rxn.addItem(rxn)

	def act_ok(self):
		self.w.accept()

	# init ============================
	def __init__(self, parent, data_name=None, btn=None):
		ui_name = 'view_mech.ui'
		self.parent = parent
		self.data_name = data_name

		# load ui and set connection ====================

		self.w = uic.loadUi(os.path.join(parent.dir_ui, ui_name))
		self.w.btn_ok.clicked.connect(self.act_ok)

		# set initial values =============================

		#dir_desk = os.path.join(self.parent.project['dir_public'],data_name)
		#dir_desk_mech = os.path.join(dir_desk,'mech')
		dir_desk = self.parent.project['mech'][data_name]['desk']
		path_yaml = os.path.join(dir_desk,'mech','chem.yaml')
		if os.path.exists(path_yaml) == False:
			msg = 'no chem.yaml file\n\n'+path_yaml
			QMessageBox.information(QWidget(),'',msg)
			return None

		self.soln = get_lwsoln(path_yaml)
		self.w.txt_name.setText(': '+ data_name)
		self.set_summary()
		self.set_lists()
		if btn is not None:
			btn.setEnabled(True)
			btn.setText('view')

		# exec and return =============================

		self.w.exec_()

