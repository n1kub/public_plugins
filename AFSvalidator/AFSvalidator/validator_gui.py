# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'validator_gui.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(418, 100)
        self.lineEdit = QLineEdit(Dialog)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setGeometry(QRect(10, 10, 311, 20))
        self.browse = QPushButton(Dialog)
        self.browse.setObjectName(u"browse")
        self.browse.setGeometry(QRect(330, 10, 75, 23))
        self.validateafs = QPushButton(Dialog)
        self.validateafs.setObjectName(u"validateafs")
        self.validateafs.setGeometry(QRect(10, 40, 391, 41))

        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Validate AFS", None))
        self.browse.setText(QCoreApplication.translate("Dialog", u"Browse", None))
        self.validateafs.setText(QCoreApplication.translate("Dialog", u"Validate AFS", None))
    # retranslateUi

