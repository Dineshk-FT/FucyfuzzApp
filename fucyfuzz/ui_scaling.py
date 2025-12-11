# ui_scaling.py
"""
Common UI scaling utilities for all frames
"""
import customtkinter as ctk
from fonts import FontConfig

class UIScaling:
    """Common UI scaling utilities"""
    
    @staticmethod
    def scale_widget(widget, widget_type, scale_factor):
        """Apply scaling to a widget based on its type"""
        if not widget.winfo_exists():
            return
        
        try:
            if isinstance(widget, ctk.CTkLabel):
                UIScaling._scale_label(widget, widget_type, scale_factor)
            elif isinstance(widget, ctk.CTkButton):
                UIScaling._scale_button(widget, widget_type, scale_factor)
            elif isinstance(widget, ctk.CTkEntry):
                UIScaling._scale_entry(widget, scale_factor)
            elif isinstance(widget, ctk.CTkOptionMenu):
                UIScaling._scale_dropdown(widget, scale_factor)
            elif isinstance(widget, ctk.CTkCheckBox):
                UIScaling._scale_checkbox(widget, scale_factor)
            elif isinstance(widget, ctk.CTkTextbox):
                UIScaling._scale_textbox(widget, scale_factor)
        except Exception as e:
            print(f"Warning: Could not scale widget {widget_type}: {e}")
    
    @staticmethod
    def _scale_label(widget, widget_type, scale_factor):
        """Scale label widget"""
        if "title" in widget_type.lower():
            widget.configure(font=FontConfig.get_title_font(scale_factor))
        elif "header" in widget_type.lower():
            widget.configure(font=FontConfig.get_section_font(scale_factor))
        else:
            widget.configure(font=FontConfig.get_label_font(scale_factor))
    
    @staticmethod
    def _scale_button(widget, widget_type, scale_factor):
        """Scale button widget"""
        # Determine button size
        if "large" in widget_type.lower() or "main" in widget_type.lower():
            height = FontConfig.get_height("button_large", scale_factor)
            width = FontConfig.get_width("button_large", scale_factor)
            font = FontConfig.get_button_font(scale_factor, bold=True, large=True)
        elif "small" in widget_type.lower() or "icon" in widget_type.lower():
            height = FontConfig.get_height("button_small", scale_factor)
            width = FontConfig.get_width("button_small", scale_factor)
            font = FontConfig.get_button_font(scale_factor * 0.9)
        else:
            height = FontConfig.get_height("button", scale_factor)
            width = FontConfig.get_width("button", scale_factor)
            font = FontConfig.get_button_font(scale_factor, bold="start" in widget_type.lower() or "execute" in widget_type.lower())
        
        # Apply scaling
        widget.configure(
            height=height,
            width=width if width > 0 else None,
            font=font,
            corner_radius=FontConfig.get_corner_radius(scale_factor)
        )
    
    @staticmethod
    def _scale_entry(widget, scale_factor):
        """Scale entry widget"""
        height = FontConfig.get_height("entry", scale_factor)
        widget.configure(
            height=height,
            font=FontConfig.get_entry_font(scale_factor),
            corner_radius=FontConfig.get_corner_radius(scale_factor)
        )
    
    @staticmethod
    def _scale_dropdown(widget, scale_factor):
        """Scale dropdown widget"""
        height = FontConfig.get_height("dropdown", scale_factor)
        font = FontConfig.get_entry_font(scale_factor)
        widget.configure(
            height=height,
            font=font,
            dropdown_font=font,
            corner_radius=FontConfig.get_corner_radius(scale_factor)
        )
    
    @staticmethod
    def _scale_checkbox(widget, scale_factor):
        """Scale checkbox widget"""
        widget.configure(font=FontConfig.get_checkbox_font(scale_factor))
    
    @staticmethod
    def _scale_textbox(widget, scale_factor):
        """Scale textbox widget"""
        widget.configure(font=FontConfig.get_mono_font(scale_factor))
    
    @staticmethod
    def scale_frame_children(parent_frame, scale_factor, exclude_types=None):
        """Scale all children widgets in a frame"""
        if exclude_types is None:
            exclude_types = []
        
        for child in parent_frame.winfo_children():
            # Skip excluded widget types
            child_type = type(child).__name__
            if child_type in exclude_types:
                continue
            
            # Recursively scale children if it's a container
            if isinstance(child, (ctk.CTkFrame, ctk.CTkScrollableFrame)):
                UIScaling.scale_frame_children(child, scale_factor, exclude_types)
            else:
                # Try to determine widget type from its properties
                # Try to determine widget type from its properties
                widget_type = "button"

                text = ""
                try:
                    text = child.cget("text")
                except Exception:
                    pass

                if isinstance(child, ctk.CTkLabel):
                    widget_type = "label"
                if isinstance(child, ctk.CTkButton):
                    widget_type = "button"
                if isinstance(child, ctk.CTkEntry):
                    widget_type = "entry"

                # Extra logic based on text
                txt = text.lower() if isinstance(text, str) else ""
                if "title" in txt:
                    widget_type = "title"
                elif any(word in txt for word in ["start", "execute", "run", "launch"]):
                    widget_type = "button_large"
                elif any(word in txt for word in ["help", "report", "view"]):
                    widget_type = "button_small"

                UIScaling.scale_widget(child, widget_type, scale_factor)