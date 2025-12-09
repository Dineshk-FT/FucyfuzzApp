# report_generators.py
import os
from datetime import datetime
from collections import defaultdict
import csv
from tkinter import messagebox
import numpy as np
import time
import re
import traceback
from tkinter import filedialog


# ReportLab imports (optional)
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
    REPORTLAB_AVAILABLE = True
    reportlab_styles = getSampleStyleSheet()
except Exception:
    REPORTLAB_AVAILABLE = False
    # Placeholders to avoid NameErrors if not installed
    SimpleDocTemplate = Paragraph = Spacer = PageBreak = Table = TableStyle = Preformatted = ListFlowable = ListItem = KeepTogether = None
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
    reportlab_styles = None


# ------------------------------
# Custom TOC DocTemplate (restored)
# ------------------------------
class TOCDocTemplate(SimpleDocTemplate):
    """DocTemplate with automatic TOC entries and PDF bookmarks"""
    def __init__(self, filename, **kw):
        super().__init__(filename, **kw)
        self.toc_entries = []
        self.bookmark_counter = 0

    def afterFlowable(self, flowable):
        """Register TOC entries and PDF bookmarks based on style names."""
        try:
            if hasattr(flowable, 'style') and hasattr(flowable.style, 'name'):
                style_name = flowable.style.name
                text = flowable.getPlainText() if hasattr(flowable, 'getPlainText') else str(flowable)

                # Level 1 header
                if style_name == 'ModuleHeader':
                    self.notify('TOCEntry', (0, text, self.page))
                    key = f"h1_{self.bookmark_counter}"
                    self.canv.bookmarkPage(key)
                    self.canv.addOutlineEntry(text, key, 0, False)
                    self.bookmark_counter += 1

                # Level 2 header
                elif style_name == 'ResultHeader':
                    self.notify('TOCEntry', (1, text, self.page))
                    key = f"h2_{self.bookmark_counter}"
                    self.canv.bookmarkPage(key)
                    self.canv.addOutlineEntry(text, key, 1, False)
                    self.bookmark_counter += 1
        except Exception:
            # Keep quiet if something goes wrong during TOC creation
            pass


# ------------------------------
# Minimal helper base for consistent header/footer and styles
# ------------------------------
class PDFBase:
    def __init__(self, app):
        self.app = app
        # Keep compatibility flag for main_app checks
        self.REPORTLAB_AVAILABLE = REPORTLAB_AVAILABLE

        # Prepare styles if ReportLab available
        if REPORTLAB_AVAILABLE:
            self.title_style = ParagraphStyle(
                'ReportTitle',
                parent=reportlab_styles['Title'],
                fontSize=28,
                alignment=1,
                spaceAfter=14,
                textColor=colors.HexColor("#222222"),
                fontName='Helvetica-Bold'
            )
            self.subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=reportlab_styles['Heading2'],
                alignment=1,
                textColor=colors.HexColor("#6c757d"),
                spaceAfter=18,
                fontName='Helvetica-Oblique'
            )
            self.module_header_style = ParagraphStyle(
                'ModuleHeader',
                parent=reportlab_styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor("#2c3e50"),
                spaceBefore=12,
                spaceAfter=8,
                leading=22,
                fontName='Helvetica-Bold'
            )
            self.result_header_style = ParagraphStyle(
                'ResultHeader',
                parent=reportlab_styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor("#2c3e50"),
                spaceBefore=8,
                spaceAfter=6,
                leading=18,
                fontName='Helvetica-Bold'
            )
            self.normal_style = ParagraphStyle(
                'NormalCustom',
                parent=reportlab_styles['Normal'],
                fontSize=10,
                leading=12,
                spaceAfter=6
            )
            self.code_style = ParagraphStyle(
                'Code',
                parent=reportlab_styles['Code'],
                fontSize=9,
                leading=11,
                backColor=colors.HexColor("#f8f9fa"),
                borderColor=colors.lightgrey,
                borderWidth=0.5,
                borderPadding=6,
                fontName='Courier'
            )
            self.toc_h1_style = ParagraphStyle(
                'TOC_H1',
                parent=reportlab_styles['Normal'],
                fontSize=12,
                leading=14,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor("#2c3e50")
            )
            self.toc_h2_style = ParagraphStyle(
                'TOC_H2',
                parent=reportlab_styles['Normal'],
                fontSize=10,
                leading=12,
                leftIndent=20,
                textColor=colors.HexColor("#34495e")
            )

    def header_footer(self, canvas, doc, title_text=None):
        """Simple header and footer"""
        canvas.saveState()
        w, h = doc.pagesize

        # Header
        if title_text:
            canvas.setFont("Helvetica-Bold", 9)
            canvas.setFillColor(colors.HexColor("#2c3e50"))
            canvas.drawString(doc.leftMargin, h - 36, title_text)

        # Timestamp right
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.gray)
        canvas.drawRightString(w - doc.rightMargin, h - 36, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Thin lines
        canvas.setStrokeColor(colors.lightgrey)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, h - 40, w - doc.rightMargin, h - 40)
        canvas.line(doc.leftMargin, 48, w - doc.rightMargin, 48)

        # Page number
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(w / 2.0, 35, f"Page {canvas.getPageNumber()}")

        canvas.restoreState()

    def ensure_reportlab(self):
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror(
                "ReportLab Missing",
                "ReportLab is required to create PDF reports.\n\nInstall with:\n\npip install reportlab"
            )
            return False
        return True


# ------------------------------
# Enhanced PDF Report (full advanced)
# ------------------------------
class EnhancedPDFReport(PDFBase):
    """
    Full advanced report with front page, TOC, risk scorecard, key findings,
    module-wise detailed logs (including execution logs), conclusion & recommendations.
    """

    def __init__(self, app_instance):
        super().__init__(app_instance)
        self.app = app_instance
        # compatibility attribute (some parts of code check instance attribute)
        self.REPORTLAB_AVAILABLE = REPORTLAB_AVAILABLE

    def _analyze_entries(self, entries):
        """
        Produce dynamic risk scorecard and key findings from entries.
        Returns:
            modules: dict(module_name -> list of entries)
            status_counts: dict counts
            risk_scorecard: list of (Metric, Status, RiskLevel)
            key_findings: list of strings
        """
        modules = defaultdict(list)
        status_counts = defaultdict(int)
        for e in entries:
            modules[e.get('module', 'Unknown')].append(e)
            st = e.get('status', '').lower()
            if 'fail' in st or 'error' in st or 'critical' in st:
                status_counts['failed'] += 1
            elif 'warn' in st or 'warning' in st:
                status_counts['warning'] += 1
            elif 'success' in st or 'passed' in st or 'ok' in st:
                status_counts['success'] += 1
            else:
                status_counts['other'] += 1

        # Risk scorecard heuristic (simple)
        risk_scorecard = [
            ('Bus Availability (DoS)', 'FAILED' if status_counts.get('failed', 0) > 0 else 'PASSED',
             'Critical' if status_counts.get('failed', 0) > 0 else 'Low'),
            ('Input Validation', 'WARNING' if status_counts.get('warning', 0) > 0 else 'PASSED',
             'High' if status_counts.get('warning', 0) > 0 else 'Low'),
            ('Diagnostic Security', 'FAILED' if self._detect_diagnostic_issues(entries) else 'PASSED',
             'High' if self._detect_diagnostic_issues(entries) else 'Low'),
            ('Protocol Compliance', 'FAILED' if self._detect_protocol_issues(entries) else 'PASSED',
             'Medium' if self._detect_protocol_issues(entries) else 'Low'),
        ]

        # Key findings — derive from failures/warnings
        key_findings = []
        if status_counts.get('failed', 0) > 0:
            key_findings.append(f"Critical: {status_counts.get('failed',0)} failed tests detected requiring immediate attention.")
        if status_counts.get('warning', 0) > 0:
            key_findings.append(f"High: {status_counts.get('warning',0)} warnings observed that may indicate potential issues.")
        # Examine entries for common patterns
        # Example: UDS reset accepted
        for e in entries:
            out = (e.get('output') or "").lower()
            if 'reset' in out and 'accepted' in out:
                key_findings.append("ECU accepted ECUReset (0x11) in default session — Security/diagnostic policy issue.")
                break

        # Add some generic notes if empty
        if not key_findings:
            key_findings.append("No major failures detected; follow-up validation recommended for edge cases.")

        return modules, status_counts, risk_scorecard, key_findings

    def _detect_diagnostic_issues(self, entries):
        for e in entries:
            out = (e.get('output') or "").lower()
            if 'ecureset' in out or '0x11' in out or 'reset accepted' in out:
                return True
        return False

    def _detect_protocol_issues(self, entries):
        for e in entries:
            out = (e.get('output') or "").lower()
            if 'bus-off' in out or 'protocol error' in out or 'crc' in out:
                return True
        return False

    def generate_pdf(self, filename=None, title="FucyFuzz Security Report", entries=None):
        """Generate the full advanced PDF with front page, TOC, risk table, module logs, and conclusions."""
        if entries is None:
            entries = getattr(self.app, 'session_history', [])

        if not self.ensure_reportlab():
            return None

        # default filename
        if filename is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filedialog.asksaveasfilename(
                title="Save PDF Report",
                defaultextension=".pdf",
                filetypes=[("PDF Report", "*.pdf")],
                initialfile=f"FucyFuzz_Report_{stamp}.pdf"
            )
            if not filename:
                return None


        try:
            modules, status_counts, risk_scorecard, key_findings = self._analyze_entries(entries)
            total_entries = len(entries)

            # Start story
            story = []

            # COVER PAGE
            story.append(Spacer(1, 2 * inch))
            story.append(Paragraph("Automotive Security Assessment Report", self.title_style))
            story.append(Paragraph("CAN Bus Fuzzing & Resilience Test", self.subtitle_style))
            story.append(Spacer(1, 0.2 * inch))

            # Cover metadata table
            cover_meta = [
                ["Target System:", getattr(self.app, 'target_system', 'Unknown')],
                ["Tooling:", getattr(self.app, 'tool_version', 'FucyFuzz')],
                ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["Report Classification:", getattr(self.app, 'classification', 'CONFIDENTIAL')]
            ]
            ctbl = Table(cover_meta, colWidths=[140, 320])
            ctbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
            ]))
            story.append(ctbl)

            story.append(Spacer(1, 0.8 * inch))

            # horizontal line
            d = Drawing(400, 1)
            d.add(Line(0, 0, 400, 0, strokeColor=colors.HexColor("#2c3e50"), strokeWidth=1.2))
            story.append(d)

            story.append(PageBreak())

            # TABLE OF CONTENTS
            story.append(Paragraph("TABLE OF CONTENTS", self.module_header_style))
            story.append(Spacer(1, 0.2 * inch))
            toc = TableOfContents()
            toc.levelStyles = [self.toc_h1_style, self.toc_h2_style]
            story.append(toc)
            story.append(PageBreak())

            # EXECUTIVE SUMMARY
            story.append(Paragraph("EXECUTIVE SUMMARY", self.module_header_style))
            story.append(Spacer(1, 0.1 * inch))

            summary_lines = [
                f"Total Tests: {total_entries}",
                f"Modules Tested: {len(modules)}",
                f"Success: {status_counts.get('success',0)}",
                f"Warnings: {status_counts.get('warning',0)}",
                f"Failures: {status_counts.get('failed',0)}",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            story.append(ListFlowable([ListItem(Paragraph(x, self.normal_style)) for x in summary_lines], bulletType='bullet', leftIndent=18))
            story.append(Spacer(1, 0.2 * inch))

            # Risk Scorecard Table
            story.append(Paragraph("RISK SCORECARD", self.result_header_style))
            rs_data = [["Metric", "Status", "Risk Level"]]
            for r in risk_scorecard:
                rs_data.append([r[0], r[1], r[2]])
            rs_tbl = Table(rs_data, colWidths=[250, 120, 120])
            rs_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2c3e50")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(rs_tbl)
            story.append(Spacer(1, 0.2 * inch))

            # Key Findings
            story.append(Paragraph("KEY FINDINGS", self.result_header_style))
            for k in key_findings:
                story.append(Paragraph(f"• {k}", self.normal_style))
            story.append(PageBreak())

            # DETAILED TECHNICAL REPORT (module-wise)
            story.append(Paragraph("DETAILED TECHNICAL REPORT & LOGS", self.module_header_style))
            story.append(Spacer(1, 0.1 * inch))

            for module_idx, (module_name, module_entries) in enumerate(modules.items()):
                # Module heading (TOC level 1)
                story.append(Paragraph(f"Module {module_idx + 1}: {module_name}", ParagraphStyle(
                    'ModuleHeader',
                    parent=reportlab_styles['Heading1'],
                    fontSize=16,
                    textColor=colors.HexColor("#2980b9"),
                    spaceBefore=12,
                    spaceAfter=6,
                    fontName='Helvetica-Bold'
                )))
                # Module summary box
                mod_success = sum(1 for e in module_entries if 'success' in e.get('status', '').lower())
                mod_total = len(module_entries)
                mod_summary = f"{mod_success} of {mod_total} tests successful ({(mod_success/mod_total*100) if mod_total else 0:.1f}% success rate)"
                story.append(Paragraph(mod_summary, self.normal_style))
                story.append(Spacer(1, 0.06 * inch))

                # Show each test with Execution Log & Analysis
                for test_idx, entry in enumerate(module_entries, start=1):
                    test_title = f"Test {test_idx}: {entry.get('command', '')[:120]}"
                    story.append(Paragraph(test_title, ParagraphStyle(
                        'ResultHeader',
                        parent=reportlab_styles['Heading2'],
                        fontSize=12,
                        textColor=colors.HexColor("#2c3e50"),
                        spaceBefore=8,
                        spaceAfter=4,
                        fontName='Helvetica-Bold'
                    )))

                    meta_table = Table([
                        ["Timestamp", entry.get('timestamp', '')],
                        ["Status", entry.get('status', '')],
                        ["Module", entry.get('module', '')],
                        ["Command", Paragraph(f"<font face='Courier'>{entry.get('command', '')}</font>", self.normal_style)]
                    ], colWidths=[110, 120, 100, 200])
                    meta_table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.lightgrey)
                    ]))
                    story.append(meta_table)
                    story.append(Spacer(1, 0.05 * inch))

                    # Execution log (preformatted)
                    output_text = entry.get('output', '') or ''
                    if len(output_text) > 8000:
                        display_out = output_text[:8000] + "\n\n[TRUNCATED - see raw logs]"
                    else:
                        display_out = output_text

                    story.append(Paragraph("<b>Execution Log:</b>", self.normal_style))
                    story.append(Preformatted(display_out, self.code_style))
                    story.append(Spacer(1, 0.15 * inch))

                    # If failure, add small recommendation
                    if 'success' not in (entry.get('status','').lower()):
                        story.append(Paragraph("<b>Recommendation:</b>", self.normal_style))
                        recs = entry.get('recommendation', None) or "Review logs, check system state, and re-run with verbose logging."
                        story.append(Paragraph(recs, self.normal_style))
                        story.append(Spacer(1, 0.1 * inch))

                # page break between modules
                story.append(PageBreak())

            # CONCLUSION & RECOMMENDATIONS
            story.append(Paragraph("CONCLUSION & RECOMMENDATIONS", self.module_header_style))
            story.append(Spacer(1, 0.1 * inch))
            conclusion_text = getattr(self.app, 'conclusion_text', None) or \
                ("The Target ECU exhibits security weaknesses identified in the tests. "
                 "Addressing the highest priority issues (listed in the risk scorecard) is recommended.")
            story.append(Paragraph(conclusion_text, self.normal_style))

            # Strategic recommendations (short)
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("Strategic Recommendations", self.result_header_style))
            recs = [
                "Implement SecOC (message authentication) for high-critical signals.",
                "Restrict UDS services while the vehicle is in motion.",
                "Harden message parsing to avoid crashes for unexpected payloads.",
                "Introduce strict input validation and bounds checking."
            ]
            for r in recs:
                story.append(Paragraph(f"• {r}", self.normal_style))

            # Appendix
            story.append(PageBreak())
            story.append(Paragraph("APPENDIX", self.module_header_style))
            story.append(Paragraph("Configuration & Metadata", self.result_header_style))
            cfg_data = [
                ["Parameter", "Value"],
                ["Working Directory", getattr(self.app, 'working_dir', 'N/A')],
                ["DBC Messages", str(len(getattr(self.app, 'dbc_messages', [])))],
                ["Generated By", "FucyFuzz Security Framework"],
                ["Generation Time", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            ]
            cfg_tbl = Table(cfg_data, colWidths=[180, 300])
            cfg_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f2f2f2")),
                ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey)
            ]))
            story.append(cfg_tbl)

            # Build the document with TOC template (multiBuild for TOC)
            doc = TOCDocTemplate(filename, pagesize=letter,
                                 rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

            doc.multiBuild(story, onFirstPage=lambda c, d: self.header_footer(c, d, title_text="FucyFuzz Report"),
                           onLaterPages=lambda c, d: self.header_footer(c, d, title_text="FucyFuzz Report"))

            # Return filename on success (no auto-open)
            messagebox.showinfo("Report Generated", f"PDF created: {filename}")
            return filename

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("PDF Generation Error", f"Failed to generate PDF:\n{str(e)}")
            return None

    def export_report_to_asc(self, filename=None, title="FucyFuzz Security Report", entries=None):
        """Export the report data to Vector ASC format."""
        if entries is None:
            entries = getattr(self.app, 'session_history', [])
        
        if filename is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filedialog.asksaveasfilename(
                title="Save ASC Report",
                defaultextension=".asc",
                filetypes=[("Vector ASC", "*.asc")],
                initialfile=f"FucyFuzz_Report_{stamp}.asc"
            )
            if not filename:
                return None

        
        try:
            modules, status_counts, risk_scorecard, key_findings = self._analyze_entries(entries)
            
            with open(filename, 'w', encoding='utf-8') as f:
                # ASC header
                f.write(f"date {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("base hex  timestamps absolute\n")
                f.write("no internal events logged\n")
                f.write("\n")
                
                # Report metadata as comments
                f.write(f"; === FucyFuzz Security Report ===\n")
                f.write(f"; Title: {title}\n")
                f.write(f"; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"; Total Tests: {len(entries)}\n")
                f.write(f"; Success: {status_counts.get('success', 0)}\n")
                f.write(f"; Warnings: {status_counts.get('warning', 0)}\n")
                f.write(f"; Failures: {status_counts.get('failed', 0)}\n")
                f.write(f"; Modules Tested: {len(modules)}\n")
                f.write("\n")
                
                # Risk scorecard as comments
                f.write("; Risk Scorecard:\n")
                for metric, status, risk_level in risk_scorecard:
                    f.write(f";   {metric}: {status} ({risk_level})\n")
                f.write("\n")
                
                # Key findings as comments
                f.write("; Key Findings:\n")
                for finding in key_findings:
                    f.write(f";   • {finding}\n")
                f.write("\n")
                
                # Extract CAN frames from logs
                f.write("; === CAN Frame Data ===\n")
                frame_counter = 0
                
                for entry in entries:
                    output_text = entry.get('output', '') or ''
                    import re
                    
                    # Look for CAN send patterns in logs
                    pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\s+\[.*?\]\s+SEND\s+ID=([0-9A-Fx]+)\s+DLC=(\d+)\s+LEN=(\d+)\s+DATA=([0-9A-F]+)'
                    matches = re.findall(pattern, output_text, re.IGNORECASE)
                    
                    for timestamp, can_id, dlc, length, data_hex in matches:
                        frame_counter += 1
                        
                        # Format timestamp for ASC
                        asc_timestamp = timestamp.replace('T', ' ').split('.')[0] + ".000"
                        
                        # Format data bytes
                        data_bytes = []
                        for i in range(0, len(data_hex), 2):
                            if i + 2 <= len(data_hex):
                                byte_hex = data_hex[i:i+2]
                                data_bytes.append(byte_hex)
                        
                        # Ensure we have DLC number of bytes
                        data_str = ' '.join(data_bytes[:int(dlc)])
                        
                        # Convert hex ID to decimal
                        if can_id.lower().startswith('0x'):
                            can_id_dec = str(int(can_id, 16))
                        else:
                            can_id_dec = can_id
                        
                        # Write ASC frame
                        f.write(f"{asc_timestamp}  Tx   {can_id_dec:>3}   {dlc}   {data_str}\n")
                
                f.write(f"\n; Total frames extracted: {frame_counter}\n")
                f.write("; === End of Report ===\n")
            
            messagebox.showinfo("ASC Export", f"Report exported to ASC format:\n{filename}")
            return filename
            
        except Exception as e:
            messagebox.showerror("ASC Export Error", f"Failed to export to ASC:\n{str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def export_report_to_mf4(self, filename=None, title="FucyFuzz Security Report", entries=None):
        """Export the report data to MDF4 format."""
        if entries is None:
            entries = getattr(self.app, 'session_history', [])
        
        if filename is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filedialog.asksaveasfilename(
                title="Save MDF4 Report",
                defaultextension=".mf4",
                filetypes=[("ASAM MDF4", "*.mf4")],
                initialfile=f"FucyFuzz_Report_{stamp}.mf4"
            )
            if not filename:
                return None

        
        try:
            # Import asammdf with error handling
            try:
                from asammdf import MDF, Signal
            except ImportError as e:
                messagebox.showerror(
                    "MDF4 Export Error",
                    f"asammdf library required for MDF4 export:\n\n"
                    f"Install with: pip install asammdf"
                )
                return None
                      
            # Prepare data arrays
            timestamps = []
            can_ids = []
            data_arrays = []  # List of byte arrays
            
            frame_counter = 0
            
            # Parse all entries for CAN frames
            for entry_idx, entry in enumerate(entries):
                output_text = entry.get('output', '') or ''
                import re
                
                # Pattern for CAN frames
                pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\s+\[.*?\]\s+SEND\s+ID=([0-9A-Fx]+)\s+DLC=(\d+)\s+LEN=(\d+)\s+DATA=([0-9A-F]+)'
                matches = re.findall(pattern, output_text, re.IGNORECASE)
                
                for timestamp_str, can_id_str, dlc_str, length_str, data_hex in matches:
                    frame_counter += 1
                    
                    # Parse CAN ID
                    if can_id_str.lower().startswith('0x'):
                        can_id = int(can_id_str, 16)
                    else:
                        can_id = int(can_id_str, 16) if 'x' in can_id_str.lower() else int(can_id_str)
                    
                    # Parse data bytes
                    data_bytes = []
                    for i in range(0, len(data_hex), 2):
                        if i + 2 <= len(data_hex):
                            byte_val = int(data_hex[i:i+2], 16)
                            data_bytes.append(byte_val)
                    
                    # Pad to 8 bytes if needed
                    while len(data_bytes) < 8:
                        data_bytes.append(0)
                    
                    # Use relative timestamp for MDF
                    # Start from 0 and increment
                    timestamps.append(frame_counter * 0.001)  # 1ms spacing
                    can_ids.append(can_id)
                    data_arrays.append(data_bytes[:8])  # First 8 bytes
            
            # If no frames found, create minimal data
            if frame_counter == 0:
                messagebox.showwarning(
                    "No CAN Data",
                    "No CAN frames found in logs. Creating minimal MDF4 file with metadata only."
                )
                # Create one dummy frame
                timestamps = [0.0]
                can_ids = [0x100]
                data_arrays = [[0] * 8]
                frame_counter = 1
            
            # Convert to numpy arrays
            timestamps_np = np.array(timestamps, dtype=np.float64)
            can_ids_np = np.array(can_ids, dtype=np.uint32)
            data_arrays_np = np.array(data_arrays, dtype=np.uint8)
            
            # Create MDF object
            mdf = MDF(version='4.10')
            
            # Create signals
            signals = []
            
            # CAN ID signal
            signals.append(Signal(
                samples=can_ids_np,
                timestamps=timestamps_np,
                name='CAN_ID',
                unit='-',
                comment='CAN Frame Identifier'
            ))
            
            # Data byte signals
            for byte_idx in range(min(8, data_arrays_np.shape[1])):
                signals.append(Signal(
                    samples=data_arrays_np[:, byte_idx],
                    timestamps=timestamps_np,
                    name=f'Data_Byte{byte_idx}',
                    unit='-',
                    comment=f'CAN Data Byte {byte_idx}'
                ))
            
            # Add metadata signals
            modules, status_counts, risk_scorecard, key_findings = self._analyze_entries(entries)
            
            # Create metadata as separate group
            meta_timestamp = np.array([0.0], dtype=np.float64)
            
            # Total tests signal
            total_tests_signal = Signal(
                samples=np.array([len(entries)], dtype=np.uint32),
                timestamps=meta_timestamp,
                name='Total_Tests',
                unit='count',
                comment='Total number of tests executed'
            )
            signals.append(total_tests_signal)
            
            # Success count signal
            success_signal = Signal(
                samples=np.array([status_counts.get('success', 0)], dtype=np.uint32),
                timestamps=meta_timestamp,
                name='Success_Count',
                unit='count',
                comment='Number of successful tests'
            )
            signals.append(success_signal)
            
            # Add all signals to MDF
            mdf.append(signals)
            
            # Set file metadata
            try:
                mdf.header.comment = (
                    f"FucyFuzz Security Report - {title}\n"
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Total Tests: {len(entries)}\n"
                    f"Success: {status_counts.get('success', 0)}\n"
                    f"Warnings: {status_counts.get('warning', 0)}\n"
                    f"Failures: {status_counts.get('failed', 0)}\n"
                    f"CAN Frames: {frame_counter}"
                )
            except:
                pass
            
            # Add file history
            try:
                if hasattr(mdf, 'add_file_history'):
                    mdf.add_file_history(f"Generated by FucyFuzz at {datetime.now().isoformat()}")
            except:
                pass
            
            # Save file
            try:
                mdf.save(filename, overwrite=True)
            except TypeError:
                mdf.save(filename)  # Older versions
            
            messagebox.showinfo("MDF4 Export", f"Report exported to MDF4 format:\n{filename}")
            return filename
            
        except Exception as e:
            error_msg = f"Failed to export to MDF4:\n{str(e)}"
            messagebox.showerror("MDF4 Export Error", error_msg)
            import traceback
            traceback.print_exc()
            return None

    def generate_all_formats(self, base_filename=None, title="FucyFuzz Security Report", entries=None):
        """Generate the report in all three formats: PDF, ASC, and MDF4."""
        if base_filename is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"FucyFuzz_Report_{stamp}"
        else:
            base_name = os.path.splitext(os.path.basename(base_filename))[0]
        
        base_dir = os.path.dirname(base_filename) if base_filename else os.getcwd()
        
        # Generate all formats
        results = {}
        
        # PDF
        pdf_file = os.path.join(base_dir, f"{base_name}.pdf")
        results['pdf'] = self.generate_pdf(pdf_file, title, entries)
        
        # ASC
        asc_file = os.path.join(base_dir, f"{base_name}.asc")
        results['asc'] = self.export_report_to_asc(asc_file, title, entries)
        
        # MDF4
        mf4_file = os.path.join(base_dir, f"{base_name}.mf4")
        results['mf4'] = self.export_report_to_mf4(mf4_file, title, entries)
        
        # Show summary
        success_count = sum(1 for v in results.values() if v is not None)
        
        if success_count > 0:
            summary = f"Generated {success_count} format(s):\n"
            for fmt, path in results.items():
                if path:
                    summary += f"• {fmt.upper()}: {os.path.basename(path)}\n"
            
            messagebox.showinfo("Report Generation Complete", summary)
        
        return results

# ------------------------------
# FailureReport (focused, minimal)
# ------------------------------
class FailureReport(PDFBase):
    def __init__(self, app_instance):
        super().__init__(app_instance)
        self.app = app_instance
        self.failures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failure_reports")
        os.makedirs(self.failures_dir, exist_ok=True)
        self.REPORTLAB_AVAILABLE = REPORTLAB_AVAILABLE

    def get_failure_entries(self, entries=None):
        if entries is None:
            entries = getattr(self.app, 'session_history', [])
        failed = []
        for e in entries:
            st = (e.get('status','') or '').lower()
            if 'fail' in st or 'error' in st or 'failed' in st:
                failed.append(e)
        return failed

    def generate_failure_report(self, filename=None, title="Failure Analysis Report"):
        failures = self.get_failure_entries()
        if not failures:
            messagebox.showinfo("No Failures", "No failed test cases found.")
            return None

        if not self.ensure_reportlab():
            return None

        if filename is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.failures_dir, f"failure_report_{stamp}.pdf")

        try:
            story = []
            story.append(Spacer(1, 1.5 * inch))
            story.append(Paragraph("FAILURE ANALYSIS REPORT", self.title_style))
            story.append(Paragraph(f"<i>{title}</i>", self.subtitle_style))
            story.append(Spacer(1, 0.2 * inch))

            summary = [
                f"Total Failures: {len(failures)}",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            story.append(ListFlowable([ListItem(Paragraph(s, self.normal_style)) for s in summary], bulletType='bullet', leftIndent=18))
            story.append(Spacer(1, 0.2 * inch))

            for idx, f in enumerate(failures, start=1):
                story.append(Paragraph(f"Failure {idx}: {f.get('command','')[:120]}", self.result_header_style))
                meta = [["Timestamp", f.get('timestamp','')], ["Module", f.get('module','')], ["Status", f.get('status','')]]
                mt = Table(meta, colWidths=[100, 380])
                mt.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f8d7da")),
                    ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
                ]))
                story.append(mt)
                story.append(Spacer(1, 0.05 * inch))

                out = f.get('output','') or ''
                if len(out) > 1200:
                    display_out = out[:1200] + "\n\n[TRUNCATED - see logs]"
                else:
                    display_out = out

                story.append(Paragraph("<b>Error Output (truncated)</b>", self.normal_style))
                story.append(Preformatted(display_out, self.code_style))
                story.append(Spacer(1, 0.1 * inch))

                fixes = self._get_suggested_fixes(self._categorize_error(out))
                if fixes:
                    story.append(Paragraph("<b>Suggested Fixes</b>", self.normal_style))
                    story.append(ListFlowable([ListItem(Paragraph(x, self.normal_style)) for x in fixes], bulletType='bullet', leftIndent=18))

                story.append(PageBreak())

            doc = SimpleDocTemplate(filename, pagesize=letter,
                                    leftMargin=72, rightMargin=72, topMargin=72, bottomMargin=72)

            doc.build(story, onFirstPage=lambda c,d: self.header_footer(c,d, title_text="Failure Report"),
                      onLaterPages=lambda c,d: self.header_footer(c,d, title_text="Failure Report"))

            messagebox.showinfo("Failure Report", f"Failure report created:\n{filename}")
            return filename

        except Exception as e:
            messagebox.showerror("Failure Report Error", f"Failed to generate PDF: {str(e)}")
            return None

    def _categorize_error(self, error_output):
        o = (error_output or "").lower()
        if 'timeout' in o:
            return 'Timeout'
        if 'connect' in o or 'connection' in o:
            return 'Connection'
        if 'permission' in o or 'access denied' in o:
            return 'Permission'
        if 'invalid' in o:
            return 'Validation'
        if 'memory' in o:
            return 'Memory'
        return 'Unexpected'

    def _get_suggested_fixes(self, error_type):
        base = [
            "Review full log for context",
            "Check permissions and paths",
            "Verify target availability",
            "Re-run test in isolated environment"
        ]
        extras = {
            "Timeout": ["Increase timeout or reduce load", "Check network latency"],
            "Connection": ["Confirm target is reachable", "Check firewall / interface"],
            "Permission": ["Run with elevated privileges or fix file permissions"],
            "Validation": ["Verify inputs and formats", "Test with known-good payloads"],
            "Memory": ["Check resource usage, reduce payload sizes"]
        }
        return extras.get(error_type, []) + base


# ------------------------------
# LogExporter — ASC and MDF4
# ------------------------------
class LogExporter:
    def __init__(self, app_instance):
        self.app = app_instance
        self.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
        os.makedirs(self.log_dir, exist_ok=True)

    def export_logs_to_asc(self, filename=None, logs=None):
        """Export logs to Vector ASC format (text)."""
        if logs is None:
            # Try to get logs from console buffer if raw_logs doesn't exist
            logs = getattr(self.app, 'full_log_buffer', [])
        
        if filename is None:
            filename = os.path.join(self.log_dir, f"fucyfuzz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.asc")

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"date {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("base hex  timestamps absolute\n")
                f.write("no internal events logged\n")
                
                # Extract CAN frames from console logs
                for line in logs:
                    if isinstance(line, str):
                        # Look for CAN frame patterns in logs
                        # Pattern: [TIMESTAMP] SEND ID=0x123 DLC=8 LEN=8 DATA=0001020304050607
                        import re
                        
                        # Try to match the pattern from your LengthAttack logs
                        match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\s+\[.*?\]\s+SEND\s+ID=([0-9A-Fx]+)\s+DLC=(\d+)\s+LEN=(\d+)\s+DATA=([0-9A-F]+)', line, re.IGNORECASE)
                        
                        if match:
                            timestamp = match.group(1)
                            can_id = match.group(2)
                            dlc = int(match.group(3))
                            data_hex = match.group(5)
                            
                            # Format data bytes
                            data_bytes = []
                            for i in range(0, len(data_hex), 2):
                                if i+2 <= len(data_hex):
                                    byte_hex = data_hex[i:i+2]
                                    data_bytes.append(byte_hex)
                            
                            # Format ASC line
                            asc_timestamp = timestamp.replace('T', ' ').split('.')[0] + ".000"
                            data_str = ' '.join(data_bytes[:dlc])
                            
                            # Convert hex ID (like 0x123) to decimal
                            if can_id.startswith('0x'):
                                can_id_dec = str(int(can_id, 16))
                            else:
                                can_id_dec = str(int(can_id, 16) if 'x' in can_id.lower() else can_id)
                            
                            f.write(f"{asc_timestamp}  Tx   {can_id_dec:>3}   {dlc}   {data_str}\n")
                            
            messagebox.showinfo("ASC Export", f"ASC exported: {filename}")
            return filename
            
        except Exception as ex:
            messagebox.showerror("ASC Export Error", f"Failed to export ASC: {str(ex)}")
            return None

    def export_logs_to_mf4(self, filename=None, logs=None):
        """Export logs to MDF4 format compatible with asammdf."""
        try:
            from asammdf import MDF, Signal
            # Check version
            import asammdf
           
        except ImportError as e:
            raise ImportError(f"asammdf not found: {e}\nInstall with: pip install asammdf")
        
        if logs is None:
            logs = getattr(self.app, 'full_log_buffer', [])
        
        if filename is None:
            filename = os.path.join(self.log_dir, f"fucyfuzz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mf4")

        try:

            # Prepare numeric data arrays
            timestamps = []
            can_ids = []
            data_bytes = []
            
            frame_counter = 0
            
            # Parse logs for CAN frames
            for i, line in enumerate(logs):
                if isinstance(line, str) and line.strip():
                    # Try to extract CAN frame information
                    
                    # Pattern from your logs: 2025-12-09T12:31:29.586469 [SUCCESS] SEND ID=0x123 DLC=0 LEN=4 DATA=00010203
                    can_pattern = r'ID=([0-9A-Fx]+).*?DATA=([0-9A-F]+)'
                    match = re.search(can_pattern, line, re.IGNORECASE)
                    
                    if match:
                        frame_counter += 1
                        can_id_str = match.group(1)
                        data_hex = match.group(2)
                        
                        # Convert CAN ID
                        if can_id_str.lower().startswith('0x'):
                            can_id = int(can_id_str, 16)
                        else:
                            can_id = int(can_id_str, 16) if 'x' in can_id_str.lower() else int(can_id_str)
                        
                        # Convert data bytes
                        data_vals = []
                        for j in range(0, len(data_hex), 2):
                            if j + 2 <= len(data_hex):
                                byte_val = int(data_hex[j:j+2], 16)
                                data_vals.append(byte_val)
                        
                        # Pad to 8 bytes if needed
                        while len(data_vals) < 8:
                            data_vals.append(0)
                        
                        # Store data
                        timestamps.append(time.time() + i * 0.001)
                        can_ids.append(can_id)
                        data_bytes.append(data_vals[:8])  # First 8 bytes
            
            # If no CAN frames found, create sample data
            if frame_counter == 0:
                print("No CAN frames found, creating sample data")
                for i in range(10):
                    timestamps.append(time.time() + i * 0.001)
                    can_ids.append(0x100 + i)
                    data_bytes.append([i*10 + j for j in range(8)])
                frame_counter = 10
            
            # Convert to numpy arrays
            timestamps_np = np.array(timestamps, dtype=np.float64)
            can_ids_np = np.array(can_ids, dtype=np.uint32)
            
            # Ensure data_bytes has correct shape
            if data_bytes:
                data_bytes_np = np.array(data_bytes, dtype=np.uint8)
            else:
                data_bytes_np = np.zeros((frame_counter, 8), dtype=np.uint8)
            
            # Create signals
            signals = []
            
            # Signal 1: CAN IDs
            signals.append(Signal(
                samples=can_ids_np,
                timestamps=timestamps_np,
                name='CAN_ID',
                unit='-',
                comment='CAN Frame Identifier'
            ))
            
            # Signals 2-9: Data bytes (only if we have data)
            if data_bytes_np.shape[0] > 0:
                for byte_idx in range(min(8, data_bytes_np.shape[1])):
                    signals.append(Signal(
                        samples=data_bytes_np[:, byte_idx],
                        timestamps=timestamps_np,
                        name=f'CAN_Data_Byte{byte_idx}',
                        unit='-',
                        comment=f'CAN Data Byte {byte_idx}'
                    ))
            
            # Create MDF file
            mdf = MDF()
            
            # Append signals - handle different versions
            try:
                mdf.append(signals)
            except Exception as append_error:
                print(f"Warning: mdf.append() failed: {append_error}")
                # Try alternative approach
                for signal in signals:
                    try:
                        mdf.append(signal)
                    except:
                        print(f"Could not append signal: {signal.name}")
            
            # Add metadata - version compatible
            try:
                # Set comment using the appropriate method for this version
                mdf.header.comment = (
                    f"FucyFuzz CAN Bus Fuzzing Logs\n"
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Frames: {frame_counter}\n"
                    f"Tool: FucyFuzz Security Framework"
                )
            except AttributeError:
                # Try alternative if header.comment doesn't work
                try:
                    mdf.comment = (
                        f"FucyFuzz CAN Bus Fuzzing Logs\n"
                        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Frames: {frame_counter}"
                    )
                except:
                    pass
            
            # Try to add file history if method exists
            try:
                if hasattr(mdf, 'add_file_history'):
                    mdf.add_file_history(f"FucyFuzz export at {datetime.now().isoformat()}")
                elif hasattr(mdf, 'add_history'):
                    mdf.add_history(f"FucyFuzz export at {datetime.now().isoformat()}")
            except Exception as history_error:
                print(f"Note: Could not add file history: {history_error}")
            
            # Save file
            try:
                mdf.save(filename, overwrite=True)
                print(f"MDF4 export completed: {filename} ({frame_counter} frames)")
                return filename
            except Exception as save_error:
                # Try without overwrite parameter
                try:
                    mdf.save(filename)
                    print(f"MDF4 export completed: {filename} ({frame_counter} frames)")
                    return filename
                except Exception as save_error2:
                    raise Exception(f"Failed to save MDF4 file: {save_error2}")
                
        except Exception as ex:
            # Provide more detailed error
            error_msg = f"Failed to create MDF4 file: {type(ex).__name__}: {str(ex)}"
            
            # Check for specific asammdf version issues
            
            tb = traceback.format_exc()
            print(f"Full traceback:\n{tb}")
            
            if "Unknown type" in str(ex) or "dtype=" in str(ex):
                error_msg += "\n\nData type compatibility issue with asammdf.\n"
                error_msg += "Try: pip install asammdf==7.3.0"
            
            raise Exception(error_msg)


# ------------------------------
# Helper to attach to app
# ------------------------------
def attach_report_capabilities(app_instance):
    """
    Attach generators and exporter to an existing app instance:
        app_instance.pdf_generator = EnhancedPDFReport(app_instance)
        app_instance.failure_report = FailureReport(app_instance)
        app_instance.log_exporter = LogExporter(app_instance)
    """
    app_instance.pdf_generator = EnhancedPDFReport(app_instance)
    app_instance.failure_report = FailureReport(app_instance)
    app_instance.log_exporter = LogExporter(app_instance)
    
    # Also attach the format-specific methods directly for convenience
    app_instance.export_report_pdf = app_instance.pdf_generator.generate_pdf
    app_instance.export_report_asc = app_instance.pdf_generator.export_report_to_asc
    app_instance.export_report_mf4 = app_instance.pdf_generator.export_report_to_mf4
    app_instance.export_report_all = app_instance.pdf_generator.generate_all_formats
    
    return app_instance
