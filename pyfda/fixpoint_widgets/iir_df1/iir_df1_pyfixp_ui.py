# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Widget for specifying the parameters of a direct-form DF1 FIR filter
"""
import sys

import numpy as np
import pyfda.filterbroker as fb
from pyfda.libs.pyfda_lib import set_dict_defaults, pprint_log
from pyfda.libs.pyfda_qt_lib import qget_cmb_box

from pyfda.libs.compat import QWidget, QVBoxLayout, pyqtSignal

from pyfda.fixpoint_widgets.fixpoint_helpers import UI_W, UI_Q
from .iir_df1_pyfixp import IIR_DF1_pyfixp

import logging
logger = logging.getLogger(__name__)

#  Dict containing {widget class name : display name}
classes = {'IIR_DF1_pyfixp_UI': 'IIR_DF1 (pyfixp)'}  # widget class name : display name


# =============================================================================
class IIR_DF1_pyfixp_UI(QWidget):
    """
    Widget for entering word formats & quantization, also instantiates fixpoint
    filter class :class:`FilterFIR`.
    """
    sig_rx = pyqtSignal(object)  # incoming
    sig_tx = pyqtSignal(object)  # outcgoing
    from pyfda.libs.pyfda_qt_lib import emit

    def __init__(self):
        super().__init__()

        self.title = ("<b>Direct-Form 1 (DF1) IIR Filter</b><br />"
                      "Canonical IIR topology.")
        self.img_name = "iir_df1.png"

        self._construct_UI()
        # Construct an instance of the fixpoint filter using the settings from
        # the 'fxqc' quantizer dict
# ------------------------------------------------------------------------------

    def _construct_UI(self):
        """
        Intitialize the UI with widgets for coefficient format and input and
        output quantization
        """
        if 'QA' not in fb.fil[0]['fxqc']:
            fb.fil[0]['fxqc']['QA'] = {}
        set_dict_defaults(fb.fil[0]['fxqc']['QA'],
                          {'WI': 0, 'WF': 30, 'W': 32, 'ovfl': 'wrap', 'quant': 'floor'})

        self.wdg_w_coeffs_b = UI_W(
            fb.fil[0]['fxqc']['QCB'], wdg_name='w_coeff_b',
            label='Coeff. Format <i>B<sub>I.F&nbsp;</sub></i>:',
            tip_WI='Number of integer bits - edit in "b,a" tab',
            tip_WF='Number of fractional bits - edit in "b,a" tab',
            WI=fb.fil[0]['fxqc']['QCB']['WI'],
            WF=fb.fil[0]['fxqc']['QCB']['WF'])

        self.wdg_w_coeffs_a = UI_W(
            fb.fil[0]['fxqc']['QCA'], wdg_name='w_coeff_a',
            label='Coeff. Format <i>A<sub>I.F&nbsp;</sub></i>:',
            tip_WI='Number of integer bits - edit in "b,a" tab',
            tip_WF='Number of fractional bits - edit in "b,a" tab',
            WI=fb.fil[0]['fxqc']['QCA']['WI'],
            WF=fb.fil[0]['fxqc']['QCA']['WF'])


#        self.wdg_q_coeffs = UI_Q(self, fb.fil[0]['fxqc']['QCB'],
#                                        cur_ov=fb.fil[0]['fxqc']['QCB']['ovfl'],
#                                        cur_q=fb.fil[0]['fxqc']['QCB']['quant'])
#        self.wdg_q_coeffs.sig_tx.connect(self.update_q_coeff)

        self.wdg_w_accu = UI_W(fb.fil[0]['fxqc']['QA'], label='', wdg_name='w_accu',
                               fractional=True, combo_visible=True)

        self.wdg_q_accu = UI_Q(fb.fil[0]['fxqc']['QA'], wdg_name='q_accu',
                               label='Accu Quantizer <i>Q<sub>A&nbsp;</sub></i>:')

        # initial setting for accumulator
        cmbW = qget_cmb_box(self.wdg_w_accu.cmbW, data=False)
        self.wdg_w_accu.ledWF.setEnabled(cmbW == 'man')
        self.wdg_w_accu.ledWI.setEnabled(cmbW == 'man')

        # ----------------------------------------------------------------------
        # LOCAL SIGNALS & SLOTs & EVENTFILTERS
        # ----------------------------------------------------------------------
        self.wdg_w_coeffs_b.sig_tx.connect(self.update_q_coeff)
        self.wdg_w_coeffs_a.sig_tx.connect(self.update_q_coeff)
        self.wdg_w_accu.sig_tx.connect(self.process_sig_rx)
        self.wdg_q_accu.sig_tx.connect(self.process_sig_rx)
# ------------------------------------------------------------------------------

        layVWdg = QVBoxLayout()
        layVWdg.setContentsMargins(0, 0, 0, 0)

        layVWdg.addWidget(self.wdg_w_coeffs_b)
        layVWdg.addWidget(self.wdg_w_coeffs_a)
#        layVWdg.addWidget(self.wdg_q_coeffs)
        layVWdg.addWidget(self.wdg_q_accu)
        layVWdg.addWidget(self.wdg_w_accu)

        layVWdg.addStretch()

        self.setLayout(layVWdg)

# ------------------------------------------------------------------------------
    def process_sig_rx(self, dict_sig=None):
        logger.warning("sig_rx:\n{0}".format(pprint_log(dict_sig)))
        # check whether anything needs to be done locally
        # could also check here for 'quant', 'ovfl', 'WI', 'WF' (not needed at the moment)
        # if not, just emit the dict.
        if 'ui' in dict_sig:
            if dict_sig['wdg_name'] in {'w_coeff_b', 'w_coeff_a'}:  # coeff. format updated
                """
                Update coefficient quantization settings and coefficients.

                The new values are written to the fixpoint coefficient dict as
                `fb.fil[0]['fxqc']['QCB']` and  `fb.fil[0]['fxqc']['b']`.
                """

                fb.fil[0]['fxqc'].update(self.ui2dict())

            elif dict_sig['wdg_name'] == 'w_accu':  # accu format updated
                cmbW = qget_cmb_box(self.wdg_w_accu.cmbW, data=False)
                self.wdg_w_accu.ledWF.setEnabled(cmbW == 'man')
                self.wdg_w_accu.ledWI.setEnabled(cmbW == 'man')
                if cmbW in {'full', 'auto'}\
                        or ('ui' in dict_sig and dict_sig['ui'] in {'WF', 'WI'}):
                    pass

                elif cmbW == 'man':  # switched to manual, don't do anything
                    return

            # Accu quantization or overflow settings have been changed
            elif dict_sig['wdg_name'] == 'q_accu':
                pass

            else:
                logger.error(f"Unknown widget name '{dict_sig['wdg_name']}' "
                             f"in '{__name__}' !")
                return

            # - update fixpoint accu and coefficient quantization dict
            # - emit {'fx_sim': 'specs_changed'}
            fb.fil[0]['fxqc'].update(self.ui2dict())
            self.emit({'fx_sim': 'specs_changed'})

        else:
            logger.error(f"Unknown key '{dict_sig['wdg_name']}' (should be 'ui')"
                         f"in '{__name__}' !")

# ------------------------------------------------------------------------------
    def update_q_coeff(self, dict_sig):
        """
        Update coefficient quantization settings and coefficients.

        The new values are written to the fixpoint coefficient dict as
        `fb.fil[0]['fxqc']['QCB']` and
        `fb.fil[0]['fxqc']['b']`.
        """
        logger.debug("update q_coeff - dict_sig:\n{0}".format(pprint_log(dict_sig)))
        # dict_sig.update({'ui':'C'+dict_sig['ui']})
        fb.fil[0]['fxqc'].update(self.ui2dict())
        logger.warning("b = {0}".format(pprint_log(fb.fil[0]['fxqc']['b'])))
        logger.warning("a = {0}".format(pprint_log(fb.fil[0]['fxqc']['a'])))

        self.process_sig_rx(dict_sig)

# ------------------------------------------------------------------------------
    def update_accu_settings(self):
        """
        Calculate number of extra integer bits needed in the accumulator (bit
        growth) depending on the coefficient area (sum of absolute coefficient
        values) for `cmbW == 'auto'` or depending on the number of coefficients
        for `cmbW == 'full'`. The latter works for arbitrary coefficients but
        requires more bits.

        The new values are written to the fixpoint coefficient dict
        `fb.fil[0]['fxqc']['QA']`.
        """
        try:
            if qget_cmb_box(self.wdg_w_accu.cmbW, data=False) == "full":
                A_coeff = int(np.ceil(np.log2(len(fb.fil[0]['fxqc']['b']))))
            elif qget_cmb_box(self.wdg_w_accu.cmbW, data=False) == "auto":
                A_coeff = int(np.ceil(np.log2(np.sum(np.abs(fb.fil[0]['ba'][0])))))
        except Exception as e:
            logger.error(e)
            return

        if qget_cmb_box(self.wdg_w_accu.cmbW, data=False) == "full" or\
                qget_cmb_box(self.wdg_w_accu.cmbW, data=False) == "auto":
            fb.fil[0]['fxqc']['QA']['WF'] = fb.fil[0]['fxqc']['QI']['WF']\
                + fb.fil[0]['fxqc']['QCB']['WF']
            fb.fil[0]['fxqc']['QA']['WI'] = fb.fil[0]['fxqc']['QI']['WI']\
                + fb.fil[0]['fxqc']['QCB']['WI'] + A_coeff

        # calculate total accumulator word length and 'Q' format
        fb.fil[0]['fxqc']['QA']['W'] = fb.fil[0]['fxqc']['QA']['WI']\
            + fb.fil[0]['fxqc']['QA']['WF'] + 1
        fb.fil[0]['fxqc']['QA']['Q'] = str(fb.fil[0]['fxqc']['QA']['WI'])\
            + '.' + str(fb.fil[0]['fxqc']['QA']['WF'])

        # update quantization settings
        fb.fil[0]['fxqc']['QA'].update(self.wdg_q_accu.q_dict)

        # update UI
        self.wdg_w_accu.dict2ui(fb.fil[0]['fxqc']['QA'])

# ------------------------------------------------------------------------------
    def dict2ui(self):
        """
        Update all parts of the UI that need to be updated when specs have been
        changed outside this class, e.g. coefficients and coefficient wordlength.
        This also provides the initial setting for the widgets when the filter has
        been changed.

        This is called from one level above by
        :class:`pyfda.input_widgets.input_fixpoint_specs.Input_Fixpoint_Specs`.
        """
        fxqc_dict = fb.fil[0]['fxqc']
        if 'QA' not in fxqc_dict:
            fxqc_dict.update({'QA': {}})  # no accumulator settings in dict yet
            logger.warning("QA key missing")

        if 'QCB' not in fxqc_dict:
            fxqc_dict.update({'QCB': {}})  # no coefficient settings in dict yet
            logger.warning("QCB key missing")
        if 'QCA' not in fxqc_dict:
            fxqc_dict.update({'QCA': {}})  # no coefficient settings in dict yet
            logger.warning("QCA key missing")

        self.wdg_w_coeffs_b.dict2ui(fxqc_dict['QCB'])  # update coefficient wordlength
        self.wdg_w_coeffs_a.dict2ui(fxqc_dict['QCA'])  # update coefficient wordlength

        self.update_accu_settings()                  # update accumulator settings

# ------------------------------------------------------------------------------
    def ui2dict(self):
        """
        Read out the quantization subwidgets and store their settings in the central
        fixpoint dictionary `fb.fil[0]['fxqc']` using the keys described below.

        Coefficients are quantized with these settings in the subdictionary under
        the keys 'b' and 'a'.

        Additionally, these subdictionaries are returned  to the caller
        (``input_fixpoint_specs``) where they are used to update ``fb.fil[0]['fxqc']``

        Parameters
        ----------

        None

        Returns
        -------
        fxqc_dict : dict

           containing the following keys and values:

        - 'QCB': dictionary with b coefficients quantization settings

        - 'QA': dictionary with accumulator quantization settings

        - 'b' : list of quantized b coefficients in format WI.WF

        - 'a' : list of quantized a coefficients in format WI.WF
        TODO: This is still the same format as 'b'

        """
        fxqc_dict = fb.fil[0]['fxqc']
        if 'QA' not in fxqc_dict:
            # no accumulator settings in dict yet:
            fxqc_dict.update({'QA': self.wdg_w_accu.q_dict})
            logger.warning("Empty dict 'fxqc['QA]'!")
        else:
            fxqc_dict['QA'].update(self.wdg_w_accu.q_dict)

        if 'QCB' not in fxqc_dict:
            # no coefficient settings in dict yet
            fxqc_dict.update({'QCB': self.wdg_w_coeffs_b.q_dict})
            logger.warning("Empty dict 'fxqc['QCB]'!")
        else:
            fxqc_dict['QCB'].update(self.wdg_w_coeffs_b.q_dict)

        if 'QCA' not in fxqc_dict:
            # no coefficient settings in dict yet
            fxqc_dict.update({'QCA': self.wdg_w_coeffs_a.q_dict})
            logger.warning("Empty dict 'fxqc['QCA]'!")
        else:
            fxqc_dict['QCA'].update(self.wdg_w_coeffs_a.q_dict)

        fxqc_dict.update({'b': self.wdg_w_coeffs_b.quant_coeffs(
            self.wdg_w_coeffs_b.q_dict, fb.fil[0]['ba'][0])})
        fxqc_dict.update({'a': self.wdg_w_coeffs_b.quant_coeffs(
            self.wdg_w_coeffs_a.q_dict, fb.fil[0]['ba'][1])})
        return fxqc_dict

# ------------------------------------------------------------------------------
    def init_filter(self):
        """
        Construct an instance of the fixpoint filter object using the settings from
        the 'fxqc' quantizer dict
        """
        p = fb.fil[0]['fxqc']  # parameter dictionary with coefficients etc.
        self.fx_filt = IIR_DF1_pyfixp(p)

# ------------------------------------------------------------------------------
    # def to_hdl(self, **kwargs):
    #     """
    #     Convert the migen description to Verilog
    #     """
    #     return verilog.convert(self.fixp_filter,
    #                            ios={self.fixp_filter.i, self.fixp_filter.o},
    #                            **kwargs)

    # ------------------------------------------------------------------------
    def fxfilter(self, stimulus):

        return self.fx_filt.fxfilter(x=stimulus)[0]


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    """ Run widget standalone with
    `python -m pyfda.fixpoint_widgets.iir_df1.iir_df1_pyfixp_ui`
    """
    from pyfda.libs.compat import QApplication
    from pyfda import pyfda_rc as rc

    app = QApplication(sys.argv)
    app.setStyleSheet(rc.qss_rc)
    mainw = IIR_DF1_pyfixp_UI()
    app.setActiveWindow(mainw)
    mainw.show()
    sys.exit(app.exec_())
