# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Create the UI for the PlotImz class
"""
from pyfda.libs.compat import (
    QCheckBox, QWidget, QComboBox, QLineEdit, QLabel, QPushButton, QPushButtonRT,
    QIcon, QProgressBar, pyqtSignal, QEvent, Qt, QSize, QHBoxLayout, QVBoxLayout,
    QGridLayout, QTabWidget, QFrame)

from pyfda.libs.pyfda_lib import to_html, safe_eval, pprint_log
import pyfda.filterbroker as fb
from pyfda.libs.pyfda_qt_lib import (
    qcmb_box_populate, qget_cmb_box, qset_cmb_box, qtext_width,
    QVLine, PushButton)
from pyfda.libs.pyfda_fft_windows_lib import get_windows_dict, QFFTWinSelector
from pyfda.pyfda_rc import params  # FMT string for QLineEdit fields, e.g. '{:.3g}'

from pyfda.plot_widgets.plot_fft_win import Plot_FFT_win

import logging
logger = logging.getLogger(__name__)


class PlotImpz_UI(QWidget):
    """
    Create the UI for the PlotImpz class
    """
    # incoming: not implemented at the moment, update_N is triggered directly
    # by plot_impz
    # sig_rx = pyqtSignal(object)
    # outgoing: from various UI elements to PlotImpz ('ui_changed':'xxx')
    sig_tx = pyqtSignal(object)
    # outgoing: to fft related widgets (FFT window widget, qfft_win_select)
    sig_tx_fft = pyqtSignal(object)

    from pyfda.libs.pyfda_qt_lib import emit

# ------------------------------------------------------------------------------
    def process_sig_rx(self, dict_sig=None):
        """
        Process signals coming from
        - FFT window widget
        - qfft_win_select
        """

        # logger.debug("PROCESS_SIG_RX - vis: {0}\n{1}"
        #              .format(self.isVisible(), pprint_log(dict_sig)))

        if 'id' in dict_sig and dict_sig['id'] == id(self):
            logger.warning("Stopped infinite loop:\n{0}".format(pprint_log(dict_sig)))
            return

        # --- signals coming from the FFT window widget or the FFT window selector
        if dict_sig['class'] in {'Plot_FFT_win', 'QFFTWinSelector'}:
            if 'closeEvent' in dict_sig:   # hide FFT window widget and return
                self.hide_fft_wdg()
                return
            else:
                # check for value 'fft_win*':
                if 'view_changed' in dict_sig and 'fft_win' in dict_sig['view_changed']:
                    # local connection to FFT window widget and qfft_win_select
                    self.emit(dict_sig, sig_name='sig_tx_fft')
                    # global connection to e.g. plot_impz
                    self.emit(dict_sig)

# ------------------------------------------------------------------------------
    def __init__(self):
        super().__init__()

        """
        Intitialize the widget, consisting of:
        - top chkbox row
        - coefficient table
        - two bottom rows with action buttons
        """
        # initial settings
        self.N_start = 0
        self.N_user = 0
        self.N = 0
        self.N_frame_user = 0
        self.N_frame = 0

        # time
        self.plt_time_resp = "stem"
        self.plt_time_stim = "line"
        self.plt_time_stmq = "none"
        self.plt_time_spgr = "none"

        self.bottom_t = -80  # initial value for log. scale (time)
        self.time_nfft_spgr = 256  # number of fft points per spectrogram segment
        self.time_ovlp_spgr = 128  # number of overlap points between spectrogram segments
        self.mode_spgr_time = "psd"

        # frequency
        self.cmb_freq_display_item = "mag"
        self.plt_freq_resp = "line"
        self.plt_freq_stim = "none"
        self.plt_freq_stmq = "none"

        self.bottom_f = -120  # initial value for log. scale
        self.param = None

        self.f_scale = fb.fil[0]['f_S']
        self.t_scale = fb.fil[0]['T_S']
        # list of windows that are available for FFT analysis
        win_names_list = ["Boxcar", "Rectangular", "Barthann", "Bartlett", "Blackman",
                          "Blackmanharris", "Bohman", "Cosine", "Dolph-Chebyshev",
                          "Flattop", "General Gaussian", "Gauss", "Hamming", "Hann",
                          "Kaiser", "Nuttall", "Parzen", "Slepian", "Triangular", "Tukey"]
        self.cur_win_name = "Rectangular"  # set initial window type

        # initialize windows dict with the list above
        self.win_dict = get_windows_dict(
            win_names_list=win_names_list,
            cur_win_name=self.cur_win_name)

        # instantiate FFT window with default windows dict
        self.fft_widget = Plot_FFT_win(
            self, self.win_dict, sym=False, title="pyFDA Spectral Window Viewer")
        # hide window initially, this is modeless i.e. a non-blocking popup window
        self.fft_widget.hide()

        # data / icon / tooltipp (none) for plotting styles
        self.plot_styles_list = [
            ("Plot style"),
            ("none", QIcon(":/plot_style-none"), "off"),
            ("dots*", QIcon(":/plot_style-mkr"), "markers only"),
            ("line", QIcon(":/plot_style-line"), "line"),
            ("line*", QIcon(":/plot_style-line-mkr"), "line + markers"),
            ("stem", QIcon(":/plot_style-stem"), "stems"),
            ("stem*", QIcon(":/plot_style-stem-mkr"), "stems + markers"),
            ("steps", QIcon(":/plot_style-steps"), "steps"),
            ("steps*", QIcon(":/plot_style-steps-mkr"), "steps + markers")
            ]

        self.cmb_time_spgr_items = [
            "<span>Show Spectrogram for selected signal.</span>",
            ("none", "None", ""),
            ("xn", "x[n]", "input"),
            ("xqn", "x_q[n]", "quantized input"),
            ("yn", "y[n]", "output")
            ]

        self.cmb_mode_spgr_time_items = [
            "<span>Spectrogram display mode.</span>",
            ("psd", "PSD",
             "<span>Power Spectral Density, either per bin or referred to "
             "<i>f<sub>S</sub></i></span>"),
            ("magnitude", "Mag.", "Signal magnitude"),
            ("angle", "Angle", "Phase, wrapped to &pm; &pi;"),
            ("phase", "Phase", "Phase (unwrapped)")
            ]
#        self.N

        self.cmb_freq_display_items = [
            "<span>Select how to display the spectrum.</span>",
            ("mag", "Magnitude", "<span>Spectral magnitude</span>"),
            ("mag_phi", "Mag. / Phase", "<span>Magnitude and phase.</span>"),
            ("re_im", "Re. / Imag.", "<span>Real and imaginary part of spectrum.</span>")
            ]

        self._construct_UI()
#        self._enable_stim_widgets()
        self.update_N(emit=False)  # also updates window function and win_dict
#        self._update_noi()

    def _construct_UI(self):
        # ----------- ---------------------------------------------------
        # Run control widgets
        # ---------------------------------------------------------------
        # self.but_auto_run = QPushButtonRT(text=to_html("Auto", frmt="b"), margin=0)
        self.but_auto_run = QPushButton(" Auto", self)
        self.but_auto_run.setObjectName("but_auto_run")
        self.but_auto_run.setToolTip("<span>Update response automatically when "
                                     "parameters have been changed.</span>")
        # self.but_auto_run.setMaximumWidth(qtext_width(text=" Auto "))
        self.but_auto_run.setCheckable(True)
        self.but_auto_run.setChecked(True)

        but_height = self.but_auto_run.sizeHint().height()

        self.but_run = QPushButton(self)
        self.but_run.setIcon(QIcon(":/play.svg"))

        self.but_run.setIconSize(QSize(but_height, but_height))
        self.but_run.setFixedSize(QSize(2*but_height, but_height))
        self.but_run.setToolTip("Run simulation")
        self.but_run.setEnabled(True)

        self.cmb_sim_select = QComboBox(self)
        self.cmb_sim_select.addItems(["Float", "Fixpoint"])
        qset_cmb_box(self.cmb_sim_select, "Float")
        self.cmb_sim_select.setToolTip("<span>Simulate floating-point or "
                                       "fixpoint response.</span>")

        self.lbl_N_points = QLabel(to_html("N", frmt='bi') + " =", self)
        self.led_N_points = QLineEdit(self)
        self.led_N_points.setText(str(self.N))
        self.led_N_points.setToolTip(
            "<span>Last data point. "
            "<i>N</i> = 0 tries to choose for you.</span>")
        self.led_N_points.setMaximumWidth(qtext_width(N_x=8))
        self.lbl_N_start = QLabel(to_html("N_0", frmt='bi') + " =", self)
        self.led_N_start = QLineEdit(self)
        self.led_N_start.setText(str(self.N_start))
        self.led_N_start.setToolTip("<span>First point to plot.</span>")
        self.led_N_start.setMaximumWidth(qtext_width(N_x=8))

        self.lbl_N_frame = QLabel(to_html("&Delta;N", frmt='bi') + " =", self)
        self.led_N_frame = QLineEdit(self)
        self.led_N_frame.setText(str(self.N_frame))
        self.led_N_frame.setToolTip(
            "<span>Frame length; longer frames calculate faster but calculation cannot "
            "be stopped so quickly. "
            "<i>&Delta;N</i> = 0 calculates all samples in one frame.</span>")
        self.led_N_frame.setMaximumWidth(qtext_width(N_x=8))

        self.prg_wdg = QProgressBar(self)
        self.prg_wdg.setFixedHeight(but_height)
        self.prg_wdg.setFixedWidth(qtext_width(N_x=6))
        self.prg_wdg.setMinimum(0)
        self.prg_wdg.setValue(0)

        self.but_toggle_stim_options = PushButton(" Stimuli ", checked=True)
        self.but_toggle_stim_options.setObjectName("but_stim_options")
        self.but_toggle_stim_options.setToolTip("<span>Show / hide stimulus options.</span>")

        self.lbl_stim_cmplx_warn = QLabel(self)
        self.lbl_stim_cmplx_warn = QLabel(to_html("Cmplx!", frmt='b'), self)
        self.lbl_stim_cmplx_warn.setToolTip(
            '<span>Signal is complex valued; '
            'single-sided and H<sub>id</sub> spectra may be wrong.</span>')
        self.lbl_stim_cmplx_warn.setStyleSheet("background-color : yellow;"
                                               "border : 1px solid grey")

        self.but_fft_wdg = QPushButton(self)
        self.but_fft_wdg.setIcon(QIcon(":/fft.svg"))
        self.but_fft_wdg.setIconSize(QSize(but_height, but_height))
        self.but_fft_wdg.setFixedSize(QSize(int(1.5 * but_height), but_height))
        self.but_fft_wdg.setToolTip('<span>Show / hide FFT widget (select window type '
                                    ' and display its properties).</span>')
        self.but_fft_wdg.setCheckable(True)
        self.but_fft_wdg.setChecked(False)

        self.qfft_win_select = QFFTWinSelector(self, self.win_dict)

        self.but_fx_scale = PushButton(" FX:Int ")
        self.but_fx_scale.setObjectName("but_fx_scale")
        self.but_fx_scale.setToolTip(
            "<span>Display data with integer (fixpoint) scale.</span>")

        self.but_fx_range = PushButton(" FX:Range")
        self.but_fx_range.setObjectName("but_fx_limits")
        self.but_fx_range.setToolTip("<span>Display limits of fixpoint range.</span>")

        layH_ctrl_run = QHBoxLayout()
        layH_ctrl_run.addWidget(self.but_auto_run)
        layH_ctrl_run.addWidget(self.but_run)
        layH_ctrl_run.addWidget(self.cmb_sim_select)
        layH_ctrl_run.addSpacing(10)
        layH_ctrl_run.addWidget(self.lbl_N_start)
        layH_ctrl_run.addWidget(self.led_N_start)
        layH_ctrl_run.addWidget(self.lbl_N_points)
        layH_ctrl_run.addWidget(self.led_N_points)
        layH_ctrl_run.addWidget(self.lbl_N_frame)
        layH_ctrl_run.addWidget(self.led_N_frame)
        layH_ctrl_run.addWidget(self.prg_wdg)

        layH_ctrl_run.addSpacing(20)
        layH_ctrl_run.addWidget(self.but_toggle_stim_options)
        layH_ctrl_run.addSpacing(5)
        layH_ctrl_run.addWidget(self.lbl_stim_cmplx_warn)
        layH_ctrl_run.addSpacing(20)
        layH_ctrl_run.addWidget(self.but_fft_wdg)
        layH_ctrl_run.addWidget(self.qfft_win_select)
        layH_ctrl_run.addSpacing(20)
        layH_ctrl_run.addWidget(self.but_fx_scale)
        layH_ctrl_run.addWidget(self.but_fx_range)
        layH_ctrl_run.addStretch(10)

        # layH_ctrl_run.setContentsMargins(*params['wdg_margins'])

        self.wdg_ctrl_run = QWidget(self)
        self.wdg_ctrl_run.setLayout(layH_ctrl_run)
        # --- end of run control ----------------------------------------

        # ----------- ---------------------------------------------------
        # Controls for time domain
        # ---------------------------------------------------------------
        self.lbl_plt_time_stim = QLabel(to_html("Stim. x", frmt='bi'), self)
        self.cmb_plt_time_stim = QComboBox(self)
        qcmb_box_populate(
            self.cmb_plt_time_stim, self.plot_styles_list, self.plt_time_stim)
        self.cmb_plt_time_stim.setToolTip("<span>Plot style for stimulus.</span>")

        self.lbl_plt_time_stmq = QLabel(to_html(
            "&nbsp;&nbsp;Fixp. Stim. x_Q", frmt='bi'), self)
        self.cmb_plt_time_stmq = QComboBox(self)
        qcmb_box_populate(
            self.cmb_plt_time_stmq, self.plot_styles_list, self.plt_time_stmq)
        self.cmb_plt_time_stmq.setToolTip("<span>Plot style for <em>fixpoint</em> "
                                          "(quantized) stimulus.</span>")

        lbl_plt_time_resp = QLabel(to_html("&nbsp;&nbsp;Resp. y", frmt='bi'), self)
        self.cmb_plt_time_resp = QComboBox(self)
        qcmb_box_populate(
            self.cmb_plt_time_resp, self.plot_styles_list, self.plt_time_resp)
        self.cmb_plt_time_resp.setToolTip("<span>Plot style for response.</span>")

        self.lbl_win_time = QLabel(to_html("&nbsp;&nbsp;Win", frmt='bi'), self)
        self.chk_win_time = QCheckBox(self)
        self.chk_win_time.setObjectName("chk_win_time")
        self.chk_win_time.setToolTip(
            '<span>Plot FFT windowing function.</span>')
        self.chk_win_time.setChecked(False)

        line1 = QVLine()
        line2 = QVLine(width=5)

        self.but_log_time = PushButton(" dB")
        self.but_log_time.setObjectName("but_log_time")
        self.but_log_time.setToolTip("<span>Logarithmic scale for y-axis.</span>")

        lbl_plt_time_spgr = QLabel(to_html("Spectrogram", frmt='bi'), self)
        self.cmb_plt_time_spgr = QComboBox(self)
        qcmb_box_populate(
            self.cmb_plt_time_spgr, self.cmb_time_spgr_items, self.plt_time_spgr)
        spgr_en = self.plt_time_spgr != "none"

        self.cmb_mode_spgr_time = QComboBox(self)
        qcmb_box_populate(
            self.cmb_mode_spgr_time, self.cmb_mode_spgr_time_items, self.mode_spgr_time)
        self.cmb_mode_spgr_time.setVisible(spgr_en)

        self.lbl_byfs_spgr_time = QLabel(to_html("&nbsp;per f_S", frmt='b'), self)
        self.lbl_byfs_spgr_time.setVisible(spgr_en)
        self.chk_byfs_spgr_time = QCheckBox(self)
        self.chk_byfs_spgr_time.setObjectName("chk_log_spgr")
        self.chk_byfs_spgr_time.setToolTip("<span>Display spectral density "
                                           "i.e. scale by f_S</span>")
        self.chk_byfs_spgr_time.setChecked(True)
        self.chk_byfs_spgr_time.setVisible(spgr_en)

        self.but_log_spgr_time = QPushButton("dB")
        self.but_log_spgr_time.setMaximumWidth(qtext_width(text=" dB"))
        self.but_log_spgr_time.setObjectName("but_log_spgr")
        self.but_log_spgr_time.setToolTip(
            "<span>Logarithmic scale for spectrogram.</span>")
        self.but_log_spgr_time.setCheckable(True)
        self.but_log_spgr_time.setChecked(True)
        self.but_log_spgr_time.setVisible(spgr_en)

        self.lbl_time_nfft_spgr = QLabel(to_html("&nbsp;N_FFT =", frmt='bi'), self)
        self.lbl_time_nfft_spgr.setVisible(spgr_en)
        self.led_time_nfft_spgr = QLineEdit(self)
        self.led_time_nfft_spgr.setText(str(self.time_nfft_spgr))
        self.led_time_nfft_spgr.setToolTip("<span>Number of FFT points per "
                                           "spectrogram segment.</span>")
        self.led_time_nfft_spgr.setVisible(spgr_en)

        self.lbl_time_ovlp_spgr = QLabel(to_html("&nbsp;N_OVLP =", frmt='bi'), self)
        self.lbl_time_ovlp_spgr.setVisible(spgr_en)
        self.led_time_ovlp_spgr = QLineEdit(self)
        self.led_time_ovlp_spgr.setText(str(self.time_ovlp_spgr))
        self.led_time_ovlp_spgr.setToolTip("<span>Number of overlap data points "
                                           "between spectrogram segments.</span>")
        self.led_time_ovlp_spgr.setVisible(spgr_en)

        self.lbl_log_bottom_time = QLabel(to_html("min =", frmt='bi'), self)
        self.led_log_bottom_time = QLineEdit(self)
        self.led_log_bottom_time.setText(str(self.bottom_t))
        self.led_log_bottom_time.setMaximumWidth(qtext_width(N_x=8))
        self.led_log_bottom_time.setToolTip(
            "<span>Minimum display value for time and spectrogram plots with log. scale."
            "</span>")
        self.lbl_log_bottom_time.setVisible(
            self.but_log_time.isChecked() or
            (spgr_en and self.but_log_spgr_time.isChecked()))
        self.led_log_bottom_time.setVisible(self.lbl_log_bottom_time.isVisible())

        # self.lbl_colorbar_time = QLabel(to_html("&nbsp;Col.bar", frmt='b'), self)
        # self.lbl_colorbar_time.setVisible(spgr_en)
        # self.chk_colorbar_time = QCheckBox(self)
        # self.chk_colorbar_time.setObjectName("chk_colorbar_time")
        # self.chk_colorbar_time.setToolTip("<span>Enable colorbar</span>")
        # self.chk_colorbar_time.setChecked(True)
        # self.chk_colorbar_time.setVisible(spgr_en)

        layH_ctrl_time = QHBoxLayout()
        layH_ctrl_time.addWidget(self.lbl_plt_time_stim)
        layH_ctrl_time.addWidget(self.cmb_plt_time_stim)
        #
        layH_ctrl_time.addWidget(self.lbl_plt_time_stmq)
        layH_ctrl_time.addWidget(self.cmb_plt_time_stmq)
        #
        layH_ctrl_time.addWidget(lbl_plt_time_resp)
        layH_ctrl_time.addWidget(self.cmb_plt_time_resp)
        #
        layH_ctrl_time.addWidget(self.lbl_win_time)
        layH_ctrl_time.addWidget(self.chk_win_time)
        layH_ctrl_time.addSpacing(5)
        layH_ctrl_time.addWidget(line1)
        layH_ctrl_time.addSpacing(5)
        #
        layH_ctrl_time.addWidget(self.lbl_log_bottom_time)
        layH_ctrl_time.addWidget(self.led_log_bottom_time)
        layH_ctrl_time.addWidget(self.but_log_time)

        layH_ctrl_time.addSpacing(5)
        layH_ctrl_time.addWidget(line2)
        layH_ctrl_time.addSpacing(5)
        #
        layH_ctrl_time.addWidget(lbl_plt_time_spgr)
        layH_ctrl_time.addWidget(self.cmb_plt_time_spgr)
        layH_ctrl_time.addWidget(self.cmb_mode_spgr_time)
        layH_ctrl_time.addWidget(self.lbl_byfs_spgr_time)
        layH_ctrl_time.addWidget(self.chk_byfs_spgr_time)
        layH_ctrl_time.addWidget(self.but_log_spgr_time)
        layH_ctrl_time.addWidget(self.lbl_time_nfft_spgr)
        layH_ctrl_time.addWidget(self.led_time_nfft_spgr)
        layH_ctrl_time.addWidget(self.lbl_time_ovlp_spgr)
        layH_ctrl_time.addWidget(self.led_time_ovlp_spgr)

        layH_ctrl_time.addStretch(10)

        # layH_ctrl_time.setContentsMargins(*params['wdg_margins'])

        self.wdg_ctrl_time = QWidget(self)
        self.wdg_ctrl_time.setLayout(layH_ctrl_time)
        # ---- end time domain ------------------

        # ---------------------------------------------------------------
        # Controls for frequency domain
        # ---------------------------------------------------------------
        self.lbl_plt_freq_stim = QLabel(to_html("Stimulus X", frmt='bi'), self)
        self.cmb_plt_freq_stim = QComboBox(self)
        qcmb_box_populate(
            self.cmb_plt_freq_stim, self.plot_styles_list, self.plt_freq_stim)
        self.cmb_plt_freq_stim.setToolTip("<span>Plot style for stimulus.</span>")

        self.lbl_plt_freq_stmq = QLabel(to_html("&nbsp;Fixp. Stim. X_Q", frmt='bi'), self)
        self.cmb_plt_freq_stmq = QComboBox(self)
        qcmb_box_populate(
            self.cmb_plt_freq_stmq, self.plot_styles_list, self.plt_freq_stmq)
        self.cmb_plt_freq_stmq.setToolTip(
            "<span>Plot style for <em>fixpoint</em> (quantized) stimulus.</span>")

        lbl_plt_freq_resp = QLabel(to_html("&nbsp;Response Y", frmt='bi'), self)
        self.cmb_plt_freq_resp = QComboBox(self)
        qcmb_box_populate(
            self.cmb_plt_freq_resp, self.plot_styles_list, self.plt_freq_resp)
        self.cmb_plt_freq_resp.setToolTip("<span>Plot style for response.</span>")

        self.but_log_freq = QPushButton("dB")
        self.but_log_freq.setMaximumWidth(qtext_width(" dB"))
        self.but_log_freq.setObjectName(".but_log_freq")
        self.but_log_freq.setToolTip("<span>Logarithmic scale for y-axis.</span>")
        self.but_log_freq.setCheckable(True)
        self.but_log_freq.setChecked(True)

        self.lbl_log_bottom_freq = QLabel(to_html("min =", frmt='bi'), self)
        self.lbl_log_bottom_freq.setVisible(self.but_log_freq.isChecked())
        self.led_log_bottom_freq = QLineEdit(self)
        self.led_log_bottom_freq.setText(str(self.bottom_f))
        self.led_log_bottom_freq.setMaximumWidth(qtext_width(N_x=8))
        self.led_log_bottom_freq.setToolTip(
            "<span>Minimum display value for log. scale.</span>")
        self.led_log_bottom_freq.setVisible(self.but_log_freq.isChecked())

        if not self.but_log_freq.isChecked():
            self.bottom_f = 0

        self.cmb_freq_display = QComboBox(self)
        qcmb_box_populate(self.cmb_freq_display, self.cmb_freq_display_items,
                          self.cmb_freq_display_item)
        self.cmb_freq_display.setObjectName("cmb_re_im_freq")

        self.but_Hf = QPushButtonRT(self, to_html("H_id", frmt="bi"), margin=5)
        self.but_Hf.setObjectName("chk_Hf")
        self.but_Hf.setToolTip("<span>Show ideal frequency response, calculated "
                               "from the filter coefficients.</span>")
        self.but_Hf.setChecked(False)
        self.but_Hf.setCheckable(True)

        self.but_freq_norm_impz = QPushButtonRT(text="<b><i>E<sub>X</sub></i> = 1</b>",
                                                margin=5)
        self.but_freq_norm_impz.setToolTip(
            "<span>Normalize the FFT of the stimulus with <i>N<sub>FFT</sub></i> for "
            "<i>E<sub>X</sub></i> = 1. For a dirac pulse, this yields "
            "|<i>Y(f)</i>| = |<i>H(f)</i>|. DC and Noise need to be "
            "turned off, window should be <b>Rectangular</b>.</span>")
        self.but_freq_norm_impz.setCheckable(True)
        self.but_freq_norm_impz.setChecked(True)
        self.but_freq_norm_impz.setObjectName("freq_norm_impz")

        self.but_freq_show_info = QPushButton("Info", self)
        self.but_freq_show_info.setMaximumWidth(qtext_width(" Info "))
        self.but_freq_show_info.setObjectName("but_show_info_freq")
        self.but_freq_show_info.setToolTip("<span>Show signal power in legend.</span>")
        self.but_freq_show_info.setCheckable(True)
        self.but_freq_show_info.setChecked(False)

        layH_ctrl_freq = QHBoxLayout()
        layH_ctrl_freq.addWidget(self.lbl_plt_freq_stim)
        layH_ctrl_freq.addWidget(self.cmb_plt_freq_stim)
        #
        layH_ctrl_freq.addWidget(self.lbl_plt_freq_stmq)
        layH_ctrl_freq.addWidget(self.cmb_plt_freq_stmq)
        #
        layH_ctrl_freq.addWidget(lbl_plt_freq_resp)
        layH_ctrl_freq.addWidget(self.cmb_plt_freq_resp)
        #
        layH_ctrl_freq.addSpacing(5)
        layH_ctrl_freq.addWidget(self.but_Hf)
        layH_ctrl_freq.addStretch(1)
        #
        layH_ctrl_freq.addWidget(self.lbl_log_bottom_freq)
        layH_ctrl_freq.addWidget(self.led_log_bottom_freq)
        layH_ctrl_freq.addWidget(self.but_log_freq)
        layH_ctrl_freq.addStretch(1)
        layH_ctrl_freq.addWidget(self.cmb_freq_display)
        layH_ctrl_freq.addStretch(1)

        layH_ctrl_freq.addWidget(self.but_freq_norm_impz)
        layH_ctrl_freq.addStretch(1)
        layH_ctrl_freq.addWidget(self.but_freq_show_info)
        layH_ctrl_freq.addStretch(10)

        # layH_ctrl_freq.setContentsMargins(*params['wdg_margins'])

        self.wdg_ctrl_freq = QWidget(self)
        self.wdg_ctrl_freq.setLayout(layH_ctrl_freq)
        # ---- end Frequency Domain ------------------

        # ----------------------------------------------------------------------
        # GLOBAL SIGNALS & SLOTs
        # ----------------------------------------------------------------------
        # connect FFT widget to qfft_selector and vice versa and to and signals upstream:
        self.fft_widget.sig_tx.connect(self.process_sig_rx)
        self.qfft_win_select.sig_tx.connect(self.process_sig_rx)
        # connect process_sig_rx output to both FFT widgets
        self.sig_tx_fft.connect(self.fft_widget.sig_rx)
        self.sig_tx_fft.connect(self.qfft_win_select.sig_rx)

        # ----------------------------------------------------------------------
        # LOCAL SIGNALS & SLOTs
        # ----------------------------------------------------------------------
        # --- run control ---
        self.led_N_start.editingFinished.connect(self.update_N)
        self.led_N_points.editingFinished.connect(self.update_N)
        self.led_N_frame.editingFinished.connect(self.update_N)
        self.but_fft_wdg.clicked.connect(self.toggle_fft_wdg)

    # -------------------------------------------------------------------------
    def update_N(self, emit=True):
        """
        Update values for `self.N` and `self.win_dict['N']`, for `self.N_start` and
        `self.N_end` from the corresponding QLineEditWidgets.
        When `emit==True`, fire `'ui_changed': 'N'` to update the FFT window and the
        `plot_impz` widgets. In contrast to `view_changed`, this also forces a
        recalculation of the transient response.

        This method is called by:

        - `self._construct_ui()` with `emit==False`
        - `plot_impz()` with `emit==False` when the automatic calculation
                of N has to be updated (e.g. order of FIR Filter has changed
        - signal-slot connection when `N_start` or `N_end` QLineEdit widgets have
                been changed (`emit==True`)
        """
        if not isinstance(emit, bool):
            logger.error("update N: emit={0}".format(emit))
        self.N_start = safe_eval(self.led_N_start.text(), self.N_start,
                                 return_type='int', sign='poszero')
        self.led_N_start.setText(str(self.N_start))  # update widget

        self.N_user = safe_eval(self.led_N_points.text(), self.N_user,
                                return_type='int', sign='poszero')

        if self.N_user == 0:  # automatic calculation
            self.N = self.calc_n_points(self.N_user)  # widget remains set to 0
            self.led_N_points.setText("0")  # update widget
        else:
            self.N = self.N_user
            self.led_N_points.setText(str(self.N))  # update widget

        # total number of points to be calculated: N + N_start
        self.N_end = self.N + self.N_start
        
        self.N_frame_user = safe_eval(self.led_N_frame.text(), self.N_frame_user,
                                 return_type='int', sign='poszero')
        
        if self.N_frame_user == 0:
            self.N_frame = self.N_end  # use N_end for frame length
            self.led_N_frame.setText("0")  # update widget with "0" as set by user
        else:
            self.N_frame = self.N_frame_user
            self.led_N_frame.setText(str(self.N_frame))  # update widget

        # recalculate displayed freq. index values when freq. unit == 'k'
        if fb.fil[0]['freq_specs_unit'] == 'k':
            self.update_freqs()

        if emit:
            # use `'ui_changed'` as this triggers recalculation of the transient
            # response
            self.emit({'ui_changed': 'N'})

    # ------------------------------------------------------------------------------
    def toggle_fft_wdg(self):
        """
        Show / hide FFT widget depending on the state of the corresponding button
        When widget is shown, trigger an update of the window function.
        """
        if self.but_fft_wdg.isChecked():
            self.fft_widget.show()
            self.emit({'view_changed': 'fft_win_type'}, sig_name='sig_tx_fft')
        else:
            self.fft_widget.hide()

    # --------------------------------------------------------------------------
    def hide_fft_wdg(self):
        """
        The closeEvent caused by clicking the "x" in the FFT widget is caught
        there and routed here to only hide the window
        """
        self.but_fft_wdg.setChecked(False)
        self.fft_widget.hide()

    # ------------------------------------------------------------------------------
    def calc_n_points(self, N_user=0):
        """
        Calculate number of points to be displayed, depending on type of filter
        (FIR, IIR) and user input. If the user selects 0 points, the number is
        calculated automatically.

        An improvement would be to calculate the dominant pole and the corresponding
        settling time.
        """
        if N_user == 0:  # set number of data points automatically
            if fb.fil[0]['ft'] == 'IIR':
                # IIR: No algorithm yet, set N = 100
                N = 100
            else:
                # FIR: N = number of coefficients (max. 100)
                N = min(len(fb.fil[0]['ba'][0]), 100)
        else:
            N = N_user

        return N


# ------------------------------------------------------------------------------
def main():
    import sys
    from pyfda.libs.compat import QApplication

    app = QApplication(sys.argv)

    mainw = PlotImpz_UI(None)
    layVMain = QVBoxLayout()
    layVMain.addWidget(mainw.wdg_ctrl_time)
    layVMain.addWidget(mainw.wdg_ctrl_freq)
    layVMain.addWidget(mainw.wdg_ctrl_stim)
    layVMain.addWidget(mainw.wdg_ctrl_run)
    layVMain.setContentsMargins(*params['wdg_margins'])  # (left, top, right, bottom)

    mainw.setLayout(layVMain)

    app.setActiveWindow(mainw)
    mainw.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    """ Run widget standalone with `python -m pyfda.plot_widgets.plot_impz_ui` """
    import sys
    from pyfda.libs.compat import QApplication
    from pyfda import pyfda_rc as rc

    app = QApplication(sys.argv)
    app.setStyleSheet(rc.qss_rc)
    mainw = PlotImpz_UI()

    layVMain = QVBoxLayout()
    layVMain.addWidget(mainw.wdg_ctrl_time)
    layVMain.addWidget(mainw.wdg_ctrl_freq)
    layVMain.addWidget(mainw.wdg_ctrl_stim)
    layVMain.addWidget(mainw.wdg_ctrl_run)
    mainw.setLayout(layVMain)
    app.setActiveWindow(mainw)
    mainw.show()
    sys.exit(app.exec_())
