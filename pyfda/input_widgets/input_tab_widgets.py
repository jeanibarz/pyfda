# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Tabbed container for all input widgets
"""
import sys
import importlib
import logging
logger = logging.getLogger(__name__)

from ..compat import QTabWidget, QWidget, QVBoxLayout, QScrollArea, pyqtSignal

SCROLL = True

from pyfda.pyfda_rc import params
import pyfda.filterbroker as fb
from pyfda.pyfda_lib import pprint_log

class InputTabWidgets(QWidget):
    """
    Create a tabbed widget for all input subwidgets in the list ``fb.input_widgets_list``.
    This list is compiled at startup in :class:`pyfda.tree_builder.Tree_Builder`.
    """
    # signals as class variables (shared between instances if more than one exists)
    # incoming, connected here to individual senders, passed on to process sigmals
    sig_rx = pyqtSignal(object)
    # outgoing, connected in receiver (pyfdax -> plot_tab_widgets)
    sig_tx = pyqtSignal(object)


    def __init__(self, parent):
        
        super(InputTabWidgets, self).__init__(parent)
        self._construct_UI()

    def _construct_UI(self):
        """
        Initialize UI with tabbed subwidgets and connect the available signals
        of all subwidgets (not all widgets have both `sig_rx` and `sig_tx` signals).
            
        - `self.sig_rx` is distributed to all `inst.sig_rx` signals

        - all `inst.sig_tx` signals are collected in `self.sig_tx`

        - `self.sig_tx.connect(self.sig_rx)` distributes incoming signals (via
           pyfdax or coming from the input widgets) among all input widgets. 
           In order to prevent infinite loops, every widget needs to block in-
           coming signals with its own name!
        """
        tabWidget = QTabWidget(self)

        n_wdg = 0 # number and ... 
        inst_wdg_str = "" # ... full names of successfully instantiated widgets

        for input_class in fb.input_classes:
            try:
                mod_fq_name = fb.input_classes[input_class]['mod'] # fully qualified module name
                mod = importlib.import_module(mod_fq_name)
                wdg_class = getattr(mod, input_class)
                # and instantiate it
                inst = wdg_class(self)
            except ImportError as e:
                    logger.warning('Class "{0}" could not be imported from {1}:\n{2}.'\
                               .format(input_class, mod_fq_name, e))
                    continue # unsuccessful, try next widget

            if hasattr(inst, "state") and inst.state == "deactivated":
                continue # with next widget
            if hasattr(inst, 'tab_label'):
                tabWidget.addTab(inst, inst.tab_label)
            else:
                tabWidget.addTab(inst, "not set")
            if hasattr(inst, 'tool_tip'):
                tabWidget.setTabToolTip(n_wdg, inst.tool_tip)
            if hasattr(inst, 'sig_tx'):
                inst.sig_tx.connect(self.sig_tx)
            if hasattr(inst, 'sig_rx'):
                self.sig_rx.connect(inst.sig_rx)

            n_wdg += 1 # successfully instantiated one more widget
            inst_wdg_str += '\t' + mod_fq_name + "." + input_class + '\n'

        if len(inst_wdg_str) == 0:
            logger.critical("No input widgets found!")
            sys.exit()
        else:
            logger.info("Imported {0:d} input classes:\n{1}"
                        .format(n_wdg, inst_wdg_str))

        #
        # TODO: document signal options

        #----------------------------------------------------------------------
        # GLOBAL SIGNALS & SLOTs
        #----------------------------------------------------------------------       
        #self.sig_rx.connect(inst.sig_rx) # happens in _construct_UI()
        #----------------------------------------------------------------------
        # LOCAL SIGNALS & SLOTs
        #----------------------------------------------------------------------       
        self.sig_tx.connect(self.sig_rx) # loop back to local inputs
        # self.sig_rx.connect(self.log_rx) # enable for debugging
        # When user has selected a different tab, trigger a redraw of current tab
        tabWidget.currentChanged.connect(self.current_tab_changed)
        # The following does not work: maybe current scope must be left?
        # tabWidget.currentChanged.connect(tabWidget.currentWidget().redraw)

        layVMain = QVBoxLayout()

        #setContentsMargins -> number of pixels between frame window border
        layVMain.setContentsMargins(*params['wdg_margins']) 

#--------------------------------------
        if SCROLL:
            scroll = QScrollArea(self)
            scroll.setWidget(tabWidget)
            scroll.setWidgetResizable(True) # Size of monitored widget is allowed to grow:

            layVMain.addWidget(scroll)
        else:
            layVMain.addWidget(tabWidget) # add the tabWidget directly

        self.setLayout(layVMain) # set the main layout of the window

#------------------------------------------------------------------------------
    def log_rx(self, dict_sig=None):
        """
        Enable `self.sig_rx.connect(self.log_rx)` above for debugging.
        """
        if type(dict_sig) == dict:
            logger.warning("SIG_RX\n{0}"\
                .format(pprint_log(dict_sig)))
        else:
            logger.warning("empty dict")  

#------------------------------------------------------------------------------
    def current_tab_changed(self):
        self.sig_tx.emit({'sender':__name__, 'ui_changed':'tab'})

#------------------------------------------------------------------------

def main():
    from pyfda import pyfda_rc as rc
    from ..compat import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet(rc.css_rc)

    mainw = InputTabWidgets(None)
    app.setActiveWindow(mainw)
    mainw.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
