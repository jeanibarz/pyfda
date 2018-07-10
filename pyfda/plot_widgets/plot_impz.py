# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Widget for plotting impulse and general transient responses
"""
from __future__ import print_function, division, unicode_literals, absolute_import
import logging
logger = logging.getLogger(__name__)

from ..compat import QWidget, QEvent, Qt, pyqtSignal, QTabWidget, QVBoxLayout, QLabel

import numpy as np
import scipy.signal as sig
import matplotlib.patches as mpl_patches

import pyfda.filterbroker as fb
from pyfda.pyfda_lib import expand_lim, to_html, safe_eval
from pyfda.pyfda_rc import params # FMT string for QLineEdit fields, e.g. '{:.3g}'
from pyfda.plot_widgets.mpl_widget import MplWidget
#from mpl_toolkits.mplot3d.axes3d import Axes3D
from .plot_impz_ui import PlotImpz_UI


class Plot_Impz(QWidget):
    """
    Construct a widget for plotting impulse and general transient responses
    """
    # incoming
    sig_rx = pyqtSignal(object)
    # outgoing, e.g. when stimulus has been calculated
    sig_tx = pyqtSignal(object)
    
    def __init__(self, parent):
        super(Plot_Impz, self).__init__(parent)

        self.ACTIVE_3D = False
        self.ui = PlotImpz_UI(self) # create the UI part with buttons etc.
        
        # initial settings for line edit widgets
        self.f1 = self.ui.f1
        self.f2 = self.ui.f2
        self.needs_draw = True   # flag whether plot needs to be updated 
        self.needs_redraw = True # flag whether plot needs to be redrawn
        self.tool_tip = "Impulse and transient response"
        self.tab_label = "h[n]"

        self._construct_UI()

    def _construct_UI(self):
        """
        Create the top level UI of the widget, consisting of matplotlib widget
        and control frame.
        """
        
        #----------------------------------------------------------------------
        # MplWidget for time domain plots
        #----------------------------------------------------------------------
        self.mplwidget_t = MplWidget(self)
        self.mplwidget_t.layVMainMpl.addWidget(self.ui.wdg_ctrl_time)
        self.mplwidget_t.layVMainMpl.setContentsMargins(*params['wdg_margins'])
        
        #----------------------------------------------------------------------
        # MplWidget for frequency domain plots
        #----------------------------------------------------------------------
        self.mplwidget_f = MplWidget(self)
        self.mplwidget_f.layVMainMpl.addWidget(self.ui.wdg_ctrl_freq)
        self.mplwidget_f.layVMainMpl.setContentsMargins(*params['wdg_margins'])

        #----------------------------------------------------------------------
        # MplWidget for stimulus plots
        #----------------------------------------------------------------------
        self.mplwidget_s = MplWidget(self)
        self.mplwidget_s.layVMainMpl.addWidget(self.ui.wdg_ctrl_stim)
        self.mplwidget_s.layVMainMpl.setContentsMargins(*params['wdg_margins'])


        # Tabbed layout, tabs to the left
        tabWidget = QTabWidget(self)
        tabWidget.addTab(self.mplwidget_t, "Time")
        tabWidget.addTab(self.mplwidget_f, "Frequency")
        tabWidget.addTab(self.mplwidget_s, "Stimuli")
        tabWidget.setTabPosition(QTabWidget.West)
        layVMain = QVBoxLayout()
        layVMain.addWidget(tabWidget)
        layVMain.addWidget(self.ui.wdg_ctrl_run)
        layVMain.setContentsMargins(*params['wdg_margins'])#(left, top, right, bottom)

        self.setLayout(layVMain)
        #----------------------------------------------------------------------
        # SIGNALS & SLOTs
        #----------------------------------------------------------------------
        # frequency widgets require special handling as they are scaled with f_s
        self.ui.ledFreq1.installEventFilter(self)
        self.ui.ledFreq2.installEventFilter(self)

        self.mplwidget_t.mplToolbar.sig_tx.connect(self.process_sig_rx) # connect to toolbar
        self.mplwidget_f.mplToolbar.sig_tx.connect(self.process_sig_rx) # connect to toolbar

        self.sig_rx.connect(self.ui.sig_rx)
        self.ui.sig_tx.connect(self.process_sig_rx) # connect to widgets and signals upstream

        self.draw() # initial calculation and drawing

#------------------------------------------------------------------------------
    def process_sig_rx(self, dict_sig=None):
        """
        Process signals coming from the navigation toolbar and input_tab_widgets
        """
        logger.debug("Processing {0} | needs_draw = {1}, visible = {2}"\
                     .format(dict_sig, self.needs_draw, self.isVisible()))
        if dict_sig['sender'] == __name__:
            logger.warning("Stopped infinite loop, {0}".format(dict_sig))
        if 'fx_sim' in dict_sig:
            try:
                if dict_sig['fx_sim'] == 'get_stimulus':
                    self.calc_stimulus() # calculate selected stimulus with selected length
                    # pass stimulus in self.x back  via dict
                    self.sig_tx.emit({'sender':__name__, 'fx_sim':'set_stimulus',
                                      'fx_stimulus':self.x})
                elif dict_sig['fx_sim'] == 'set_results':
                    self.y = dict_sig['fx_results']
                    logger.info("Received fixpoint results.")
                    self.calc_y_real_imag()
                    self.calc_fft()
                    self.draw_impz()
                    
            except KeyError as e:
                logger.error('Interface to fixpoint simulation is defect:\n{0}.'.format(e))
                self.fx_sim = None

        if self.isVisible():
            if 'data_changed' in dict_sig or 'specs_changed' in dict_sig\
                or 'view_changed' in dict_sig or 'home' in dict_sig or self.needs_draw:
                self.draw()
                self.needs_draw = False
                self.needs_redraw = False
            elif 'ui_changed' in dict_sig and dict_sig['ui_changed'] == 'resized'\
                    or self.needs_redraw:
                self.redraw()
                self.needs_redraw = False
        else:
            if 'data_changed' in dict_sig or 'specs_changed' in dict_sig:
                self.needs_draw = True
            elif 'ui_changed' in dict_sig and dict_sig['ui_changed'] == 'resized':
                self.needs_redraw = True

#------------------------------------------------------------------------------
    def eventFilter(self, source, event):
        """
        Filter all events generated by the monitored widgets. Source and type
        of all events generated by monitored objects are passed to this eventFilter,
        evaluated and passed on to the next hierarchy level.

        - When a QLineEdit widget gains input focus (`QEvent.FocusIn`), display
          the stored value from filter dict with full precision
        - When a key is pressed inside the text field, set the `spec_edited` flag
          to True.
        - When a QLineEdit widget loses input focus (`QEvent.FocusOut`), store
          current value normalized to f_S with full precision (only if
          `spec_edited`== True) and display the stored value in selected format
        """

        def _store_entry(source):
            if self.spec_edited:
                if source.objectName() == "stimFreq1":
                   self.f1 = safe_eval(source.text(), self.f1 * fb.fil[0]['f_S'],
                                            return_type='float') / fb.fil[0]['f_S']
                   source.setText(str(params['FMT'].format(self.f1 * fb.fil[0]['f_S'])))

                elif source.objectName() == "stimFreq2":
                   self.f2 = safe_eval(source.text(), self.f2 * fb.fil[0]['f_S'],
                                            return_type='float') / fb.fil[0]['f_S']
                   source.setText(str(params['FMT'].format(self.f2 * fb.fil[0]['f_S'])))

                self.spec_edited = False # reset flag
                self.draw()

#        if isinstance(source, QLineEdit): 
#        if source.objectName() in {"stimFreq1","stimFreq2"}:
        if event.type() in {QEvent.FocusIn,QEvent.KeyPress, QEvent.FocusOut}:
            if event.type() == QEvent.FocusIn:
                self.spec_edited = False
                self.load_fs()
            elif event.type() == QEvent.KeyPress:
                self.spec_edited = True # entry has been changed
                key = event.key()
                if key in {Qt.Key_Return, Qt.Key_Enter}:
                    _store_entry(source)
                elif key == Qt.Key_Escape: # revert changes
                    self.spec_edited = False
                    if source.objectName() == "stimFreq1":                    
                        source.setText(str(params['FMT'].format(self.f1 * fb.fil[0]['f_S'])))
                    elif source.objectName() == "stimFreq2":                    
                        source.setText(str(params['FMT'].format(self.f2 * fb.fil[0]['f_S'])))

            elif event.type() == QEvent.FocusOut:
                _store_entry(source)

        # Call base class method to continue normal event processing:
        return super(Plot_Impz, self).eventFilter(source, event)

#-------------------------------------------------------------        
    def load_fs(self):
        """
        Reload sampling frequency from filter dictionary and transform
        the displayed frequency spec input fields according to the units
        setting (i.e. f_S). Spec entries are always stored normalized w.r.t. f_S 
        in the dictionary; when f_S or the unit are changed, only the displayed values
        of the frequency entries are updated, not the dictionary!

        load_fs() is called during init and when the frequency unit or the
        sampling frequency have been changed.

        It should be called when sigSpecsChanged or sigFilterDesigned is emitted
        at another place, indicating that a reload is required.
        """

        # recalculate displayed freq spec values for (maybe) changed f_S
        if self.ui.ledFreq1.hasFocus():
            # widget has focus, show full precision
            self.ui.ledFreq1.setText(str(self.f1 * fb.fil[0]['f_S']))
        elif self.ui.ledFreq2.hasFocus():
            # widget has focus, show full precision
            self.ui.ledFreq2.setText(str(self.f2 * fb.fil[0]['f_S']))
        else:
            # widgets have no focus, round the display
            self.ui.ledFreq1.setText(
                str(params['FMT'].format(self.f1 * fb.fil[0]['f_S'])))
            self.ui.ledFreq2.setText(
                str(params['FMT'].format(self.f2 * fb.fil[0]['f_S'])))

#------------------------------------------------------------------------------
    def init_axes(self):
        # clear the axes and (re)draw the plot
        #
        for ax in self.mplwidget_t.fig.get_axes():
            self.mplwidget_t.fig.delaxes(ax)

        num_subplots = 0 + (self.ui.plt_time != "None")\
                        + (self.cmplx and self.ui.plt_time in {"Response", "Both"})\
                        + (self.ui.plt_freq != "None")

        if num_subplots > 0:
            self.mplwidget_t.fig.subplots_adjust(hspace = 0.5)
    
            if self.ui.plt_time != "None":
                self.ax_r = self.mplwidget_t.fig.add_subplot(num_subplots,1 ,1)
                self.ax_r.clear()
                self.ax_r.get_xaxis().tick_bottom() # remove axis ticks on top
                self.ax_r.get_yaxis().tick_left() # remove axis ticks right
    
            if self.cmplx and self.ui.plt_time in {"Response", "Both"}:
                self.ax_i = self.mplwidget_t.fig.add_subplot(num_subplots, 1, 2, sharex = self.ax_r)
                self.ax_i.clear()
                self.ax_i.get_xaxis().tick_bottom() # remove axis ticks on top
                self.ax_i.get_yaxis().tick_left() # remove axis ticks right
    
            if self.ui.plt_freq != "None":
                self.ax_fft = self.mplwidget_t.fig.add_subplot(num_subplots, 1, num_subplots)    
                self.ax_fft.clear()

                self.ax_fft.get_xaxis().tick_bottom() # remove axis ticks on top
                self.ax_fft.get_yaxis().tick_left() # remove axis ticks right
    
            if self.ACTIVE_3D: # not implemented / tested yet
                self.ax3d = self.mplwidget_t.fig.add_subplot(111, projection='3d')

#------------------------------------------------------------------------------
    def calc_stimulus(self):
        """
        (Re-)calculate stimulus x[n] and filter response y[n]
        """
        self.n = np.arange(self.ui.N_end)
        self.t = self.n / fb.fil[0]['f_S']

        # calculate stimuli x[n] ==============================================
        if self.ui.stim == "Pulse":
            self.x = np.zeros(self.ui.N_end)
            self.x[0] = self.ui.A1 # create dirac impulse as input signal
            self.title_str = r'Impulse Response'
            self.H_str = r'$h[n]$' # default

        elif self.ui.stim == "Step":
            self.x = self.ui.A1 * np.ones(self.ui.N_end) # create step function
            self.title_str = r'Filter Step Response'
            self.H_str = r'$h_{\epsilon}[n]$'
            
        elif self.ui.stim == "StepErr":
            self.x = self.ui.A1 * np.ones(self.ui.N_end) # create step function
            self.title_str = r'Settling Error'
            self.H_str = r'$h_{\epsilon, \infty} - h_{\epsilon}[n]$'
            
        elif self.ui.stim == "Cos":
            self.x = self.ui.A1 * np.cos(2 * np.pi * self.n * self.f1) +\
                self.ui.A2 * np.cos(2 * np.pi * self.n * self.f2 + self.ui.phi2)
            self.title_str = r'Filter Response to Cosine Signal'
            self.H_str = r'$y[n]$'
                
        elif self.ui.stim == "Sine":
            self.x = self.ui.A1 * np.sin(2 * np.pi * self.n * self.f1 + self.ui.phi1) +\
                self.ui.A2 * np.sin(2 * np.pi * self.n * self.f2 + self.ui.phi2)
            self.title_str = r'Filter Response to Sinusoidal Signal'
            self.H_str = r'$y[n]$'
            
        elif self.ui.stim == "Rect":
            self.x = self.ui.A1 * np.sign(np.sin(2 * np.pi * self.n * self.f1))
            self.title_str = r'Filter Response to Rect. Signal'
            self.H_str = r'$y[n]$'

        elif self.ui.stim == "Saw":
            self.x = self.ui.A1 * sig.sawtooth(self.n * self.f1 * 2*np.pi)
            self.title_str = r'Filter Response to Sawtooth Signal'
            self.H_str = r'$y[n]$'

        else:
            logger.error('Unknown stimulus "{0}"'.format(self.ui.stim))
            return
        
        # Add noise to stimulus
        if self.ui.noise == "gauss":
            self.x[self.ui.N_start:] += self.ui.noi * np.random.randn(self.ui.N)
        elif self.ui.noise == "uniform":
            self.x[self.ui.N_start:] += self.ui.noi * (np.random.rand(self.ui.N)-0.5)

        # Add DC to stimulus when visible / enabled
        if self.ui.ledDC.isVisible:
            self.x += self.ui.DC

#------------------------------------------------------------------------------
    def calc_response(self):
        """
        (Re-)calculate filter response y[n]
        """
        # calculate response self.y_r[n] and self.y_i[n] (for complex case) =====   
        self.bb = np.asarray(fb.fil[0]['ba'][0])
        self.aa = np.asarray(fb.fil[0]['ba'][1])
        if min(len(self.aa), len(self.bb)) < 2:
            logger.error('No proper filter coefficients: len(a), len(b) < 2 !')
            return

        sos = np.asarray(fb.fil[0]['sos'])
        antiCausal = 'zpkA' in fb.fil[0]
        causal     = not (antiCausal)

        if len(sos) > 0 and causal: # has second order sections and is causal
            y = sig.sosfilt(sos, self.x)
        elif antiCausal:
            y = sig.filtfilt(self.bb, self.aa, self.x, -1, None)
        else: # no second order sections or antiCausals for current filter
            y = sig.lfilter(self.bb, self.aa, self.x)

        if self.ui.stim == "StepErr":
            dc = sig.freqz(self.bb, self.aa, [0]) # DC response of the system
            y = y - abs(dc[1]) # subtract DC (final) value from response

        self.y = np.real_if_close(y, tol = 1e3)  # tol specified in multiples of machine eps

#------------------------------------------------------------------------------
    def calc_y_real_imag(self):
        """
        Check whether y is complex and calculate imag. / real components
        """
        self.cmplx = np.any(np.iscomplex(self.y))
        if self.cmplx:
            self.y_i = self.y.imag
            self.y_r = self.y.real
        else:
            self.y_r = self.y
            self.y_i = None

#------------------------------------------------------------------------------
    def calc_fft(self):
        """
        (Re-)calculate ffts X(f) and Y(f) of stimulus and response
        """
        # calculate FFT of stimulus / response
#        if self.ui.plt_freq in {"Stimulus", "Both"}:
        x_win = self.x[self.ui.N_start:self.ui.N_end] * self.ui.win
        self.X = np.abs(np.fft.fft(x_win)) / self.ui.N

#        if self.ui.plt_freq in {"Response", "Both"}:
        y_win = self.y[self.ui.N_start:self.ui.N_end] * self.ui.win
        self.Y = np.abs(np.fft.fft(y_win)) / self.ui.N

#------------------------------------------------------------------------------
    def update_view(self):
        """
        place holder; should update only the limits without recalculating
        the impulse respons
        """
        self.draw_impz()

#------------------------------------------------------------------------------
    def draw(self):
        """
        Recalculate response and redraw it
        """
        self.calc_stimulus()
        self.calc_response()
        self.calc_y_real_imag()
        self.calc_fft()
        self.draw_impz()

#------------------------------------------------------------------------------
    def draw_impz(self):
        """
        (Re-)draw the figure
        """
        f_unit = fb.fil[0]['freq_specs_unit']
        if f_unit in {"f_S", "f_Ny"}:
            unit_frmt = "i" # italic
        else:
            unit_frmt = None
        self.ui.lblFreqUnit1.setText(to_html(f_unit, frmt=unit_frmt))
        self.ui.lblFreqUnit2.setText(to_html(f_unit, frmt=unit_frmt))
        N_start = self.ui.N_start
        self.load_fs()
        self.init_axes()
        
        #================ Main Plotting Routine =========================
        if self.ui.chkMarker.isChecked():
            mkfmt_r = 'o'
            mkfmt_i = 'd'
        else:
            mkfmt_r = mkfmt_i = ' '

        if self.ui.chkLog.isChecked(): # log. scale for stimulus / response time domain
            H_str = '$|$' + self.H_str + '$|$ in dBV'
            x = np.maximum(20 * np.log10(abs(self.x)), self.ui.bottom)
            y = np.maximum(20 * np.log10(abs(self.y_r)), self.ui.bottom)
            if self.cmplx:
                y_i = np.maximum(20 * np.log10(abs(self.y_i)), self.ui.bottom)
                H_i_str = r'$|\Im\{$' + self.H_str + '$\}|$' + ' in dBV'
                H_str =   r'$|\Re\{$' + self.H_str + '$\}|$' + ' in dBV'
        else:
            self.ui.bottom = 0
            x = self.x
            y = self.y_r
            y_i = self.y_i
            
            if self.cmplx:           
                H_i_str = r'$\Im\{$' + self.H_str + '$\}$ in V'
                H_str = r'$\Re\{$' + self.H_str + '$\}$ in V'
            else:
                H_str = self.H_str + ' in V'


        if self.ui.plt_time in {"Response", "Both"}:
            [ml, sl, bl] = self.ax_r.stem(self.t[N_start:], y[N_start:], 
                bottom=self.ui.bottom, markerfmt=mkfmt_r, label = '$y[n]$')

        if self.ui.plt_time in {"Stimulus", "Both"}:
            stem_fmt = params['mpl_stimuli']
            [ms, ss, bs] = self.ax_r.stem(self.t[N_start:], x[N_start:], 
                bottom=self.ui.bottom, label = 'Stim.', **stem_fmt)
            ms.set_mfc(stem_fmt['mfc'])
            ms.set_mec(stem_fmt['mec'])
            ms.set_ms(stem_fmt['ms'])
            ms.set_alpha(stem_fmt['alpha'])
            for stem in ss:
                stem.set_linewidth(stem_fmt['lw'])
                stem.set_color(stem_fmt['mec'])
                stem.set_alpha(stem_fmt['alpha'])
            bs.set_visible(False) # invisible bottomline

        if self.cmplx and self.ui.plt_time in {"Response", "Both"}:
            [ml_i, sl_i, bl_i] = self.ax_i.stem(self.t[N_start:], y_i[N_start:],
                bottom=self.ui.bottom, markerfmt=mkfmt_i, label = '$y_i[n]$')
            self.ax_i.set_xlabel(fb.fil[0]['plt_tLabel'])
            # self.ax_r.get_xaxis().set_ticklabels([]) # removes both xticklabels
            # plt.setp(ax_r.get_xticklabels(), visible=False) 
            # is shorter but imports matplotlib, set property directly instead:
            [label.set_visible(False) for label in self.ax_r.get_xticklabels()]
            self.ax_r.set_ylabel(H_str + r'$\rightarrow $')
            self.ax_i.set_ylabel(H_i_str + r'$\rightarrow $')
        else:
            self.ax_r.set_xlabel(fb.fil[0]['plt_tLabel'])
            self.ax_r.set_ylabel(H_str + r'$\rightarrow $')
        
        self.ax_r.set_title(self.title_str)
        self.ax_r.set_xlim([self.t[N_start],self.t[self.ui.N_end-1]])
        expand_lim(self.ax_r, 0.02)

        # plot frequency domain =========================================
        if self.ui.plt_freq != "None":
            plt_response = self.ui.plt_freq in {"Response","Both"}
            plt_stimulus = self.ui.plt_freq in {"Stimulus","Both"}
            if plt_response and not plt_stimulus:
                XY_str = r'$|Y(\mathrm{e}^{\mathrm{j} \Omega})|$'
            elif not plt_response and plt_stimulus:
                XY_str = r'$|X(\mathrm{e}^{\mathrm{j} \Omega})|$'
            else:
                XY_str = r'$|X,Y(\mathrm{e}^{\mathrm{j} \Omega})|$'
            F = np.fft.fftfreq(self.ui.N, d = 1. / fb.fil[0]['f_S'])

            if plt_stimulus:
                X = self.X.copy()/np.sqrt(2) # enforce deep copy and convert to RMS
                self.Px = np.sum(np.square(self.X))
                if fb.fil[0]['freqSpecsRangeType'] == 'half':
                    X[1:] = 2 * X[1:] # correct for single-sided spectrum (except DC)
            if plt_response:
                Y = self.Y.copy()/np.sqrt(2) # enforce deep copy and convert to RMS
                self.Py = np.sum(np.square(self.Y))
                if fb.fil[0]['freqSpecsRangeType'] == 'half':
                    Y[1:] = 2 * Y[1:] # correct for single-sided spectrum (except DC)

            if self.ui.chkLogF.isChecked():
                unit = unit_P = "dBW"
                unit_nenbw = "dB"
                nenbw = 10 * np.log10(self.ui.nenbw)
                if plt_stimulus:
                    X = np.maximum(20 * np.log10(X), self.ui.bottom_f)
                    self.Px = 10*np.log10(self.Px)
                if plt_response:
                    Y = np.maximum(20 * np.log10(Y), self.ui.bottom_f)
                    self.Py = 10*np.log10(self.Py)
            else:
                unit = "Vrms"
                unit_P = "W"
                unit_nenbw = "bins"
                nenbw = self.ui.nenbw

            XY_str = XY_str + ' in ' + unit

            if fb.fil[0]['freqSpecsRangeType'] == 'sym':
            # shift X, Y and F by f_S/2
                if plt_response:
                    Y = np.fft.fftshift(Y)
                if plt_stimulus:
                    X = np.fft.fftshift(X)
                F = np.fft.fftshift(F)
            elif fb.fil[0]['freqSpecsRangeType'] == 'half':
                # only use the first half of X, Y and F
                if plt_response:
                    Y = Y[0:self.ui.N//2]
                if plt_stimulus:
                    X = X[0:self.ui.N//2]
                F = F[0:self.ui.N//2]
            else: # fb.fil[0]['freqSpecsRangeType'] == 'whole'
                # plot for F = 0 ... 1
                F = np.fft.fftshift(F) + fb.fil[0]['f_S']/2.

            handles = []
            labels = []
            if plt_stimulus:
                h, = self.ax_fft.plot(F, X, color =(0.5,0.5,0.5,0.5), lw=2)
                handles.append(h)
                labels.append("$P_X$ = {0:.3g} {1}".format(self.Px, unit_P))
            if plt_response:
                h, = self.ax_fft.plot(F, Y)
                handles.append(h)
                labels.append("$P_Y$ = {0:.3g} {1}".format(self.Py, unit_P))
                
            labels.append("$NENBW$ = {0:.4g} {1}".format(nenbw, unit_nenbw))
            labels.append("$CGAIN$  = {0:.4g}".format(self.ui.scale))
            handles.append(mpl_patches.Rectangle((0, 0), 1, 1, fc="white",ec="white", lw=0))
            handles.append(mpl_patches.Rectangle((0, 0), 1, 1, fc="white",ec="white", lw=0))
            self.ax_fft.legend(handles, labels, loc='best', fontsize = 'small',
                               fancybox=True, framealpha=0.5)
            

            self.ax_fft.set_xlabel(fb.fil[0]['plt_fLabel'])
            self.ax_fft.set_ylabel(XY_str)
            self.ax_fft.set_xlim(fb.fil[0]['freqSpecsRange'])
            if self.ui.plt_time == "None":
                self.ax_fft.set_title(self.title_str) # no time window, print title here
                
            if self.ui.chkLogF.isChecked():
                # create second axis scaled for noise power scale
                self.ax_fft_noise = self.ax_fft.twinx()
                self.ax_fft_noise.is_twin = True

                corr = 10*np.log10(self.ui.N / self.ui.nenbw) 
                mn, mx = self.ax_fft.get_ylim()
                self.ax_fft_noise.set_ylim(mn+corr, mx+corr)
                self.ax_fft_noise.set_ylabel(r'$P_N$ in dBW')

        if self.ACTIVE_3D: # not implemented / tested yet
            # plotting the stems
            for i in range(N_start, self.ui.N_end):
              self.ax3d.plot([self.t[i], self.t[i]], [y[i], y[i]], [0, y_i[i]],
                             '-', linewidth=2, alpha=.5)

            # plotting a circle on the top of each stem
            self.ax3d.plot(self.t[N_start:], y[N_start:], y_i[N_start:], 'o', markersize=8,
                           markerfacecolor='none', label='$y[n]$')

            self.ax3d.set_xlabel('x')
            self.ax3d.set_ylabel('y')
            self.ax3d.set_zlabel('z')

        self.redraw()

#------------------------------------------------------------------------------
    def redraw(self):
        """
        Redraw the canvas when e.g. the canvas size has changed
        """
        self.mplwidget_t.redraw()
        if hasattr(self, "ax2_fft"):
            self.ax2_fft.grid(False)

#------------------------------------------------------------------------------

def main():
    import sys
    from ..compat import QApplication

    app = QApplication(sys.argv)
    mainw = Plot_Impz(None)
    app.setActiveWindow(mainw) 
    mainw.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
