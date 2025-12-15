# fonts.py
class FontConfig:
    """
    Font configuration for FucyFuzz GUI with increased font sizes
    All values are increased by ~20% from original
    """
    
    # ====================
    # BASE FONT SIZES
    # ====================
    
    # Title fonts
    MAIN_TITLE = 28        # Increased from ~22-24
    SECTION_TITLE = 24     # Increased from ~20
    TAB_TITLE = 20         # Increased from ~16
    SUBTITLE = 18          # Increased from ~14-16
    
    # UI fonts
    LABEL = 15             # Increased from ~12 (now 25% larger)
    BUTTON = 14            # Increased from ~12
    BUTTON_LARGE = 16      # For main action buttons
    ENTRY = 14             # Increased from ~12
    DROPDOWN = 14          # Increased from ~12
    CHECKBOX = 13          # Increased from ~11
    
    # Console fonts
    CONSOLE_HEADER = 14    # Increased from ~12
    CONSOLE_TEXT = 13      # Increased from ~11-12
    CONSOLE_MONO = 13      # Increased from ~11-12
    
    # Tab fonts
    TAB_TEXT = 16          # Increased from ~14
    
    # ====================
    # FONT FAMILIES
    # ====================
    SANS_SERIF = "Arial"
    MONOSPACE = "Consolas"
    
    # ====================
    # DIMENSION MULTIPLIERS
    # ====================
    @classmethod
    def get_height(cls, widget_type, scale_factor):
        """Get height for different widget types"""
        base_heights = {
            "title": 50,
            "button": 45,
            "button_large": 55,
            "button_small": 40,
            "entry": 40,
            "dropdown": 40,
            "checkbox": 25,
            "label": 30
        }
        
        if widget_type in base_heights:
            base = base_heights[widget_type]
            return max(base * 0.7, min(base * 1.5, int(base * scale_factor)))
        return int(40 * scale_factor)
    
    @classmethod
    def get_width(cls, widget_type, scale_factor):
        """Get width for different widget types"""
        base_widths = {
            "button": 140,
            "button_large": 200,
            "button_small": 100,
            "entry": 200,
            "dropdown": 200
        }
        
        if widget_type in base_widths:
            base = base_widths[widget_type]
            return max(base * 0.7, min(base * 1.5, int(base * scale_factor)))
        return int(150 * scale_factor)
    
    @classmethod
    def get_padding(cls, scale_factor):
        """Get padding based on scale"""
        base_pad = 20
        return max(10, min(30, int(base_pad * scale_factor)))
    
    @classmethod
    def get_corner_radius(cls, scale_factor):
        """Get corner radius based on scale"""
        base_radius = 8
        return max(6, min(12, int(base_radius * scale_factor)))
    
    # ====================
    # HELPER METHODS
    # ====================
    
    
    @staticmethod
    def get_demo_button_font(scale_factor=1.0, bold=True):
            """Get consistent font for demo buttons"""
            base_size = 14
            size = max(10, int(base_size * scale_factor))
            
            if bold:
                return ("Arial", size, "bold")
            return ("Arial", size)
    
    @classmethod
    def get_title_font(cls, scale_factor=1.0):
        """Get title font with scaling"""
        size = max(20, min(36, int(cls.MAIN_TITLE * scale_factor)))
        return (cls.SANS_SERIF, size, "bold")
    
    @classmethod
    def get_section_font(cls, scale_factor=1.0):
        """Get section title font with scaling"""
        size = max(18, min(30, int(cls.SECTION_TITLE * scale_factor)))
        return (cls.SANS_SERIF, size, "bold")
    
    @classmethod
    def get_tab_font(cls, scale_factor=1.0):
        """Get tab font with scaling"""
        size = max(14, min(24, int(cls.TAB_TEXT * scale_factor)))
        return (cls.SANS_SERIF, size, "bold")
    
    @classmethod
    def get_label_font(cls, scale_factor=1.0, bold=False):
        """Get label font with scaling"""
        size = max(13, min(22, int(cls.LABEL * scale_factor)))
        if bold:
            return (cls.SANS_SERIF, size, "bold")
        return (cls.SANS_SERIF, size)
    
    @classmethod
    def get_button_font(cls, scale_factor=1.0, bold=False, large=False):
        """Get button font with scaling"""
        base_size = cls.BUTTON_LARGE if large else cls.BUTTON
        size = max(12, min(22, int(base_size * scale_factor)))
        if bold:
            return (cls.SANS_SERIF, size, "bold")
        return (cls.SANS_SERIF, size)
    
    @classmethod
    def get_entry_font(cls, scale_factor=1.0):
        """Get entry/dropdown font with scaling"""
        size = max(12, min(20, int(cls.ENTRY * scale_factor)))
        return (cls.SANS_SERIF, size)
    
    @classmethod
    def get_checkbox_font(cls, scale_factor=1.0):
        """Get checkbox font with scaling"""
        size = max(11, min(18, int(cls.CHECKBOX * scale_factor)))
        return (cls.SANS_SERIF, size)
    
    @classmethod
    def get_console_font(cls, scale_factor=1.0):
        """Get console text font with scaling"""
        size = max(12, min(18, int(cls.CONSOLE_TEXT * scale_factor)))
        return (cls.MONOSPACE, size)
    
    @classmethod
    def get_console_header_font(cls, scale_factor=1.0):
        """Get console header font with scaling"""
        size = max(13, min(20, int(cls.CONSOLE_HEADER * scale_factor)))
        return (cls.SANS_SERIF, size, "bold")
    
    @classmethod
    def get_mono_font(cls, scale_factor=1.0, size_multiplier=1.0):
        """Get monospaced font for code/text display"""
        base_size = cls.CONSOLE_MONO * size_multiplier
        size = max(11, min(18, int(base_size * scale_factor)))
        return (cls.MONOSPACE, size)