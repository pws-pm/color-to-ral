import streamlit as st
import json
from colormath.color_objects import sRGBColor, LabColor, LCHabColor
from colormath.color_conversions import convert_color
import numpy as np
import os

# Define paths to the JSON files relative to the script location
base_dir = os.path.dirname(os.path.abspath(__file__))
ral_classic_path = os.path.join(base_dir, 'ral-colors.json')
ral_design_path = os.path.join(base_dir, 'ral-design-plus-colors.json')

# Load RAL Classic and RAL Design data
with open(ral_classic_path, 'r') as file:
    ral_classic_colors = json.load(file)

with open(ral_design_path, 'r') as file:
    ral_design_colors = json.load(file)

def hex_to_oklch(hex_color):
    rgb = sRGBColor.new_from_rgb_hex(hex_color)
    lab = convert_color(rgb, LabColor)
    lch = convert_color(lab, LCHabColor)
    return (lch.lch_l, lch.lch_c, lch.lch_h)

def color_difference(oklch1, oklch2):
    return np.sqrt(sum((a - b) ** 2 for a, b in zip(oklch1, oklch2)))

def find_closest_ral_colors(hex_color, ral_palette, num_matches):
    target_oklch = hex_to_oklch(hex_color)
    differences = []
    for ral_name, ral_hex in ral_palette.items():
        ral_oklch = hex_to_oklch(ral_hex)
        diff = color_difference(target_oklch, ral_oklch)
        differences.append((diff, ral_hex, ral_name))
    differences.sort(key=lambda x: x[0])
    return differences[:num_matches]

st.title('Hex to RAL Color Matcher')

hex_color = st.text_input('Enter a HEX color (e.g., #34a8eb):', '#34a8eb')
palette_type = st.selectbox('Select RAL Palette', ['RAL Classic', 'RAL Design'])
num_matches = st.selectbox('Number of matches', list(range(1, 10)), index=2)

if palette_type == 'RAL Classic':
    ral_palette = ral_classic_colors
else:
    ral_palette = ral_design_colors

if hex_color:
    closest_colors = find_closest_ral_colors(hex_color, ral_palette, num_matches)
    
    # Display the input color
    st.markdown(f"<div style='text-align:center; padding:10px; font-size:24px;'>Input Color: {hex_color}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='background-color:{hex_color}; height:192px;'></div>", unsafe_allow_html=True)
    
    # Display the matching RAL colors
    for diff, ral_hex, ral_name in closest_colors:
        st.markdown(f"<div style='background-color:{ral_hex}; height:192px; margin:0;'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center; padding:10px; font-size:18px;'>{ral_name} - {ral_hex}</div>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .stTextInput div {text-align: center;}
    .stSelectbox div {text-align: center;}
    .stButton div {text-align: center;}
    .stButton button {margin: 0 auto;}
    </style>
    """,
    unsafe_allow_html=True
)
