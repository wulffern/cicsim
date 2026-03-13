"""Centralized color theme definitions for cicwave.

This module is intentionally lightweight (no PySide6/pyqtgraph/numpy
imports) so that it can be imported from both the tkinter and PySide6
code paths without pulling in heavy dependencies.
"""

THEMES = {
    'dark': {
        'pg_background': 'k',
        'pg_foreground': 'w',
        'panel_bg': '#2b2b2b',
        'panel_fg': '#e0e0e0',
        'text_color': '#e0e0e0',
        'overlay_fill': (51, 51, 51, 220),
        'annotation_fill': (51, 51, 51, 200),
        'annotation_border': 'w',
        'title_color': 'w',
        'tree_default_fg': '#e0e0e0',
        'cursor_a': '#2196F3',
        'cursor_b': '#FF9800',
        'wave_colors': [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        ],
        'export_colors': [
            '#0060a8', '#d45800', '#1a8a1a', '#c02020', '#7040a0',
            '#6b4226', '#b8439e', '#505050', '#8a8c00', '#008fa8',
            '#2980b9', '#e67e22', '#27ae60', '#e74c3c', '#8e44ad',
        ],
        'export_annotation_color': '#333333',
        'export_annotation_bg': '#ffffcc',
        'export_annotation_ec': '#888888',
        'grid_pen': (255, 255, 255, 60),
        'export_stats_color': '#666666',
        'palette': {
            'Window': (43, 43, 43),
            'WindowText': (224, 224, 224),
            'Base': (30, 30, 30),
            'AlternateBase': (43, 43, 43),
            'ToolTipBase': (43, 43, 43),
            'ToolTipText': (224, 224, 224),
            'Text': (224, 224, 224),
            'Button': (53, 53, 53),
            'ButtonText': (224, 224, 224),
            'BrightText': (255, 50, 50),
            'Link': (42, 130, 218),
            'Highlight': (42, 130, 218),
            'HighlightedText': (0, 0, 0),
        },
    },
    'light': {
        'pg_background': 'w',
        'pg_foreground': 'k',
        'panel_bg': '#f0f0f0',
        'panel_fg': '#1a1a1a',
        'text_color': '#1a1a1a',
        'overlay_fill': (240, 240, 240, 230),
        'annotation_fill': (255, 255, 240, 220),
        'annotation_border': '#888888',
        'title_color': 'k',
        'tree_default_fg': '#1a1a1a',
        'cursor_a': '#1565C0',
        'cursor_b': '#E65100',
        'wave_colors': [
            '#0060a8', '#d45800', '#1a8a1a', '#c02020', '#7040a0',
            '#6b4226', '#b8439e', '#505050', '#8a8c00', '#008fa8',
            '#2980b9', '#e67e22', '#27ae60', '#e74c3c', '#8e44ad',
        ],
        'export_colors': [
            '#0060a8', '#d45800', '#1a8a1a', '#c02020', '#7040a0',
            '#6b4226', '#b8439e', '#505050', '#8a8c00', '#008fa8',
            '#2980b9', '#e67e22', '#27ae60', '#e74c3c', '#8e44ad',
        ],
        'export_annotation_color': '#333333',
        'export_annotation_bg': '#ffffcc',
        'export_annotation_ec': '#888888',
        'grid_pen': (0, 0, 0, 90),
        'export_stats_color': '#666666',
        'palette': {
            'Window': (240, 240, 240),
            'WindowText': (26, 26, 26),
            'Base': (255, 255, 255),
            'AlternateBase': (245, 245, 245),
            'ToolTipBase': (255, 255, 220),
            'ToolTipText': (26, 26, 26),
            'Text': (26, 26, 26),
            'Button': (225, 225, 225),
            'ButtonText': (26, 26, 26),
            'BrightText': (200, 30, 30),
            'Link': (42, 130, 218),
            'Highlight': (42, 130, 218),
            'HighlightedText': (255, 255, 255),
        },
    },
}

_active_theme = THEMES['dark']


def _get_theme():
    return _active_theme


def _set_active_theme(name):
    global _active_theme
    _active_theme = THEMES[name]
