# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Helper classes and functions for generating and simulating fixpoint filters
"""
import sys

from numpy.lib.function_base import iterable

import pyfda.libs.pyfda_fix_lib as fx

from pyfda.libs.compat import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QIcon,
    QVBoxLayout, QHBoxLayout, QFrame, pyqtSignal)

from pyfda.libs.pyfda_qt_lib import qget_cmb_box, qset_cmb_box
# from pyfda.pyfda_rc import params
from pyfda.libs.pyfda_lib import qstr, safe_eval, to_html

import logging
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
class UI_W(QWidget):
    """
    Widget for entering integer and fractional bits. The result can be read out
    via the attributes `self.WI`, `self.WF` and `self.W`.

    The constructor accepts a dictionary for initial widget settings.
    The following keys are defined; default values are used for missing keys:

    'wdg_name'      : 'ui_w'                    # widget name
    'label'         : 'WI.WF'                   # widget text label
    'visible'       : True                      # Is widget visible?
    'enabled'       : True                      # Is widget enabled?

    'fractional'    : True                      # Display WF, otherwise WF=0
    'lbl_sep'       : '.'                       # label between WI and WF field
    'max_led_width' : 30                        # max. length of lineedit field
    'WI'            : 0                         # number of frac. *bits*
    'WI_len'        : 2                         # max. number of integer *digits*
    'tip_WI'        : 'Number of integer bits'  # Mouse-over tooltip
    'WF'            : 15                        # number of frac. *bits*
    'WF_len'        : 2                         # max. number of frac. *digits*
    'tip_WF'        : 'Number of frac. bits'    # Mouse-over tooltip


    'lock_visible'  : False                     # Pushbutton for locking visible
    'tip_lock'      : 'Lock input/output quant.'# Tooltip for  lock push button

    'combo_visible' : False                     # Enable integrated combo widget
    'combo_items'   : ['auto', 'full', 'man']   # Combo selection
    'tip_combo'     : 'Calculate Acc. width.'   # tooltip for combo
    """
    # sig_rx = pyqtSignal(object)  # incoming,
    sig_tx = pyqtSignal(object)  # outcgoing
    from pyfda.libs.pyfda_qt_lib import emit

    def __init__(self, parent, q_dict, **kwargs):
        super(UI_W, self).__init__(parent)
        self.q_dict = q_dict  # pass a dict with initial settings for construction
        self._construct_UI(**kwargs)
        self.ui2dict(s='init')  # initialize the class attributes

    def _construct_UI(self, **kwargs):
        """
        Construct widget from quantization dict, individual settings and
        the default dict below """

        # default settings
        dict_ui = {'wdg_name': 'ui_w', 'label': 'WI.WF', 'lbl_sep': '.',
                   'max_led_width': 30,
                   'WI': 0, 'WI_len': 2, 'tip_WI': 'Number of integer bits',
                   'WF': 15, 'WF_len': 2, 'tip_WF': 'Number of fractional bits',
                   'enabled': True, 'visible': True, 'fractional': True,
                   'combo_visible': False, 'combo_items': ['auto', 'full', 'man'],
                   'tip_combo': 'Calculate Acc. width.',
                   'lock_visible': False, 'tip_lock': 'Lock input/output quantization.'
                   }  #: default values

        if self.q_dict:
            dict_ui.update(self.q_dict)

        for k, v in kwargs.items():
            if k not in dict_ui:
                logger.warning("Unknown key {0}".format(k))
            else:
                dict_ui.update({k: v})

        self.wdg_name = dict_ui['wdg_name']

        if not dict_ui['fractional']:
            dict_ui['WF'] = 0
        self.WI = dict_ui['WI']
        self.WF = dict_ui['WF']
        self.W = int(self.WI + self.WF + 1)
        if self.q_dict:
            self.q_dict.update({'WI': self.WI, 'WF': self.WF, 'W': self.W})
        else:
            self.q_dict = {'WI': self.WI, 'WF': self.WF, 'W': self.W}

        lblW = QLabel(to_html(dict_ui['label'], frmt='bi'), self)

        self.cmbW = QComboBox(self)
        self.cmbW.addItems(dict_ui['combo_items'])
        self.cmbW.setVisible(dict_ui['combo_visible'])
        self.cmbW.setToolTip(dict_ui['tip_combo'])
        self.cmbW.setObjectName("cmbW")

        self.butLock = QPushButton(self)
        self.butLock.setCheckable(True)
        self.butLock.setChecked(False)
        self.butLock.setVisible(dict_ui['lock_visible'])
        self.butLock.setToolTip(dict_ui['tip_lock'])

        self.ledWI = QLineEdit(self)
        self.ledWI.setToolTip(dict_ui['tip_WI'])
        self.ledWI.setMaxLength(dict_ui['WI_len'])  # maximum of 2 digits
        self.ledWI.setFixedWidth(dict_ui['max_led_width'])  # width of lineedit in points
        self.ledWI.setObjectName("WI")

        lblDot = QLabel(dict_ui['lbl_sep'], self)
        lblDot.setVisible(dict_ui['fractional'])

        self.ledWF = QLineEdit(self)
        self.ledWF.setToolTip(dict_ui['tip_WF'])
        self.ledWF.setMaxLength(dict_ui['WI_len'])  # maximum of 2 digits
        self.ledWF.setFixedWidth(dict_ui['max_led_width'])  # width of lineedit in points
        self.ledWF.setVisible(dict_ui['fractional'])
        self.ledWF.setObjectName("WF")

        layH = QHBoxLayout()
        layH.addWidget(lblW)
        layH.addStretch()
        layH.addWidget(self.cmbW)
        layH.addWidget(self.butLock)
        layH.addWidget(self.ledWI)
        layH.addWidget(lblDot)
        layH.addWidget(self.ledWF)
        layH.setContentsMargins(0, 0, 0, 0)

        frmMain = QFrame(self)
        frmMain.setLayout(layH)

        layVMain = QVBoxLayout()  # Widget main layout
        layVMain.addWidget(frmMain)
        layVMain.setContentsMargins(0, 5, 0, 0)  # *params['wdg_margins'])

        self.setLayout(layVMain)

        # ----------------------------------------------------------------------
        # INITIAL SETTINGS
        # ----------------------------------------------------------------------
        self.ledWI.setText(qstr(dict_ui['WI']))
        self.ledWF.setText(qstr(dict_ui['WF']))

        frmMain.setEnabled(dict_ui['enabled'])
        frmMain.setVisible(dict_ui['visible'])

        # ----------------------------------------------------------------------
        # LOCAL SIGNALS & SLOTs
        # ----------------------------------------------------------------------
        self.ledWI.editingFinished.connect(self.ui2dict)
        self.ledWF.editingFinished.connect(self.ui2dict)
        self.butLock.clicked.connect(self.butLock_clicked)
        self.cmbW.currentIndexChanged.connect(self.ui2dict)

        # initialize button icon
        self.butLock_clicked(self.butLock.isChecked())

    def quant_coeffs(self, q_dict: dict, coeffs: iterable, to_int: bool = False) -> list:
        """
        Quantize the coefficients, scale and convert them to integer and return them
        as a list of integers

        This is called every time one of the coefficient subwidgets is edited or changed.

        Parameters:
        -----------
        q_dict: dict
           Dictionary with quantizer settings for coefficients

        coeffs: iterable
           a list or ndarray of coefficients to be quantized

        Returns:
        --------
        A list of integer coeffcients, quantized and scaled with the settings
        of the passed quantization dict

        """
        # Create coefficient quantizer instance using the passed quantization parameters
        # dict from `input_widgets/input_coeffs.py` (and stored in the central
        # filter dict)
        Q_coeff = fx.Fixed(q_dict)
        Q_coeff.frmt = 'dec'  # always use decimal format for coefficients

        if coeffs is None:
            logger.error("Coeffs empty!")
        # quantize floating point coefficients with the selected scale (WI.WF),
        # next convert array float  -> array of fixp
        #                           -> list of int (scaled by 2^WF) when `to_int == True`
        if to_int:
            return list(Q_coeff.float2frmt(coeffs) * (1 << Q_coeff.WF))
        else:
            return list(Q_coeff.fixp(coeffs))

    # --------------------------------------------------------------------------
    def butLock_clicked(self, clicked):
        """
        Update the icon of the push button depending on its state
        """
        if clicked:
            self.butLock.setIcon(QIcon(':/lock-locked.svg'))
        else:
            self.butLock.setIcon(QIcon(':/lock-unlocked.svg'))

        q_icon_size = self.butLock.iconSize()  # <- uncomment this for manual sizing
        self.butLock.setIconSize(q_icon_size)

        dict_sig = {'wdg_name': self.wdg_name, 'ui': 'butLock'}
        self.emit(dict_sig)

    # --------------------------------------------------------------------------
    def ui2dict(self, s=None):
        """
        Update the attributes `self.WI`, `self.WF` and `self.W` and `self.q_dict`
        when one of the QLineEdit widgets has been edited.

        Emit a signal with `{'ui':objectName of the sender}`.
        """

        self.WI = int(safe_eval(self.ledWI.text(), self.WI, return_type="int",
                                sign='poszero'))
        self.ledWI.setText(qstr(self.WI))
        self.WF = int(safe_eval(self.ledWF.text(), self.WF, return_type="int",
                                sign='poszero'))
        self.ledWF.setText(qstr(self.WF))
        self.W = int(self.WI + self.WF + 1)

        self.q_dict.update({'WI': self.WI, 'WF': self.WF, 'W': self.W})

        if self.sender():
            obj_name = self.sender().objectName()
            logger.debug("sender: {0}".format(obj_name))
            dict_sig = {'wdg_name': self.wdg_name, 'ui': obj_name}
            self.emit(dict_sig)
        elif s == 'init':
            logger.debug("called by __init__")
        else:
            logger.error("sender without name!")

    # --------------------------------------------------------------------------
    def dict2ui(self, q_dict=None):
        """
        Update the widgets `WI` and `WF` and the corresponding attributes
        from the dict passed as the argument
        """
        if q_dict is None:
            q_dict = self.q_dict

        if 'WI' in q_dict:
            self.WI = safe_eval(q_dict['WI'], self.WI, return_type="int", sign='poszero')
            self.ledWI.setText(qstr(self.WI))
        else:
            logger.warning("No key 'WI' in dict!")

        if 'WF' in q_dict:
            self.WF = safe_eval(q_dict['WF'], self.WF, return_type="int", sign='poszero')
            self.ledWF.setText(qstr(self.WF))
        else:
            logger.warning("No key 'WF' in dict!")

        self.W = self.WF + self.WI + 1


# ==============================================================================
class UI_Q(QWidget):
    """
    Widget for selecting quantization / overflow options. The result can be read out
    via the attributes `self.ovfl` and `self.quant`.

    The constructor accepts a reference to the quantization dictionary for
    initial widget settings and for (re-)storing values.

    The following keys are defined; default values are used for missing keys:

    'wdg_name'  : 'ui_q'                            # widget name
    'label'     : ''                                # widget text label

    'label_q'   : 'Quant.'                          # subwidget text label
    'tip_q'     : 'Select kind of quantization.'    # Mouse-over tooltip
    'cmb_q'     : [round', 'fix', 'floor']          # combo-box choices
    'cur_q'     : 'round'                           # initial / current setting

    'label_ov'  : 'Ovfl.'                           # subwidget text label
    'tip_ov'    : 'Select overflow behaviour.'      # Mouse-over tooltip
    'cmb_ov'    : ['wrap', 'sat']                   # combo-box choices
    'cur_ov'    : 'wrap'                            # initial / current setting

    'enabled'   : True                              # Is widget enabled?
    'visible'   : True                              # Is widget visible?
    """
    # incoming,
    # sig_rx = pyqtSignal(object)
    # outcgoing
    sig_tx = pyqtSignal(object)
    from pyfda.libs.pyfda_qt_lib import emit

    def __init__(self, parent, q_dict, **kwargs):
        super(UI_Q, self).__init__(parent)
        self.q_dict = q_dict
        self._construct_UI(**kwargs)

    def _construct_UI(self, **kwargs):
        """ Construct widget """

        dict_ui = {'wdg_name': 'ui_q', 'label': '',
                   'label_q': 'Quant.', 'tip_q': 'Select the kind of quantization.',
                   'cmb_q': ['round', 'fix', 'floor'], 'cur_q': 'round',
                   'label_ov': 'Ovfl.', 'tip_ov': 'Select overflow behaviour.',
                   'cmb_ov': ['wrap', 'sat'], 'cur_ov': 'wrap',
                   'enabled': True, 'visible': True
                   }  #: default widget settings

        if 'quant' in self.q_dict and self.q_dict['quant'] in dict_ui['cmb_q']:
            dict_ui['cur_q'] = self.q_dict['quant']
        if 'ovfl' in self.q_dict and self.q_dict['ovfl'] in dict_ui['cmb_ov']:
            dict_ui['cur_ov'] = self.q_dict['ovfl']

        for key, val in kwargs.items():
            dict_ui.update({key: val})
        # dict_ui.update(map(kwargs)) # same as above?

        self.wdg_name = dict_ui['wdg_name']

        lblQuant = QLabel(dict_ui['label_q'], self)
        self.cmbQuant = QComboBox(self)
        self.cmbQuant.addItems(dict_ui['cmb_q'])
        qset_cmb_box(self.cmbQuant, dict_ui['cur_q'])
        self.cmbQuant.setToolTip(dict_ui['tip_q'])
        self.cmbQuant.setObjectName('quant')

        lblOvfl = QLabel(dict_ui['label_ov'], self)
        self.cmbOvfl = QComboBox(self)
        self.cmbOvfl.addItems(dict_ui['cmb_ov'])
        qset_cmb_box(self.cmbOvfl, dict_ui['cur_ov'])
        self.cmbOvfl.setToolTip(dict_ui['tip_ov'])
        self.cmbOvfl.setObjectName('ovfl')

        # ComboBox size is adjusted automatically to fit the longest element
        self.cmbQuant.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmbOvfl.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        layH = QHBoxLayout()
        if dict_ui['label'] != "":
            lblW = QLabel(to_html(dict_ui['label'], frmt='bi'), self)
            layH.addWidget(lblW)
        layH.addStretch()
        layH.addWidget(lblOvfl)
        layH.addWidget(self.cmbOvfl)
        # layH.addStretch(1)
        layH.addWidget(lblQuant)
        layH.addWidget(self.cmbQuant)
        layH.setContentsMargins(0, 0, 0, 0)

        frmMain = QFrame(self)
        frmMain.setLayout(layH)

        layVMain = QVBoxLayout()  # Widget main layout
        layVMain.addWidget(frmMain)
        layVMain.setContentsMargins(0, 0, 0, 0)  # *params['wdg_margins'])

        self.setLayout(layVMain)

        # ----------------------------------------------------------------------
        # INITIAL SETTINGS
        # ----------------------------------------------------------------------
        self.ovfl = qget_cmb_box(self.cmbOvfl, data=False)
        self.quant = qget_cmb_box(self.cmbQuant, data=False)
        frmMain.setEnabled(dict_ui['enabled'])
        frmMain.setVisible(dict_ui['visible'])

        # ----------------------------------------------------------------------
        # LOCAL SIGNALS & SLOTs
        # ----------------------------------------------------------------------
        self.cmbOvfl.currentIndexChanged.connect(self.ui2dict)
        self.cmbQuant.currentIndexChanged.connect(self.ui2dict)

    # --------------------------------------------------------------------------
    def ui2dict(self):
        """
        Update the quantization dict and the attributes `self.ovfl` and
        `self.quant` from the UI
        """
        self.ovfl = self.cmbOvfl.currentText()
        self.quant = self.cmbQuant.currentText()

        self.q_dict.update({'ovfl': self.ovfl,
                            'quant': self.quant})

        if self.sender():
            obj_name = self.sender().objectName()
            dict_sig = {'wdg_name': self.wdg_name, 'ui': obj_name}
            self.emit(dict_sig)

    # --------------------------------------------------------------------------
    def dict2ui(self, q_dict):
        """ Update UI from passed dictionary """
        pass


# ==============================================================================
if __name__ == '__main__':

    from pyfda.libs.compat import QApplication
    app = QApplication(sys.argv)
    mainw = UI_W(None)
    mainw.show()

    app.exec_()
