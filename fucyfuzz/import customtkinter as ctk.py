import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import signal
import sys
import time
import random
import json
from datetime import datetime
from collections import defaultdict
import csv


# --- OPTIONAL IMPORTS ---
try:
    import cantools
except ImportError:
    cantools = None

# ==============================================================================
#  ENHANCED PDF REPORT GENERATOR WITH TOC
# ==============================================================================

# First, let's check and import ReportLab modules
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Table, TableStyle, Preformatted, Image, ListFlowable,
        ListItem, KeepTogether
    )
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.graphics.shapes import Drawing, Line

    # Store these as module-level variables for easy access
    REPORTLAB_AVAILABLE = True
    reportlab_styles = getSampleStyleSheet()

except ImportError:
    REPORTLAB_AVAILABLE = False
    SimpleDocTemplate = None
    Paragraph = None
    Spacer = None
    PageBreak = None
    Table = None
    TableStyle = None
    Preformatted = None
    ListFlowable = None
    ListItem = None
    KeepTogether = None
    TableOfContents = None
    Canvas = None
    Drawing = None
    Line = None
    colors = None
    letter = None
    A4 = None
    ParagraphStyle = None
    inch = None
    cm = None
    getSampleStyleSheet = None


class TOCDocTemplate(SimpleDocTemplate):
    """Custom DocTemplate for Table of Contents and PDF Bookmarks"""
    def __init__(self, filename, **kw):
        super().__init__(filename, **kw)
        self.toc_entries = []
        self.bookmark_counter = 0

    def afterFlowable(self, flowable):
        """Register TOC entries and PDF bookmarks for heading styles"""
        if hasattr(flowable, 'style') and hasattr(flowable.style, 'name'):
            style_name = flowable.style.name
            text = flowable.getPlainText() if hasattr(flowable, 'getPlainText') else str(flowable)

            # Module Header - Level 1
            if style_name == 'ModuleHeader':
                self.notify('TOCEntry', (0, text, self.page))
                key = f"h1_{self.bookmark_counter}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, 0, False)
                self.bookmark_counter += 1

            # Result Header - Level 2
            elif style_name == 'ResultHeader':
                self.notify('TOCEntry', (1, text, self.page))
                key = f"h2_{self.bookmark_counter}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, 1, False)
                self.bookmark_counter += 1


class EnhancedPDFReport:
    """Enhanced PDF report generator with TOC, bookmarks, and dynamic content"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.REPORTLAB_AVAILABLE = REPORTLAB_AVAILABLE

    def generate_pdf(self, filename, title, entries):
        """Generate enhanced PDF report with TOC, bookmarks, and statistics"""
        if not self.REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "ReportLab not installed. Saving as .txt instead.")
            return self.save_txt_report(filename.replace(".pdf", ".txt"), title, entries)

        try:
            # ----------------------------------------------------
            # 1. DATA ANALYSIS & STATISTICS
            # ----------------------------------------------------
            total_entries = len(entries)
            modules = defaultdict(list)
            status_counts = defaultdict(int)

            for e in entries:
                modules[e['module']].append(e)
                status = e['status'].lower()
                if 'success' in status:
                    status_counts['success'] += 1
                elif 'warning' in status:
                    status_counts['warning'] += 1
                elif 'error' in status or 'failed' in status:
                    status_counts['error'] += 1
                else:
                    status_counts['other'] += 1

            # Calculate percentages
            status_percentages = {}
            for status, count in status_counts.items():
                status_percentages[status] = (count / total_entries * 100) if total_entries > 0 else 0

            # ----------------------------------------------------
            # 2. SETUP HEADER & FOOTER
            # ----------------------------------------------------
            def header_footer(canvas, doc):
                canvas.saveState()

                # Header
                canvas.setFont("Helvetica-Bold", 10)
                canvas.setFillColor(colors.HexColor("#2c3e50"))
                canvas.drawString(doc.leftMargin, doc.pagesize[1] - 30, title)

                # Header line
                canvas.setStrokeColor(colors.HexColor("#3498db"))
                canvas.setLineWidth(1)
                canvas.line(doc.leftMargin, doc.pagesize[1] - 35,
                           doc.pagesize[0] - doc.rightMargin, doc.pagesize[1] - 35)

                # Footer
                canvas.setFont("Helvetica", 8)
                canvas.setFillColor(colors.gray)
                page_num = canvas.getPageNumber()

                # Footer line
                canvas.setStrokeColor(colors.lightgrey)
                canvas.setLineWidth(0.5)
                canvas.line(doc.leftMargin, 40, doc.pagesize[0] - doc.rightMargin, 40)

                # Left footer - Report info
                canvas.drawString(doc.leftMargin, 25, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # Center footer - Confidential
                canvas.setFont("Helvetica-Oblique", 8)
                canvas.drawCentredString(doc.pagesize[0]/2, 25, "CONFIDENTIAL - FucyFuzz Security Report")

                # Right footer - Page number
                canvas.setFont("Helvetica", 9)
                canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 25, f"Page {page_num}")

                canvas.restoreState()

            # ----------------------------------------------------
            # 3. DEFINE STYLES
            # ----------------------------------------------------
            # Title Page Styles
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=reportlab_styles['Title'],
                fontSize=32,
                alignment=1,
                spaceAfter=30,
                textColor=colors.HexColor("#2c3e50"),
                fontName='Helvetica-Bold'
            )

            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=reportlab_styles['Heading2'],
                alignment=1,
                textColor=colors.HexColor("#7f8c8d"),
                spaceAfter=40,
                fontName='Helvetica-Oblique'
            )

            # Content Styles
            module_header_style = ParagraphStyle(
                'ModuleHeader',
                parent=reportlab_styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor("#2980b9"),
                spaceBefore=20,
                spaceAfter=12,
                leading=24,
                fontName='Helvetica-Bold',
                borderWidth=1,
                borderPadding=5,
                borderColor=colors.HexColor("#3498db"),
                borderRadius=2,
                backColor=colors.HexColor("#f8f9fa")
            )

            result_header_style = ParagraphStyle(
                'ResultHeader',
                parent=reportlab_styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor("#2c3e50"),
                spaceBefore=12,
                spaceAfter=8,
                leading=18,
                fontName='Helvetica-Bold'
            )

            normal_style = ParagraphStyle(
                'NormalCustom',
                parent=reportlab_styles['Normal'],
                fontSize=10,
                leading=12,
                spaceAfter=6
            )

            highlight_style = ParagraphStyle(
                'Highlight',
                parent=reportlab_styles['Normal'],
                fontSize=10,
                leading=12,
                backColor=colors.HexColor("#e8f4fd"),
                borderColor=colors.HexColor("#3498db"),
                borderWidth=1,
                borderPadding=8,
                spaceAfter=10
            )

            code_style = ParagraphStyle(
                'Code',
                parent=reportlab_styles['Code'],
                fontSize=9,
                leading=11,
                backColor=colors.HexColor("#f8f9fa"),
                borderColor=colors.lightgrey,
                borderWidth=1,
                borderPadding=10,
                fontName='Courier'
            )

            # TOC Styles
            toc_h1_style = ParagraphStyle(
                'TOC_H1',
                parent=reportlab_styles['Normal'],
                fontSize=12,
                leading=14,
                spaceAfter=4,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor("#2c3e50")
            )

            toc_h2_style = ParagraphStyle(
                'TOC_H2',
                parent=reportlab_styles['Normal'],
                fontSize=10,
                leading=12,
                leftIndent=20,
                spaceAfter=2,
                textColor=colors.HexColor("#34495e")
            )

            # ----------------------------------------------------
            # 4. BUILD STORY
            # ----------------------------------------------------
            story = []

            # --- COVER PAGE ---
            story.append(Spacer(1, 2 * inch))
            story.append(Paragraph("FUZZYFUZZ SECURITY TEST REPORT", title_style))
            story.append(Paragraph(f"<i>{title}</i>", subtitle_style))
            story.append(Spacer(1, 1.5 * inch))

            # Add decorative line
            d = Drawing(400, 1)
            d.add(Line(0, 0, 400, 0, strokeColor=colors.HexColor("#3498db"), strokeWidth=2))
            story.append(d)
            story.append(Spacer(1, 0.5 * inch))

            # Executive Summary Box
            exec_summary = [
                "Executive Summary",
                f"• Total Tests: {total_entries}",
                f"• Modules Tested: {len(modules)}",
                f"• Success Rate: {status_percentages.get('success', 0):.1f}%",
                f"• Failures: {status_counts.get('error', 0)}",
                f"• Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ]

            story.append(Paragraph("<b>EXECUTIVE SUMMARY</b>", reportlab_styles['Heading2']))
            story.append(Spacer(1, 0.2 * inch))

            summary_list = ListFlowable(
                [ListItem(Paragraph(text, normal_style)) for text in exec_summary[1:]],
                bulletType='bullet',
                leftIndent=20,
                bulletFontSize=10
            )
            story.append(summary_list)
            story.append(PageBreak())

            # --- TABLE OF CONTENTS PAGE ---
            story.append(Paragraph("TABLE OF CONTENTS", reportlab_styles['Heading1']))
            story.append(Spacer(1, 0.3 * inch))

            # Add TOC
            toc = TableOfContents()
            toc.levelStyles = [toc_h1_style, toc_h2_style]
            story.append(toc)
            story.append(PageBreak())

            # --- EXECUTIVE DASHBOARD PAGE ---
            story.append(Paragraph("EXECUTIVE DASHBOARD", reportlab_styles['Heading1']))
            story.append(Spacer(1, 0.3 * inch))

            # Statistics Table
            stats_data = [
                ["Metric", "Count", "Percentage"],
                ["Total Tests", str(total_entries), "100%"],
                ["Successful", str(status_counts.get('success', 0)), f"{status_percentages.get('success', 0):.1f}%"],
                ["Warnings", str(status_counts.get('warning', 0)), f"{status_percentages.get('warning', 0):.1f}%"],
                ["Failures", str(status_counts.get('error', 0)), f"{status_percentages.get('error', 0):.1f}%"],
                ["Other", str(status_counts.get('other', 0)), f"{status_percentages.get('other', 0):.1f}%"]
            ]

            t1 = Table(stats_data, colWidths=[200, 100, 100])
            t1.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#ecf0f1")),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(t1)
            story.append(Spacer(1, 0.5 * inch))

            # Module Distribution
            story.append(Paragraph("Module Distribution", reportlab_styles['Heading2']))
            story.append(Spacer(1, 0.2 * inch))

            module_data = [["Module", "Test Count", "Percentage"]]
            for module_name, module_entries in modules.items():
                percentage = (len(module_entries) / total_entries * 100) if total_entries > 0 else 0
                module_data.append([module_name, str(len(module_entries)), f"{percentage:.1f}%"])

            t2 = Table(module_data, colWidths=[250, 100, 100])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (2, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ]))
            story.append(t2)
            story.append(PageBreak())

            # --- DETAILED TEST RESULTS ---
            story.append(Paragraph("DETAILED TEST RESULTS", reportlab_styles['Heading1']))
            story.append(Spacer(1, 0.3 * inch))

            for module_idx, (module_name, module_entries) in enumerate(modules.items()):
                # Module Header with counter (triggers Level 1 TOC)
                story.append(Paragraph(f"Module {module_idx + 1}: {module_name}", module_header_style))
                story.append(Spacer(1, 0.1 * inch))

                # Module Summary
                module_success = sum(1 for e in module_entries if 'success' in e['status'].lower())
                module_total = len(module_entries)
                module_percentage = (module_success / module_total * 100) if module_total > 0 else 0

                summary_text = f"""
                <b>Module Summary:</b> {module_success} of {module_total} tests successful ({module_percentage:.1f}% success rate)
                """
                story.append(Paragraph(summary_text, highlight_style))
                story.append(Spacer(1, 0.2 * inch))

                # Individual Test Results
                for test_idx, entry in enumerate(module_entries):
                    # Test Header (triggers Level 2 TOC)
                    test_title = f"Test {test_idx + 1}: {entry['command'][:60]}..."
                    story.append(Paragraph(test_title, result_header_style))

                    # Test Metadata Table
                    status_color = "#27ae60" if "success" in entry["status"].lower() else \
                                  "#f39c12" if "warning" in entry["status"].lower() else "#c0392b"

                    meta_data = [
                        ["Timestamp:", entry['timestamp']],
                        ["Status:", f"<font color='{status_color}'><b>{entry['status']}</b></font>"],
                        ["Command:", f"<font face='Courier'>{entry['command']}</font>"]
                    ]

                    meta_table = Table(meta_data, colWidths=[100, 400])
                    meta_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
                    ]))
                    story.append(meta_table)
                    story.append(Spacer(1, 0.1 * inch))

                    # Output Section
                    story.append(Paragraph("<b>Output:</b>", reportlab_styles['Heading3']))

                    output_text = entry["output"]
                    if len(output_text) > 5000:
                        output_text = output_text[:5000] + "\n\n[TRUNCATED - Output too large. See logs for full details.]"

                    # Split long output into chunks
                    output_lines = output_text.split('\n')
                    max_lines = 100

                    if len(output_lines) > max_lines:
                        story.append(Paragraph(f"<i>Showing first {max_lines} of {len(output_lines)} lines...</i>", normal_style))
                        output_text = '\n'.join(output_lines[:max_lines])

                    story.append(Preformatted(output_text, code_style))

                    # Recommendations if not successful
                    if "success" not in entry["status"].lower():
                        story.append(Spacer(1, 0.1 * inch))
                        story.append(Paragraph("<b>Recommendations:</b>", reportlab_styles['Heading3']))
                        rec_text = "• Review the test configuration<br/>• Check system permissions<br/>• Verify input parameters<br/>• Consult security guidelines<br/>• Check target system availability<br/>• Review error logs in detail"
                        story.append(Paragraph(rec_text, normal_style))

                    story.append(Spacer(1, 0.3 * inch))

                # Add page break between modules except the last one
                if module_idx < len(modules) - 1:
                    story.append(PageBreak())

            # --- APPENDIX ---
            story.append(PageBreak())
            story.append(Paragraph("APPENDIX", reportlab_styles['Heading1']))
            story.append(Spacer(1, 0.3 * inch))

            # Configuration Details
            story.append(Paragraph("Configuration Details", reportlab_styles['Heading2']))
            config_data = [
                ["Parameter", "Value"],
                ["Working Directory", self.app.working_dir],
                ["DBC Messages", str(len(self.app.dbc_messages))],
                ["Report Format", "PDF v2.0 with TOC"],
                ["Generated By", "FucyFuzz Security Framework"],
                ["Generation Time", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            ]

            t3 = Table(config_data, colWidths=[200, 300])
            t3.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#95a5a6")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ]))
            story.append(t3)

            # ----------------------------------------------------
            # 5. GENERATE DOCUMENT
            # ----------------------------------------------------
            doc = TOCDocTemplate(
                filename,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            # Build document with multi-pass for TOC
            doc.multiBuild(story, onFirstPage=header_footer, onLaterPages=header_footer)

            # Show success message with file location
            abs_path = os.path.abspath(filename)
            messagebox.showinfo(
                "Success",
                f"✓ PDF Report Generated Successfully!\n\n"
                f"File: {os.path.basename(filename)}\n"
                f"Location: {os.path.dirname(abs_path)}\n\n"
                f"Features Included:\n"
                f"• Table of Contents with Bookmarks\n"
                f"• Executive Dashboard\n"
                f"• Detailed Module Results\n"
                f"• Status Statistics\n"
                f"• Page Headers & Footers"
            )

            # Open the PDF if on Windows
            if os.name == 'nt':
                os.startfile(abs_path)

            return filename

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"PDF Generation Error:\n{error_details}")
            messagebox.showerror(
                "PDF Generation Error",
                f"Failed to generate PDF report:\n\n"
                f"Error: {str(e)}\n\n"
                f"Please ensure:\n"
                f"1. ReportLab is properly installed\n"
                f"2. You have write permissions\n"
                f"3. Enough disk space is available\n\n"
                f"Details have been logged to console."
            )
            # Fallback to text export
            txt_filename = filename.replace(".pdf", "_error_fallback.txt")
            return self.save_txt_report(txt_filename, title, entries)

    def save_txt_report(self, filename, title, entries):
        """Fallback method to save report as text file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{'='*60}\n")
                f.write(f"FucyFuzz Security Report: {title}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n\n")

                # Group by module
                modules = {}
                for entry in entries:
                    modules.setdefault(entry['module'], []).append(entry)

                for module_name, module_entries in modules.items():
                    f.write(f"\n{'='*40}\n")
                    f.write(f"MODULE: {module_name}\n")
                    f.write(f"{'='*40}\n\n")

                    for idx, entry in enumerate(module_entries):
                        f.write(f"Test {idx + 1}:\n")
                        f.write(f"  Timestamp: {entry['timestamp']}\n")
                        f.write(f"  Status: {entry['status']}\n")
                        f.write(f"  Command: {entry['command']}\n")
                        f.write(f"  Output:\n{'-'*20}\n")
                        f.write(entry['output'][:2000])  # Limit output length
                        f.write(f"\n{'-'*20}\n\n")

            messagebox.showinfo(
                "Fallback Export",
                f"Exported as text file instead:\n{filename}"
            )
            return filename

        except Exception as e:
            messagebox.showerror("Text Export Error", f"Failed to save text report: {str(e)}")
            return None


# ==============================================================================
#  FAILURE CAPTURE AND RE-RUN SYSTEM
# ==============================================================================

class FailureCaptureSystem:
    """System to capture and re-run failed test cases from length attack and other modules"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.failed_cases_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed_cases")
        self.failed_cases_file = os.path.join(self.failed_cases_dir, "failed_cases.json")
        self.ensure_directory()
        self.failed_cases = self.load_failed_cases()

    def ensure_directory(self):
        """Create failed cases directory if it doesn't exist"""
        if not os.path.exists(self.failed_cases_dir):
            os.makedirs(self.failed_cases_dir)

    def load_failed_cases(self):
        """Load failed cases from JSON file"""
        if os.path.exists(self.failed_cases_file):
            try:
                with open(self.failed_cases_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {"length_attack": [], "other_modules": []}
        return {"length_attack": [], "other_modules": []}

    def save_failed_cases(self):
        """Save failed cases to JSON file"""
        try:
            with open(self.failed_cases_file, 'w') as f:
                json.dump(self.failed_cases, f, indent=2)
        except Exception as e:
            print(f"Error saving failed cases: {e}")

    def parse_failure_line(self, line, module_name):
        """Parse a failure line from console output and extract details"""
        try:
            # Check if this is a [FAIL] line from length attack
            if "[FAIL]" in line and "SEND" in line and "ID=" in line:
                # Parse length attack failure format:
                # 2024-01-01T12:00:00.000000 [FAIL] SEND ID=0x123 DLC=8 LEN=8 (Socket/Bus Error)
                parts = line.split("[FAIL]")[1].strip()

                # Extract ID
                id_start = parts.find("ID=0x") + 3
                id_end = parts.find(" ", id_start)
                arb_id = parts[id_start:id_end]

                # Extract DLC
                dlc_start = parts.find("DLC=") + 4
                dlc_end = parts.find(" ", dlc_start)
                dlc = parts[dlc_start:dlc_end]

                # Extract length
                len_start = parts.find("LEN=") + 4
                len_end = parts.find(" ", len_start)
                if len_end == -1:
                    len_end = len(parts)
                data_len = parts[len_start:len_end]

                # Extract data if available
                data = ""
                data_start = parts.find("DATA=")
                if data_start != -1:
                    data_start += 5
                    data_end = parts.find(" ", data_start)
                    if data_end == -1:
                        data_end = len(parts)
                    data = parts[data_start:data_end]

                failure_details = {
                    "timestamp": line.split(" [FAIL]")[0].strip(),
                    "module": module_name,
                    "arbitration_id": arb_id,
                    "dlc": dlc,
                    "data_length": data_len,
                    "data": data,
                    "error_type": "Socket/Bus Error" if "(Socket/Bus Error)" in parts else "Unknown Error",
                    "raw_line": line.strip()
                }

                return failure_details

            # Check for other failure formats
            elif "[FAIL]" in line and "ERROR sending" in line:
                # Parse error sending format
                parts = line.split("[FAIL]")[1].strip()

                # Extract ID if available
                arb_id = "Unknown"
                if "0x" in parts:
                    id_start = parts.find("0x")
                    id_end = parts.find(":", id_start)
                    if id_end != -1:
                        arb_id = parts[id_start:id_end]

                failure_details = {
                    "timestamp": line.split(" [FAIL]")[0].strip(),
                    "module": module_name,
                    "arbitration_id": arb_id,
                    "error_type": parts.split(":")[-1].strip() if ":" in parts else "Unknown Error",
                    "raw_line": line.strip()
                }

                return failure_details

            # Generic failure pattern
            elif "[FAIL]" in line:
                failure_details = {
                    "timestamp": line.split(" [FAIL]")[0].strip() if " [FAIL]" in line else datetime.now().isoformat(),
                    "module": module_name,
                    "error_type": "Generic Failure",
                    "raw_line": line.strip()
                }
                return failure_details

        except Exception as e:
            print(f"Error parsing failure line: {e}")
            print(f"Line: {line}")

        return None

    def capture_failure(self, output_text, module_name):
        """Capture failures from console output"""
        lines = output_text.split('\n')
        new_failures = []

        for line in lines:
            if "[FAIL]" in line and "SEND" in line:
                failure = self.parse_failure_line(line, module_name)
                if failure:
                    # Check if this failure already exists
                    existing = False
                    for existing_failure in self.failed_cases.get("length_attack", []):
                        if (existing_failure.get("arbitration_id") == failure.get("arbitration_id") and
                            existing_failure.get("dlc") == failure.get("dlc") and
                            existing_failure.get("data_length") == failure.get("data_length")):
                            existing = True
                            break

                    if not existing:
                        self.failed_cases["length_attack"].append(failure)
                        new_failures.append(failure)

            elif "[FAIL]" in line:
                failure = self.parse_failure_line(line, module_name)
                if failure and failure not in self.failed_cases.get("other_modules", []):
                    self.failed_cases.setdefault("other_modules", []).append(failure)
                    new_failures.append(failure)

        if new_failures:
            self.save_failed_cases()
            self.app._console_write(f"[INFO] Captured {len(new_failures)} new failure(s)\n")

        return new_failures

    def get_failed_length_attack_cases(self):
        """Get all length attack failed cases"""
        return self.failed_cases.get("length_attack", [])

    def get_failed_other_cases(self):
        """Get all other module failed cases"""
        return self.failed_cases.get("other_modules", [])

    def get_all_failed_cases(self):
        """Get all failed cases"""
        all_cases = self.failed_cases.get("length_attack", []) + self.failed_cases.get("other_modules", [])
        return all_cases

    def clear_failed_cases(self, module_type=None):
        """Clear failed cases for specific module or all"""
        if module_type == "length_attack":
            self.failed_cases["length_attack"] = []
        elif module_type == "other_modules":
            self.failed_cases["other_modules"] = []
        else:
            self.failed_cases = {"length_attack": [], "other_modules": []}

        self.save_failed_cases()

    def generate_retry_command(self, failure_case):
        """Generate retry command for a failed case"""
        module = failure_case.get("module", "")

        if module == "LengthAttack":
            arb_id = failure_case.get("arbitration_id", "")
            if arb_id:
                # For length attack, we need to create a command that targets the specific ID
                # We'll use the basic length attack command with the failed ID
                cmd = ["lenattack", arb_id, "-i", "vcan0"]

                # Add optional parameters based on what we know
                dlc = failure_case.get("dlc", "")
                if dlc and dlc.isdigit():
                    cmd.extend(["--min-dlc", dlc, "--max-dlc", dlc])

                return " ".join(cmd)

        # For other modules, return the raw line or a generic retry
        return failure_case.get("raw_line", f"python -m fucyfuzz.fucyfuzz {module}")

    def retry_failed_case(self, failure_case):
        """Retry a specific failed case"""
        module = failure_case.get("module", "")

        if module == "LengthAttack":
            arb_id = failure_case.get("arbitration_id", "")
            if arb_id:
                # Run length attack for this specific ID
                self.app.run_command(["lenattack", arb_id, "-i", "vcan0"], "LengthAttack_Retry")
                return True

        # For other modules, we can't easily retry without more context
        self.app._console_write(f"[INFO] Manual retry required for {module} failure\n")
        self.app._console_write(f"[INFO] Original failure: {failure_case.get('raw_line', 'Unknown')}\n")
        return False

    def retry_all_failed_length_attack(self):
        """Retry all length attack failed cases"""
        failed_cases = self.get_failed_length_attack_cases()
        if not failed_cases:
            messagebox.showinfo("No Failures", "No length attack failures to retry.")
            return

        # Group by arbitration ID to avoid duplicates
        unique_ids = set()
        for case in failed_cases:
            arb_id = case.get("arbitration_id", "")
            if arb_id and arb_id not in unique_ids:
                unique_ids.add(arb_id)

        if not unique_ids:
            messagebox.showwarning("Warning", "No valid arbitration IDs found in failures.")
            return

        # Ask for confirmation
        confirm = messagebox.askyesno(
            "Confirm Retry",
            f"Found {len(failed_cases)} failures with {len(unique_ids)} unique IDs.\n"
            f"Do you want to retry all unique failed cases?"
        )

        if confirm:
            self.app._console_write(f"\n[INFO] Retrying {len(unique_ids)} unique length attack failures\n")
            for arb_id in unique_ids:
                self.app._console_write(f"[RETRY] Running length attack for ID: {arb_id}\n")
                self.app.run_command(["lenattack", arb_id, "-i", "vcan0"], "LengthAttack_Bulk_Retry")
                time.sleep(1)  # Small delay between retries

    def export_failed_cases_csv(self, filename=None):
        """Export failed cases to CSV format"""
        all_cases = self.get_all_failed_cases()

        if not all_cases:
            messagebox.showinfo("No Failures", "No failed cases to export.")
            return None

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.failed_cases_dir, f"failed_cases_export_{timestamp}.csv")

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'module', 'arbitration_id', 'dlc', 'data_length',
                            'data', 'error_type', 'retry_command']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for case in all_cases:
                    retry_cmd = self.generate_retry_command(case)
                    writer.writerow({
                        'timestamp': case.get('timestamp', ''),
                        'module': case.get('module', ''),
                        'arbitration_id': case.get('arbitration_id', ''),
                        'dlc': case.get('dlc', ''),
                        'data_length': case.get('data_length', ''),
                        'data': case.get('data', ''),
                        'error_type': case.get('error_type', ''),
                        'retry_command': retry_cmd
                    })

            messagebox.showinfo(
                "CSV Export Complete",
                f"Exported {len(all_cases)} failed cases to:\n{filename}"
            )
            return filename

        except Exception as e:
            messagebox.showerror("CSV Export Error", f"Failed to export CSV: {str(e)}")
            return None

    def show_failed_cases_summary(self):
        """Show a summary of captured failed cases"""
        length_attack_failures = self.get_failed_length_attack_cases()
        other_failures = self.get_failed_other_cases()

        total_failures = len(length_attack_failures) + len(other_failures)

        if total_failures == 0:
            messagebox.showinfo("Failure Summary", "✅ No failed cases captured yet.")
            return

        # Create summary dialog
        summary_dialog = ctk.CTkToplevel(self.app)
        summary_dialog.title("Captured Failure Cases Summary")
        summary_dialog.geometry("600x500")
        summary_dialog.attributes("-topmost", True)

        # Summary header
        header = ctk.CTkFrame(summary_dialog, fg_color="#c0392b")
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(header, text="📊 CAPTURED FAILURE CASES", font=("Arial", 18, "bold"),
                    text_color="white").pack(pady=10)

        # Summary content
        content_frame = ctk.CTkFrame(summary_dialog)
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Statistics
        stats_text = f"""
        Total Captured Failures: {total_failures}

        Length Attack Failures: {len(length_attack_failures)}
        Other Module Failures: {len(other_failures)}

        Unique IDs in Length Attack: {len(set(case.get('arbitration_id', '') for case in length_attack_failures))}

        Last Capture: {max(case.get('timestamp', '') for case in length_attack_failures + other_failures) if total_failures > 0 else 'N/A'}
        """

        stats_label = ctk.CTkLabel(content_frame, text=stats_text, font=("Arial", 12),
                                 justify="left")
        stats_label.pack(pady=20, padx=20)

        # Action buttons
        btn_frame = ctk.CTkFrame(content_frame)
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="🔄 Retry All Length Attack", fg_color="#27ae60",
                     command=lambda: [summary_dialog.destroy(), self.retry_all_failed_length_attack()]).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="📥 Export CSV", fg_color="#2980b9",
                     command=lambda: [summary_dialog.destroy(), self.export_failed_cases_csv()]).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="🗑 Clear All", fg_color="#e74c3c",
                     command=lambda: [self.clear_failed_cases(),
                                     summary_dialog.destroy(),
                                     messagebox.showinfo("Cleared", "All captured failures cleared.")]).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Close",
                     command=summary_dialog.destroy).pack(side="left", padx=5)


# ==============================================================================
#  FAILURE REPORT GENERATOR
# ==============================================================================

class FailureReport:
    """Specialized failure report generator for failed test cases"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.failures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failure_reports")
        self.ensure_directory()

    def ensure_directory(self):
        """Create failure reports directory if it doesn't exist"""
        if not os.path.exists(self.failures_dir):
            os.makedirs(self.failures_dir)

    def get_failure_entries(self, entries=None):
        """Filter and return only failed entries from session history"""
        if entries is None:
            entries = self.app.session_history

        failed_entries = []
        for entry in entries:
            status_lower = entry['status'].lower()
            if ('error' in status_lower or
                'failed' in status_lower or
                status_lower != 'success' and 'running' not in status_lower):
                failed_entries.append(entry)

        return failed_entries

    def generate_failure_report(self, filename=None, title="Failure Analysis Report"):
        """Generate comprehensive failure report"""
        failed_entries = self.get_failure_entries()

        if not failed_entries:
            messagebox.showinfo("No Failures", "No failed test cases found in current session.")
            return None

        # Use default filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.failures_dir, f"failure_report_{timestamp}.pdf")

        # Group failures by module and error type
        modules = defaultdict(list)
        error_types = defaultdict(list)
        failure_categories = {
            'timeout': [],
            'connection': [],
            'permission': [],
            'validation': [],
            'unexpected': []
        }

        for entry in failed_entries:
            modules[entry['module']].append(entry)

            # Categorize by error type
            output_lower = entry['output'].lower()
            if 'timeout' in output_lower:
                error_types['Timeout'].append(entry)
                failure_categories['timeout'].append(entry)
            elif 'connection' in output_lower or 'connect' in output_lower:
                error_types['Connection'].append(entry)
                failure_categories['connection'].append(entry)
            elif 'permission' in output_lower or 'access denied' in output_lower:
                error_types['Permission'].append(entry)
                failure_categories['permission'].append(entry)
            elif 'invalid' in output_lower or 'validation' in output_lower:
                error_types['Validation'].append(entry)
                failure_categories['validation'].append(entry)
            else:
                error_types['Unexpected'].append(entry)
                failure_categories['unexpected'].append(entry)

        # Check if ReportLab is available for PDF generation
        if REPORTLAB_AVAILABLE and self.app.pdf_generator.REPORTLAB_AVAILABLE:
            return self._generate_failure_pdf(filename, title, failed_entries, modules, error_types, failure_categories)
        else:
            return self._generate_failure_text(filename, title, failed_entries, modules, error_types, failure_categories)

    def _generate_failure_pdf(self, filename, title, failed_entries, modules, error_types, failure_categories):
        """Generate PDF failure report using ReportLab"""
        try:
            # Use the existing PDF generator but with custom content
            story = []

            # Title Page
            story.append(Spacer(1, 2 * inch))
            story.append(Paragraph("FAILURE ANALYSIS REPORT", ParagraphStyle(
                'FailureTitle',
                parent=reportlab_styles['Title'],
                fontSize=36,
                alignment=1,
                spaceAfter=20,
                textColor=colors.HexColor("#c0392b"),
                fontName='Helvetica-Bold'
            )))
            story.append(Paragraph(f"<i>{title}</i>", ParagraphStyle(
                'FailureSubtitle',
                parent=reportlab_styles['Heading2'],
                alignment=1,
                textColor=colors.HexColor("#7f8c8d"),
                spaceAfter=40,
                fontName='Helvetica-Oblique'
            )))

            # Critical Information Box
            critical_info = [
                f"⚠️  CRITICAL: {len(failed_entries)} FAILURES DETECTED",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Total Tests in Session: {len(self.app.session_history)}",
                f"Failure Rate: {(len(failed_entries)/len(self.app.session_history)*100):.1f}%"
            ]

            critical_box = Table([[Paragraph(info, ParagraphStyle(
                'CriticalText',
                parent=reportlab_styles['Normal'],
                fontSize=12,
                textColor=colors.white,
                fontName='Helvetica-Bold'
            )) for info in critical_info]], colWidths=[500])
            critical_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#c0392b")),
                ('BOX', (0, 0), (-1, 0), 2, colors.white),
                ('PADDING', (0, 0), (-1, 0), 15),
            ]))
            story.append(critical_box)
            story.append(PageBreak())

            # Executive Summary
            story.append(Paragraph("EXECUTIVE SUMMARY", reportlab_styles['Heading1']))
            story.append(Spacer(1, 0.2 * inch))

            # Summary Statistics
            stats_data = [
                ["Metric", "Count", "Percentage"],
                ["Total Failures", str(len(failed_entries)), "100%"],
                ["Timeout Errors", str(len(error_types.get('Timeout', []))),
                 f"{(len(error_types.get('Timeout', []))/len(failed_entries)*100):.1f}%"],
                ["Connection Errors", str(len(error_types.get('Connection', []))),
                 f"{(len(error_types.get('Connection', []))/len(failed_entries)*100):.1f}%"],
                ["Permission Errors", str(len(error_types.get('Permission', []))),
                 f"{(len(error_types.get('Permission', []))/len(failed_entries)*100):.1f}%"],
                ["Validation Errors", str(len(error_types.get('Validation', []))),
                 f"{(len(error_types.get('Validation', []))/len(failed_entries)*100):.1f}%"],
                ["Unexpected Errors", str(len(error_types.get('Unexpected', []))),
                 f"{(len(error_types.get('Unexpected', []))/len(failed_entries)*100):.1f}%"]
            ]

            t1 = Table(stats_data, colWidths=[200, 100, 100])
            t1.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#e74c3c")),
                ('TEXTCOLOR', (0, 1), (0, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ]))
            story.append(t1)
            story.append(Spacer(1, 0.5 * inch))

            # Module-wise Failure Distribution
            story.append(Paragraph("FAILURE DISTRIBUTION BY MODULE", reportlab_styles['Heading2']))
            story.append(Spacer(1, 0.2 * inch))

            module_data = [["Module", "Failures", "Percentage", "Most Common Error"]]
            for module_name, module_failures in modules.items():
                percentage = (len(module_failures) / len(failed_entries) * 100)
                # Determine most common error type for this module
                error_counts = defaultdict(int)
                for failure in module_failures:
                    error_type = self._categorize_error(failure['output'])
                    error_counts[error_type] += 1
                most_common = max(error_counts.items(), key=lambda x: x[1])[0] if error_counts else "Unknown"
                module_data.append([module_name, str(len(module_failures)), f"{percentage:.1f}%", most_common])

            t2 = Table(module_data, colWidths=[150, 80, 80, 190])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e74c3c")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ]))
            story.append(t2)
            story.append(PageBreak())

            # Detailed Failure Analysis
            story.append(Paragraph("DETAILED FAILURE ANALYSIS", reportlab_styles['Heading1']))
            story.append(Spacer(1, 0.3 * inch))

            for module_idx, (module_name, module_failures) in enumerate(modules.items()):
                story.append(Paragraph(f"Module: {module_name}", ParagraphStyle(
                    'ModuleHeader',
                    parent=reportlab_styles['Heading2'],
                    fontSize=18,
                    textColor=colors.HexColor("#c0392b"),
                    spaceBefore=20,
                    spaceAfter=10,
                    fontName='Helvetica-Bold'
                )))

                for failure_idx, failure in enumerate(module_failures):
                    # Failure Card
                    story.append(Paragraph(f"Failure {failure_idx + 1}", ParagraphStyle(
                        'FailureHeader',
                        parent=reportlab_styles['Heading3'],
                        fontSize=14,
                        textColor=colors.HexColor("#2c3e50"),
                        spaceBefore=10,
                        spaceAfter=5,
                        fontName='Helvetica-Bold'
                    )))

                    # Failure Details Table
                    error_type = self._categorize_error(failure['output'])
                    details_data = [
                        ["Timestamp:", failure['timestamp']],
                        ["Error Type:", f"<font color='#c0392b'><b>{error_type}</b></font>"],
                        ["Command:", f"<font face='Courier'>{failure['command'][:80]}...</font>"],
                        ["Status:", f"<font color='#c0392b'><b>{failure['status']}</b></font>"]
                    ]

                    details_table = Table(details_data, colWidths=[100, 400])
                    details_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f2d7d5")),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e74c3c")),
                        ('PADDING', (0, 0), (-1, -1), 5),
                    ]))
                    story.append(details_table)

                    # Error Output (truncated)
                    story.append(Paragraph("<b>Error Output:</b>", reportlab_styles['Heading4']))
                    error_output = failure['output'][:1000]  # Limit output
                    if len(failure['output']) > 1000:
                        error_output += "\n\n[TRUNCATED - See full logs for complete error details]"

                    story.append(Preformatted(error_output, ParagraphStyle(
                        'ErrorCode',
                        parent=reportlab_styles['Code'],
                        fontSize=9,
                        leading=10,
                        backColor=colors.HexColor("#fdedec"),
                        borderColor=colors.HexColor("#e74c3c"),
                        borderWidth=1,
                        borderPadding=8,
                        fontName='Courier'
                    )))

                    # Suggested Fixes
                    suggested_fixes = self._get_suggested_fixes(error_type, failure)
                    if suggested_fixes:
                        story.append(Paragraph("<b>Suggested Fixes:</b>", reportlab_styles['Heading4']))
                        fixes_list = ListFlowable(
                            [ListItem(Paragraph(fix, ParagraphStyle(
                                'FixText',
                                parent=reportlab_styles['Normal'],
                                fontSize=10,
                                leading=12
                            ))) for fix in suggested_fixes],
                            bulletType='bullet',
                            leftIndent=20
                        )
                        story.append(fixes_list)

                    story.append(Spacer(1, 0.3 * inch))

                if module_idx < len(modules) - 1:
                    story.append(PageBreak())

            # Recommendations Page
            story.append(PageBreak())
            story.append(Paragraph("RECOMMENDATIONS & NEXT STEPS", reportlab_styles['Heading1']))
            story.append(Spacer(1, 0.3 * inch))

            recommendations = [
                "1. Review the most frequent error types and address systematic issues",
                "2. Check network connectivity and target system availability",
                "3. Verify configuration settings and permissions",
                "4. Update to latest version of testing tools",
                "5. Review security policies and firewall rules",
                "6. Consider implementing retry mechanisms for transient failures",
                "7. Schedule follow-up tests for resolved issues",
                "8. Document root cause analysis for each failure category"
            ]

            for rec in recommendations:
                story.append(Paragraph(rec, ParagraphStyle(
                    'RecText',
                    parent=reportlab_styles['Normal'],
                    fontSize=12,
                    leading=14,
                    spaceAfter=8
                )))

            # Generate the PDF
            doc = TOCDocTemplate(
                filename,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            doc.multiBuild(story)

            # Show success message
            abs_path = os.path.abspath(filename)
            messagebox.showinfo(
                "Failure Report Generated",
                f"✓ Failure Analysis Report Created!\n\n"
                f"Failures Analyzed: {len(failed_entries)}\n"
                f"File: {os.path.basename(filename)}\n"
                f"Location: {os.path.dirname(abs_path)}\n\n"
                f"Report includes:\n"
                f"• Executive summary\n"
                f"• Error categorization\n"
                f"• Module-wise analysis\n"
                f"• Suggested fixes\n"
                f"• Recommendations"
            )

            # Open the PDF if on Windows
            if os.name == 'nt':
                os.startfile(abs_path)

            return filename

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Failure PDF Generation Error:\n{error_details}")
            messagebox.showerror(
                "Failure Report Error",
                f"Failed to generate failure report:\n\n{str(e)}\n\n"
                f"Generating text report instead..."
            )
            # Fallback to text report
            return self._generate_failure_text(
                filename.replace(".pdf", ".txt"),
                title,
                failed_entries,
                modules,
                error_types,
                failure_categories
            )

    def _generate_failure_text(self, filename, title, failed_entries, modules, error_types, failure_categories):
        """Generate text-based failure report"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("FAILURE ANALYSIS REPORT\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"Report Title: {title}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Tests in Session: {len(self.app.session_history)}\n")
                f.write(f"Total Failures: {len(failed_entries)}\n")
                f.write(f"Failure Rate: {(len(failed_entries)/len(self.app.session_history)*100):.1f}%\n")
                f.write("\n" + "=" * 80 + "\n\n")

                # Error Type Summary
                f.write("ERROR TYPE SUMMARY:\n")
                f.write("-" * 40 + "\n")
                for error_type, entries in error_types.items():
                    if entries:
                        percentage = (len(entries) / len(failed_entries) * 100)
                        f.write(f"{error_type}: {len(entries)} failures ({percentage:.1f}%)\n")
                f.write("\n")

                # Module-wise Summary
                f.write("MODULE-WISE FAILURE DISTRIBUTION:\n")
                f.write("-" * 40 + "\n")
                for module_name, module_failures in modules.items():
                    percentage = (len(module_failures) / len(failed_entries) * 100)
                    f.write(f"{module_name}: {len(module_failures)} failures ({percentage:.1f}%)\n")
                f.write("\n")

                # Detailed Failures
                f.write("DETAILED FAILURE ANALYSIS:\n")
                f.write("=" * 80 + "\n\n")

                for module_name, module_failures in modules.items():
                    f.write(f"MODULE: {module_name}\n")
                    f.write("-" * 40 + "\n\n")

                    for idx, failure in enumerate(module_failures):
                        f.write(f"Failure {idx + 1}:\n")
                        f.write(f"  Timestamp: {failure['timestamp']}\n")
                        f.write(f"  Status: {failure['status']}\n")
                        f.write(f"  Command: {failure['command']}\n")
                        error_type = self._categorize_error(failure['output'])
                        f.write(f"  Error Type: {error_type}\n")
                        f.write(f"  Error Output:\n{'='*30}\n")
                        f.write(failure['output'][:1500])
                        f.write(f"\n{'='*30}\n\n")

                        # Suggested fixes
                        fixes = self._get_suggested_fixes(error_type, failure)
                        if fixes:
                            f.write("  Suggested Fixes:\n")
                            for fix in fixes:
                                f.write(f"    • {fix}\n")
                            f.write("\n")

                # Recommendations
                f.write("\n" + "=" * 80 + "\n")
                f.write("RECOMMENDATIONS:\n")
                f.write("-" * 40 + "\n")
                recommendations = [
                    "1. Review most frequent error types",
                    "2. Check network connectivity",
                    "3. Verify configuration settings",
                    "4. Update testing tools",
                    "5. Review security policies",
                    "6. Implement retry mechanisms",
                    "7. Schedule follow-up tests",
                    "8. Document root cause analysis"
                ]
                for rec in recommendations:
                    f.write(f"{rec}\n")
                f.write("=" * 80 + "\n")

            messagebox.showinfo(
                "Failure Report Generated",
                f"Text failure report saved:\n{filename}"
            )
            return filename

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save failure report: {str(e)}")
            return None

    def _categorize_error(self, error_output):
        """Categorize error based on output content"""
        output_lower = error_output.lower()

        if 'timeout' in output_lower:
            return "Timeout Error"
        elif 'connection' in output_lower or 'connect' in output_lower:
            return "Connection Error"
        elif 'permission' in output_lower or 'access denied' in output_lower:
            return "Permission Error"
        elif 'invalid' in output_lower:
            return "Validation Error"
        elif 'no such file' in output_lower or 'file not found' in output_lower:
            return "File Not Found"
        elif 'syntax' in output_lower:
            return "Syntax Error"
        elif 'memory' in output_lower:
            return "Memory Error"
        elif 'segmentation fault' in output_lower:
            return "Segmentation Fault"
        else:
            return "Unexpected Error"

    def _get_suggested_fixes(self, error_type, failure):
        """Get suggested fixes based on error type"""
        fixes = {
            "Timeout Error": [
                "Increase timeout duration in configuration",
                "Check target system responsiveness",
                "Verify network connectivity",
                "Reduce packet size or frequency"
            ],
            "Connection Error": [
                "Verify target IP/port configuration",
                "Check firewall settings",
                "Ensure target service is running",
                "Test with basic connectivity tools (ping, telnet)"
            ],
            "Permission Error": [
                "Run with elevated privileges if required",
                "Check file/folder permissions",
                "Verify user account has necessary rights",
                "Review security policies"
            ],
            "Validation Error": [
                "Review input parameters for validity",
                "Check data format and constraints",
                "Verify command syntax",
                "Test with known valid inputs first"
            ],
            "File Not Found": [
                "Verify file paths are correct",
                "Check file exists and is accessible",
                "Ensure file extensions are correct",
                "Test with absolute paths"
            ],
            "Syntax Error": [
                "Review command syntax",
                "Check for typos or missing parameters",
                "Consult module documentation",
                "Test with simplified command first"
            ]
        }

        base_fixes = [
            "Review full error log for additional details",
            "Check system resources (memory, CPU, disk)",
            "Verify all dependencies are installed",
            "Test in isolated environment to rule out conflicts"
        ]

        return fixes.get(error_type, []) + base_fixes

    def export_failures_csv(self, filename=None):
        """Export failures to CSV format for external analysis"""
        failed_entries = self.get_failure_entries()

        if not failed_entries:
            messagebox.showinfo("No Failures", "No failed test cases to export.")
            return None

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.failures_dir, f"failures_export_{timestamp}.csv")

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'module', 'status', 'command', 'error_type', 'error_summary']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for entry in failed_entries:
                    error_type = self._categorize_error(entry['output'])
                    error_summary = entry['output'][:500].replace('\n', ' ').replace(',', ';')

                    writer.writerow({
                        'timestamp': entry['timestamp'],
                        'module': entry['module'],
                        'status': entry['status'],
                        'command': entry['command'][:200],
                        'error_type': error_type,
                        'error_summary': error_summary
                    })

            messagebox.showinfo(
                "CSV Export Complete",
                f"Exported {len(failed_entries)} failures to:\n{filename}"
            )
            return filename

        except Exception as e:
            messagebox.showerror("CSV Export Error", f"Failed to export CSV: {str(e)}")
            return None

    def clear_failure_history(self):
        """Clear all recorded failures from session history"""
        # Filter out failed entries, keep only successful/running ones
        self.app.session_history = [
            entry for entry in self.app.session_history
            if 'success' in entry['status'].lower() or 'running' in entry['status'].lower()
        ]
        messagebox.showinfo("Cleared", "Failure history cleared from session.")


# ==============================================================================
#   MAIN APP (UPDATED WITH ENHANCED REPORTING AND FAILURE REPORTS)
# ==============================================================================

class FucyfuzzApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FUCYFUZZ INTERFACE")
        self.geometry("1400x1100")
        self.minsize(1000, 700)

        # Base dimensions for scaling calculations
        self.base_width = 1400
        self.base_height = 950

        # Data Management - INITIALIZE THESE FIRST
        self.current_process = None
        self.session_history = []
        self.full_log_buffer = []
        self.pending_console_messages = []  # Store messages until console is ready

        # GLOBAL DBC STORE
        self.dbc_db = None
        self.dbc_messages = {}

        # Initialize PDF Report Generator
        self.pdf_generator = EnhancedPDFReport(self)

        # Initialize Failure Report Generator
        self.failure_report = FailureReport(self)

        # NEW: Initialize Failure Capture System
        self.failure_capture = FailureCaptureSystem(self)

        # --- INITIALIZE WORKING DIRECTORY ---
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_script_dir)
        default_path = os.path.join(parent_dir, "fucyfuzz_tool")

        if os.path.exists(default_path):
            self.working_dir = default_path
            self.pending_console_messages.append(f"[INFO] Auto-detected working directory: {self.working_dir}\n")
        else:
            possible_paths = [
                default_path,
                os.path.join(current_script_dir, "fucyfuzz_tool"),
                os.path.join(parent_dir, "..", "fucyfuzz_tool"),
                os.path.join(os.getcwd(), "fucyfuzz_tool"),
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    self.working_dir = path
                    self.pending_console_messages.append(f"[INFO] Found working directory: {self.working_dir}\n")
                    break
            else:
                self.working_dir = os.getcwd()
                self.pending_console_messages.append(f"[WARNING] Using current directory as fallback: {self.working_dir}\n")
                self.pending_console_messages.append("[WARNING] Some features may not work correctly.\n")

        # Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ===========================
        # 1) TABVIEW WITH SCALING
        # ===========================
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        tab_names = [
            "Configuration", "Recon","Demo", "Fuzzer", "Length Attack",
            "DCM","UDS", "Advanced", "Send", "Monitor"
        ]
        for name in tab_names:
            self.tabs.add(name)

        # ===========================
        # 2) TAB FRAMES
        # ===========================
        self.frames = {}
        self.frames["config"] = ConfigFrame(self.tabs.tab("Configuration"), self)
        self.frames["recon"] = ReconFrame(self.tabs.tab("Recon"), self)
        self.frames["demo"] = DemoFrame(self.tabs.tab("Demo"), self)
        self.frames["fuzzer"] = FuzzerFrame(self.tabs.tab("Fuzzer"), self)
        self.frames["lenattack"] = LengthAttackFrame(self.tabs.tab("Length Attack"), self)
        self.frames["dcm"] = DCMFrame(self.tabs.tab("DCM"), self)
        self.frames["uds"] = UDSFrame(self.tabs.tab("UDS"), self)
        self.frames["advanced"] = AdvancedFrame(self.tabs.tab("Advanced"), self)
        self.frames["send"] = SendFrame(self.tabs.tab("Send"), self)
        self.frames["monitor"] = MonitorFrame(self.tabs.tab("Monitor"), self)

        for frm in self.frames.values():
            frm.pack(fill="both", expand=True, padx=15, pady=15)

        # ===========================
        # 3) CONSOLE
        # ===========================
        self.console_frame = ctk.CTkFrame(self, height=250, fg_color="#111")
        self.console_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        header = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=5)

        self.console_label = ctk.CTkLabel(header, text="SYSTEM OUTPUT", font=("Arial", 12, "bold"))
        self.console_label.pack(side="left", padx=5)

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        # Global Buttons - UPDATED WITH FAILURE REPORT AND CAPTURE BUTTONS
        self.btn_dbc = ctk.CTkButton(btn_frame, text="📂 Import DBC (Global)", width=140, fg_color="#8e44ad",
                      command=self.load_global_dbc)
        self.btn_dbc.pack(side="left", padx=5)

        self.btn_pdf = ctk.CTkButton(btn_frame, text="📄 Overall PDF Report", width=140, fg_color="#2980b9",
                      command=self.save_overall_report)
        self.btn_pdf.pack(side="left", padx=5)

        # NEW: Failure Capture Button
        self.btn_capture = ctk.CTkButton(btn_frame, text="🔴 Capture Failures", width=140, fg_color="#e74c3c",
                      command=self.capture_failures)
        self.btn_capture.pack(side="left", padx=5)

        self.btn_failure = ctk.CTkButton(btn_frame, text="📊 Failure Report", width=140, fg_color="#c0392b",
                      command=self.save_failure_report)
        self.btn_failure.pack(side="left", padx=5)

        self.btn_log = ctk.CTkButton(btn_frame, text="📜 Save Logs", width=100, fg_color="#7f8c8d",
                      command=self.save_full_logs)
        self.btn_log.pack(side="left", padx=5)

        self.btn_stop = ctk.CTkButton(btn_frame, text="⛔ STOP", fg_color="#c0392b", width=100,
                      command=self.stop_process)
        self.btn_stop.pack(side="left", padx=5)

        self.console = ctk.CTkTextbox(self.console_frame, font=("Consolas", 12), text_color="#00ff00", fg_color="#000")
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

        # NEW: Flush pending console messages now that console is ready
        self._flush_pending_console_messages()

        # Bind main window resize to update all frames
        self.bind("<Configure>", self._on_main_resize)
        self._last_resize_time = 0

    def _flush_pending_console_messages(self):
        """Write any pending console messages that were stored before console was ready"""
        if hasattr(self, 'pending_console_messages') and self.pending_console_messages:
            for message in self.pending_console_messages:
                self.full_log_buffer.append(message)
                self.console.insert("end", message)
            self.console.see("end")
            # Clear the pending messages
            self.pending_console_messages.clear()

    def _on_main_resize(self, event=None):
        # Throttle resize events to prevent excessive updates
        current_time = time.time()
        if current_time - self._last_resize_time > 0.1:  # 100ms throttle
            self._last_resize_time = current_time

            # Check if window still exists
            if not self.winfo_exists():
                return

            try:
                # 1. Update Global Tab Scaling
                self._update_app_scaling()

                # 2. Update all frames
                for frame in self.frames.values():
                    if hasattr(frame, 'update_scaling') and frame.winfo_exists():
                        frame.update_scaling()
            except Exception as e:
                # Ignore resize errors during window destruction
                if "invalid command name" not in str(e) and "has been destroyed" not in str(e):
                    print(f"Resize error: {e}")

    def _update_app_scaling(self):
        """Scales the TabView text based on window size"""
        try:
            # Check if window is being destroyed
            if not self.winfo_exists():
                return

            current_width = self.winfo_width()
            current_height = self.winfo_height()

            if current_width < 100 or current_height < 100:
                return

            scale_factor = min(current_width / self.base_width, current_height / self.base_height)

            # Calculate Tab Font Size
            tab_font_size = max(11, min(18, int(14 * scale_factor)))
            font_cfg = ("Arial", tab_font_size, "bold")

            # Apply to Tabview Segmented Button (The tabs themselves)
            if hasattr(self.tabs, '_segmented_button') and self.tabs._segmented_button.winfo_exists():
                self.tabs._segmented_button.configure(font=font_cfg)

            # Scale Console Header
            console_font = max(10, min(16, int(12 * scale_factor)))
            if self.console_label.winfo_exists():
                self.console_label.configure(font=("Arial", console_font, "bold"))

        except Exception as e:
            if "invalid command name" in str(e) or "has been destroyed" in str(e):
                pass
            else:
                print(f"Scaling error: {e}")

    def safe_destroy(self):
        """Safely destroy the application without cleanup errors"""
        try:
            # Stop any running processes first
            if self.current_process:
                self.stop_process()

            # Unbind events to prevent callbacks during destruction
            self.unbind("<Configure>")

            # Destroy the application
            self.destroy()
        except Exception as e:
            # Force exit if there are any destruction errors
            import os
            os._exit(0)

    # =======================================
    # GLOBAL DBC LOGIC
    # =======================================
    def load_global_dbc(self):
        if not cantools:
            messagebox.showerror("Error", "Python 'cantools' library missing.\nRun: pip install cantools")
            return

        fp = filedialog.askopenfilename(filetypes=[("DBC files", "*.dbc"), ("All", "*.*")])
        if not fp: return

        try:
            self.dbc_db = cantools.database.load_file(fp)
            self.dbc_messages = {msg.name: msg.frame_id for msg in self.dbc_db.messages}

            msg_count = len(self.dbc_messages)
            self._console_write(f"[INFO] Loaded DBC: {os.path.basename(fp)} ({msg_count} messages)\n")
            self.refresh_tab_dropdowns()

        except Exception as e:
            self._console_write(f"[ERROR] Failed to load DBC: {e}\n")

    def refresh_tab_dropdowns(self):
        msg_names = sorted(list(self.dbc_messages.keys()))
        if not msg_names: return

        for tab_name in ["fuzzer", "lenattack", "send", "uds","dcm"]:
            if hasattr(self.frames[tab_name], "update_msg_list"):
                self.frames[tab_name].update_msg_list(msg_names)

    def get_id_by_name(self, name):
        if name in self.dbc_messages:
            return hex(self.dbc_messages[name])
        return ""

    # =======================================
    # HELP MODAL LOGIC
    # =======================================
    def show_module_help(self, module_names):
        if isinstance(module_names, str):
            module_names = [module_names]

        full_output = ""

        for mod in module_names:
            full_output += f"=== HELP: {mod.upper()} ===\n"

            cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz", mod, "--help"]
            full_output += f"Command: {' '.join(cmd)}\n\n"

            try:
                env = os.environ.copy()
                env["PYTHONPATH"] = self.working_dir + os.pathsep + env.get("PYTHONPATH", "")

                output = subprocess.check_output(
                    cmd,
                    env=env,
                    stderr=subprocess.STDOUT,
                    cwd=self.working_dir,
                    text=True,
                    timeout=10
                )
                full_output += output

            except subprocess.CalledProcessError as e:
                full_output += f"Process returned error but here's the output:\n{e.output}"
            except subprocess.TimeoutExpired:
                full_output += f"Timeout: Help command took too long to execute\n"
            except FileNotFoundError:
                full_output += f"Error: Cannot find Python or fucyfuzz module\n"
            except Exception as e:
                full_output += f"Execution error: {str(e)}\n"

            full_output += "\n" + "-"*60 + "\n\n"

        # Create Modal Window
        top = ctk.CTkToplevel(self)
        top.title("Module Help")
        top.geometry("900x700")
        top.attributes("-topmost", True)
        top.focus_set()
        top.grab_set()

        ctk.CTkLabel(top, text="Module Documentation", font=("Arial", 20, "bold")).pack(pady=10)

        textbox = ctk.CTkTextbox(top, font=("Consolas", 12))
        textbox.pack(fill="both", expand=True, padx=15, pady=10)
        textbox.insert("0.0", full_output)
        textbox.configure(state="disabled")

        ctk.CTkButton(top, text="Close", command=top.destroy, fg_color="#c0392b").pack(pady=10)


    # =======================================
    # PROCESS EXECUTION
    # =======================================
    def run_command(self, args_list, module_name="General"):
        if self.current_process:
            messagebox.showwarning("Busy", "Process running. Stop first.")
            return

        working_dir = self.working_dir

        print(f"DEBUG: Working directory: {working_dir}")
        print(f"DEBUG: Args list: {args_list}")

        cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + [str(a) for a in args_list]

        env = os.environ.copy()
        env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")

        self._console_write(f"\n>>> [{module_name}] START: {' '.join(cmd)}\n")
        self._console_write(f">>> CWD: {working_dir}\n")
        self._console_write(f">>> PYTHONPATH: {env['PYTHONPATH']}\n")

        current_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "module": module_name,
            "command": " ".join(cmd),
            "output": "", "status": "Running"
        }

        def target():
            out_buf = []
            try:
                module_check_cmd = [sys.executable, "-c", "import fucyfuzz.fucyfuzz; print('Module found')"]
                check_result = subprocess.run(
                    module_check_cmd,
                    cwd=working_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if check_result.returncode != 0:
                    self._console_write(f"ERROR: Cannot import fucyfuzz module from {working_dir}\n")
                    self._console_write(f"Error details: {check_result.stderr}\n")
                    return

                cflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=working_dir,
                    env=env,
                    creationflags=cflags,
                    universal_newlines=True
                )

                while True:
                    line = self.current_process.stdout.readline()
                    if not line and self.current_process.poll() is not None:
                        break
                    if line:
                        self._console_write(line)
                        out_buf.append(line)

                rc = self.current_process.poll()
                self._console_write(f"\n<<< FINISHED (Code: {rc})\n")

                current_entry["output"] = "".join(out_buf)
                current_entry["status"] = "Success" if rc == 0 else f"Failed ({rc})"
                self.session_history.append(current_entry)

                # NEW: Automatically capture failures from output
                if rc != 0 or "[FAIL]" in current_entry["output"]:
                    self._console_write("[INFO] Analyzing output for failure patterns...\n")
                    captured = self.failure_capture.capture_failure(current_entry["output"], module_name)
                    if captured:
                        self._console_write(f"[INFO] Captured {len(captured)} failure(s) from this run\n")

            except Exception as e:
                self._console_write(f"\nERROR: {e}\n")
                current_entry["output"] = "".join(out_buf) + f"\nError: {e}"
                current_entry["status"] = "Error"
                self.session_history.append(current_entry)
            finally:
                self.current_process = None

        threading.Thread(target=target, daemon=True).start()


    def stop_process(self):
        if self.current_process:
            try:
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.current_process.pid)])
                else:
                    os.kill(self.current_process.pid, signal.SIGTERM)
            except: pass
            self.current_process = None
            self._console_write("\n[Process Stopped by User]\n")

    def _console_write(self, text):
        self.full_log_buffer.append(text)
        if hasattr(self, 'console') and self.console.winfo_exists():
            self.console.after(0, lambda: (self.console.insert("end", text), self.console.see("end")))
        else:
            if not hasattr(self, 'pending_console_messages'):
                self.pending_console_messages = []
            self.pending_console_messages.append(text)

    # =======================================
    # ENHANCED REPORTING METHODS
    # =======================================
    def generate_pdf(self, filename, title, entries):
        """Use the enhanced PDF generator"""
        return self.pdf_generator.generate_pdf(filename, title, entries)

    def save_txt_report(self, filename, title, entries):
        """Use the enhanced text report generator"""
        return self.pdf_generator.save_txt_report(filename, title, entries)

    def save_overall_report(self):
        if not self.session_history:
            messagebox.showinfo("Info", "No history to report.")
            return

        # Use PDF generator if available, otherwise text
        if self.pdf_generator.REPORTLAB_AVAILABLE:
            ext = ".pdf"
            ftypes = [("PDF Document", "*.pdf")]
        else:
            ext = ".txt"
            ftypes = [("Text File", "*.txt")]

        fn = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=ftypes,
            initialfile=f"FucyFuzz_Overall_Report{ext}"
        )

        if fn:
            title = "FucyFuzz Overall Security Report"
            if ext == ".pdf":
                self.generate_pdf(fn, title, self.session_history)
            else:
                self.save_txt_report(fn, title, self.session_history)

    def save_module_report(self, mod):
        entries = [e for e in self.session_history if e['module'] == mod]
        if not entries:
            messagebox.showinfo("Info", f"No history for {mod}.")
            return

        if self.pdf_generator.REPORTLAB_AVAILABLE:
            ext = ".pdf"
            ftypes = [("PDF Document", "*.pdf")]
        else:
            ext = ".txt"
            ftypes = [("Text File", "*.txt")]

        fn = filedialog.asksaveasfilename(
            initialfile=f"{mod}_Report{ext}",
            defaultextension=ext,
            filetypes=ftypes
        )

        if fn:
            title = f"{mod} Module Report"
            if ext == ".pdf":
                self.generate_pdf(fn, title, entries)
            else:
                self.save_txt_report(fn, title, entries)

    def save_full_logs(self):
        fn = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log File", "*.log"), ("Text File", "*.txt")]
        )
        if fn:
            try:
                with open(fn, "w", encoding='utf-8') as f:
                    f.writelines(self.full_log_buffer)
                messagebox.showinfo("Success", f"Logs saved to:\n{fn}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {str(e)}")

    # =======================================
    # FAILURE CAPTURE AND RETRY METHODS
    # =======================================
    def capture_failures(self):
        """Manually capture failures from current console output"""
        current_output = self.console.get("1.0", "end-1c")

        # Ask which module to associate with
        module_dialog = ctk.CTkInputDialog(
            text="Enter module name for these failures (e.g., LengthAttack, Fuzzer):",
            title="Capture Failures"
        )
        module_name = module_dialog.get_input()

        if module_name:
            captured = self.failure_capture.capture_failure(current_output, module_name)
            if captured:
                messagebox.showinfo(
                    "Failures Captured",
                    f"Captured {len(captured)} new failure(s) for module: {module_name}"
                )
                # Show summary
                self.failure_capture.show_failed_cases_summary()
            else:
                messagebox.showinfo("No New Failures", "No new failure patterns found in current output.")

    def retry_failed_cases(self):
        """Show options for retrying failed cases"""
        # Create a dialog with retry options
        retry_dialog = ctk.CTkToplevel(self)
        retry_dialog.title("Retry Failed Cases")
        retry_dialog.geometry("500x300")
        retry_dialog.attributes("-topmost", True)

        header = ctk.CTkFrame(retry_dialog, fg_color="#27ae60")
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(header, text="🔄 RETRY FAILED CASES", font=("Arial", 18, "bold"),
                    text_color="white").pack(pady=10)

        # Content frame
        content = ctk.CTkFrame(retry_dialog)
        content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Statistics
        length_attack_failures = self.failure_capture.get_failed_length_attack_cases()
        other_failures = self.failure_capture.get_failed_other_cases()
        total = len(length_attack_failures) + len(other_failures)

        stats_text = f"""
        Total Captured Failures: {total}

        Length Attack Failures: {len(length_attack_failures)}
        Other Module Failures: {len(other_failures)}

        Select retry option:
        """

        ctk.CTkLabel(content, text=stats_text, font=("Arial", 12),
                   justify="left").pack(pady=20, padx=20)

        # Button frame
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="🔄 Retry All Length Attack", fg_color="#27ae60",
                     command=lambda: [retry_dialog.destroy(),
                                     self.failure_capture.retry_all_failed_length_attack()]).pack(pady=5, fill="x")

        ctk.CTkButton(btn_frame, text="📊 Show Summary", fg_color="#2980b9",
                     command=lambda: [retry_dialog.destroy(),
                                     self.failure_capture.show_failed_cases_summary()]).pack(pady=5, fill="x")

        ctk.CTkButton(btn_frame, text="📥 Export CSV", fg_color="#8e44ad",
                     command=lambda: [retry_dialog.destroy(),
                                     self.failure_capture.export_failed_cases_csv()]).pack(pady=5, fill="x")

        ctk.CTkButton(btn_frame, text="Close", fg_color="#7f8c8d",
                     command=retry_dialog.destroy).pack(pady=5, fill="x")

    def save_failure_report(self):
        """Generate and save failure analysis report"""
        if not self.session_history:
            messagebox.showinfo("Info", "No test history available.")
            return

        # Check if there are any failures
        failed_entries = self.failure_report.get_failure_entries()
        if not failed_entries:
            messagebox.showinfo("No Failures", "No failed test cases found in current session.")
            return

        # Ask user for report format
        format_dialog = ctk.CTkInputDialog(
            text="Select report format:\n1. PDF (Comprehensive)\n2. Text (Simple)\n3. CSV (Data export)\n\nEnter 1, 2, or 3:",
            title="Failure Report Format"
        )
        format_choice = format_dialog.get_input()

        if format_choice == "1":
            # PDF report
            if self.pdf_generator.REPORTLAB_AVAILABLE:
                fn = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF Document", "*.pdf")],
                    initialfile=f"Failure_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                )
                if fn:
                    self.failure_report.generate_failure_report(fn, "Failure Analysis Report")
            else:
                messagebox.showwarning("PDF Unavailable", "ReportLab not installed. Generating text report instead.")
                self._save_failure_text_report()

        elif format_choice == "2":
            # Text report
            self._save_failure_text_report()

        elif format_choice == "3":
            # CSV export
            self.failure_report.export_failures_csv()

        else:
            messagebox.showwarning("Cancelled", "Failure report generation cancelled.")

    def _save_failure_text_report(self):
        """Save failure report as text file"""
        fn = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            initialfile=f"Failure_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if fn:
            self.failure_report.generate_failure_report(fn, "Failure Analysis Report")

    def show_failure_summary(self):
        """Show a quick summary of failures in a dialog"""
        failed_entries = self.failure_report.get_failure_entries()

        if not failed_entries:
            messagebox.showinfo("Failure Summary", "✅ No failures detected in current session.")
            return

        # Create summary dialog
        summary_dialog = ctk.CTkToplevel(self)
        summary_dialog.title("Failure Summary")
        summary_dialog.geometry("600x400")
        summary_dialog.attributes("-topmost", True)

        # Summary header
        header = ctk.CTkFrame(summary_dialog, fg_color="#c0392b")
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(header, text="⚠️ FAILURE SUMMARY", font=("Arial", 18, "bold"),
                    text_color="white").pack(pady=10)

        # Summary content
        content_frame = ctk.CTkFrame(summary_dialog)
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Statistics
        stats_text = f"""
        Total Tests: {len(self.session_history)}
        Total Failures: {len(failed_entries)}
        Failure Rate: {(len(failed_entries)/len(self.session_history)*100):.1f}%

        Failed Modules:"""

        # Group by module
        modules = {}
        for entry in failed_entries:
            modules[entry['module']] = modules.get(entry['module'], 0) + 1

        for module, count in modules.items():
            stats_text += f"\n  • {module}: {count} failures"

        stats_label = ctk.CTkLabel(content_frame, text=stats_text, font=("Arial", 12),
                                 justify="left")
        stats_label.pack(pady=20, padx=20)

        # Action buttons
        btn_frame = ctk.CTkFrame(content_frame)
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Generate Full Report", fg_color="#c0392b",
                     command=lambda: [summary_dialog.destroy(), self.save_failure_report()]).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Export CSV", fg_color="#2980b9",
                     command=lambda: [summary_dialog.destroy(), self.failure_report.export_failures_csv()]).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Close",
                     command=summary_dialog.destroy).pack(side="left", padx=5)

    def clear_failure_history(self):
        """Clear failure history from session"""
        self.failure_report.clear_failure_history()


# ==============================================================================
#  BASE FRAME WITH SCALING AND TRANSITIONS
# ==============================================================================

class ScalableFrame(ctk.CTkFrame):
    """Base frame with responsive scaling capabilities and smooth transitions"""
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.base_width = 1400
        self.base_height = 800
        self._current_scale = 1.0
        self._transition_in_progress = False
        self._last_scale_update = 0

    def vw(self, percentage):
        """Convert percentage to width relative to base width (like CSS vw)"""
        return int((percentage / 100) * self.base_width)

    def vh(self, percentage):
        """Convert percentage to height relative to base height (like CSS vh)"""
        return int((percentage / 100) * self.base_height)

    def update_scaling(self):
        """Update scaling based on current frame size"""
        current_width = self.winfo_width()
        current_height = self.winfo_height()

        if current_width > 100 and current_height > 100:
            scale_factor = min(current_width / self.base_width, current_height / self.base_height)
            self._apply_scaling_with_transition(scale_factor)

    def _apply_scaling_with_transition(self, scale_factor):
        """Apply scaling with smooth transition effect"""
        current_time = time.time()
        if (self._transition_in_progress or
            abs(scale_factor - self._current_scale) < 0.05 or
            current_time - self._last_scale_update < 0.05):
            return

        self._transition_in_progress = True
        self._last_scale_update = current_time
        self._current_scale = scale_factor

        # Apply scaling immediately
        self._apply_scaling(scale_factor)

        # Reset transition flag after a short delay for smooth effect
        self.after(50, lambda: setattr(self, '_transition_in_progress', False))

    def _apply_scaling(self, scale_factor):
        """Apply scaling to widgets - to be implemented by subclasses"""
        pass

# ==============================================================================
#  FRAMES (CONTINUED FROM ORIGINAL CODE)
# ==============================================================================

# Note: All the existing frame classes (ConfigFrame, ReconFrame, DemoFrame, etc.)
# remain exactly the same as in your original code. Only the main app class
# and new FailureReport class were modified above.

# The rest of your existing frame classes continue here exactly as they were...

class ConfigFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.title_label = ctk.CTkLabel(self, text="System Configuration", font=("Arial", 24, "bold"))
        self.title_label.pack(anchor="w", pady=(0, 20))

        # Grid for options
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(fill="x", pady=20)

        # Working Directory Section
        ctk.CTkLabel(self.grid_frame, text="Fucyfuzz Path:").grid(row=0, column=0, padx=20, pady=20)

        self.wd_entry = ctk.CTkEntry(self.grid_frame, placeholder_text="/path/to/fucyfuzz")
        self.wd_entry.grid(row=0, column=1, padx=(20, 5), pady=20, sticky="ew")
        self.wd_entry.insert(0, app.working_dir)

        self.browse_btn = ctk.CTkButton(self.grid_frame, text="Browse", command=self.browse_wd)
        self.browse_btn.grid(row=0, column=2, padx=20, pady=20)

        # Interface Section
        ctk.CTkLabel(self.grid_frame, text="Interface:").grid(row=1, column=0, padx=20, pady=20)

        # CHANGE: Added fg_color and button_color to match
        self.driver = ctk.CTkOptionMenu(self.grid_frame, values=["socketcan", "vector", "pcan"],
                                        fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.driver.grid(row=1, column=1, padx=20, pady=20, sticky="ew")

        ctk.CTkLabel(self.grid_frame, text="Channel:").grid(row=2, column=0, padx=20, pady=20)
        self.channel = ctk.CTkEntry(self.grid_frame, placeholder_text="vcan0")
        self.channel.grid(row=2, column=1, padx=20, pady=20, sticky="ew")

        self.grid_frame.grid_columnconfigure(1, weight=1)

        self.save_btn = ctk.CTkButton(self, text="Save Config", command=self.save)
        self.save_btn.pack(pady=20)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes with smooth scaling
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))

        # Update fonts with smooth transition
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update padding and element sizes
        base_pad = int(20 * scale_factor)
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(35, min(50, int(40 * scale_factor)))
        btn_width = max(100, min(180, int(140 * scale_factor)))

        font_cfg = ("Arial", label_font_size)

        # Update widget sizes with improved padding
        self.save_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.browse_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.wd_entry.configure(height=entry_height, font=font_cfg)
        self.channel.configure(height=entry_height, font=font_cfg)

        # FIX: Added dropdown_font scaling
        self.driver.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)

    def browse_wd(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.wd_entry.delete(0, "end")
            self.wd_entry.insert(0, dir_path)

    def save(self):
        # Update App Working Directory
        new_wd = self.wd_entry.get().strip()
        if os.path.exists(new_wd):
            self.app.working_dir = new_wd
            self.app._console_write(f"[CONFIG] Working Directory updated to: {new_wd}\n")
        else:
            messagebox.showwarning("Warning", "Path does not exist. Working directory not updated.")

        try:
            with open(os.path.expanduser("~/.canrc"), "w") as f:
                f.write(f"[default]\ninterface={self.driver.get()}\nchannel={self.channel.get()}\n")
            self.app._console_write("[CONFIG] ~/.canrc Config Saved.\n")
        except Exception as e: messagebox.showerror("Error", str(e))

class ReconFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Reconnaissance", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("listener"))
        self.help_btn.pack(side="right", padx=10)

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("Recon"))
        self.report_btn.pack(side="right", padx=10)

        # Center the main button with better padding
        self.button_container = ctk.CTkFrame(self, fg_color="transparent")
        self.button_container.pack(expand=True, fill="both", pady=40)

        # ADDED: Interface checkbox
        self.interface_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.interface_frame.pack(pady=(0, 20))

        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.pack()

        self.start_btn = ctk.CTkButton(self.button_container, text="▶ Start Listener",
                      command=self.run_listener)
        self.start_btn.pack(expand=True)

    def run_listener(self):
        """Run listener with correct FucyFuzz interface handling"""
        cmd = []

        # Add interface BEFORE the module name
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Module name and arguments
        cmd.extend(["listener", "-r"])

        self.app.run_command(cmd, "Recon")


    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        button_font_size = max(14, min(22, int(16 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button sizes with better padding
        btn_height = max(50, min(90, int(70 * scale_factor)))
        btn_width = max(200, min(350, int(280 * scale_factor)))
        small_btn_size = max(40, min(70, int(55 * scale_factor)))
        small_btn_width = max(140, min(220, int(180 * scale_factor)))

        self.start_btn.configure(height=btn_height, font=("Arial", button_font_size, "bold"),
                               width=btn_width, corner_radius=12)
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1),
                                width=small_btn_width, corner_radius=10)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size,
                              font=("Arial", button_font_size), corner_radius=10)
        self.interface_check.configure(font=("Arial", checkbox_font_size))

class DemoFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Demo commands", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Main container for all buttons
        self.button_container = ctk.CTkFrame(self, fg_color="transparent")
        self.button_container.pack(expand=True, fill="both", pady=20)

        # Speed control buttons
        self.speed_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.speed_frame.pack(pady=10)

        self.start_speeding_btn = ctk.CTkButton(self.speed_frame, text="Start Fuzzing",
                                              command=self.start_speeding)
        self.start_speeding_btn.pack(side="left", padx=5)

        self.stop_speeding_btn = ctk.CTkButton(self.speed_frame, text="Stop Fuzzing",
                                             command=self.stop_speeding)
        self.stop_speeding_btn.pack(side="left", padx=5)

        self.reset_speed_btn = ctk.CTkButton(self.speed_frame, text="Reset",
                                           command=self.reset_speed)
        self.reset_speed_btn.pack(side="left", padx=5)

        # Indicator buttons
        self.indicator_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.indicator_frame.pack(pady=10)

        self.left_indicator_btn = ctk.CTkButton(self.indicator_frame, text="Left Indicator ON",
                                              command=self.left_indicator_on)
        self.left_indicator_btn.pack(side="left", padx=5)

        self.right_indicator_btn = ctk.CTkButton(self.indicator_frame, text="Right Indicator ON",
                                               command=self.right_indicator_on)
        self.right_indicator_btn.pack(side="left", padx=5)

        self.indicators_off_btn = ctk.CTkButton(self.indicator_frame, text="Indicators OFF",
                                              command=self.indicators_off)
        self.indicators_off_btn.pack(side="left", padx=5)

        # Door control buttons
        self.doors_frame = ctk.CTkFrame(self.button_container, fg_color="transparent")
        self.doors_frame.pack(pady=10)

        self.front_doors_open_btn = ctk.CTkButton(self.doors_frame, text="Front Doors Open",
                                                command=self.front_doors_open)
        self.front_doors_open_btn.pack(side="left", padx=5)

        self.front_doors_close_btn = ctk.CTkButton(self.doors_frame, text="Front Doors Close",
                                                 command=self.front_doors_close)
        self.front_doors_close_btn.pack(side="left", padx=5)

        self.back_doors_open_btn = ctk.CTkButton(self.doors_frame, text="Back Doors Open",
                                               command=self.back_doors_open)
        self.back_doors_open_btn.pack(side="left", padx=5)

        self.back_doors_close_btn = ctk.CTkButton(self.doors_frame, text="Back Doors Close",
                                                command=self.back_doors_close)
        self.back_doors_close_btn.pack(side="left", padx=5)

        # Fuzzing state variables
        self.fuzzing_active = False
        self.fuzzing_process = None

    def run_demo_command(self, cmd_args, description):
        """Run demo commands without blocking the main process"""
        try:
            # Use subprocess directly without going through app.run_command
            working_dir = self.app.working_dir
            env = os.environ.copy()
            env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")

            # Build the full command
            cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + cmd_args

            # Run in background without waiting for completion
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=working_dir,
                env=env
            )

            # Just log that we sent the command
            self.app._console_write(f"[DEMO] Sent: {description}\n")

            return process

        except Exception as e:
            self.app._console_write(f"[DEMO ERROR] {description}: {e}\n")
            return None

    def start_speeding(self):
        """Start fuzzing speed data"""
        if not self.fuzzing_active:
            self.fuzzing_active = True
            self.start_speeding_btn.configure(fg_color="#c0392b", text="Fuzzing...")

            # Start fuzzing for message ID 0x244
            cmd = ["fuzzer", "mutate", "244", ".."]
            self.fuzzing_process = self.run_demo_command(cmd, "Started fuzzing message ")

            if self.fuzzing_process:
                self.app._console_write("[DEMO] Started fuzzing speed messages\n")
            else:
                self.fuzzing_active = False
                self.start_speeding_btn.configure(fg_color="#1f538d", text="Start Fuzzing")

    def stop_speeding(self):
        """Stop fuzzing speed data"""
        if self.fuzzing_active and self.fuzzing_process:
            # Terminate the fuzzing process
            self.fuzzing_process.terminate()
            self.fuzzing_process = None

        self.fuzzing_active = False
        self.start_speeding_btn.configure(fg_color="#1f538d", text="Start Fuzzing")
        self.app._console_write("[DEMO] Stopped fuzzing\n")

    def reset_speed(self):
        """Reset speed to 0"""
        self.stop_speeding()  # Stop any ongoing fuzzing
        cmd = ["send", "message", "0x244#00"]
        self.run_demo_command(cmd, "Reset Speed to 0")

    def left_indicator_on(self):
        """Turn left indicator on"""
        cmd = ["send", "message", "0x188#01"]
        self.run_demo_command(cmd, "Left Indicator ON")

    def right_indicator_on(self):
        """Turn right indicator on"""
        cmd = ["send", "message", "0x188#02"]
        self.run_demo_command(cmd, "Right Indicator ON")

    def indicators_off(self):
        """Turn all indicators off"""
        cmd = ["send", "message", "0x188#00"]
        self.run_demo_command(cmd, "Indicators OFF")

    def front_doors_open(self):
        """Open front doors"""
        cmd = ["send", "message", "0x19B#01.01.00.00"]
        self.run_demo_command(cmd, "Front Doors Open")

    def front_doors_close(self):
        """Close front doors"""
        cmd = ["send", "message", "0x19B#00.00.00.00"]
        self.run_demo_command(cmd, "Front Doors Close")

    def back_doors_open(self):
        """Open back doors"""
        cmd = ["send", "message", "0x19B#00.00.01.01"]
        self.run_demo_command(cmd, "Back Doors Open")

    def back_doors_close(self):
        """Close back doors"""
        cmd = ["send", "message", "0x19B#00.00.00.00"]
        self.run_demo_command(cmd, "Back Doors Close")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        button_font_size = max(14, min(22, int(16 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button sizes
        btn_height = max(40, min(70, int(50 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))

        # Apply scaling to all buttons
        buttons = [
            self.start_speeding_btn, self.stop_speeding_btn, self.reset_speed_btn,
            self.left_indicator_btn, self.right_indicator_btn, self.indicators_off_btn,
            self.front_doors_open_btn, self.front_doors_close_btn,
            self.back_doors_open_btn, self.back_doors_close_btn
        ]

        for button in buttons:
            button.configure(height=btn_height, font=("Arial", button_font_size),
                           width=btn_width, corner_radius=8)

class FuzzerFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        # Header
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Signal Fuzzer", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("fuzzer"))
        self.help_btn.pack(side="right", padx=10)

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("Fuzzer"))
        self.report_btn.pack(side="right", padx=10)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, pady=20)

        # Targeted Fuzz
        self.smart_tab = self.tabs.add("Targeted")

        ctk.CTkLabel(self.smart_tab, text="Select Message (Optional):").pack(pady=(20, 10))

        # CHANGE: Unified colors
        self.msg_select = ctk.CTkOptionMenu(self.smart_tab, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=10, fill="x", padx=20)

        # ADDED: Manual ID entry that's always enabled
        ctk.CTkLabel(self.smart_tab, text="OR Enter Manual ID:").pack(pady=(10, 5))
        self.tid = ctk.CTkEntry(self.smart_tab, placeholder_text="Target ID (e.g., 0x123)")
        self.tid.pack(pady=5, fill="x", padx=20)

        # CHANGED: Made data field optional with better placeholder
        self.data = ctk.CTkEntry(self.smart_tab, placeholder_text="Data Pattern (Optional - e.g., 1122..44)")
        self.data.pack(pady=10, fill="x", padx=20)

        # CHANGE: Unified colors
        self.mode = ctk.CTkOptionMenu(self.smart_tab, values=["brute", "mutate"],
                                    fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.mode.pack(pady=20, fill="x", padx=20)

        # ADDED: Interface checkbox for targeted fuzzing
        self.interface_frame = ctk.CTkFrame(self.smart_tab, fg_color="transparent")
        self.interface_frame.pack(pady=10, fill="x", padx=20)

        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.pack()

        # Add launch button for targeted fuzzing
        self.launch_btn = ctk.CTkButton(self.smart_tab, text="Start Targeted Fuzzing",
                                      command=self.run_smart, fg_color="#27ae60")
        self.launch_btn.pack(pady=20, fill="x", padx=20)

        # Random
        self.rnd_tab = self.tabs.add("Random")

        # ADDED: Interface checkbox for random fuzzing
        self.random_interface_frame = ctk.CTkFrame(self.rnd_tab, fg_color="transparent")
        self.random_interface_frame.pack(pady=(20, 10), fill="x", padx=20)

        self.random_use_interface = ctk.BooleanVar(value=True)
        self.random_interface_check = ctk.CTkCheckBox(self.random_interface_frame, text="Use -i vcan0 interface",
                                                    variable=self.random_use_interface)
        self.random_interface_check.pack()

        self.random_btn = ctk.CTkButton(self.rnd_tab, text="Start Random Noise", fg_color="#c0392b",
                                      command=self.run_random)
        self.random_btn.pack(pady=10, fill="x", padx=20)

    def run_smart(self):
        """Run targeted fuzzing with optional interface"""
        tid = self.tid.get().strip()

        # CHANGED: Only require ID, data is optional
        if not tid:
            messagebox.showerror("Error", "Please enter a Target ID")
            return

        data = self.data.get().strip()
        mode = self.mode.get()

        # Build command with optional interface
        cmd = ["fuzzer", mode]
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])
        cmd.extend([tid])

        # ADDED: Only add data if provided
        if data:
            cmd.extend([data])

        # Run the command
        self.app.run_command(cmd, "Fuzzer")

    def run_random(self):
        """Run random fuzzing with optional interface"""
        cmd = ["fuzzer", "random"]
        if self.random_use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Fuzzer")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(13, min(19, int(15 * scale_factor)))
        button_font_size = max(13, min(19, int(15 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button and entry sizes with better padding
        btn_height = max(40, min(65, int(50 * scale_factor)))
        entry_height = max(38, min(55, int(45 * scale_factor)))
        small_btn_size = max(40, min(65, int(50 * scale_factor)))
        btn_width = max(160, min(260, int(200 * scale_factor)))

        font_cfg = ("Arial", label_font_size)

        # Configure all buttons that exist
        self.launch_btn.configure(height=btn_height, font=("Arial", button_font_size, "bold"),
                                corner_radius=10)
        self.random_btn.configure(height=btn_height, font=("Arial", button_font_size, "bold"),
                                corner_radius=10)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size,
                              font=("Arial", button_font_size), corner_radius=10)
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1),
                                width=btn_width, corner_radius=10)

        # Update entry and dropdown sizes
        # FIX: Added dropdown_font
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg, corner_radius=8)
        self.tid.configure(height=entry_height, font=font_cfg, corner_radius=8)
        self.data.configure(height=entry_height, font=font_cfg, corner_radius=8)
        self.mode.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg, corner_radius=8)

        # Update checkbox fonts
        self.interface_check.configure(font=("Arial", checkbox_font_size))
        self.random_interface_check.configure(font=("Arial", checkbox_font_size))

        # Scale inner Tabview fonts as well
        self.tabs._segmented_button.configure(font=("Arial", label_font_size))

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.tid.delete(0, "end")
            self.tid.insert(0, hex_id)


class LengthAttackFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Length Attack", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("lenattack"))
        self.help_btn.pack(side="right", padx=10)

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("LengthAttack"))
        self.report_btn.pack(side="right", padx=10)

        self.card = ctk.CTkFrame(self, corner_radius=12)
        self.card.pack(fill="x", padx=30, pady=30)

        # Row 0: DBC Select (Optional)
        ctk.CTkLabel(self.card, text="DBC Message (Optional):").grid(row=0, column=0, padx=20, pady=15)

        # CHANGE: Unified colors
        self.msg_select = ctk.CTkOptionMenu(self.card, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.grid(row=0, column=1, padx=20, pady=15, sticky="ew")

        # Row 1: Target ID (Manual entry - always available)
        ctk.CTkLabel(self.card, text="OR Enter Target ID (Hex):").grid(row=1, column=0, padx=20, pady=15)
        self.lid = ctk.CTkEntry(self.card, placeholder_text="0x123")
        self.lid.grid(row=1, column=1, padx=20, pady=15, sticky="ew")

        # Row 2: Extra Args
        ctk.CTkLabel(self.card, text="Extra Args:").grid(row=2, column=0, padx=20, pady=15)
        self.largs = ctk.CTkEntry(self.card, placeholder_text="Optional (e.g. -v)")
        self.largs.grid(row=2, column=1, padx=20, pady=15, sticky="ew")

        # Row 3: Interface checkbox
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.card, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.grid(row=3, column=0, columnspan=2, padx=20, pady=15, sticky="w")

        self.card.grid_columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(self, text="START ATTACK", fg_color="#8e44ad", command=self.run_attack)
        self.start_btn.pack(fill="x", padx=50, pady=30)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(13, min(19, int(15 * scale_factor)))
        button_font_size = max(14, min(22, int(16 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button and entry sizes with better padding
        btn_height = max(45, min(75, int(55 * scale_factor)))
        entry_height = max(38, min(55, int(45 * scale_factor)))
        small_btn_size = max(40, min(65, int(50 * scale_factor)))
        btn_width = max(160, min(260, int(200 * scale_factor)))

        self.start_btn.configure(height=btn_height, font=("Arial", button_font_size, "bold"), corner_radius=12)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size,
                              font=("Arial", button_font_size), corner_radius=10)
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1),
                                width=btn_width, corner_radius=10)

        font_cfg = ("Arial", label_font_size)

        # Update entry and dropdown sizes
        # FIX: Added dropdown_font
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg, corner_radius=8)
        self.lid.configure(height=entry_height, font=font_cfg, corner_radius=8)
        self.largs.configure(height=entry_height, font=font_cfg, corner_radius=8)
        self.interface_check.configure(font=("Arial", checkbox_font_size))

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.lid.delete(0, "end")
            self.lid.insert(0, hex_id)

    def run_attack(self):
        tid = self.lid.get().strip()
        if not tid:
            messagebox.showerror("Error", "Please enter a Target ID")
            return

        if not tid.startswith("0x") and not tid.isdigit():
            tid = "0x" + tid

        cmd = ["lenattack", tid]
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])
        if self.largs.get().strip():
            cmd.extend(self.largs.get().strip().split())

        self.app.run_command(cmd, "LengthAttack")

class DCMFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="DCM Diagnostics", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("dcm"))
        self.help_btn.pack(side="right", padx=5)

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("DCM"))
        self.report_btn.pack(side="right", padx=5)

        # DCM Action Selection
        ctk.CTkLabel(self, text="DCM Action:").pack(pady=(20, 10))

        self.dcm_act = ctk.CTkOptionMenu(self,
                                       values=["discovery", "services", "subfunc", "dtc", "testerpresent"],
                                       fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e",
                                       command=self.on_dcm_action_change)
        self.dcm_act.pack(pady=10, fill="x", padx=20)
        self.dcm_act.set("discovery")

        # DBC Message Selection (Optional)
        ctk.CTkLabel(self, text="DBC Message (Optional):").pack(pady=(10, 5))

        self.msg_select = ctk.CTkOptionMenu(self, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5, fill="x", padx=20)

        # DCM Parameters Frame
        self.dcm_params_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dcm_params_frame.pack(fill="x", pady=10, padx=20)

        # Target ID (for most DCM commands)
        ctk.CTkLabel(self.dcm_params_frame, text="Target ID:").pack(anchor="w")
        self.dcm_tid = ctk.CTkEntry(self.dcm_params_frame, placeholder_text="e.g., 0x733")
        self.dcm_tid.pack(fill="x", pady=5)

        # Response ID (for services, subfunc, dtc)
        self.dcm_rid_label = ctk.CTkLabel(self.dcm_params_frame, text="Response ID:")
        self.dcm_rid = ctk.CTkEntry(self.dcm_params_frame, placeholder_text="e.g., 0x633")

        # Additional parameters for subfunc
        self.subfunc_frame = ctk.CTkFrame(self.dcm_params_frame, fg_color="transparent")

        self.subfunc_label = ctk.CTkLabel(self.subfunc_frame, text="Subfunction Parameters:")

        self.subfunc_params_frame = ctk.CTkFrame(self.subfunc_frame, fg_color="transparent")

        ctk.CTkLabel(self.subfunc_params_frame, text="Service:").grid(row=0, column=0, padx=(0, 5))
        self.dcm_service = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="0x22", width=80)
        self.dcm_service.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(self.subfunc_params_frame, text="Subfunc:").grid(row=0, column=2, padx=(10, 5))
        self.dcm_subfunc = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="2", width=60)
        self.dcm_subfunc.grid(row=0, column=3, padx=5)

        ctk.CTkLabel(self.subfunc_params_frame, text="Data:").grid(row=0, column=4, padx=(10, 5))
        self.dcm_data = ctk.CTkEntry(self.subfunc_params_frame, placeholder_text="3", width=60)
        self.dcm_data.grid(row=0, column=5, padx=5)

        self.subfunc_params_frame.grid_columnconfigure(5, weight=1)

        # DCM Options Frame
        self.dcm_options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dcm_options_frame.pack(fill="x", pady=10, padx=20)

        # Blacklist options
        self.blacklist_label = ctk.CTkLabel(self.dcm_options_frame, text="Blacklist IDs (space separated):")
        self.dcm_blacklist = ctk.CTkEntry(self.dcm_options_frame, placeholder_text="0x123 0x456")

        # Auto blacklist
        self.autoblacklist_frame = ctk.CTkFrame(self.dcm_options_frame, fg_color="transparent")

        self.autoblacklist_label = ctk.CTkLabel(self.autoblacklist_frame, text="Auto Blacklist Count:")
        self.dcm_autoblacklist = ctk.CTkEntry(self.autoblacklist_frame, placeholder_text="10", width=80)

        # Extra Args
        ctk.CTkLabel(self, text="Extra Args:").pack(pady=(10, 5))
        self.dcm_extra_args = ctk.CTkEntry(self, placeholder_text="Additional arguments")
        self.dcm_extra_args.pack(fill="x", pady=5, padx=20)

        # DCM Interface checkbox
        self.dcm_use_interface = ctk.BooleanVar(value=True)
        self.dcm_interface_check = ctk.CTkCheckBox(self, text="Use -i vcan0 interface",
                                                 variable=self.dcm_use_interface)
        self.dcm_interface_check.pack(pady=10, padx=20)

        # DCM Execute Button
        self.dcm_execute_btn = ctk.CTkButton(self, text="Execute DCM", command=self.run_dcm, fg_color="#8e44ad")
        self.dcm_execute_btn.pack(pady=20, fill="x", padx=20)

        # Initialize UI based on default action
        self.on_dcm_action_change("discovery")

    def on_dcm_action_change(self, selection):
        """Update DCM UI based on selected action"""
        # Hide all optional elements first
        self.dcm_rid_label.pack_forget()
        self.dcm_rid.pack_forget()
        self.subfunc_label.pack_forget()
        self.subfunc_frame.pack_forget()
        self.subfunc_params_frame.pack_forget()
        self.blacklist_label.pack_forget()
        self.dcm_blacklist.pack_forget()
        self.autoblacklist_label.pack_forget()
        self.autoblacklist_frame.pack_forget()
        self.dcm_autoblacklist.pack_forget()

        # Show common elements
        self.dcm_tid.pack(fill="x", pady=5)

        # Action-specific configurations
        if selection == "discovery":
            # Show blacklist options for discovery
            self.blacklist_label.pack(anchor="w")
            self.dcm_blacklist.pack(fill="x", pady=5)

            self.autoblacklist_label.pack(side="left")
            self.dcm_autoblacklist.pack(side="left", padx=10)
            self.autoblacklist_frame.pack(fill="x", pady=5)

        elif selection in ["services", "dtc"]:
            # Show response ID for services and dtc
            self.dcm_rid_label.pack(anchor="w")
            self.dcm_rid.pack(fill="x", pady=5)

        elif selection == "subfunc":
            # Show response ID and subfunction parameters
            self.dcm_rid_label.pack(anchor="w")
            self.dcm_rid.pack(fill="x", pady=5)

            self.subfunc_label.pack(anchor="w", pady=(10, 0))
            self.subfunc_params_frame.pack(fill="x", pady=5)
            self.subfunc_frame.pack(fill="x", pady=10)

        elif selection == "testerpresent":
            # Only target ID needed for testerpresent
            pass

    def run_dcm(self):
        """Execute DCM command"""
        action = self.dcm_act.get()
        cmd = ["dcm", action]

        # Add target ID if provided
        tid = self.dcm_tid.get().strip()
        if tid:
            cmd.append(tid)
        elif action != "discovery":  # discovery can work without target ID
            messagebox.showerror("Error", "Target ID is required for this action")
            return

        # Action-specific parameters
        if action in ["services", "subfunc", "dtc"]:
            rid = self.dcm_rid.get().strip()
            if rid:
                cmd.append(rid)
            else:
                messagebox.showerror("Error", "Response ID is required for this action")
                return

        if action == "subfunc":
            # Add subfunction parameters
            service = self.dcm_service.get().strip()
            subfunc = self.dcm_subfunc.get().strip()
            data = self.dcm_data.get().strip()

            if service:
                cmd.append(service)
            else:
                messagebox.showerror("Error", "Service parameter is required for subfunc")
                return

            if subfunc:
                cmd.append(subfunc)
            if data:
                cmd.append(data)

        # Add blacklist options for discovery
        if action == "discovery":
            blacklist = self.dcm_blacklist.get().strip()
            if blacklist:
                cmd.extend(["-blacklist"] + blacklist.split())

            autoblacklist = self.dcm_autoblacklist.get().strip()
            if autoblacklist:
                cmd.extend(["-autoblacklist", autoblacklist])

        # Add extra arguments if provided
        extra_args = self.dcm_extra_args.get().strip()
        if extra_args:
            cmd.extend(extra_args.split())

        # Add interface if checkbox is checked
        if self.dcm_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        self.app.run_command(cmd, "DCM")

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.dcm_tid.delete(0, "end")
            self.dcm_tid.insert(0, hex_id)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))

        self.dcm_execute_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)

        font_cfg = ("Arial", label_font_size)

        # Update entry and dropdown sizes
        self.dcm_act.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.dcm_tid.configure(height=entry_height, font=font_cfg)
        self.dcm_rid.configure(height=entry_height, font=font_cfg)
        self.dcm_service.configure(height=entry_height, font=font_cfg)
        self.dcm_subfunc.configure(height=entry_height, font=font_cfg)
        self.dcm_data.configure(height=entry_height, font=font_cfg)
        self.dcm_blacklist.configure(height=entry_height, font=font_cfg)
        self.dcm_autoblacklist.configure(height=entry_height, font=font_cfg)
        self.dcm_extra_args.configure(height=entry_height, font=font_cfg)
        self.dcm_interface_check.configure(font=("Arial", checkbox_font_size))

class UDSFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="UDS Diagnostics", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("uds"))
        self.help_btn.pack(side="right", padx=5)

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("UDS"))
        self.report_btn.pack(side="right", padx=5)

        # CHANGE: Unified colors
        self.act = ctk.CTkOptionMenu(self, values=["discovery", "services", "subservices", "dump_dids", "read_mem", "security_seed"],
                                    fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.act.pack(pady=10)

        # ADDED DBC SELECTION
        ctk.CTkLabel(self, text="DBC Message (Optional):").pack(pady=(10, 0))

        # CHANGE: Unified colors
        self.msg_select = ctk.CTkOptionMenu(self, values=["No DBC Loaded"], command=self.on_msg_select,
                                            fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5)

        # ==========================================================
        #  FIXED LAYOUT: Checkbox above Entry for Perfect Alignment
        # ==========================================================

        # 1. Checkbox acts as label
        self.use_id_var = ctk.BooleanVar(value=True)
        self.id_chk = ctk.CTkCheckBox(self, text="Use Target ID:", variable=self.use_id_var,
                                      command=self.toggle_id_entry)
        self.id_chk.pack(pady=(10, 5), anchor="w", padx=5)

        # 2. Entry uses fill="x" to match other fields exactly
        self.tid = ctk.CTkEntry(self, placeholder_text="Target ID (0x7E0)")
        self.tid.pack(fill="x", pady=5)

        self.args = ctk.CTkEntry(self, placeholder_text="Extra Args")
        self.args.pack(fill="x", pady=5) # Matches width of tid above

        # ADDED: Interface checkbox
        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.pack(pady=10)

        self.execute_btn = ctk.CTkButton(self, text="Execute UDS", command=self.run)
        self.execute_btn.pack(pady=20)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))

        self.execute_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)

        font_cfg = ("Arial", label_font_size)

        # Update entry and dropdown sizes
        # FIX: Added dropdown_font
        self.act.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.tid.configure(height=entry_height, font=font_cfg)
        self.args.configure(height=entry_height, font=font_cfg)
        self.id_chk.configure(font=font_cfg)
        self.interface_check.configure(font=("Arial", checkbox_font_size))

    def toggle_id_entry(self):
        # Gray out the entry if checkbox is unchecked
        state = "normal" if self.use_id_var.get() else "disabled"
        self.tid.configure(state=state)

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

    def on_msg_select(self, selection):
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            self.use_id_var.set(True) # Auto-enable
            self.toggle_id_entry()
            self.tid.delete(0, "end")
            self.tid.insert(0, hex_id)

    def run(self):
        cmd = ["uds", self.act.get()]

        # Only add ID if checkbox is True AND entry is not empty
        if self.use_id_var.get():
            val = self.tid.get().strip()
            if val:
                cmd.append(val)

        # Add interface if checkbox is checked
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])

        if self.args.get(): cmd.extend(self.args.get().split())
        self.app.run_command(cmd, "UDS")

class AdvancedFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Advanced", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Buttons (Show help for all advanced modules)
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help(["doip", "xcp", "uds"]))
        self.help_btn.pack(side="right", padx=5)

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("Advanced"))
        self.report_btn.pack(side="right", padx=5)

        # Create notebook for different advanced functions
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, pady=10)

        # Tab 1: DoIP
        self.doip_tab = self.tabs.add("DoIP")

        # DoIP Section with interface checkbox
        self.doip_frame = ctk.CTkFrame(self.doip_tab, fg_color="transparent")
        self.doip_frame.pack(fill="x", pady=10, padx=20)

        self.doip_use_interface = ctk.BooleanVar(value=True)
        self.doip_interface_check = ctk.CTkCheckBox(self.doip_frame, text="Use -i vcan0 interface for DoIP",
                                                  variable=self.doip_use_interface)
        self.doip_interface_check.pack(pady=5)

        self.doip_btn = ctk.CTkButton(self.doip_frame, text="DoIP Discovery",
                                    command=self.run_doip)
        self.doip_btn.pack(fill="x", pady=5)

        # Tab 2: XCP
        self.xcp_tab = self.tabs.add("XCP")

        # XCP Section with interface checkbox
        self.xcp_frame = ctk.CTkFrame(self.xcp_tab, fg_color="transparent")
        self.xcp_frame.pack(fill="x", pady=10, padx=20)

        self.xcp_use_interface = ctk.BooleanVar(value=True)
        self.xcp_interface_check = ctk.CTkCheckBox(self.xcp_frame, text="Use -i vcan0 interface for XCP",
                                                 variable=self.xcp_use_interface)
        self.xcp_interface_check.pack(pady=5)

        self.xcp_id = ctk.CTkEntry(self.xcp_frame, placeholder_text="XCP ID (e.g., 0x123)")
        self.xcp_id.pack(pady=5, fill="x")

        self.xcp_btn = ctk.CTkButton(self.xcp_frame, text="XCP Info",
                                   command=self.run_xcp)
        self.xcp_btn.pack(pady=5, fill="x")

        # Tab 3: UDS DID Reader
        self.did_tab = self.tabs.add("DID Reader")

        # UDS DID Reader Section
        self.did_frame = ctk.CTkFrame(self.did_tab, fg_color="transparent")
        self.did_frame.pack(fill="both", expand=True, pady=10, padx=20)

        # DID Selection
        ctk.CTkLabel(self.did_frame, text="Select DID to Read:").pack(anchor="w", pady=(0, 5))

        self.did_select = ctk.CTkOptionMenu(self.did_frame,
                                          values=[
                                              "Single DID: 0xF190 - VIN (Vehicle ID)",
                                              "Single DID: 0xF180 - Boot Software ID",
                                              "Single DID: 0xF181 - Application Software ID",
                                              "Single DID: 0xF186 - Active Session",
                                              "Single DID: 0xF187 - Spare Part Number",
                                              "Single DID: 0xF188 - ECU SW Number",
                                              "Single DID: 0xF198 - Repair Shop Code",
                                              "Single DID: 0xF18C - ECU Serial Number",
                                              "Custom DID",
                                              "Scan Range: 0xF180-0xF1FF (Manufacturer DIDs)"
                                          ],
                                          command=self.on_did_selection_change,
                                          fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.did_select.pack(pady=5, fill="x")
        self.did_select.set("Single DID: 0xF190 - VIN (Vehicle ID)")

        # Custom DID entry (initially hidden)
        self.custom_did_frame = ctk.CTkFrame(self.did_frame, fg_color="transparent")

        ctk.CTkLabel(self.custom_did_frame, text="Custom DID (Hex):").pack(anchor="w", pady=(0, 5))
        self.custom_did_entry = ctk.CTkEntry(self.custom_did_frame, placeholder_text="e.g., F190 (without 0x)")
        self.custom_did_entry.pack(pady=5, fill="x")

        # Range scanning options (initially hidden)
        self.range_frame = ctk.CTkFrame(self.did_frame, fg_color="transparent")

        ctk.CTkLabel(self.range_frame, text="Start DID (Hex):").pack(anchor="w", pady=(0, 5))
        self.start_did_entry = ctk.CTkEntry(self.range_frame, placeholder_text="F180")
        self.start_did_entry.pack(pady=5, fill="x")

        ctk.CTkLabel(self.range_frame, text="End DID (Hex):").pack(anchor="w", pady=(10, 5))
        self.end_did_entry = ctk.CTkEntry(self.range_frame, placeholder_text="F1FF")
        self.end_did_entry.pack(pady=5, fill="x")

        # Target ID for UDS request
        ctk.CTkLabel(self.did_frame, text="Target ECU ID (Hex):").pack(anchor="w", pady=(10, 5))
        self.uds_target_id = ctk.CTkEntry(self.did_frame, placeholder_text="0x7E0 (default)")
        self.uds_target_id.insert(0, "0x7E0")
        self.uds_target_id.pack(pady=5, fill="x")

        # Response ID
        ctk.CTkLabel(self.did_frame, text="Response ID:").pack(anchor="w", pady=(10, 5))
        self.uds_response_id = ctk.CTkEntry(self.did_frame, placeholder_text="0x7E8 (default)")
        self.uds_response_id.insert(0, "0x7E8")
        self.uds_response_id.pack(pady=5, fill="x")

        # Timeout option
        ctk.CTkLabel(self.did_frame, text="Timeout (seconds):").pack(anchor="w", pady=(10, 5))
        self.timeout_entry = ctk.CTkEntry(self.did_frame, placeholder_text="0.2 (default)")
        self.timeout_entry.insert(0, "0.2")
        self.timeout_entry.pack(pady=5, fill="x")

        # Interface checkbox for DID reading
        self.did_use_interface = ctk.BooleanVar(value=True)
        self.did_interface_check = ctk.CTkCheckBox(self.did_frame, text="Use -i vcan0 interface for UDS",
                                                 variable=self.did_use_interface)
        self.did_interface_check.pack(pady=10)

        # NEW: Response display section
        self.response_section = ctk.CTkFrame(self.did_frame, fg_color="transparent")
        self.response_section.pack(fill="x", pady=(10, 0))

        # Two buttons side by side
        self.button_frame = ctk.CTkFrame(self.response_section, fg_color="transparent")
        self.button_frame.pack(fill="x")

        # Read DID button
        self.did_read_btn = ctk.CTkButton(self.button_frame, text="🔍 Read DID",
                                        command=self.read_did, fg_color="#8e44ad")
        self.did_read_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # NEW: Show Response button
        self.show_response_btn = ctk.CTkButton(self.button_frame, text="📥 Show Response",
                                             command=self.show_did_response, fg_color="#27ae60")
        self.show_response_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # NEW: Response display textbox
        self.response_text = ctk.CTkTextbox(self.did_frame, height=200, font=("Consolas", 11))
        self.response_text.pack(fill="both", expand=True, pady=(10, 0))

        # Initialize UI state
        self.on_did_selection_change("Single DID: 0xF190 - VIN (Vehicle ID)")

        # Tab 4: UDS Response Analyzer
        self.analyzer_tab = self.tabs.add("UDS Analyzer")

        # UDS Analyzer Frame
        self.analyzer_frame = ctk.CTkFrame(self.analyzer_tab, fg_color="transparent")
        self.analyzer_frame.pack(fill="both", expand=True, pady=10, padx=20)

        # Section 1: Input raw UDS response
        input_frame = ctk.CTkFrame(self.analyzer_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(input_frame, text="Paste UDS Response (from candump):").pack(anchor="w")

        # Example formats
        examples_label = ctk.CTkLabel(input_frame,
                                    text="Example format:\nvcan0  7E8   [8]  10 14 62 F1 90 46 55 43",
                                    text_color="#95a5a6",
                                    font=("Arial", 11))
        examples_label.pack(anchor="w", pady=(0, 5))

        self.uds_response_entry = ctk.CTkTextbox(input_frame, height=120)
        self.uds_response_entry.pack(fill="x", pady=5)

        # Example buttons
        example_btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        example_btn_frame.pack(fill="x", pady=5)

        self.load_vin_example_btn = ctk.CTkButton(example_btn_frame, text="VIN Example",
                                                command=lambda: self.load_uds_example("vin"),
                                                fg_color="#3498db", width=120)
        self.load_vin_example_btn.pack(side="left", padx=(0, 5))

        self.load_boot_example_btn = ctk.CTkButton(example_btn_frame, text="Boot ID Example",
                                                command=lambda: self.load_uds_example("boot"),
                                                fg_color="#3498db", width=120)
        self.load_boot_example_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(example_btn_frame, text="Clear",
                                     command=self.clear_uds_input,
                                     fg_color="#7f8c8d", width=80)
        self.clear_btn.pack(side="right")

        # Analyze button
        self.analyze_btn = ctk.CTkButton(self.analyzer_frame, text="🔍 Analyze Response",
                                       command=self.analyze_uds_response,
                                       fg_color="#27ae60", height=40)
        self.analyze_btn.pack(pady=10)

        # Section 2: Results display
        results_frame = ctk.CTkFrame(self.analyzer_frame, fg_color="transparent")
        results_frame.pack(fill="both", expand=True, pady=(10, 0))

        ctk.CTkLabel(results_frame, text="Analysis Results:").pack(anchor="w")

        self.results_text = ctk.CTkTextbox(results_frame, font=("Consolas", 12))
        self.results_text.pack(fill="both", expand=True, pady=5)

    def on_did_selection_change(self, selection):
        """Show/hide custom DID entry based on selection"""
        # Hide all optional frames first
        self.custom_did_frame.pack_forget()
        self.range_frame.pack_forget()

        if selection == "Custom DID":
            self.custom_did_frame.pack(fill="x", pady=10)
        elif "Scan Range:" in selection:
            # Pre-fill the range for manufacturer DIDs
            self.start_did_entry.delete(0, "end")
            self.end_did_entry.delete(0, "end")
            self.start_did_entry.insert(0, "F180")
            self.end_did_entry.insert(0, "F1FF")
            self.range_frame.pack(fill="x", pady=10)

    def read_did(self):
        """Execute UDS DID read command using raw CAN send"""
        # Get target ID
        target_id = self.uds_target_id.get().strip()

        if not target_id:
            messagebox.showerror("Error", "Please enter a Target ECU ID")
            return

        # Ensure target_id has 0x prefix
        if not target_id.startswith("0x"):
            target_id = "0x" + target_id

        # Get selected DID
        selection = self.did_select.get()

        if selection == "Custom DID":
            did_hex = self.custom_did_entry.get().strip()
            if not did_hex:
                messagebox.showerror("Error", "Please enter a custom DID")
                return
            # Remove 0x prefix if present
            did_hex = did_hex.replace("0x", "")
            # Ensure it's 4 hex digits
            if len(did_hex) != 4:
                messagebox.showerror("Error", "DID must be 4 hex digits (e.g., F190)")
                return
            did_bytes = did_hex.upper()

        elif "Single DID:" in selection:
            # Extract DID from the option text
            # e.g., "Single DID: 0xF190 - VIN (Vehicle ID)" -> "F190"
            did_full = selection.split(": ")[1].split(" - ")[0]  # "0xF190"
            did_bytes = did_full[2:].upper()  # "F190"

        elif "Scan Range:" in selection:
            # For range scanning, use the dump_dids command
            self.read_did_range()
            return
        else:
            messagebox.showerror("Error", "Invalid selection")
            return

        # Build the CAN frame in the correct format
        # Format: 0x7E0#03.22.f1.90.00.00.00.00
        # Where:
        #   03 = length (3 bytes total for UDS request: 0x22 + 2-byte DID)
        #   22 = UDS Read Data By Identifier service
        #   f1.90 = DID (2 bytes, lowercase)
        #   00.00.00.00 = padding

        # Parse the DID into two bytes
        did_high_byte = did_bytes[0:2].lower()  # First 2 chars (e.g., "f1")
        did_low_byte = did_bytes[2:4].lower()   # Last 2 chars (e.g., "90")

        # Create the CAN frame with lowercase hex
        can_frame = f"{target_id}#03.22.{did_high_byte}.{did_low_byte}.00.00.00.00"

        # Build the send command
        cmd = ["send", "message", can_frame]

        # Add interface if selected
        if self.did_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Run the command
        self.app.run_command(cmd, "UDS_DID_Reader")

        # Show the command that was sent
        response_id = self.uds_response_id.get().strip() or "0x7E8"
        self.app._console_write(f"\n📤 Sent UDS Request:\n")
        self.app._console_write(f"   Service: 0x22 (Read Data By Identifier)\n")
        self.app._console_write(f"   DID: 0x{did_bytes}\n")
        self.app._console_write(f"   Raw Frame: {can_frame}\n")
        self.app._console_write(f"   Expected Response on: {response_id}\n")
        self.app._console_write(f"\n💡 Manual commands:\n")
        self.app._console_write(f"   cansend vcan0 {target_id}#0322{did_bytes}00000000\n")
        self.app._console_write(f"   python -m fucyfuzz.fucyfuzz send message {can_frame}\n")

        # Store the DID for later use in show_response
        self.last_did_hex = did_bytes
        self.last_target_id = target_id
        self.last_response_id = response_id

    def read_did_range(self):
        """Use dump_dids for range scanning"""
        target_id = self.uds_target_id.get().strip()
        response_id = self.uds_response_id.get().strip()

        # Get timeout value (use default if not set)
        timeout = "0.2"
        if hasattr(self, 'timeout_entry'):
            timeout_val = self.timeout_entry.get().strip()
            if timeout_val:
                timeout = timeout_val

        if not target_id:
            messagebox.showerror("Error", "Please enter a Target ECU ID")
            return

        # Ensure target_id has 0x prefix
        if not target_id.startswith("0x"):
            target_id = "0x" + target_id

        # Get range
        selection = self.did_select.get()

        if selection == "Scan Range: 0xF180-0xF1FF (Manufacturer DIDs)":
            min_did = "0xF180"
            max_did = "0xF1FF"
        else:
            # This shouldn't happen, but just in case
            return

        # Build the UDS dump_dids command
        cmd = ["uds", "dump_dids", target_id]

        if response_id:
            cmd.append(response_id)

        # Add options
        cmd.extend(["--min_did", min_did, "--max_did", max_did, "-t", timeout])

        # Add interface if selected
        if self.did_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Run the command
        self.app.run_command(cmd, "UDS_DID_Scanner")

        # Also show manual examples for the first few DIDs in the range
        self.app._console_write(f"\n📋 Manual examples for this range:\n")

        # Show examples for first 3 DIDs in the range
        try:
            start_val = int(min_did, 16)
            for i in range(3):
                did_hex = f"{start_val + i:04X}"
                self.app._console_write(f"   cansend vcan0 {target_id}#0322{did_hex}00000000\n")
        except:
            pass

    def show_did_response(self):
        """Show response for the last read DID using dump_dids command"""
        # Check if we have stored DID information from last read
        if not hasattr(self, 'last_did_hex'):
            messagebox.showwarning("Warning", "Please read a DID first before showing response")
            return

        # Get target and response IDs
        target_id = self.uds_target_id.get().strip() or self.last_target_id
        response_id = self.uds_response_id.get().strip() or self.last_response_id

        if not target_id:
            messagebox.showerror("Error", "Please enter a Target ECU ID")
            return

        # Ensure target_id has 0x prefix
        if not target_id.startswith("0x"):
            target_id = "0x" + target_id

        # Ensure response_id has 0x prefix
        if response_id and not response_id.startswith("0x"):
            response_id = "0x" + response_id

        # Clear previous response
        self.response_text.delete("1.0", "end")
        self.response_text.insert("1.0", "Fetching response for DID 0x{}...\n".format(self.last_did_hex))

        # Get timeout value
        timeout = "0.2"
        if hasattr(self, 'timeout_entry'):
            timeout_val = self.timeout_entry.get().strip()
            if timeout_val:
                timeout = timeout_val

        # Convert DID to hex integer
        try:
            did_int = int(self.last_did_hex, 16)
        except ValueError:
            self.response_text.insert("end", f"❌ Invalid DID format: 0x{self.last_did_hex}\n")
            return

        # Build the dump_dids command for specific DID
        cmd = ["uds", "dump_dids", target_id]

        if response_id:
            cmd.append(response_id)

        # Add options for specific DID
        cmd.extend([
            "--min_did", f"0x{did_int:04X}",
            "--max_did", f"0x{did_int:04X}",
            "-t", timeout
        ])

        # Add interface if selected
        if self.did_use_interface.get():
            cmd.extend(["-i", "vcan0"])

        # Show the command being executed
        cmd_str = " ".join(cmd)
        self.response_text.insert("end", f"\n📋 Executing: python -m fucyfuzz.fucyfuzz {cmd_str}\n\n")

        # Run the command in a separate thread to avoid freezing UI
        threading.Thread(target=self._execute_dump_dids, args=(cmd,), daemon=True).start()

    def _execute_dump_dids(self, cmd):
        """Execute dump_dids command and show results in response_text"""
        working_dir = self.app.working_dir
        env = os.environ.copy()
        env["PYTHONPATH"] = working_dir + os.pathsep + env.get("PYTHONPATH", "")

        try:
            # Build the full command
            full_cmd = [sys.executable, "-m", "fucyfuzz.fucyfuzz"] + cmd

            # Run subprocess
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=working_dir,
                env=env,
                universal_newlines=True
            )

            # Read output in real-time
            output_lines = []
            for line in iter(process.stdout.readline, ''):
                output_lines.append(line)
                # Update UI with each line
                self.after(0, self._update_response_text, line)

            process.wait()

            # Update final status
            if process.returncode == 0:
                self.after(0, self._update_response_text, f"\n✅ Command completed successfully (Exit code: {process.returncode})\n")

                # NEW: Decode the response after completion
                full_output = "".join(output_lines)
                self.after(0, self._decode_uds_response, full_output)

            else:
                self.after(0, self._update_response_text, f"\n⚠️ Command completed with errors (Exit code: {process.returncode})\n")

        except Exception as e:
            error_msg = f"\n❌ Error running command: {str(e)}\n"
            self.after(0, self._update_response_text, error_msg)

    def _decode_uds_response(self, full_output):
        """Decode UDS response from dump_dids output"""
        # Add separator
        self.after(0, self._update_response_text, "\n" + "="*70 + "\n")
        self.after(0, self._update_response_text, "📊 UDS RESPONSE DECODER\n")
        self.after(0, self._update_response_text, "="*70 + "\n\n")

        # Look for DID data in the output
        lines = full_output.split('\n')
        decoded_data = []
        current_did = None
        current_data = []

        for line in lines:
            line = line.strip()

            # Look for DID lines
            if "0x" in line and ("f1" in line.lower() or "f2" in line.lower()):
                # Try to parse DID and data
                parts = line.split()
                for part in parts:
                    if part.lower().startswith("0xf"):
                        # Found a DID
                        try:
                            did_hex = part.lower().replace("0x", "")
                            if len(did_hex) == 4:  # Valid DID
                                current_did = did_hex.upper()
                                self.after(0, self._update_response_text, f"🔍 Found DID: 0x{current_did}\n")

                                # Look for data bytes in the same line
                                data_start = line.lower().find(did_hex.lower()) + 4
                                rest_of_line = line[data_start:].strip()

                                # Extract hex bytes (2 chars each)
                                data_bytes = []
                                for i in range(0, len(rest_of_line), 2):
                                    if i+2 <= len(rest_of_line):
                                        byte_str = rest_of_line[i:i+2]
                                        if byte_str.isalnum() and len(byte_str) == 2:
                                            try:
                                                data_bytes.append(int(byte_str, 16))
                                            except:
                                                pass

                                if data_bytes:
                                    current_data = data_bytes
                                    self._decode_did_data(current_did, current_data)
                                break
                        except:
                            continue

        # If no DID found in the output, check for raw hex data
        if not decoded_data:
            # Look for any hex data in the output
            all_hex_data = []
            for line in lines:
                # Extract hex bytes (2 chars each)
                hex_parts = []
                line = line.strip()

                # Split by spaces and look for hex strings
                for word in line.split():
                    if len(word) == 2 and all(c in "0123456789abcdefABCDEF" for c in word):
                        try:
                            hex_parts.append(int(word, 16))
                        except:
                            pass

                if hex_parts:
                    all_hex_data.extend(hex_parts)

            if all_hex_data:
                self.after(0, self._update_response_text, "📋 Raw hex data found:\n")
                self.after(0, self._update_response_text, f"   Hex: {' '.join(f'{b:02X}' for b in all_hex_data)}\n")

                # Try to decode as UDS response
                self._decode_uds_bytes(all_hex_data)

        # Show quick reference
        self.after(0, self._update_response_text, "\n" + "="*70 + "\n")
        self.after(0, self._update_response_text, "📚 UDS RESPONSE FORMAT REFERENCE:\n\n")

        # Positive Response (0x62) format
        self.after(0, self._update_response_text, "✅ Positive Response (0x62) format:\n")
        self.after(0, self._update_response_text, "   Byte 0: 0x10 (First Frame)\n")
        self.after(0, self._update_response_text, "   Byte 1: Total data length (n)\n")
        self.after(0, self._update_response_text, "   Byte 2: 0x62 (Positive response to service 0x22)\n")
        self.after(0, self._update_response_text, "   Byte 3-4: DID (2 bytes, e.g., F1 90)\n")
        self.after(0, self._update_response_text, "   Byte 5+: Data payload\n\n")

        # Negative Response (0x7F) format
        self.after(0, self._update_response_text, "❌ Negative Response (0x7F) format:\n")
        self.after(0, self._update_response_text, "   Byte 0: 0x10 (First Frame)\n")
        self.after(0, self._update_response_text, "   Byte 1: 0x03 (Length)\n")
        self.after(0, self._update_response_text, "   Byte 2: 0x7F (Negative response)\n")
        self.after(0, self._update_response_text, "   Byte 3: Requested service (e.g., 0x22)\n")
        self.after(0, self._update_response_text, "   Byte 4: NRC (Negative Response Code)\n\n")

        # Common NRC codes
        self.after(0, self._update_response_text, "🔧 Common NRC Codes:\n")
        nrc_codes = {
            0x11: "0x11 - Service not supported",
            0x12: "0x12 - Sub-function not supported",
            0x13: "0x13 - Incorrect message length or format",
            0x22: "0x22 - Conditions not correct",
            0x31: "0x31 - Request out of range",
            0x33: "0x33 - Security access denied",
            0x35: "0x35 - Invalid key",
            0x78: "0x78 - Response pending"
        }

        for code, desc in nrc_codes.items():
            self.after(0, self._update_response_text, f"   {desc}\n")

        self.after(0, self._update_response_text, "="*70 + "\n")

    def _decode_did_data(self, did_hex, data_bytes):
        """Decode specific DID data"""
        did_map = {
            "F190": "VIN (Vehicle Identification Number)",
            "F180": "Boot Software ID",
            "F181": "Application Software ID",
            "F186": "Active Session",
            "F187": "Spare Part Number",
            "F188": "ECU SW Number",
            "F198": "Repair Shop Code",
            "F18C": "ECU Serial Number"
        }

        did_name = did_map.get(did_hex.upper(), "Unknown DID")
        self.after(0, self._update_response_text, f"📝 DID 0x{did_hex}: {did_name}\n")

        # Decode based on DID type
        if did_hex.upper() == "F190":  # VIN
            # VIN is ASCII encoded
            ascii_data = ""
            for byte in data_bytes:
                if 32 <= byte <= 126:  # Printable ASCII
                    ascii_data += chr(byte)
                elif byte == 0x00:
                    ascii_data += "·"
                else:
                    ascii_data += f"\\x{byte:02X}"

            self.after(0, self._update_response_text, f"   Decoded VIN: {ascii_data}\n")
            self.after(0, self._update_response_text, f"   Raw hex: {' '.join(f'{b:02X}' for b in data_bytes)}\n")

        elif did_hex.upper() in ["F180", "F181", "F187", "F188", "F18C"]:
            # Software IDs are usually ASCII
            ascii_data = ""
            hex_data = []
            for byte in data_bytes:
                if 32 <= byte <= 126:  # Printable ASCII
                    ascii_data += chr(byte)
                    hex_data.append(f"{byte:02X}")
                elif byte == 0x00:
                    ascii_data += "·"
                    hex_data.append("00")
                else:
                    ascii_data += f"\\x{byte:02X}"
                    hex_data.append(f"{byte:02X}")

            if ascii_data:
                self.after(0, self._update_response_text, f"   ASCII: {ascii_data}\n")
            self.after(0, self._update_response_text, f"   Hex: {' '.join(hex_data)}\n")

        else:
            # Generic hex display
            self.after(0, self._update_response_text, f"   Hex data: {' '.join(f'{b:02X}' for b in data_bytes)}\n")

            # Try ASCII conversion anyway
            ascii_data = ""
            for byte in data_bytes:
                if 32 <= byte <= 126:
                    ascii_data += chr(byte)
                elif byte == 0x00:
                    ascii_data += "·"
                else:
                    ascii_data += "."

            if ascii_data.replace(".", "").replace("·", ""):
                self.after(0, self._update_response_text, f"   ASCII attempt: {ascii_data}\n")

    def _decode_uds_bytes(self, data_bytes):
        """Decode UDS protocol bytes"""
        if not data_bytes:
            return

        self.after(0, self._update_response_text, "\n🔬 UDS Protocol Analysis:\n")

        # Check first byte for frame type
        first_byte = data_bytes[0]

        if first_byte == 0x10:  # First frame
            self.after(0, self._update_response_text, "   Frame Type: First Frame (Multi-frame response)\n")

            if len(data_bytes) >= 2:
                total_len = data_bytes[1]
                self.after(0, self._update_response_text, f"   Total Data Length: {total_len} bytes\n")

            if len(data_bytes) >= 3:
                service = data_bytes[2]
                service_name = {
                    0x62: "Positive Response to Read Data By Identifier (0x22)",
                    0x7F: "Negative Response",
                    0x67: "Positive Response to Security Access (0x27)",
                    0x6E: "Positive Response to Tester Present (0x3E)"
                }.get(service, f"Unknown service 0x{service:02X}")
                self.after(0, self._update_response_text, f"   Service: 0x{service:02X} ({service_name})\n")

                if service == 0x62 and len(data_bytes) >= 5:
                    # Positive response to DID read
                    did = (data_bytes[3] << 8) | data_bytes[4]
                    self.after(0, self._update_response_text, f"   DID: 0x{did:04X}\n")

                    # Extract data payload
                    if len(data_bytes) > 5:
                        payload = data_bytes[5:]
                        self.after(0, self._update_response_text, f"   Payload ({len(payload)} bytes): {' '.join(f'{b:02X}' for b in payload)}\n")

                        # Try to decode payload
                        ascii_payload = ""
                        for byte in payload:
                            if 32 <= byte <= 126:
                                ascii_payload += chr(byte)
                            elif byte == 0x00:
                                ascii_payload += "·"
                            else:
                                ascii_payload += "."

                        if ascii_payload.replace(".", "").replace("·", ""):
                            self.after(0, self._update_response_text, f"   Payload ASCII: {ascii_payload}\n")

                elif service == 0x7F and len(data_bytes) >= 5:
                    # Negative response
                    failed_service = data_bytes[3]
                    nrc = data_bytes[4]

                    nrc_codes = {
                        0x11: "Service not supported",
                        0x12: "Sub-function not supported",
                        0x13: "Incorrect message length or format",
                        0x22: "Conditions not correct",
                        0x31: "Request out of range",
                        0x33: "Security access denied",
                        0x35: "Invalid key",
                        0x78: "Response pending"
                    }

                    self.after(0, self._update_response_text, f"   Failed Service: 0x{failed_service:02X}\n")
                    self.after(0, self._update_response_text, f"   NRC: 0x{nrc:02X} - {nrc_codes.get(nrc, 'Unknown error')}\n")

        elif (first_byte & 0xF0) == 0x20:  # Continuation frame
            frame_num = first_byte & 0x0F
            self.after(0, self._update_response_text, f"   Frame Type: Continuation Frame {frame_num}\n")

            # Extract data
            payload = data_bytes[1:] if len(data_bytes) > 1 else []
            if payload:
                self.after(0, self._update_response_text, f"   Payload ({len(payload)} bytes): {' '.join(f'{b:02X}' for b in payload)}\n")

                # Try ASCII
                ascii_payload = ""
                for byte in payload:
                    if 32 <= byte <= 126:
                        ascii_payload += chr(byte)
                    elif byte == 0x00:
                        ascii_payload += "·"
                    else:
                        ascii_payload += "."

                if ascii_payload.replace(".", "").replace("·", ""):
                    self.after(0, self._update_response_text, f"   Payload ASCII: {ascii_payload}\n")

        elif first_byte == 0x7F:  # Negative response (single frame)
            self.after(0, self._update_response_text, "   Frame Type: Negative Response (Single Frame)\n")

            if len(data_bytes) >= 3:
                failed_service = data_bytes[1]
                nrc = data_bytes[2]

                nrc_codes = {
                    0x11: "Service not supported",
                    0x12: "Sub-function not supported",
                    0x13: "Incorrect message length or format",
                    0x22: "Conditions not correct",
                    0x31: "Request out of range",
                    0x33: "Security access denied",
                    0x35: "Invalid key",
                    0x78: "Response pending"
                }

                self.after(0, self._update_response_text, f"   Failed Service: 0x{failed_service:02X}\n")
                self.after(0, self._update_response_text, f"   NRC: 0x{nrc:02X} - {nrc_codes.get(nrc, 'Unknown error')}\n")

        else:
            # Single frame response
            if len(data_bytes) >= 3:
                service = data_bytes[0]
                did_high = data_bytes[1]
                did_low = data_bytes[2]
                did = (did_high << 8) | did_low

                service_name = {
                    0x62: "Positive Response to Read Data By Identifier (0x22)",
                }.get(service, f"Unknown service 0x{service:02X}")

                self.after(0, self._update_response_text, f"   Service: 0x{service:02X} ({service_name})\n")
                self.after(0, self._update_response_text, f"   DID: 0x{did:04X}\n")

                if len(data_bytes) > 3:
                    payload = data_bytes[3:]
                    self.after(0, self._update_response_text, f"   Payload ({len(payload)} bytes): {' '.join(f'{b:02X}' for b in payload)}\n")

                    # Try ASCII
                    ascii_payload = ""
                    for byte in payload:
                        if 32 <= byte <= 126:
                            ascii_payload += chr(byte)
                        elif byte == 0x00:
                            ascii_payload += "·"
                        else:
                            ascii_payload += "."

                    if ascii_payload.replace(".", "").replace("·", ""):
                        self.after(0, self._update_response_text, f"   Payload ASCII: {ascii_payload}\n")
            else:
                self.after(0, self._update_response_text, f"   Unknown frame format\n")
                self.after(0, self._update_response_text, f"   Raw bytes: {' '.join(f'{b:02X}' for b in data_bytes)}\n")

    def _update_response_text(self, text):
        """Update response textbox with new text"""
        self.response_text.insert("end", text)
        self.response_text.see("end")

    def load_uds_example(self, example_type):
        """Load example UDS responses"""
        examples = {
            "vin": """vcan0  7E8   [8]  10 14 62 F1 90 46 55 43
vcan0  7E8   [8]  21 59 54 45 43 48 2D 56
vcan0  7E8   [8]  22 49 4E 2D 30 30 30 31""",

            "boot": """vcan0  7E8   [8]  10 0E 62 F1 80 46 55 43
vcan0  7E8   [8]  21 59 2D 42 4F 4F 54 2D
vcan0  7E8   [8]  22 56 31 2E 30 00 00 00""",

            "app": """vcan0  7E8   [8]  10 10 62 F1 81 46 55 43
vcan0  7E8   [8]  21 59 2D 41 50 50 2D 56
vcan0  7E8   [8]  22 32 2E 35 2E 31 00 00""",

            "serial": """vcan0  7E8   [8]  10 12 62 F1 8C 53 4E 2D
vcan0  7E8   [8]  21 46 55 43 59 2D 38 38
vcan0  7E8   [8]  22 38 38 38 38 38 38 38"""
        }

        if example_type in examples:
            self.uds_response_entry.delete("1.0", "end")
            self.uds_response_entry.insert("1.0", examples[example_type])
            messagebox.showinfo("Example Loaded", f"Loaded {example_type.upper()} response example")

    def clear_uds_input(self):
        """Clear the UDS response input"""
        self.uds_response_entry.delete("1.0", "end")
        self.results_text.delete("1.0", "end")

    def analyze_uds_response(self):
        """Analyze UDS response and decode the data"""
        raw_text = self.uds_response_entry.get("1.0", "end-1c").strip()

        if not raw_text:
            messagebox.showwarning("Warning", "Please paste UDS response data")
            return

        lines = raw_text.split('\n')
        frames = []

        # Parse each line
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for data bytes in typical candump format
            if '[' in line and ']' in line:
                # Extract data bytes part (after the closing bracket)
                parts = line.split(']')
                if len(parts) > 1:
                    hex_part = parts[1].strip()
                    if hex_part:
                        try:
                            # Convert hex string to bytes
                            bytes_list = [int(b, 16) for b in hex_part.split() if b]
                            if bytes_list:  # Only add if we found bytes
                                frames.append(bytes_list)
                        except ValueError as e:
                            continue

        if not frames:
            # Try alternative format - just hex bytes
            all_bytes = []
            for line in lines:
                try:
                    bytes_list = [int(b, 16) for b in line.split() if len(b) == 2]
                    if bytes_list:
                        all_bytes.extend(bytes_list)
                except:
                    continue

            if all_bytes:
                # Group bytes into frames of 8
                for i in range(0, len(all_bytes), 8):
                    frames.append(all_bytes[i:i+8])

        if not frames:
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", "❌ No valid data found. Please check format.\n\nExpected format:\nvcan0  7E8   [8]  10 14 62 F1 90 46 55 43")
            return

        # Analyze frames
        result = "=" * 60 + "\n"
        result += "               UDS RESPONSE ANALYZER\n"
        result += "=" * 60 + "\n\n"

        total_ascii = ""

        for i, frame_bytes in enumerate(frames):
            result += f"📦 FRAME {i+1} ({len(frame_bytes)} bytes):\n"
            result += f"   Hex: {' '.join(f'{b:02X}' for b in frame_bytes)}\n"

            # Check first byte for frame type
            first_byte = frame_bytes[0]

            if first_byte == 0x10:  # First frame
                result += "   Type: First Frame (Multi-frame response)\n"

                if len(frame_bytes) >= 2:
                    total_len = frame_bytes[1]
                    result += f"   Total Data Length: {total_len} bytes\n"

                if len(frame_bytes) >= 3:
                    service = frame_bytes[2]
                    service_name = {
                        0x62: "Read Data By Identifier (0x22)",
                        0x7F: "Negative Response",
                        0x67: "Security Access (0x27)",
                        0x6E: "Tester Present (0x3E)"
                    }.get(service, f"Unknown service 0x{service:02X}")
                    result += f"   Service: 0x{service:02X} ({service_name})\n"

                if len(frame_bytes) >= 5:
                    did = (frame_bytes[3] << 8) | frame_bytes[4]
                    did_info = {
                        0xF190: "VIN (Vehicle Identification Number)",
                        0xF180: "Boot Software ID",
                        0xF181: "Application Software ID",
                        0xF187: "Spare Part Number",
                        0xF18C: "ECU Serial Number",
                        0xF186: "Active Session",
                        0xF188: "ECU SW Number",
                        0xF198: "Repair Shop Code"
                    }

                    result += f"   DID: 0x{did:04X}"
                    if did in did_info:
                        result += f" - {did_info[did]}\n"
                    else:
                        result += f" (Unknown DID)\n"

                # Extract ASCII data from first frame
                if len(frame_bytes) > 5:
                    ascii_part = ""
                    for byte in frame_bytes[5:]:
                        if 32 <= byte <= 126:  # Printable ASCII
                            ascii_part += chr(byte)
                        elif byte == 0x00:
                            ascii_part += "·"  # Show null as dot
                        else:
                            ascii_part += f"\\x{byte:02X}"

                    if ascii_part:
                        result += f"   Data: {ascii_part}\n"
                        total_ascii += ascii_part.replace("·", "")

            elif (first_byte & 0xF0) == 0x20:  # Continuation frame
                frame_num = first_byte & 0x0F
                result += f"   Type: Continuation Frame {frame_num}\n"

                # Extract ASCII data from continuation frame
                ascii_part = ""
                for byte in frame_bytes[1:]:
                    if 32 <= byte <= 126:  # Printable ASCII
                        ascii_part += chr(byte)
                        total_ascii += chr(byte)
                    elif byte == 0x00:
                        ascii_part += "·"
                    else:
                        ascii_part += f"\\x{byte:02X}"
                        total_ascii += f"\\x{byte:02X}"

                if ascii_part:
                    result += f"   Data: {ascii_part}\n"

            elif first_byte == 0x7F:  # Negative response
                result += "   Type: Negative Response\n"
                if len(frame_bytes) >= 3:
                    failed_service = frame_bytes[1]
                    nrc = frame_bytes[2]
                    nrc_codes = {
                        0x11: "Service not supported",
                        0x12: "Sub-function not supported",
                        0x13: "Incorrect message length or format",
                        0x22: "Conditions not correct",
                        0x31: "Request out of range",
                        0x33: "Security access denied",
                        0x35: "Invalid key",
                        0x78: "Response pending"
                    }
                    result += f"   Failed Service: 0x{failed_service:02X}\n"
                    result += f"   NRC: 0x{nrc:02X} - {nrc_codes.get(nrc, 'Unknown error')}\n"

            else:
                result += f"   Type: Unknown (0x{first_byte:02X})\n"

            result += "\n"

        # Show complete decoded message
        if total_ascii:
            result += "-" * 60 + "\n"
            result += "📊 COMPLETE DECODED MESSAGE:\n\n"

            # Clean up the ASCII (remove null bytes and non-printable)
            clean_ascii = ""
            hex_representation = ""

            for i, char in enumerate(total_ascii):
                if char == "·":
                    continue
                elif len(char) > 1:  # \xXX format
                    hex_representation += char + " "
                elif 32 <= ord(char) <= 126:  # Printable ASCII
                    clean_ascii += char
                    hex_representation += f"{ord(char):02X} "
                else:
                    hex_representation += f"\\x{ord(char):02X} "

            if clean_ascii:
                result += f"   ASCII: {clean_ascii}\n"

            if hex_representation.strip():
                result += f"   Hex: {hex_representation.strip()}\n"

        # Show UDS quick reference
        result += "\n" + "=" * 60 + "\n"
        result += "📚 UDS QUICK REFERENCE:\n\n"
        result += "Service 0x22 - Read Data By Identifier\n"
        result += "  • Positive Response: 0x62\n"
        result += "  • First Frame: 0x10 XX 62 F1 90 ...\n"
        result += "  • Continuation: 0x2N (N = frame number)\n\n"
        result += "Common DIDs:\n"
        result += "  • 0xF190 - VIN\n"
        result += "  • 0xF180 - Boot Software ID\n"
        result += "  • 0xF181 - Application Software ID\n"
        result += "  • 0xF18C - ECU Serial Number\n"
        result += "=" * 60

        # Display results
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", result)
    def run_doip(self):
        """Run DoIP with optional interface"""
        cmd = ["doip", "discovery"]
        if self.doip_use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Advanced")

    def run_xcp(self):
        """Run XCP with optional interface"""
        xcp_id = self.xcp_id.get().strip()
        if not xcp_id:
            messagebox.showerror("Error", "Please enter an XCP ID")
            return

        cmd = ["xcp", "info", xcp_id]
        if self.xcp_use_interface.get():
            cmd.extend(["-i", "vcan0"])
        self.app.run_command(cmd, "Advanced")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))
        results_font_size = max(11, min(16, int(13 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))

        self.doip_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.xcp_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.did_read_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.show_response_btn.configure(height=btn_height, font=("Arial", button_font_size))
        self.analyze_btn.configure(height=btn_height + 5, font=("Arial", button_font_size))
        self.load_vin_example_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1))
        self.load_boot_example_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1))
        self.clear_btn.configure(height=small_btn_size, font=("Arial", button_font_size-1))
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)

        # Configure entry fields
        font_cfg = ("Arial", label_font_size)
        self.xcp_id.configure(height=entry_height, font=font_cfg)
        self.uds_target_id.configure(height=entry_height, font=font_cfg)
        self.uds_response_id.configure(height=entry_height, font=font_cfg)
        self.custom_did_entry.configure(height=entry_height, font=font_cfg)
        self.start_did_entry.configure(height=entry_height, font=font_cfg)
        self.end_did_entry.configure(height=entry_height, font=font_cfg)
        self.timeout_entry.configure(height=entry_height, font=font_cfg)

        # Configure text areas
        self.uds_response_entry.configure(font=("Consolas", results_font_size))
        self.results_text.configure(font=("Consolas", results_font_size))
        self.response_text.configure(font=("Consolas", results_font_size))

        # Update dropdowns
        self.did_select.configure(height=entry_height, font=font_cfg,
                                 dropdown_font=("Arial", label_font_size))

        # Configure checkboxes
        self.doip_interface_check.configure(font=("Arial", checkbox_font_size))
        self.xcp_interface_check.configure(font=("Arial", checkbox_font_size))
        self.did_interface_check.configure(font=("Arial", checkbox_font_size))

        # Scale tabview fonts
        if hasattr(self.tabs, '_segmented_button'):
            self.tabs._segmented_button.configure(font=("Arial", label_font_size))

class SendFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.head_frame, text="Send & Replay", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        # Buttons
        self.help_btn = ctk.CTkButton(self.head_frame, text="❓", fg_color="#f39c12", text_color="white",
                      command=lambda: app.show_module_help("send"))
        self.help_btn.pack(side="right", padx=5)

        self.report_btn = ctk.CTkButton(self.head_frame, text="📥 Report (PDF)",
                      command=lambda: app.save_module_report("SendReplay"))
        self.report_btn.pack(side="right", padx=5)

        # Main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, pady=10)

        # Send Type Selection
        ctk.CTkLabel(self.main_container, text="Send Type:").pack(pady=(10, 5))

        # CHANGE: Unified colors
        self.send_type = ctk.CTkOptionMenu(self.main_container,
                                         values=["message", "file"],
                                         command=self.on_send_type_change,
                                         fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.send_type.pack(pady=5, fill="x", padx=20)
        self.send_type.set("message")

        # Message Frame
        self.message_frame = ctk.CTkFrame(self.main_container)
        self.message_frame.pack(fill="x", pady=10, padx=20)

        # DBC Message Selection (for message type)
        ctk.CTkLabel(self.message_frame, text="DBC Message (Optional):").pack(pady=(10, 5))
        self.msg_select = ctk.CTkOptionMenu(self.message_frame,
                                          values=["No DBC Loaded"],
                                          command=self.on_msg_select,
                                          fg_color="#1f538d", button_color="#1f538d", button_hover_color="#14375e")
        self.msg_select.pack(pady=5, fill="x")

        # Manual ID and Data Entry
        ctk.CTkLabel(self.message_frame, text="Manual CAN Frame (ID#DATA):").pack(pady=(10, 5))
        self.manual_frame = ctk.CTkEntry(self.message_frame,
                                       placeholder_text="e.g., 0x7a0#c0.ff.ee.00.11.22.33.44 or 123#de.ad.be.ef")
        self.manual_frame.pack(pady=5, fill="x")

        # Additional Options for message
        self.message_options_frame = ctk.CTkFrame(self.message_frame, fg_color="transparent")
        self.message_options_frame.pack(fill="x", pady=5)

        # Delay option
        ctk.CTkLabel(self.message_options_frame, text="Delay (seconds):").grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.delay_entry = ctk.CTkEntry(self.message_options_frame, placeholder_text="0.5", width=80)
        self.delay_entry.grid(row=0, column=1, padx=(0, 20), sticky="w")

        # Periodic option
        self.periodic_var = ctk.BooleanVar()
        self.periodic_check = ctk.CTkCheckBox(self.message_options_frame, text="Periodic send",
                                            variable=self.periodic_var)
        self.periodic_check.grid(row=0, column=2, padx=20, sticky="w")

        self.message_options_frame.grid_columnconfigure(2, weight=1)

        # File Frame (initially hidden)
        self.file_frame = ctk.CTkFrame(self.main_container)

        ctk.CTkLabel(self.file_frame, text="CAN Dump File:").pack(pady=(10, 5))

        self.file_selection_frame = ctk.CTkFrame(self.file_frame, fg_color="transparent")
        self.file_selection_frame.pack(fill="x", pady=5)

        self.file_path_entry = ctk.CTkEntry(self.file_selection_frame, placeholder_text="Select CAN dump file...")
        self.file_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.browse_file_btn = ctk.CTkButton(self.file_selection_frame, text="Browse",
                                           command=self.browse_file, width=80)
        self.browse_file_btn.pack(side="right")

        # File options
        ctk.CTkLabel(self.file_frame, text="File Send Delay (seconds):").pack(pady=(10, 5))
        self.file_delay_entry = ctk.CTkEntry(self.file_frame, placeholder_text="0.2")
        self.file_delay_entry.pack(pady=5, fill="x")

        # Interface checkbox (common for both)
        self.interface_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.interface_frame.pack(fill="x", pady=10, padx=20)

        self.use_interface = ctk.BooleanVar(value=True)
        self.interface_check = ctk.CTkCheckBox(self.interface_frame, text="Use -i vcan0 interface",
                                             variable=self.use_interface)
        self.interface_check.pack()

        # Send Button
        self.send_btn = ctk.CTkButton(self.main_container, text="Send",
                                    command=self.run_send, fg_color="#27ae60")
        self.send_btn.pack(pady=20, fill="x", padx=20)

        # Initialize UI state
        self.on_send_type_change("message")

    def on_send_type_change(self, selection):
        """Show/hide appropriate frames based on send type selection"""
        if selection == "message":
            self.message_frame.pack(fill="x", pady=10, padx=20)
            self.file_frame.pack_forget()
            self.send_btn.configure(text="Send Message")
        else:  # file
            self.message_frame.pack_forget()
            self.file_frame.pack(fill="x", pady=10, padx=20)
            self.send_btn.configure(text="Send File")

    def on_msg_select(self, selection):
        """When DBC message is selected, populate manual field with ID"""
        hex_id = self.app.get_id_by_name(selection)
        if hex_id:
            # Keep existing data if any, just update ID
            current_text = self.manual_frame.get()
            if "#" in current_text:
                # Replace ID part
                data_part = current_text.split("#")[1]
                self.manual_frame.delete(0, "end")
                self.manual_frame.insert(0, f"{hex_id}#{data_part}")
            else:
                # Just set ID
                self.manual_frame.delete(0, "end")
                self.manual_frame.insert(0, f"{hex_id}#")

    def browse_file(self):
        """Browse for CAN dump file"""
        filename = filedialog.askopenfilename(
            title="Select CAN Dump File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, filename)

    def run_send(self):
        """Execute send command based on selected type and options"""
        send_type = self.send_type.get()
        cmd = ["send"]

        # Add interface if selected
        if self.use_interface.get():
            cmd.extend(["-i", "vcan0"])

        if send_type == "message":
            # Build message command
            manual_input = self.manual_frame.get().strip()
            if not manual_input:
                messagebox.showerror("Error", "Please enter CAN frame in format: ID#DATA")
                return

            # Add delay if specified
            delay = self.delay_entry.get().strip()
            if delay:
                try:
                    float(delay)  # Validate it's a number
                    cmd.extend(["-d", delay])
                except ValueError:
                    messagebox.showerror("Error", "Delay must be a valid number")
                    return

            # Add periodic flag if selected
            if self.periodic_var.get():
                cmd.extend(["-p"])

            # Add the message
            cmd.extend(["message", manual_input])

        else:  # file type
            file_path = self.file_path_entry.get().strip()
            if not file_path:
                messagebox.showerror("Error", "Please select a CAN dump file")
                return

            if not os.path.exists(file_path):
                messagebox.showerror("Error", "Selected file does not exist")
                return

            # Add file delay if specified
            file_delay = self.file_delay_entry.get().strip()
            if file_delay:
                try:
                    float(file_delay)  # Validate it's a number
                    cmd.extend(["-d", file_delay])
                except ValueError:
                    messagebox.showerror("Error", "File delay must be a valid number")
                    return

            # Add file command
            cmd.extend(["file", file_path])

        self.app.run_command(cmd, "SendReplay")

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        label_font_size = max(12, min(18, int(14 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        checkbox_font_size = max(12, min(18, int(14 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button and entry sizes
        btn_height = max(35, min(55, int(45 * scale_factor)))
        entry_height = max(30, min(45, int(35 * scale_factor)))
        small_btn_size = max(35, min(60, int(45 * scale_factor)))
        btn_width = max(120, min(200, int(150 * scale_factor)))

        self.send_btn.configure(height=btn_height, font=("Arial", button_font_size), corner_radius=8)
        self.browse_file_btn.configure(height=btn_height, font=("Arial", button_font_size-1), width=btn_width)
        self.help_btn.configure(height=small_btn_size, width=small_btn_size, font=("Arial", button_font_size))
        self.report_btn.configure(height=small_btn_size, font=("Arial", button_font_size-2), width=btn_width)

        font_cfg = ("Arial", label_font_size)

        # Update entry and dropdown sizes
        self.send_type.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.msg_select.configure(height=entry_height, font=font_cfg, dropdown_font=font_cfg)
        self.manual_frame.configure(height=entry_height, font=font_cfg)
        self.delay_entry.configure(height=entry_height, font=font_cfg)
        self.file_path_entry.configure(height=entry_height, font=font_cfg)
        self.file_delay_entry.configure(height=entry_height, font=font_cfg)
        self.interface_check.configure(font=("Arial", checkbox_font_size))
        self.periodic_check.configure(font=("Arial", checkbox_font_size))

    def update_msg_list(self, names):
        self.msg_select.configure(values=names)
        self.msg_select.set("Select Message")

class MonitorFrame(ScalableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.is_monitoring = False

        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x", pady=10)

        self.title_label = ctk.CTkLabel(self.head_frame, text="Traffic Monitor", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left")

        self.save_btn = ctk.CTkButton(self.head_frame, text="📥 Save CSV", command=self.save_monitor)
        self.save_btn.pack(side="right")

        self.ctl_frame = ctk.CTkFrame(self)
        self.ctl_frame.pack(fill="x", pady=5)

        self.sim_btn = ctk.CTkButton(self.ctl_frame, text="▶ Simulate", command=self.toggle_sim, fg_color="#27ae60")
        self.sim_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(self.ctl_frame, text="🗑 Clear", command=self.clear, fg_color="gray30")
        self.clear_btn.pack(side="right")

        self.cols = ["Time", "ID", "Name", "Signals", "Raw"]
        self.header = ctk.CTkFrame(self, fg_color="#111")
        self.header.pack(fill="x")
        for i, c in enumerate(self.cols):
            lbl = ctk.CTkLabel(self.header, text=c, font=("Arial", 11, "bold"))
            lbl.grid(row=0, column=i, sticky="ew", padx=2)
            self.header.grid_columnconfigure(i, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        self.scroll.pack(fill="both", expand=True)

    def _apply_scaling(self, scale_factor):
        """Apply responsive scaling to all elements"""
        # Font sizes
        title_font_size = max(20, min(32, int(24 * scale_factor)))
        button_font_size = max(12, min(18, int(14 * scale_factor)))
        header_font_size = max(10, min(16, int(12 * scale_factor)))

        # Update fonts
        self.title_label.configure(font=("Arial", title_font_size, "bold"))

        # Update button sizes
        btn_height = max(30, min(50, int(40 * scale_factor)))
        btn_width = max(100, min(160, int(120 * scale_factor)))
        small_btn_width = max(60, min(100, int(80 * scale_factor)))

        self.save_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.sim_btn.configure(height=btn_height, font=("Arial", button_font_size), width=btn_width)
        self.clear_btn.configure(height=btn_height, font=("Arial", button_font_size), width=small_btn_width)

        # Update header font
        for widget in self.header.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(font=("Arial", header_font_size, "bold"))

        # Update header height
        header_height = max(25, min(40, int(30 * scale_factor)))
        self.header.configure(height=header_height)

    def add_row(self, aid, data):
        if len(self.scroll.winfo_children()) > 60: self.scroll.winfo_children()[0].destroy()
        vals = [time.strftime("%H:%M:%S"), hex(aid), "Unknown", "---", " ".join(f"{b:02X}" for b in data)]

        if self.app.dbc_db:
            try:
                m = self.app.dbc_db.get_message_by_frame_id(aid)
                if m:
                    vals[2] = m.name
                    vals[3] = str(m.decode(data))
            except: pass

        row = ctk.CTkFrame(self.scroll, fg_color=("gray20", "gray15"))
        row.pack(fill="x", pady=1)
        for i, v in enumerate(vals):
            ctk.CTkLabel(row, text=v, font=("Consolas", 10), anchor="w").grid(row=0, column=i, sticky="ew", padx=2)
            row.grid_columnconfigure(i, weight=1)

    def save_monitor(self):
        fn = filedialog.asksaveasfilename(defaultextension=".csv")
        if fn:
            with open(fn, "w") as f:
                f.write("Time,ID,Name,Signals,Raw\n")
                for row in self.scroll.winfo_children():
                    cols = [w.cget("text") for w in row.winfo_children() if isinstance(w, ctk.CTkLabel)]
                    f.write(",".join(cols) + "\n")

    def clear(self):
        for w in self.scroll.winfo_children(): w.destroy()

    def toggle_sim(self):
        if not self.is_monitoring:
            self.is_monitoring = True
            threading.Thread(target=self._sim, daemon=True).start()
        else: self.is_monitoring = False

    def _sim(self):
        while self.is_monitoring:
            if self.app.dbc_db and self.app.dbc_db.messages:
                m = random.choice(self.app.dbc_db.messages)
                b = bytes([random.getrandbits(8) for _ in range(m.length)])
                self.after(0, lambda i=m.frame_id, d=b: self.add_row(i, d))
            else:
                b = bytes([random.getrandbits(8) for _ in range(8)])
                self.after(0, lambda i=random.randint(0x100, 0x500), d=b: self.add_row(i, d))
            time.sleep(0.2)

if __name__ == "__main__":
    app = FucyfuzzApp()
    app.mainloop()
