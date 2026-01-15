# dashboard_frame.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
from collections import defaultdict, Counter
import base64
import json
import os

# Try to import font configuration with fallback
try:
    from fonts import FontConfig
    HAS_FONTS = True
except ImportError:
    HAS_FONTS = False
    print("[WARNING] fonts module not found, using default fonts")

try:
    from ui_scaling import UIScaling
    HAS_UI_SCALING = True
except ImportError:
    HAS_UI_SCALING = False
    print("[WARNING] ui_scaling module not found")

# Import Plotly as the lightweight charting library
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.io as pio
    HAS_PLOTLY = True
    # Set default template for dark theme
    pio.templates.default = "plotly_dark"
except ImportError:
    HAS_PLOTLY = False
    print("[WARNING] Plotly not found, charts will display as text")

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

# ==============================================================================
#  DASHBOARD FRAME
# ==============================================================================

class DashboardFrame(ctk.CTkFrame):
    """Dashboard showing test statistics, failures, and visualizations"""
    
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._chart_cache = {}           # cache for rendered chart images
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Header
        self.head_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.head_frame.pack(fill="x", pady=(0, 10))
        
        # Use FontConfig if available, otherwise use default
        if HAS_FONTS:
            title_font = FontConfig.get_title_font(1.2)
        else:
            title_font = ctk.CTkFont(family="Arial", size=16, weight="bold")
        
        self.title_label = ctk.CTkLabel(self.head_frame, text="📊 Dashboard", font=title_font)
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
        
        # Initialize each tab (lightweight)
        self._setup_overview_tab()
        self._setup_statistics_tab()
        self._setup_failures_tab()
        self._setup_timeline_tab()
        
        # Re-render heavy charts only when the Statistics or Timeline tab is active
        self._bind_tab_change_events()
        
        # Initial refresh (light)
        self.after(100, self.refresh_dashboard)
    
    def _bind_tab_change_events(self):
        """Bind tab change events"""
        try:
            self.dashboard_tabs.configure(command=self._on_dashboard_tab_change)
        except Exception:
            # Fallback for older CTk versions
            self.dashboard_tabs._segmented_button.configure(command=self._on_dashboard_tab_change)
    
    def _on_dashboard_tab_change(self, *args):
        """Safe tab-change callback"""
        try:
            self.after(50, self.refresh_dashboard)
        except Exception as e:
            print(f"[Dashboard] tab-change callback error: {e}")
    
    def _setup_overview_tab(self):
        """Setup overview tab with key metrics"""
        self.overview_grid = ctk.CTkFrame(self.overview_tab, fg_color="transparent")
        self.overview_grid.pack(fill="both", expand=True, padx=10, pady=10)
        
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
            
            # Analyze data (fast)
            self._analyze_data()
            
            # Update lightweight tabs
            self._update_overview_tab()
            self._update_failures_tab()
            
            # Heavy tabs only if visible
            current = None
            try:
                current = self.dashboard_tabs.get()
            except Exception:
                current = None
            
            if current == "Statistics" or current is None:
                self._update_statistics_tab()
            
            if current == "Timeline" or current is None:
                self._update_timeline_tab()
            
        except Exception as e:
            print(f"Dashboard refresh error: {e}")
            import traceback
            traceback.print_exc()
    
    def _clear_dashboard_widgets(self):
        """Clear existing dashboard widgets"""
        for widget in self.overview_grid.winfo_children():
            widget.destroy()
        
        for widget in self.stats_scroll.winfo_children():
            widget.destroy()
        
        for widget in self.failures_scroll.winfo_children():
            widget.destroy()
        
        for widget in self.timeline_scroll.winfo_children():
            widget.destroy()
    
    def _analyze_data(self):
        """Analyze session data"""
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
    
    # ---------------------------
    # Chart rendering helpers (using Plotly)
    # ---------------------------
    def _get_stats_hash(self, stats_part):
        """Return a small hashable signature for the data to detect changes."""
        try:
            import hashlib
            return hashlib.sha1(json.dumps(stats_part, sort_keys=True, default=str).encode()).hexdigest()
        except Exception:
            return str(stats_part)
    
    def _create_plotly_chart_async(self, chart_creator, target_frame, cache_key, width=600, height=400):
        """Create Plotly chart asynchronously and display as HTML in WebView"""
        if not HAS_PLOTLY:
            # Fallback to text display if Plotly is not available
            self.after(0, lambda: ctk.CTkLabel(target_frame, text="(Plotly not installed)", 
                                             font=("Arial", 12)).pack(pady=10))
            return
        
        stats_hash = getattr(chart_creator, 'data_hash', None)
        
        # Check cache
        cached = self._chart_cache.get(cache_key)
        if cached and cached[0] == stats_hash:
            html_content = cached[1]
            def show_cached():
                self._display_chart_html(target_frame, html_content, width, height)
            self.after(0, show_cached)
            return

        def worker():
            try:
                fig = chart_creator()
                # Generate HTML with inline plot
                html_content = pio.to_html(fig, include_plotlyjs='cdn', full_html=False,
                                         config={'displayModeBar': False})
                return html_content, stats_hash
            except Exception as e:
                print(f"Plotly chart creation error: {e}")
                return None, stats_hash

        future = self.executor.submit(worker)

        def on_done(fut):
            try:
                result, stats_hash = fut.result()
            except Exception:
                result, stats_hash = None, stats_hash

            if not result:
                def show_err():
                    ctk.CTkLabel(target_frame, text="(Chart render error)",
                               font=("Arial", 12)).pack(pady=10)
                self.after(0, show_err)
                return

            def finalize():
                # Cache the HTML content
                self._chart_cache[cache_key] = (stats_hash, result)
                self._display_chart_html(target_frame, result, width, height)
            
            self.after(0, finalize)

        future.add_done_callback(on_done)
    
    def _display_chart_html(self, parent, html_content, width=600, height=400):
        """Display Plotly chart HTML in a WebView or alternative"""
        try:
            # Try to use tkinterhtml or tkinterweb for HTML display
            try:
                from tkinterhtml import HtmlFrame
                html_frame = HtmlFrame(parent, horizontal_scrollbar="auto")
                html_frame.set_content(html_content)
                html_frame.configure(width=width//10, height=height//10)  # Approximate scaling
                html_frame.pack(pady=10, fill="both", expand=True)
                return
            except ImportError:
                pass
            
            # Alternative: Use webbrowser to open in external browser
            chart_frame = ctk.CTkFrame(parent, fg_color="#2c3e50", corner_radius=10)
            chart_frame.pack(fill="x", padx=10, pady=10)
            
            # Create a button to view chart
            ctk.CTkButton(chart_frame, text="📊 View Chart in Browser",
                         command=lambda: self._open_chart_in_browser(html_content),
                         fg_color="#3498db", height=30).pack(pady=20)
            
            # Also save as temporary file for viewing
            ctk.CTkLabel(chart_frame, text="Chart will open in your web browser",
                        font=("Arial", 11)).pack(pady=(0, 10))
            
        except Exception as e:
            print(f"Chart display error: {e}")
            ctk.CTkLabel(parent, text="(Chart display error - install tkinterhtml for inline charts)",
                        font=("Arial", 11)).pack(pady=10)
    
    def _open_chart_in_browser(self, html_content):
        """Open chart HTML in default web browser"""
        try:
            import tempfile
            import webbrowser
            
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                full_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>FucyFuzz Chart</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1e1e1e; color: white; }}
                        .chart-container {{ margin: 0 auto; max-width: 900px; }}
                    </style>
                </head>
                <body>
                    <div class="chart-container">
                        <h2>FucyFuzz Dashboard Chart</h2>
                        {html_content}
                        <p style="margin-top: 20px; color: #aaa;">
                            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                    </div>
                </body>
                </html>
                """
                f.write(full_html)
                temp_file = f.name
            
            # Open in browser
            webbrowser.open(f'file://{temp_file}')
            
            # Schedule cleanup after 30 seconds
            self.after(30000, lambda: os.unlink(temp_file) if os.path.exists(temp_file) else None)
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open chart: {e}")
    
    def _create_pie_chart(self, parent, title, labels, sizes, colors):
        """Create a pie chart using Plotly"""
        chart_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#2c3e50")
        chart_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(chart_frame, text=title, font=("Arial", 14, "bold"),
                    text_color="white").pack(pady=(10, 5))
        
        data_hash = self._get_stats_hash({"type":"pie","labels":labels,"sizes":sizes})
        
        def chart_creator():
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=sizes,
                marker_colors=colors,
                hole=0.3,
                textinfo='label+percent',
                textposition='outside',
                textfont=dict(color='white', size=12)
            )])
            
            fig.update_layout(
                title=dict(
                    text=title,
                    font=dict(color='white', size=16)
                ),
                paper_bgcolor='#2c3e50',
                plot_bgcolor='#2c3e50',
                showlegend=True,
                legend=dict(
                    font=dict(color='white'),
                    bgcolor='rgba(0,0,0,0)'
                ),
                height=400
            )
            
            return fig
        
        setattr(chart_creator, 'data_hash', data_hash)
        cache_key = f"pie::{','.join(map(str,labels))}::{','.join(map(str,sizes))}"
        
        # Create inner frame for chart
        inner_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
        inner_frame.pack(fill="x", pady=(0, 10))
        
        self._create_plotly_chart_async(chart_creator, inner_frame, cache_key, width=500, height=400)
    
    def _create_bar_chart(self, parent, title, labels, values, color):
        """Create a bar chart using Plotly"""
        chart_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#2c3e50")
        chart_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(chart_frame, text=title, font=("Arial", 14, "bold"),
                    text_color="white").pack(pady=(10, 5))
        
        data_hash = self._get_stats_hash({"type":"bar","labels":labels,"values":values})
        
        def chart_creator():
            fig = go.Figure(data=[go.Bar(
                x=labels,
                y=values,
                marker_color=color,
                text=[f'{v:.1f}%' if isinstance(v, float) else str(v) for v in values],
                textposition='auto',
                textfont=dict(color='white')
            )])
            
            fig.update_layout(
                title=dict(
                    text=title,
                    font=dict(color='white', size=16)
                ),
                xaxis=dict(
                    title='',
                    tickfont=dict(color='white'),
                    tickangle=45 if len(labels) > 5 else 0
                ),
                yaxis=dict(
                    title='',
                    tickfont=dict(color='white')
                ),
                paper_bgcolor='#2c3e50',
                plot_bgcolor='#2c3e50',
                height=400
            )
            
            return fig
        
        setattr(chart_creator, 'data_hash', data_hash)
        cache_key = f"bar::{','.join(map(str,labels))}::{','.join(map(str,values))}"
        
        # Create inner frame for chart
        inner_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
        inner_frame.pack(fill="x", pady=(0, 10))
        
        self._create_plotly_chart_async(chart_creator, inner_frame, cache_key, width=600, height=400)
    
    def _create_timeline_chart(self, parent, title, hours, success_counts, fail_counts):
        """Create a timeline chart using Plotly"""
        chart_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#2c3e50")
        chart_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(chart_frame, text=title, font=("Arial", 14, "bold"),
                    text_color="white").pack(pady=(10, 5))
        
        data_hash = self._get_stats_hash({"hours":hours, "success":success_counts, "fail":fail_counts})
        
        def chart_creator():
            fig = go.Figure()
            
            # Add success bars
            fig.add_trace(go.Bar(
                x=hours,
                y=success_counts,
                name='Success',
                marker_color='#27ae60'
            ))
            
            # Add failure bars
            fig.add_trace(go.Bar(
                x=hours,
                y=fail_counts,
                name='Failures',
                marker_color='#c0392b'
            ))
            
            fig.update_layout(
                title=dict(
                    text=title,
                    font=dict(color='white', size=16)
                ),
                xaxis=dict(
                    title='Time',
                    tickfont=dict(color='white'),
                    tickangle=45
                ),
                yaxis=dict(
                    title='Test Count',
                    tickfont=dict(color='white')
                ),
                barmode='stack',
                paper_bgcolor='#2c3e50',
                plot_bgcolor='#2c3e50',
                legend=dict(
                    font=dict(color='white'),
                    bgcolor='rgba(0,0,0,0)'
                ),
                height=400
            )
            
            return fig
        
        setattr(chart_creator, 'data_hash', data_hash)
        cache_key = f"timeline::{','.join(hours)}"
        
        # Create inner frame for chart
        inner_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
        inner_frame.pack(fill="x", pady=(0, 10))
        
        self._create_plotly_chart_async(chart_creator, inner_frame, cache_key, width=700, height=400)
    
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
                "Module Success Rates (%)",
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
                "Error Types Distribution",
                error_labels,
                error_counts,
                '#e74c3c'
            )
    
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
        
        # Failure details (cap to first 10)
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
        messagebox.showinfo("Re-run", f"Would re-run failure from {failure['module']}")
    
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
            hour_labels = [h.strftime('%H:%M') for h in hours]
            success_counts = [hourly_stats[h]['success'] for h in hours]
            fail_counts = [hourly_stats[h]['fail'] for h in hours]
            
            self._create_timeline_chart(
                self.timeline_scroll,
                "Test Execution by Hour",
                hour_labels,
                success_counts,
                fail_counts
            )
        
        # Detailed timeline list (cap to last 20)
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
            elif format_type == "plotly_html":
                self._export_plotly_html()
        
        btn_frame = ctk.CTkFrame(export_dialog)
        btn_frame.pack(expand=True, padx=20, pady=10)
        
        ctk.CTkButton(btn_frame, text="JSON", width=100,
                     command=lambda: export_as("json"),
                     fg_color="#3498db").pack(pady=5)
        
        ctk.CTkButton(btn_frame, text="CSV", width=100,
                     command=lambda: export_as("csv"),
                     fg_color="#27ae60").pack(pady=5)
        
        ctk.CTkButton(btn_frame, text="HTML Report", width=100,
                     command=lambda: export_as("html"),
                     fg_color="#8e44ad").pack(pady=5)
        
        if HAS_PLOTLY:
            ctk.CTkButton(btn_frame, text="Interactive HTML", width=100,
                         command=lambda: export_as("plotly_html"),
                         fg_color="#e67e22").pack(pady=5)
        
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
    
    def _export_plotly_html(self):
        """Export dashboard as interactive Plotly HTML"""
        if not HAS_PLOTLY:
            messagebox.showwarning("Plotly Required", "Plotly is required for interactive HTML export.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("Interactive HTML", "*.html")],
            initialfile=f"dashboard_interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        
        if filename:
            try:
                html_content = self._generate_interactive_html()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                messagebox.showinfo("Success", f"Interactive HTML exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export interactive HTML: {e}")
    
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
    
    def _generate_interactive_html(self):
        """Generate interactive HTML report with Plotly charts"""
        stats = self.stats
        
        # Generate Plotly charts
        charts_html = ""
        
        # Test Results Pie Chart
        if stats['total_tests'] > 0:
            fig1 = go.Figure(data=[go.Pie(
                labels=['Success', 'Failures', 'Warnings'],
                values=[stats['success_count'], stats['failure_count'], stats['warning_count']],
                marker_colors=['#27ae60', '#c0392b', '#f39c12'],
                hole=0.3
            )])
            fig1.update_layout(title="Test Results Distribution")
            charts_html += pio.to_html(fig1, full_html=False, include_plotlyjs='cdn')
        
        # Module Performance Bar Chart
        if stats['module_stats']:
            modules = list(stats['module_stats'].keys())
            success_rates = []
            
            for module in modules:
                module_stat = stats['module_stats'][module]
                total = module_stat['total']
                success = module_stat['success']
                rate = (success / total * 100) if total > 0 else 0
                success_rates.append(rate)
            
            fig2 = go.Figure(data=[go.Bar(
                x=modules,
                y=success_rates,
                marker_color='#3498db'
            )])
            fig2.update_layout(title="Module Success Rates (%)")
            charts_html += pio.to_html(fig2, full_html=False, include_plotlyjs='cdn')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FucyFuzz Interactive Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #1e1e1e; color: white; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
                .metric-card {{ background: #34495e; padding: 20px; border-radius: 8px; }}
                .metric-value {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
                .chart-container {{ background: #2c3e50; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .success {{ color: #27ae60; }}
                .failure {{ color: #c0392b; }}
                .warning {{ color: #f39c12; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 FucyFuzz Interactive Dashboard</h1>
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
                
                <div class="chart-container">
                    <h2>Interactive Charts</h2>
                    <p>Hover over charts for detailed information. Use toolbar to zoom, pan, or download.</p>
                    {charts_html}
                </div>
                
                <div style="margin-top: 40px; padding: 20px; background: #34495e; border-radius: 8px;">
                    <p><strong>Note:</strong> This is an interactive dashboard. You can:</p>
                    <ul>
                        <li>Hover over chart elements for detailed values</li>
                        <li>Use the toolbar to zoom, pan, or reset views</li>
                        <li>Click on legend items to show/hide data series</li>
                        <li>Download charts as PNG images</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html