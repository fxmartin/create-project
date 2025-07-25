# ABOUTME: Performance dashboard dialog for monitoring application metrics in debug mode
# ABOUTME: Displays real-time performance data, memory usage, and operation statistics

"""
Performance dashboard dialog.

This module provides a debug-mode dialog for monitoring application performance
including memory usage, operation timing, system metrics, and detailed reports.
"""

import json
from typing import Optional

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from create_project.utils.logger import get_logger
from create_project.utils.performance import (
    get_monitor,
)

logger = get_logger(__name__)


class PerformanceDialog(QDialog):
    """
    Performance dashboard dialog for debug mode.
    
    Displays real-time performance metrics, memory usage,
    operation statistics, and system information.
    """

    # Signals
    export_requested = pyqtSignal(str)  # Export path
    reset_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize performance dashboard dialog."""
        super().__init__(parent)

        self.monitor = get_monitor()
        self.update_timer = QTimer()

        self._setup_ui()
        self._connect_signals()
        self._start_monitoring()

        logger.debug("Performance dialog initialized")

    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Performance Dashboard")
        self.setModal(False)  # Allow interaction with main window
        self.resize(800, 600)

        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Tab widget for different views
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_overview_tab()
        self._create_memory_tab()
        self._create_operations_tab()
        self._create_system_tab()
        self._create_raw_data_tab()

        # Control buttons
        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.reset_button = QPushButton("Reset Data")
        self.export_button = QPushButton("Export Report")
        self.close_button = QPushButton("Close")

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def _create_overview_tab(self):
        """Create overview tab with key metrics."""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)

        # Summary metrics group
        summary_group = QGroupBox("Summary Metrics")
        summary_layout = QGridLayout(summary_group)

        # Metric labels
        self.total_ops_label = QLabel("0")
        self.total_time_label = QLabel("0.000s")
        self.peak_memory_label = QLabel("0.0 MB")
        self.memory_delta_label = QLabel("0.0 MB")
        self.avg_cpu_label = QLabel("0.0%")

        summary_layout.addWidget(QLabel("Total Operations:"), 0, 0)
        summary_layout.addWidget(self.total_ops_label, 0, 1)
        summary_layout.addWidget(QLabel("Total Time:"), 1, 0)
        summary_layout.addWidget(self.total_time_label, 1, 1)
        summary_layout.addWidget(QLabel("Peak Memory:"), 2, 0)
        summary_layout.addWidget(self.peak_memory_label, 2, 1)
        summary_layout.addWidget(QLabel("Memory Delta:"), 0, 2)
        summary_layout.addWidget(self.memory_delta_label, 0, 3)
        summary_layout.addWidget(QLabel("Average CPU:"), 1, 2)
        summary_layout.addWidget(self.avg_cpu_label, 1, 3)

        layout.addWidget(summary_group)

        # Current status group
        status_group = QGroupBox("Current Status")
        status_layout = QGridLayout(status_group)

        self.current_memory_label = QLabel("0.0 MB")
        self.current_objects_label = QLabel("0")
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)

        status_layout.addWidget(QLabel("Current Memory:"), 0, 0)
        status_layout.addWidget(self.current_memory_label, 0, 1)
        status_layout.addWidget(QLabel("Python Objects:"), 1, 0)
        status_layout.addWidget(self.current_objects_label, 1, 1)
        status_layout.addWidget(QLabel("Memory Usage:"), 2, 0)
        status_layout.addWidget(self.memory_progress, 2, 1)

        layout.addWidget(status_group)

        # Recent operations group
        recent_group = QGroupBox("Recent Operations (Last 5)")
        recent_layout = QVBoxLayout(recent_group)

        self.recent_ops_table = QTableWidget()
        self.recent_ops_table.setColumnCount(4)
        self.recent_ops_table.setHorizontalHeaderLabels([
            "Operation", "Duration", "Memory Δ", "Status"
        ])
        recent_layout.addWidget(self.recent_ops_table)

        layout.addWidget(recent_group)

        layout.addStretch()
        tab.setWidget(content)
        self.tab_widget.addTab(tab, "Overview")

    def _create_memory_tab(self):
        """Create memory monitoring tab."""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)

        # Memory chart placeholder (could add actual charting library)
        chart_group = QGroupBox("Memory Usage Over Time")
        chart_layout = QVBoxLayout(chart_group)

        self.memory_info_label = QLabel("Memory tracking information will appear here")
        self.memory_info_label.setWordWrap(True)
        chart_layout.addWidget(self.memory_info_label)

        layout.addWidget(chart_group)

        # Memory details
        details_group = QGroupBox("Memory Details")
        details_layout = QGridLayout(details_group)

        self.rss_label = QLabel("0 MB")
        self.vms_label = QLabel("0 MB")
        self.available_label = QLabel("0 MB")
        self.gc_stats_label = QLabel("Gen0: 0, Gen1: 0, Gen2: 0")

        details_layout.addWidget(QLabel("Resident Set Size:"), 0, 0)
        details_layout.addWidget(self.rss_label, 0, 1)
        details_layout.addWidget(QLabel("Virtual Memory:"), 1, 0)
        details_layout.addWidget(self.vms_label, 1, 1)
        details_layout.addWidget(QLabel("Available System:"), 0, 2)
        details_layout.addWidget(self.available_label, 0, 3)
        details_layout.addWidget(QLabel("GC Statistics:"), 1, 2)
        details_layout.addWidget(self.gc_stats_label, 1, 3)

        layout.addWidget(details_group)

        layout.addStretch()
        tab.setWidget(content)
        self.tab_widget.addTab(tab, "Memory")

    def _create_operations_tab(self):
        """Create operations monitoring tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Operations table
        self.operations_table = QTableWidget()
        self.operations_table.setColumnCount(6)
        self.operations_table.setHorizontalHeaderLabels([
            "Operation", "Duration (s)", "Memory Δ (MB)", "CPU %", "Status", "Metadata"
        ])
        layout.addWidget(self.operations_table)

        # Filter controls
        filter_layout = QHBoxLayout()
        self.show_errors_button = QPushButton("Show Errors Only")
        self.show_slow_button = QPushButton("Show Slow Operations")
        self.show_memory_button = QPushButton("Show Memory Intensive")

        filter_layout.addWidget(self.show_errors_button)
        filter_layout.addWidget(self.show_slow_button)
        filter_layout.addWidget(self.show_memory_button)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        self.tab_widget.addTab(tab, "Operations")

    def _create_system_tab(self):
        """Create system information tab."""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)

        # System info display
        self.system_info_browser = QTextBrowser()
        layout.addWidget(self.system_info_browser)

        tab.setWidget(content)
        self.tab_widget.addTab(tab, "System Info")

    def _create_raw_data_tab(self):
        """Create raw data tab for debugging."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Raw data browser
        self.raw_data_browser = QTextBrowser()
        self.raw_data_browser.setFontFamily("Courier New")
        layout.addWidget(self.raw_data_browser)

        self.tab_widget.addTab(tab, "Raw Data")

    def _connect_signals(self):
        """Connect signals and slots."""
        self.refresh_button.clicked.connect(self.refresh_data)
        self.reset_button.clicked.connect(self.reset_data)
        self.export_button.clicked.connect(self.export_report)
        self.close_button.clicked.connect(self.close)

        self.show_errors_button.clicked.connect(lambda: self._filter_operations("errors"))
        self.show_slow_button.clicked.connect(lambda: self._filter_operations("slow"))
        self.show_memory_button.clicked.connect(lambda: self._filter_operations("memory"))

        # Auto-refresh timer
        self.update_timer.timeout.connect(self.refresh_data)

    def _start_monitoring(self):
        """Start real-time monitoring."""
        self.update_timer.start(2000)  # Update every 2 seconds
        self.refresh_data()

    def refresh_data(self):
        """Refresh all performance data."""
        if not self.isVisible():
            return

        try:
            self._update_overview()
            self._update_memory()
            self._update_operations()
            self._update_system_info()
            self._update_raw_data()
        except Exception as e:
            logger.error(f"Failed to refresh performance data: {e}")

    def _update_overview(self):
        """Update overview tab data."""
        report = self.monitor.generate_report()

        # Summary metrics
        self.total_ops_label.setText(str(len(report.operations)))
        self.total_time_label.setText(f"{report.total_duration:.3f}s")
        self.peak_memory_label.setText(f"{report.peak_memory_mb:.2f} MB")
        self.memory_delta_label.setText(f"{report.total_memory_delta:+.2f} MB")
        self.avg_cpu_label.setText(f"{report.avg_cpu_percent:.1f}%")

        # Current status
        snapshot = self.monitor.take_memory_snapshot()
        self.current_memory_label.setText(f"{snapshot.rss_mb:.2f} MB")
        self.current_objects_label.setText(f"{snapshot.objects_count:,}")
        self.memory_progress.setValue(int(snapshot.percent))

        # Recent operations
        recent_ops = report.operations[-5:] if report.operations else []
        self.recent_ops_table.setRowCount(len(recent_ops))

        for i, op in enumerate(recent_ops):
            self.recent_ops_table.setItem(i, 0, QTableWidgetItem(op.operation_name))
            self.recent_ops_table.setItem(i, 1, QTableWidgetItem(f"{op.duration:.3f}s"))
            self.recent_ops_table.setItem(i, 2, QTableWidgetItem(f"{op.memory_delta:+.2f}MB"))
            status = "✅" if op.success else "❌"
            self.recent_ops_table.setItem(i, 3, QTableWidgetItem(status))

    def _update_memory(self):
        """Update memory tab data."""
        snapshot = self.monitor.take_memory_snapshot()

        # Update labels
        self.rss_label.setText(f"{snapshot.rss_mb:.2f} MB")
        self.vms_label.setText(f"{snapshot.vms_mb:.2f} MB")
        self.available_label.setText(f"{snapshot.available_mb:.2f} MB")

        # GC stats
        gc_text = ", ".join([
            f"Gen{i}: {count}"
            for i, count in enumerate(snapshot.gc_stats.values())
        ])
        self.gc_stats_label.setText(gc_text)

        # Memory info
        info_text = f"""
Memory Usage Information:
• Current RSS: {snapshot.rss_mb:.2f} MB
• Current VMS: {snapshot.vms_mb:.2f} MB  
• System Usage: {snapshot.percent:.1f}%
• Available: {snapshot.available_mb:.2f} MB
• Python Objects: {snapshot.objects_count:,}
• Timestamp: {snapshot.timestamp:.3f}

Peak Memory: {self.monitor.get_peak_memory():.2f} MB
Total Delta: {self.monitor.get_total_memory_delta():+.2f} MB
        """.strip()

        self.memory_info_label.setText(info_text)

    def _update_operations(self):
        """Update operations tab data."""
        operations = self.monitor.operations
        self.operations_table.setRowCount(len(operations))

        for i, op in enumerate(operations):
            self.operations_table.setItem(i, 0, QTableWidgetItem(op.operation_name))
            self.operations_table.setItem(i, 1, QTableWidgetItem(f"{op.duration:.3f}"))
            self.operations_table.setItem(i, 2, QTableWidgetItem(f"{op.memory_delta:+.2f}"))
            self.operations_table.setItem(i, 3, QTableWidgetItem(f"{op.cpu_percent:.1f}"))

            status = "✅ Success" if op.success else f"❌ {op.error_message}"
            self.operations_table.setItem(i, 4, QTableWidgetItem(status))

            metadata = json.dumps(op.metadata) if op.metadata else ""
            self.operations_table.setItem(i, 5, QTableWidgetItem(metadata))

        # Auto-resize columns
        self.operations_table.resizeColumnsToContents()

    def _update_system_info(self):
        """Update system information tab."""
        report = self.monitor.generate_report()
        system_info = report.system_info

        info_html = "<h3>System Information</h3>"
        info_html += "<table border='1' cellpadding='5'>"

        for key, value in system_info.items():
            if isinstance(value, dict):
                info_html += f"<tr><td><b>{key}</b></td><td>{json.dumps(value, indent=2)}</td></tr>"
            else:
                info_html += f"<tr><td><b>{key}</b></td><td>{value}</td></tr>"

        info_html += "</table>"

        info_html += "<h3>Performance Summary</h3>"
        info_html += f"<p><b>Report ID:</b> {report.report_id}</p>"
        info_html += f"<p><b>Total Duration:</b> {report.total_duration:.3f}s</p>"
        info_html += f"<p><b>Operations Count:</b> {len(report.operations)}</p>"
        info_html += f"<p><b>GC Collections:</b> {report.gc_collections}</p>"

        self.system_info_browser.setHtml(info_html)

    def _update_raw_data(self):
        """Update raw data tab."""
        report = self.monitor.generate_report()

        # Convert report to JSON for display
        raw_data = {
            "report_id": report.report_id,
            "start_time": report.start_time,
            "end_time": report.end_time,
            "total_duration": report.total_duration,
            "peak_memory_mb": report.peak_memory_mb,
            "total_memory_delta": report.total_memory_delta,
            "avg_cpu_percent": report.avg_cpu_percent,
            "gc_collections": report.gc_collections,
            "system_info": report.system_info,
            "operations": [
                {
                    "operation_name": op.operation_name,
                    "duration": op.duration,
                    "memory_delta": op.memory_delta,
                    "cpu_percent": op.cpu_percent,
                    "success": op.success,
                    "error_message": op.error_message,
                    "metadata": op.metadata
                }
                for op in report.operations
            ]
        }

        json_text = json.dumps(raw_data, indent=2)
        self.raw_data_browser.setPlainText(json_text)

    def _filter_operations(self, filter_type: str):
        """Filter operations table based on type."""
        operations = self.monitor.operations

        if filter_type == "errors":
            filtered = [op for op in operations if not op.success]
        elif filter_type == "slow":
            # Show operations taking more than 1 second
            filtered = [op for op in operations if op.duration > 1.0]
        elif filter_type == "memory":
            # Show operations with significant memory changes
            filtered = [op for op in operations if abs(op.memory_delta) > 10.0]
        else:
            filtered = operations

        # Update table with filtered data
        self.operations_table.setRowCount(len(filtered))
        for i, op in enumerate(filtered):
            self.operations_table.setItem(i, 0, QTableWidgetItem(op.operation_name))
            self.operations_table.setItem(i, 1, QTableWidgetItem(f"{op.duration:.3f}"))
            self.operations_table.setItem(i, 2, QTableWidgetItem(f"{op.memory_delta:+.2f}"))
            self.operations_table.setItem(i, 3, QTableWidgetItem(f"{op.cpu_percent:.1f}"))

            status = "✅ Success" if op.success else f"❌ {op.error_message}"
            self.operations_table.setItem(i, 4, QTableWidgetItem(status))

            metadata = json.dumps(op.metadata) if op.metadata else ""
            self.operations_table.setItem(i, 5, QTableWidgetItem(metadata))

    def reset_data(self):
        """Reset all performance data."""
        reply = QMessageBox.question(
            self,
            "Reset Performance Data",
            "Are you sure you want to reset all performance monitoring data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.monitor.reset()
            self.refresh_data()
            self.reset_requested.emit()
            logger.info("Performance data reset by user")

    def export_report(self):
        """Export performance report to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Performance Report",
            f"performance_report_{int(self.monitor.start_time)}.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                report = self.monitor.generate_report()

                # Convert report to serializable format
                export_data = {
                    "report_id": report.report_id,
                    "start_time": report.start_time,
                    "end_time": report.end_time,
                    "total_duration": report.total_duration,
                    "peak_memory_mb": report.peak_memory_mb,
                    "total_memory_delta": report.total_memory_delta,
                    "avg_cpu_percent": report.avg_cpu_percent,
                    "gc_collections": report.gc_collections,
                    "system_info": report.system_info,
                    "operations": [
                        {
                            "operation_name": op.operation_name,
                            "start_time": op.start_time,
                            "end_time": op.end_time,
                            "duration": op.duration,
                            "memory_delta": op.memory_delta,
                            "cpu_percent": op.cpu_percent,
                            "success": op.success,
                            "error_message": op.error_message,
                            "metadata": op.metadata,
                            "memory_before": {
                                "timestamp": op.memory_before.timestamp,
                                "rss_mb": op.memory_before.rss_mb,
                                "vms_mb": op.memory_before.vms_mb,
                                "percent": op.memory_before.percent,
                                "available_mb": op.memory_before.available_mb,
                                "objects_count": op.memory_before.objects_count,
                                "gc_stats": op.memory_before.gc_stats
                            },
                            "memory_after": {
                                "timestamp": op.memory_after.timestamp,
                                "rss_mb": op.memory_after.rss_mb,
                                "vms_mb": op.memory_after.vms_mb,
                                "percent": op.memory_after.percent,
                                "available_mb": op.memory_after.available_mb,
                                "objects_count": op.memory_after.objects_count,
                                "gc_stats": op.memory_after.gc_stats
                            }
                        }
                        for op in report.operations
                    ]
                }

                with open(file_path, "w") as f:
                    json.dump(export_data, f, indent=2)

                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Performance report exported to:\n{file_path}"
                )

                self.export_requested.emit(file_path)
                logger.info(f"Performance report exported to: {file_path}")

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export performance report:\n{e}"
                )
                logger.error(f"Failed to export performance report: {e}")

    def closeEvent(self, event):
        """Handle dialog close event."""
        self.update_timer.stop()
        super().closeEvent(event)
        logger.debug("Performance dialog closed")
