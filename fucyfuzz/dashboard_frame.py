# dashboard_frame.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Import font configuration and scaling utilities
from fonts import FontConfig
from ui_scaling import UIScaling

# ==============================================================================
#  DASHBOARD FRAME
# ==============================================================================

class DashboardFrame(ctk.CTkFrame):
    """Dashboard showing test statistics, failures, and visualizations"""
    
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.chart_figures = []
        
        # Header
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x", pady=(0, 10))
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="📊 Dashboard", font=FontConfig.get_title_font(1.2))
        self.title_label.pack(side="left")
        
        # Refresh button
        self.refresh_btn = ctk.CTkButton(self.head_frame, text="🔄 Refresh", width=100,
                                       command=self.refresh_dashboard, fg_color="#3498db")
        self.refresh_btn.pack(side="right", padx=10)
        
        # Export button
        self.export_btn = ctk.CTkButton(self.head_frame, text="📥 Export Dashboard", width=140,
                                      command=self.export_dashboard, fg_color="#27ae60")
        self.export_btn.pack(side="right", padx=10)
        
        # Main container with tabs for different views
        self.dashboard_tabs = ctk.CTkTabview(self)
        self.dashboard_tabs.pack(fill="both", expand=True, pady=5)
        
        # Add tabs
        self.overview_tab = self.dashboard_tabs.add("Overview")
        self.statistics_tab = self.dashboard_tabs.add("Statistics")
        self.failures_tab = self.dashboard_tabs.add("Failure Analysis")
        self.timeline_tab = self.dashboard_tabs.add("Timeline")
        
        # Initialize each tab
        self._setup_overview_tab()
        self._setup_statistics_tab()
        self._setup_failures_tab()
        self._setup_timeline_tab()
        
        # Initial refresh
        self.after(100, self.refresh_dashboard)
    
    def _setup_overview_tab(self):
        """Setup overview tab with key metrics"""
        # Create a grid layout for metrics
        self.overview_grid = ctk.CTkFrame(self.overview_tab, fg_color="transparent")
        self.overview_grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Metrics will be created dynamically
        
    def _setup_statistics_tab(self):
        """Setup statistics tab with charts"""
        self.stats_container = ctk.CTkFrame(self.statistics_tab, fg_color="transparent")
        self.stats_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create scrollable frame for charts
        self.stats_scroll = ctk.CTkScrollableFrame(self.stats_container)
        self.stats_scroll.pack(fill="both", expand=True)
        
    def _setup_failures_tab(self):
        """Setup failure analysis tab"""
        self.failures_container = ctk.CTkFrame(self.failures_tab, fg_color="transparent")
        self.failures_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create scrollable frame for failure details
        self.failures_scroll = ctk.CTkScrollableFrame(self.failures_container)
        self.failures_scroll.pack(fill="both", expand=True)
        
    def _setup_timeline_tab(self):
        """Setup timeline tab"""
        self.timeline_container = ctk.CTkFrame(self.timeline_tab, fg_color="transparent")
        self.timeline_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create scrollable frame for timeline
        self.timeline_scroll = ctk.CTkScrollableFrame(self.timeline_container)
        self.timeline_scroll.pack(fill="both", expand=True)
    
    def refresh_dashboard(self):
        """Refresh all dashboard data and visualizations"""
        try:
            # Clear existing widgets
            self._clear_dashboard_widgets()
            
            # Analyze data
            self._analyze_data()
            
            # Update all tabs
            self._update_overview_tab()
            self._update_statistics_tab()
            self._update_failures_tab()
            self._update_timeline_tab()
            
        except Exception as e:
            print(f"Dashboard refresh error: {e}")
    
    def _clear_dashboard_widgets(self):
        """Clear existing dashboard widgets"""
        # Clear overview grid
        for widget in self.overview_grid.winfo_children():
            widget.destroy()
        
        # Clear statistics scroll
        for widget in self.stats_scroll.winfo_children():
            widget.destroy()
        
        # Clear failures scroll
        for widget in self.failures_scroll.winfo_children():
            widget.destroy()
        
        # Clear timeline scroll
        for widget in self.timeline_scroll.winfo_children():
            widget.destroy()
        
        # Clear existing matplotlib figures
        for fig in self.chart_figures:
            plt.close(fig)
        self.chart_figures = []
    
    def _analyze_data(self):
        """Analyze session data similar to report_generator"""
        entries = getattr(self.app, 'session_history', [])
        failure_cases = getattr(self.app, 'failure_cases', {})
        
        if not entries:
            self.stats = {
                'total_tests': 0,
                'success_count': 0,
                'failure_count': 0,
                'warning_count': 0,
                'modules': {},
                'module_stats': {},
                'failure_details': [],
                'timeline_data': [],
                'error_types': Counter(),
                'success_rate': 0
            }
            return
        
        # Initialize counters
        success_count = 0
        failure_count = 0
        warning_count = 0
        modules = set()
        module_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'fail': 0, 'warning': 0})
        timeline_data = []
        error_types = Counter()
        
        # Analyze each entry
        for entry in entries:
            module = entry.get('module', 'Unknown')
            status = entry.get('status', '').lower()
            timestamp = entry.get('timestamp', '')
            
            modules.add(module)
            module_stats[module]['total'] += 1
            
            if 'success' in status or 'passed' in status or 'ok' in status:
                module_stats[module]['success'] += 1
                success_count += 1
            elif 'fail' in status or 'error' in status:
                module_stats[module]['fail'] += 1
                failure_count += 1
                
                # Categorize error type
                output = entry.get('output', '').lower()
                if 'timeout' in output:
                    error_types['Timeout'] += 1
                elif 'connection' in output or 'connect' in output:
                    error_types['Connection'] += 1
                elif 'permission' in output:
                    error_types['Permission'] += 1
                elif 'invalid' in output:
                    error_types['Validation'] += 1
                else:
                    error_types['Other'] += 1
            elif 'warning' in status:
                module_stats[module]['warning'] += 1
                warning_count += 1
            else:
                module_stats[module]['warning'] += 1
                warning_count += 1
            
            # Add to timeline
            if timestamp:
                try:
                    # Try to parse timestamp
                    if 'T' in timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    timeline_data.append((dt, module, status))
                except:
                    pass
        
        # Prepare failure details
        failure_details = []
        for module, failures in failure_cases.items():
            for failure in failures:
                failure_details.append({
                    'module': module,
                    'timestamp': failure.get('timestamp', ''),
                    'command': failure.get('command', ''),
                    'status': failure.get('status', ''),
                    'error_type': failure.get('case_details', {}).get('error_type', 'Unknown')
                })
        
        # Calculate success rate
        success_rate = (success_count / len(entries) * 100) if entries else 0
        
        self.stats = {
            'total_tests': len(entries),
            'success_count': success_count,
            'failure_count': failure_count,
            'warning_count': warning_count,
            'modules': sorted(list(modules)),
            'module_stats': dict(module_stats),
            'failure_details': failure_details,
            'timeline_data': sorted(timeline_data, key=lambda x: x[0]) if timeline_data else [],
            'error_types': dict(error_types),
            'success_rate': success_rate
        }
    
    def _update_overview_tab(self):
        """Update overview tab with key metrics"""
        stats = self.stats
        
        # Create metrics in a 2x2 grid
        metrics = [
            {
                'title': 'Total Tests',
                'value': stats['total_tests'],
                'color': '#2980b9',
                'icon': '📊'
            },
            {
                'title': 'Success Rate',
                'value': f"{stats['success_rate']:.1f}%",
                'color': '#27ae60',
                'icon': '✅'
            },
            {
                'title': 'Failures',
                'value': stats['failure_count'],
                'color': '#c0392b',
                'icon': '❌'
            },
            {
                'title': 'Modules Tested',
                'value': len(stats['modules']),
                'color': '#8e44ad',
                'icon': '🔧'
            }
        ]
        
        # Create metric cards
        for i, metric in enumerate(metrics):
            row = i // 2
            col = i % 2
            
            card = self._create_metric_card(
                self.overview_grid,
                metric['title'],
                metric['value'],
                metric['color'],
                metric['icon']
            )
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Configure grid weights
        self.overview_grid.grid_rowconfigure(0, weight=1)
        self.overview_grid.grid_rowconfigure(1, weight=1)
        self.overview_grid.grid_columnconfigure(0, weight=1)
        self.overview_grid.grid_columnconfigure(1, weight=1)
        
        # Add recent activity section
        if stats['timeline_data']:
            recent_frame = ctk.CTkFrame(self.overview_grid)
            recent_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=20, sticky="nsew")
            
            ctk.CTkLabel(recent_frame, text="📈 Recent Activity", 
                        font=("Arial", 14, "bold")).pack(pady=(10, 5), anchor="w", padx=10)
            
            # Show last 5 activities
            recent_activities = stats['timeline_data'][-5:]
            for dt, module, status in reversed(recent_activities):
                time_str = dt.strftime("%H:%M:%S")
                status_icon = "✅" if 'success' in status.lower() else "❌" if 'fail' in status.lower() else "⚠️"
                activity_text = f"{time_str} - {status_icon} {module}: {status}"
                
                activity_label = ctk.CTkLabel(recent_frame, text=activity_text,
                                            font=("Arial", 11), anchor="w")
                activity_label.pack(fill="x", padx=10, pady=2)
    
    def _create_metric_card(self, parent, title, value, color, icon):
        """Create a metric card widget"""
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#2c3e50")
        
        # Top section with icon and title
        top_frame = ctk.CTkFrame(card, fg_color="transparent")
        top_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(top_frame, text=icon, font=("Arial", 24)).pack(side="left")
        ctk.CTkLabel(top_frame, text=title, font=("Arial", 12),
                    text_color="#bdc3c7").pack(side="left", padx=10)
        
        # Value
        value_frame = ctk.CTkFrame(card, fg_color="transparent")
        value_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(value_frame, text=str(value), font=("Arial", 32, "bold"),
                    text_color=color).pack()
        
        return card
    
    def _update_statistics_tab(self):
        """Update statistics tab with charts"""
        stats = self.stats
        
        if stats['total_tests'] == 0:
            ctk.CTkLabel(self.stats_scroll, text="No test data available",
                        font=("Arial", 14)).pack(pady=50)
            return
        
        # Chart 1: Test Results Pie Chart
        if stats['total_tests'] > 0:
            self._create_pie_chart(
                self.stats_scroll,
                "Test Results Distribution",
                ['Success', 'Failures', 'Warnings'],
                [stats['success_count'], stats['failure_count'], stats['warning_count']],
                ['#27ae60', '#c0392b', '#f39c12']
            )
        
        # Chart 2: Module Performance Bar Chart
        if stats['module_stats']:
            modules = list(stats['module_stats'].keys())
            success_rates = []
            
            for module in modules:
                module_stat = stats['module_stats'][module]
                total = module_stat['total']
                success = module_stat['success']
                rate = (success / total * 100) if total > 0 else 0
                success_rates.append(rate)
            
            self._create_bar_chart(
                self.stats_scroll,
                "Module Success Rates",
                modules,
                success_rates,
                '#3498db'
            )
        
        # Chart 3: Error Types
        if stats['error_types']:
            error_labels = list(stats['error_types'].keys())
            error_counts = list(stats['error_types'].values())
            
            self._create_bar_chart(
                self.stats_scroll,
                "Error Types",
                error_labels,
                error_counts,
                '#e74c3c'
            )
    
    def _create_pie_chart(self, parent, title, labels, sizes, colors):
        """Create a pie chart"""
        chart_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#2c3e50")
        chart_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(chart_frame, text=title, font=("Arial", 14, "bold"),
                    text_color="white").pack(pady=(10, 5))
        
        # Create figure
        fig, ax = plt.subplots(figsize=(5, 4), dpi=80)
        fig.patch.set_facecolor('#2c3e50')
        ax.set_facecolor('#2c3e50')
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                         autopct='%1.1f%%', startangle=90)
        
        # Style the text
        for text in texts:
            text.set_color('white')
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(9)
        
        ax.axis('equal')  # Equal aspect ratio ensures pie is drawn as circle
        
        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=10)
        
        # Store figure reference
        self.chart_figures.append(fig)
    
    def _create_bar_chart(self, parent, title, labels, values, color):
        """Create a bar chart"""
        chart_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#2c3e50")
        chart_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(chart_frame, text=title, font=("Arial", 14, "bold"),
                    text_color="white").pack(pady=(10, 5))
        
        # Create figure
        fig, ax = plt.subplots(figsize=(6, 4), dpi=80)
        fig.patch.set_facecolor('#2c3e50')
        ax.set_facecolor('#2c3e50')
        
        # Create bar chart
        bars = ax.bar(labels, values, color=color)
        
        # Style
        ax.set_xlabel('')
        ax.set_ylabel('')
        
        # Set colors
        ax.tick_params(axis='x', colors='white', rotation=45 if len(labels) > 5 else 0)
        ax.tick_params(axis='y', colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}' if isinstance(height, float) else f'{height}',
                   ha='center', va='bottom', color='white', fontsize=9)
        
        # Tight layout
        plt.tight_layout()
        
        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=10)
        
        # Store figure reference
        self.chart_figures.append(fig)
    
    def _update_failures_tab(self):
        """Update failure analysis tab"""
        stats = self.stats
        
        if not stats['failure_details']:
            ctk.CTkLabel(self.failures_scroll, text="✅ No failures recorded",
                        font=("Arial", 14)).pack(pady=50)
            return
        
        # Failure summary
        summary_frame = ctk.CTkFrame(self.failures_scroll, fg_color="#34495e", corner_radius=8)
        summary_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(summary_frame, text="Failure Summary",
                    font=("Arial", 14, "bold"), text_color="white").pack(pady=(10, 5), padx=10, anchor="w")
        
        summary_text = f"Total Failures: {stats['failure_count']}\n"
        summary_text += f"Modules with Failures: {len(set([f['module'] for f in stats['failure_details']]))}\n"
        summary_text += f"Most Common Error: {max(stats['error_types'].items(), key=lambda x: x[1])[0] if stats['error_types'] else 'N/A'}"
        
        ctk.CTkLabel(summary_frame, text=summary_text,
                    font=("Arial", 12), text_color="#ecf0f1", justify="left").pack(pady=(0, 10), padx=10, anchor="w")
        
        # Failure details
        ctk.CTkLabel(self.failures_scroll, text="Failure Details",
                    font=("Arial", 14, "bold")).pack(pady=(20, 10), anchor="w", padx=10)
        
        for i, failure in enumerate(stats['failure_details'][:10]):  # Show first 10
            failure_frame = ctk.CTkFrame(self.failures_scroll, fg_color="#2c3e50", corner_radius=6)
            failure_frame.pack(fill="x", padx=10, pady=5)
            
            # Failure info
            info_text = f"#{i+1} - {failure['module']}\n"
            info_text += f"Time: {failure['timestamp'][11:19] if len(failure['timestamp']) > 10 else failure['timestamp']}\n"
            info_text += f"Error: {failure['error_type']}\n"
            info_text += f"Command: {failure['command'][:60]}..." if len(failure['command']) > 60 else f"Command: {failure['command']}"
            
            ctk.CTkLabel(failure_frame, text=info_text,
                        font=("Consolas", 10), text_color="#ecf0f1", justify="left").pack(padx=10, pady=10, anchor="w")
            
            # Action button
            btn_frame = ctk.CTkFrame(failure_frame, fg_color="transparent")
            btn_frame.pack(fill="x", padx=10, pady=(0, 10))
            
            ctk.CTkButton(btn_frame, text="View Details", width=100,
                         command=lambda f=failure: self._view_failure_details(f),
                         fg_color="#3498db").pack(side="left", padx=2)
            
            ctk.CTkButton(btn_frame, text="Re-run", width=80,
                         command=lambda f=failure: self._re_run_failure(f),
                         fg_color="#27ae60").pack(side="left", padx=2)
        
        if len(stats['failure_details']) > 10:
            ctk.CTkLabel(self.failures_scroll, 
                        text=f"... and {len(stats['failure_details']) - 10} more failures",
                        font=("Arial", 11), text_color="#95a5a6").pack(pady=10)
            
            ctk.CTkButton(self.failures_scroll, text="View All Failures",
                         command=self.app.show_failure_cases,
                         fg_color="#8e44ad").pack(pady=10)
    
    def _view_failure_details(self, failure):
        """View details of a specific failure"""
        details_window = ctk.CTkToplevel(self)
        details_window.title(f"Failure Details - {failure['module']}")
        details_window.geometry("600x400")
        details_window.attributes("-topmost", True)
        
        # Header
        header = ctk.CTkFrame(details_window, fg_color="#c0392b")
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="📋 Failure Details",
                    font=("Arial", 16, "bold"), text_color="white").pack(pady=10)
        
        # Content
        content = ctk.CTkFrame(details_window)
        content.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Create scrollable frame
        scroll_content = ctk.CTkScrollableFrame(content)
        scroll_content.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Display failure information
        info_text = f"Module: {failure['module']}\n"
        info_text += f"Timestamp: {failure['timestamp']}\n"
        info_text += f"Status: {failure['status']}\n"
        info_text += f"Error Type: {failure['error_type']}\n"
        info_text += f"\nCommand:\n{failure['command']}\n"
        
        ctk.CTkLabel(scroll_content, text=info_text,
                    font=("Consolas", 11), justify="left").pack(pady=10, padx=10, anchor="w")
        
        # Close button
        ctk.CTkButton(details_window, text="Close",
                     command=details_window.destroy).pack(pady=10)
    
    def _re_run_failure(self, failure):
        """Re-run a specific failure"""
        # This would use similar logic to the failure cases dialog
        messagebox.showinfo("Re-run", f"Would re-run failure from {failure['module']}")
        # In practice, you would call: self.app._re_run_failure_case(failure, failure['module'], None)
    
    def _update_timeline_tab(self):
        """Update timeline tab"""
        stats = self.stats
        
        if not stats['timeline_data']:
            ctk.CTkLabel(self.timeline_scroll, text="No timeline data available",
                        font=("Arial", 14)).pack(pady=50)
            return
        
        ctk.CTkLabel(self.timeline_scroll, text="Test Execution Timeline",
                    font=("Arial", 14, "bold")).pack(pady=(10, 20), anchor="w", padx=10)
        
        # Group by hour
        hourly_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'fail': 0})
        
        for dt, module, status in stats['timeline_data']:
            hour_key = dt.replace(minute=0, second=0, microsecond=0)
            hourly_stats[hour_key]['total'] += 1
            if 'success' in status.lower():
                hourly_stats[hour_key]['success'] += 1
            elif 'fail' in status.lower():
                hourly_stats[hour_key]['fail'] += 1
        
        # Create timeline visualization
        if hourly_stats:
            hours = sorted(hourly_stats.keys())
            total_counts = [hourly_stats[h]['total'] for h in hours]
            success_counts = [hourly_stats[h]['success'] for h in hours]
            fail_counts = [hourly_stats[h]['fail'] for h in hours]
            
            # Create figure
            fig, ax = plt.subplots(figsize=(8, 4), dpi=80)
            fig.patch.set_facecolor('#2c3e50')
            ax.set_facecolor('#2c3e50')
            
            # Plot stacked bar
            x = range(len(hours))
            bar_width = 0.6
            
            ax.bar(x, success_counts, bar_width, label='Success', color='#27ae60')
            ax.bar(x, fail_counts, bar_width, bottom=success_counts, label='Failures', color='#c0392b')
            
            # Style
            ax.set_xlabel('Time', color='white')
            ax.set_ylabel('Test Count', color='white')
            ax.set_title('Test Execution by Hour', color='white')
            
            # Format x-axis
            hour_labels = [h.strftime('%H:%M') for h in hours]
            ax.set_xticks(x)
            ax.set_xticklabels(hour_labels, rotation=45, color='white')
            
            ax.tick_params(axis='y', colors='white')
            ax.legend(facecolor='#2c3e50', edgecolor='#2c3e50', labelcolor='white')
            
            # Set spine colors
            for spine in ax.spines.values():
                spine.set_color('white')
            
            plt.tight_layout()
            
            # Embed in Tkinter
            chart_frame = ctk.CTkFrame(self.timeline_scroll, corner_radius=10, fg_color="#2c3e50")
            chart_frame.pack(fill="x", padx=10, pady=10)
            
            canvas = FigureCanvasTkAgg(fig, chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(pady=10)
            
            self.chart_figures.append(fig)
        
        # Detailed timeline list
        ctk.CTkLabel(self.timeline_scroll, text="Detailed Timeline",
                    font=("Arial", 14, "bold")).pack(pady=(20, 10), anchor="w", padx=10)
        
        for dt, module, status in stats['timeline_data'][-20:]:  # Last 20 entries
            time_str = dt.strftime("%H:%M:%S")
            date_str = dt.strftime("%Y-%m-%d")
            status_icon = "✅" if 'success' in status.lower() else "❌" if 'fail' in status.lower() else "⚠️"
            
            timeline_entry = ctk.CTkFrame(self.timeline_scroll, fg_color="#34495e", corner_radius=6)
            timeline_entry.pack(fill="x", padx=10, pady=2)
            
            entry_text = f"{date_str} {time_str} - {status_icon} {module}: {status}"
            
            ctk.CTkLabel(timeline_entry, text=entry_text,
                        font=("Arial", 11), text_color="#ecf0f1").pack(padx=10, pady=5, anchor="w")
    
    def export_dashboard(self):
        """Export dashboard data to a report"""
        if self.stats['total_tests'] == 0:
            messagebox.showinfo("Info", "No data to export")
            return
        
        # Create export dialog
        export_dialog = ctk.CTkToplevel(self)
        export_dialog.title("Export Dashboard")
        export_dialog.geometry("400x300")
        export_dialog.attributes("-topmost", True)
        
        ctk.CTkLabel(export_dialog, text="Export Dashboard Data",
                    font=("Arial", 16, "bold")).pack(pady=20)
        
        ctk.CTkLabel(export_dialog, text="Select export format:",
                    font=("Arial", 12)).pack(pady=10)
        
        def export_as(format_type):
            export_dialog.destroy()
            
            if format_type == "json":
                self._export_json()
            elif format_type == "csv":
                self._export_csv()
            elif format_type == "html":
                self._export_html()
        
        btn_frame = ctk.CTkFrame(export_dialog)
        btn_frame.pack(expand=True, padx=20, pady=10)
        
        ctk.CTkButton(btn_frame, text="JSON", width=120,
                     command=lambda: export_as("json"),
                     fg_color="#3498db").pack(pady=10)
        
        ctk.CTkButton(btn_frame, text="CSV", width=120,
                     command=lambda: export_as("csv"),
                     fg_color="#27ae60").pack(pady=10)
        
        ctk.CTkButton(btn_frame, text="HTML", width=120,
                     command=lambda: export_as("html"),
                     fg_color="#8e44ad").pack(pady=10)
        
        ctk.CTkButton(export_dialog, text="Cancel",
                     command=export_dialog.destroy).pack(pady=10)
    
    def _export_json(self):
        """Export dashboard data as JSON"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"dashboard_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(self.stats, f, indent=2, default=str)
                messagebox.showinfo("Success", f"Dashboard data exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export JSON: {e}")
    
    def _export_csv(self):
        """Export dashboard data as CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"dashboard_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Write summary
                    writer.writerow(["Dashboard Summary"])
                    writer.writerow(["Metric", "Value"])
                    writer.writerow(["Total Tests", self.stats['total_tests']])
                    writer.writerow(["Success Count", self.stats['success_count']])
                    writer.writerow(["Failure Count", self.stats['failure_count']])
                    writer.writerow(["Warning Count", self.stats['warning_count']])
                    writer.writerow(["Success Rate", f"{self.stats['success_rate']:.2f}%"])
                    writer.writerow([])
                    
                    # Write module stats
                    writer.writerow(["Module Statistics"])
                    writer.writerow(["Module", "Total", "Success", "Failures", "Warnings", "Success Rate"])
                    for module, stats in self.stats['module_stats'].items():
                        rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                        writer.writerow([
                            module, stats['total'], stats['success'], 
                            stats['fail'], stats['warning'], f"{rate:.2f}%"
                        ])
                
                messagebox.showinfo("Success", f"Dashboard data exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export CSV: {e}")
    
    def _export_html(self):
        """Export dashboard as HTML report"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html")],
            initialfile=f"dashboard_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        
        if filename:
            try:
                html_content = self._generate_html_report()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                messagebox.showinfo("Success", f"HTML report exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export HTML: {e}")
    
    def _generate_html_report(self):
        """Generate HTML report content"""
        stats = self.stats
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FucyFuzz Dashboard Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
                .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .metric-value {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
                .table {{ width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
                .table th {{ background: #3498db; color: white; }}
                .success {{ color: #27ae60; }}
                .failure {{ color: #c0392b; }}
                .warning {{ color: #f39c12; }}
                .timestamp {{ font-size: 12px; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 FucyFuzz Dashboard Report</h1>
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="metrics">
                    <div class="metric-card">
                        <h3>Total Tests</h3>
                        <div class="metric-value">{stats['total_tests']}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Success Rate</h3>
                        <div class="metric-value success">{stats['success_rate']:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <h3>Failures</h3>
                        <div class="metric-value failure">{stats['failure_count']}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Modules Tested</h3>
                        <div class="metric-value">{len(stats['modules'])}</div>
                    </div>
                </div>
                
                <h2>Module Performance</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Module</th>
                            <th>Total Tests</th>
                            <th>Success</th>
                            <th>Failures</th>
                            <th>Warnings</th>
                            <th>Success Rate</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for module, module_stats in stats['module_stats'].items():
            total = module_stats['total']
            success = module_stats['success']
            failure = module_stats['fail']
            warning = module_stats['warning']
            rate = (success / total * 100) if total > 0 else 0
            
            html += f"""
                        <tr>
                            <td>{module}</td>
                            <td>{total}</td>
                            <td class="success">{success}</td>
                            <td class="failure">{failure}</td>
                            <td class="warning">{warning}</td>
                            <td>{rate:.1f}%</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
                
                <h2>Recent Activity</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Module</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Add recent activities
        recent_activities = stats['timeline_data'][-10:]
        for dt, module, status in recent_activities:
            time_str = dt.strftime("%H:%M:%S")
            date_str = dt.strftime("%Y-%m-%d")
            status_class = "success" if 'success' in status.lower() else "failure" if 'fail' in status.lower() else "warning"
            
            html += f"""
                        <tr>
                            <td><span class="timestamp">{date_str}</span> {time_str}</td>
                            <td>{module}</td>
                            <td class="{status_class}">{status}</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
                
                <div style="margin-top: 40px; padding: 20px; background: #ecf0f1; border-radius: 8px;">
                    <p><strong>Report Summary:</strong> This report was generated by FucyFuzz Security Framework.</p>
                    <p>Total execution time analysis available in detailed logs.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html