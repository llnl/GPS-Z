import sys
from PyQt5.QtWidgets import *
import os
import cantera as ct
import json
import time
import copy

from PyQt5 import uic
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from .def_dialog import common
from src.core.def_tools import keys_sorted, num2str

class dialog_sensitivity(common):

    # helper ============================
    def make_string(self, data):
        mech_name = data['mech_name']
        dbs = data['databases']
        string = mech_name + "|" + "_".join(dbs)
        return string

    # display ============================


    # get ============================
    def read_mechanism(self):
        mech_name = str(self.w.cb_mech.currentText())
        if(mech_name == ''):
            msg = 'Must specify a valid mechanism'
            QMessageBox.information(QWidget(),'',msg)
            return False
        self.data['mech_name'] = mech_name
        return True

    def read_databases(self):
        model = self.w.list_dbs.model()

        self.data['databases'] = []
        for j in range(model.rowCount()):
            item_name = str(model.item(j).text())    
            if model.item(j).checkState():
                self.data['databases'].append(item_name)

        if(not bool(self.data['databases'])):
            msg = 'Must include at least one database'
            QMessageBox.information(QWidget(),'',msg)
            return False
        return True

    # acts ============================


#    def act_deft_cust(self):
#        if self.w.rbtn_from_sens.isChecked():
#            #User wants to use sensitivity to define reactions
#            pass
#        else:
#            #User wants to define reactions explicitly
#            pass
        

    def act_save(self):
        
        if self.read_name() and self.read_mechanism() and self.read_databases():
            new_str = self.make_string(self.data)
            if self.old_name != None and new_str != self.old_str:    

                msg = 'warning: you modified this sensitivity analysis\n'+\
                    '1. if this analysis is used in previous calculations of the'+\
                    'current project, modifications will make data files inconsistent;\n'+\
                    '2. modifications will be applied to all tunings using this analysis'+\
                    '\n\ncontinue to save?'
                Qanswer = QMessageBox.question(QWidget(),'',msg, \
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                if Qanswer == QMessageBox.No:
                    return None
            
            self.w.accept() 


    # init ============================

    def __init__(self, parent, data_name=None, extra=None):

        ui_name = 'sensitivity.ui'
        self.parent = parent
        self.old_name = data_name    

        self.key = 'sens'
        self.occupied = self.init_occupied()

        # load ui and set connection ====================

        self.w = uic.loadUi(os.path.join(self.parent.dir_ui, ui_name))    
        self.w.setFixedSize(self.w.width(), self.w.height())    
        self.w.btn_save.clicked.connect(self.act_save)
        self.w.btn_cancel.clicked.connect(self.act_cancel)
        self.w.cb_mech.currentTextChanged.connect(self.read_mechanism)

        # set initial values =============================
        self.mech_names = ['detailed'] + parent.get_mech_names()

        if data_name is None:
            self.data = dict()
            self.data['name'] = self.new_name('sensitivity', self.occupied)
            self.data['checked'] = True
            self.data['databases'] = []
            self.data['mech_name'] = ''
        else:
            self.data = copy.copy(self.parent.project['sens'][data_name])
            self.old_str = self.make_string(self.data)

        self.w.txt_name.setText(self.data['name'])
        for m in self.mech_names:
            self.w.cb_mech.addItem(m)
        idx = self.w.cb_mech.findText(self.data['mech_name'])
        if( idx != -1 ):
            self.w.cb_mech.setCurrentIndex(idx)


        model = QStandardItemModel()
        for db in parent.project['database'].keys():
            reactor_type = parent.project['database'][db]['reactor']
            if(reactor_type[0:7] != 'autoign'):
                continue
            Qitem = QStandardItem(db)
            Qitem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            if db in self.data['databases']:
                Qitem.setData(QVariant(Qt.Checked), Qt.CheckStateRole)
            else:
                Qitem.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)

            model.appendRow(Qitem)
        self.w.list_dbs.setModel(model)

        #self.act_deft_cust()

        # exec and return =============================

        if self.w.exec_() == QDialog.Rejected:
            self.data = None



