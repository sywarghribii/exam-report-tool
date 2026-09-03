import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QHBoxLayout, QWidget,
    QFileDialog, QLabel, QLineEdit, QComboBox, QTabWidget,
    QMessageBox
)
from exam_toolkit import parse_report
from exam_toolkit.analyzer import cluster_by_signature
from exam_toolkit.excel_export import export_reports_to_excel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EXAM Report Tool")
        self.resize(1200, 600)

        self.reports = {}       # {label: ExamReport}
        self.all_test_cases = []

        self.import_button = QPushButton("Importer des rapports XML")
        self.import_button.clicked.connect(self.import_reports)

        self.export_button = QPushButton("Exporter en Excel")
        self.export_button.clicked.connect(self.export_excel)

        self.summary_label = QLabel("Aucun rapport chargé.")

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.import_button)
        top_layout.addWidget(self.export_button)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tous", "PASS", "FAIL"])
        self.status_filter.currentTextChanged.connect(self.apply_filters)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Rechercher (nom, groupe, ID)...")
        self.search_box.textChanged.connect(self.apply_filters)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Statut:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(self.search_box)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Nom", "Groupe", "Statut", "Fails"])
        self.table.setWordWrap(True)

        tests_tab = QWidget()
        tests_layout = QVBoxLayout()
        tests_layout.addLayout(filter_layout)
        tests_layout.addWidget(self.table)
        tests_tab.setLayout(tests_layout)

        self.cluster_table = QTableWidget()
        self.cluster_table.setColumnCount(4)
        self.cluster_table.setHorizontalHeaderLabels(
            ["Rang", "Occurrences", "Tests concernés", "Exemple d'erreur"]
        )
        self.cluster_table.setWordWrap(True)

        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout()
        analysis_layout.addWidget(self.cluster_table)
        analysis_tab.setLayout(analysis_layout)

        self.tabs = QTabWidget()
        self.tabs.addTab(tests_tab, "Tests")
        self.tabs.addTab(analysis_tab, "Analyse des échecs")

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.summary_label)
        main_layout.addWidget(self.tabs)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def import_reports(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Choisir un ou plusieurs rapports XML", "", "XML Files (*.xml)"
        )
        if not file_paths:
            return

        self.reports = {}
        for path in file_paths:
            label = Path(path).name
            self.reports[label] = parse_report(path)

        self.all_test_cases = []
        for report in self.reports.values():
            self.all_test_cases.extend(report.test_cases)

        total = len(self.all_test_cases)
        passed = sum(1 for tc in self.all_test_cases if tc.final_valuation == "PASS")
        failed = sum(1 for tc in self.all_test_cases if tc.final_valuation == "FAIL")
        self.summary_label.setText(
            f"Rapports: {len(self.reports)} | Total: {total} | Passed: {passed} | Failed: {failed}"
        )

        self.apply_filters()
        self.update_clusters()

    def apply_filters(self):
        status = self.status_filter.currentText()
        search = self.search_box.text().lower()

        filtered = []
        for tc in self.all_test_cases:
            if status != "Tous" and tc.final_valuation != status:
                continue
            haystack = f"{tc.test_case_id} {tc.name} {tc.group_path_str}".lower()
            if search and search not in haystack:
                continue
            filtered.append(tc)

        self.table.setRowCount(0)
        for tc in filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(tc.test_case_id))
            self.table.setItem(row, 1, QTableWidgetItem(tc.name))
            self.table.setItem(row, 2, QTableWidgetItem(tc.group_path_str))
            self.table.setItem(row, 3, QTableWidgetItem(tc.final_valuation))
            fails_text = tc.fails_text() if tc.final_valuation == "FAIL" else ""
            self.table.setItem(row, 4, QTableWidgetItem(fails_text))

        self.table.resizeRowsToContents()
        self.table.setColumnWidth(4, 500)

    def update_clusters(self):
        if not self.reports:
            return

        clusters = cluster_by_signature(list(self.reports.values()))
        self.cluster_table.setRowCount(0)

        for i, cluster in enumerate(clusters, start=1):
            row = self.cluster_table.rowCount()
            self.cluster_table.insertRow(row)
            self.cluster_table.setItem(row, 0, QTableWidgetItem(str(i)))
            self.cluster_table.setItem(row, 1, QTableWidgetItem(str(cluster.size)))
            test_ids = ", ".join(cluster.test_case_ids) if hasattr(cluster, "test_case_ids") else ""
            self.cluster_table.setItem(row, 2, QTableWidgetItem(test_ids))
            self.cluster_table.setItem(row, 3, QTableWidgetItem(str(cluster.signature)))

        self.cluster_table.resizeRowsToContents()
        self.cluster_table.setColumnWidth(3, 500)

    def export_excel(self):
        if not self.reports:
            QMessageBox.warning(self, "Aucun rapport", "Importe d'abord un ou plusieurs rapports XML.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le rapport Excel", "rapport.xlsx", "Excel Files (*.xlsx)"
        )
        if not save_path:
            return

        export_reports_to_excel(self.reports, save_path)
        QMessageBox.information(self, "Export réussi", f"Rapport exporté vers:\n{save_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())