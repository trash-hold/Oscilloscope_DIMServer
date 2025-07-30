from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTextEdit, QLabel
)
from PySide6.QtCore import Slot
from PySide6.QtGui import QColor

import pyqtgraph as pg

class LogPanel(QWidget):
    """
    A panel dedicated to displaying the backend status and a stream of logs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Widgets ---
        self.status_label = QLabel("Connecting to backend...")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        # --- Layout ---
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        log_groupbox = QGroupBox("Live Logs")
        log_layout = QVBoxLayout()
        log_layout.addWidget(self.log_view)
        log_groupbox.setLayout(log_layout)

        main_layout.addWidget(self.status_label)
        main_layout.addWidget(log_groupbox)

    @Slot(str)
    def log_message(self, message: str):
        """Appends a raw message to the log view, determining color by content."""
        color = "black"
        if "ERROR" in message or "CRITICAL" in message:
            color = "red"
        elif "WARNING" in message:
            color = "orange"
        elif "INFO" in message:
            color = "blue"
        
        colored_message = f'<font color="{color}">{message}</font>'
        self.log_view.append(colored_message)

    @Slot(str)
    def update_status(self, message: str):
        """Updates the main status label at the top of the panel."""
        self.status_label.setText(f"Backend Status: {message}")


class PlotPanel(QWidget):
    """
    A panel that holds and manages four separate plots for oscilloscope channels.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Use a dark background for plots
        pg.setConfigOption('background', 'k')
        pg.setConfigOption('foreground', 'w')

        # --- Layout ---
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.plots = {} # Dictionary to hold our plot data lines

        # --- Create 4 Plots ---
        for i in range(1, 5):
            # Create a plot widget
            plot_widget = pg.PlotWidget()
            plot_widget.setTitle(f"Channel {i}", color="w", size="10pt")
            plot_widget.setLabel('left', 'Voltage', units='V')
            plot_widget.setLabel('bottom', 'Sample Number')
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Create a data line item with a yellow pen
            # We will update the data of this line item, which is very fast.
            data_line = plot_widget.plot(pen='y')

            # Store the data line for future updates
            self.plots[i] = data_line

            # Add the plot widget to our layout
            main_layout.addWidget(plot_widget)

    @Slot(dict)
    def update_waveforms(self, waveform_data: dict):
        """
        Receives waveform data and updates the corresponding plots.
        The data is expected in a dictionary like: {'1': [y1, y2...], '3': [y1, y2...]}
        """
        # Iterate through all our plots (1 through 4)
        for channel_num, data_line in self.plots.items():
            channel_key = str(channel_num)

            # Check if the incoming data dictionary has data for this channel
            if channel_key in waveform_data:
                y_points = waveform_data[channel_key]
                # For now, we use the sample index for the x-axis.
                # A future improvement could be to get the real time axis from the backend.
                x_points = range(len(y_points))
                
                # Update the data for this channel's plot line
                data_line.setData(x_points, y_points)
            else:
                # If no data for this channel was sent, clear the plot
                data_line.clear()