import sys
from PyQt5.QtWidgets import *
import os
import cantera as ct
import json
import time
import copy
import numpy as np

from PyQt5 import uic
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from .def_dialog import common
from src.core.def_tools import keys_sorted, num2str
from .def_run_pool import run_sens

class dialog_tuning(common):

    # helper ============================

    def make_string(self, data):
        reactions = list(data['reactions'].keys())
        reactions.sort()


        mech_name = data['mech_name']
        db_str = '_'.join([d for d in data['databases']])
        rxn_str = '_'.join(reactions)
        txt = f"{mech_name}_{db_str}_{rxn_str}"
        return  txt

    # display ============================
    def set_table_rxns(self):
        model = QStandardItemModel()
        n_row = 0

        rxns = list(self.data['reactions'].keys())
        for rxn in rxns:
            if(rxn in self.rxn_list):
                Qitem_rxn = QStandardItem(rxn)
                Qitem_rxn.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                model.setItem(n_row,0, Qitem_rxn)
                n_row += 1
            else:
                del self.data['reactions'][rxn]

        self.w.table_rxn.setModel(model)
        for i_row in range(n_row):
            self.w.table_rxn.setRowHeight(i_row,20)

        self.w.table_rxn.setColumnWidth(0, 400)


    # get ============================
    def read_mechanism(self, save=False):
        mech_name = str(self.w.cb_mech.currentText())
        if(mech_name == ''):
            if(save):
                msg = 'Must specify a valid mechanism'
                QMessageBox.information(QWidget(),'',msg)
            return False
        self.data['mech_name'] = mech_name
        self.set_rxn_list()
        self.set_table_rxns()
        return True

    def read_sensitivity(self):
        sens_name = str(self.w.cb_sens.currentText())
        self.set_sens_rxns_list()
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

    def read_rxns(self):
        if bool(self.data['reactions']):
            return True
        else:
            msg = 'this list does not contain any reactions'
            QMessageBox.information(QWidget(),'',msg)
            return False

    # set ============================
    def set_rxn_list(self):
        mech_name = str(self.w.cb_mech.currentText())
        self.rxn_list = []
        if(mech_name in self.mech_names):
            self.rxn_list = self.parent.get_soln(mech_name).reaction_equations()

        self.w.cb_rxn.blockSignals(True)
        self.w.cb_rxn.clear()
        self.w.cb_rxn.addItems(self.rxn_list)
        self.w.cb_rxn.blockSignals(False)

    def set_sensitivity(self):
        self.w.cb_sens.blockSignals(True)
        self.w.cb_sens.clear()
        self.w.cb_sens.addItems(self.sensitivities)
        self.w.cb_sens.blockSignals(False)

    def set_sens_rxns_list(self):
        sens_name = str(self.w.cb_sens.currentText())
        if(not sens_name):
            return
        sens = self.sensitivities[sens_name]
        sorted_idxs = np.argsort(-1*np.abs(sens['srels']))
        num_sens_reactions = self.w.spin_sens_numrxn.value()
        exclude_small = self.w.ck_exsm.isChecked()

        model = QStandardItemModel()
        n_row = 0
        idx = 0
        while n_row < num_sens_reactions and idx < len(sorted_idxs):
            sorted_idx = sorted_idxs[idx]
            mw = sens['mws'][sorted_idx]
            if(not exclude_small or mw > 80):
                rxn = sens['eqs'][sorted_idx]
                Qitem_rxn = QStandardItem(rxn)
                Qitem_rxn.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                model.setItem(n_row,0, Qitem_rxn)
                n_row += 1
            idx += 1

        self.w.table_rxn_sens.setModel(model)
        for i_row in range(n_row):
            self.w.table_rxn_sens.setRowHeight(i_row,20)

        self.w.table_rxn_sens.setColumnWidth(0, 400)

    # acts ============================

    def act_cell(self):
        j = self.w.table_rxn.currentIndex().row()
        if j>=0:
            rxn = str(self.w.table_rxn.model().item(j,0).text())
            index = self.rxn_list.index(rxn)
            self.w.cb_rxn.setCurrentIndex(index)


    def act_del_rxn(self):
        j = self.w.table_rxn.currentIndex().row()
        if j>=0:
            rxn = str(self.w.table_rxn.model().item(j,0).text())            
            del self.data['reactions'][rxn]
            self.set_table_rxns()

    def act_add_rxn(self, rxn=None):
        if(not rxn):
            rxn = str(self.w.cb_rxn.currentText())
        if rxn in self.rxn_list:
            self.data['reactions'][rxn] = True
            self.set_table_rxns()

    def act_add_sens_rxns(self):
        model = self.w.table_rxn_sens.model()

        for row in range(model.rowCount()):
            idx = model.index(row,0)
            rxn = model.data(idx)
            self.act_add_rxn(rxn=rxn)


    def act_save(self):
        if self.read_name() and self.read_rxns() and self.read_mechanism() and self.read_databases():
            new_str = self.make_string(self.data)
            if self.old_name != None and new_str != self.old_str:    

                msg = 'warning: you modified this tuning job\n'+\
                    '1. if this job is used in previous calculations of the'+\
                    'current project, modifications will make data files inconsistent;\n'+\
                    '2. modifications will be applied to all tunings using this job'+\
                    '\n\ncontinue to save?'
                Qanswer = QMessageBox.question(QWidget(),'',msg, \
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                if Qanswer == QMessageBox.No:
                    return None
            
            self.w.accept() 




    # init ============================

    def __init__(self, parent, data_name=None, extra=None):

        ui_name = 'tuning.ui'
        self.parent = parent
        self.old_name = data_name    

        self.key = 'tune'
        self.occupied = self.init_occupied()

        # load ui and set connection ====================

        self.w = uic.loadUi(os.path.join(self.parent.dir_ui, ui_name))    
        self.w.setFixedSize(self.w.width(), self.w.height())    

        # set initial values =============================
        self.mech_names = parent.get_mech_names()
        old_stream = None
        try:
            old_stream = parent.progress_stream
        except:
            pass
        parent.progress_stream = open(os.devnull,'w')

        self.sensitivities = run_sens(parent, progress_signal=None, check_only=True)

        parent.progress_stream.close()
        if(old_stream):
            parent.progress_stream = old_stream

        if data_name is None:
            self.data = dict()
            self.data['name'] = self.new_name('tune', self.occupied)
            self.data['mech_name'] = ''
            self.data['databases'] = []
            self.data['reactions'] = dict()
            self.data['checked'] = True
        else:
            self.data = copy.copy(self.parent.project['tune'][data_name])
            self.old_str = self.make_string(self.data)

        for m in self.mech_names:
            self.w.cb_mech.addItem(m)
         
        idx = self.w.cb_mech.findText(self.data['mech_name'])
        if( idx != -1 ):
            self.w.cb_mech.setCurrentIndex(idx)

        model = QStandardItemModel()
        for db in parent.project['database'].keys():
            reactor_type = parent.project['database'][db]['reactor']
            Qitem = QStandardItem(db)
            Qitem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            if db in self.data['databases']:
                Qitem.setData(QVariant(Qt.Checked), Qt.CheckStateRole)
            else:
                Qitem.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole)

            model.appendRow(Qitem)
        self.w.list_dbs.setModel(model)

        self.set_rxn_list()
        self.set_table_rxns()
        self.set_sensitivity()

        self.w.txt_name.setText(self.data['name'])

        self.w.spin_sens_numrxn.setRange(0, 40)
        self.w.spin_sens_numrxn.setValue(0)

        #self.act_deft_cust()
        self.w.btn_add_rxn.clicked.connect(self.act_add_rxn)
        self.w.btn_del_rxn.clicked.connect(self.act_del_rxn)
        self.w.table_rxn.clicked.connect(self.act_cell)
        self.w.btn_save.clicked.connect(self.act_save)
        self.w.btn_cancel.clicked.connect(self.act_cancel)
        self.w.cb_mech.currentTextChanged.connect(self.read_mechanism)
        self.w.cb_sens.currentTextChanged.connect(self.read_sensitivity)
        self.w.btn_add_sens_rxns.clicked.connect(self.act_add_sens_rxns)
        self.w.spin_sens_numrxn.valueChanged.connect(self.set_sens_rxns_list)
        self.w.ck_exsm.clicked.connect(self.set_sens_rxns_list)


        # exec and return =============================

        if self.w.exec_() == QDialog.Rejected:
            self.data = None



