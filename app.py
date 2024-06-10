import streamlit as st
import json
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
import numpy as np
import os

# Set Streamlit page configuration to fullscreen
st.set_page_config(layout="wide")

# Define paths to the JSON files relative to the script location
base_dir = os.path.dirname(os.path.abspath(__file__))
ral_classic_path = os.path.join(base_dir, 'ral-colors.json')
ral_design_path = os.path.join(base_dir, 'ral-design-plus-colors.json')

# Load RAL Classic and RAL Design data
with open(ral_classic_path, 'r') as file:
    ral_classic_colors = json.load(file)

with open(ral_design_path, 'r') as file:
    ral_design_colors = json.load(file)

def hex_to_lab(hex_color):
    rgb = sRGBColor.new_from_rgb_hex(hex_color)
    lab = convert_color(rgb, LabColor)
    return lab

def calculate_lab_values(ral_colors):
    lab_values = {}
    for ral_name, ral_hex in ral_colors.items():
        lab_values[ral_name] = hex_to_lab(ral_hex)
    return lab_values

# Precompute Lab values for RAL Classic and RAL Design colors
@st.cache_data
def get_precomputed_lab():
    return {
        'classic': calculate_lab_values(ral_classic_colors),
        'design': calculate_lab_values(ral_design_colors)
    }

precomputed_lab = get_precomputed_lab()

def delta_e_cie2000(lab1, lab2):
    # CIEDE2000 formula implementation
    L1, a1, b1 = lab1.lab_l, lab1.lab_a, lab1.lab_b
    L2, a2, b2 = lab2.lab_l, lab2.lab_a, lab2.lab_b
    
    # Mean values
    L_ = (L1 + L2) / 2
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    C_ = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(C_**7 / (C_**7 + 25**7)))
    
    a1_ = (1 + G) * a1
    a2_ = (1 + G) * a2
    C1_ = np.sqrt(a1_**2 + b1**2)
    C2_ = np.sqrt(a2_**2 + b2**2)
    C_ = (C1_ + C2_) / 2
    
    h1 = np.degrees(np.arctan2(b1, a1_)) % 360
    h2 = np.degrees(np.arctan2(b2, a2_)) % 360
    H_ = (h1 + h2) / 2 if np.abs(h1 - h2) <= 180 else (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2
    
    T = 1 - 0.17 * np.cos(np.radians(H_ - 30)) + 0.24 * np.cos(np.radians(2 * H_)) + 0.32 * np.cos(np.radians(3 * H_ + 6)) - 0.20 * np.cos(np.radians(4 * H_ - 63))
    dH = h2 - h1 if np.abs(h2 - h1) <= 180 else h2 - h1 + 360 if h2 <= h1 else h2 - h1 - 360
    dL_ = L2 - L1
    dC_ = C2_ - C1_
    dH_ = 2 * np.sqrt(C1_ * C2_) * np.sin(np.radians(dH / 2))
    
    S_L = 1 + (0.015 * (L_ - 50)**2) / np.sqrt(20 + (L_ - 50)**2)
    S_C = 1 + 0.045 * C_
    S_H = 1 + 0.015 * C_ * T
    R_T = -2 * np.sqrt(C_**7 / (C_**7 + 25**7)) * np.sin(np.radians(60 * np.exp(-((H_ - 275) / 25)**2)))
    
    dE = np.sqrt((dL_ / S_L)**2 + (dC_ / S_C)**2 + (dH_ / S_H)**2 + R_T * (dC_ / S_C) * (dH_ / S_H))
    
    return dE

def find_closest_ral_colors(input_lab, ral_lab, num_matches):
    differences = []
    for ral_name, ral_lab_values in ral_lab.items():
        diff = delta_e_cie2000(input_lab, ral_lab_values)
        differences.append((diff, ral_name))
    
    differences.sort(key=lambda x: x[0])
    return differences[:num_matches]

st.title('Hex to RAL Color Matcher')

hex_color = st.text_input('Enter a HEX color (e.g., #2e2f33):', '#2e2f33')
palette_type = st.selectbox('Select RAL Palette', ['RAL Classic', 'RAL Design'])
num_matches = st.selectbox('Number of matches', list(range(1, 10)), index=8)

if palette_type == 'RAL Classic':
    ral_palette = ral_classic_colors
    ral_lab = precomputed_lab['classic']
else:
    ral_palette = ral_design_colors
    ral_lab = precomputed_lab['design']

if hex_color:
    input_lab = hex_to_lab(hex_color)
    closest_colors = find_closest_ral_colors(input_lab, ral_lab, num_matches)
    
    # Display the input color
    st.markdown(f"<div style='text-align:center; padding:10px; font-size:24px;'>Input Color: {hex_color}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='background-color:{hex_color}; height:192px; width:100%;'></div>", unsafe_allow_html=True)
    
    # Display the matching RAL colors side by side
    cols = st.columns(num_matches)
    for i, (diff, ral_name) in enumerate(closest_colors):
        ral_hex = ral_palette[ral_name]
        with cols[i]:
            st.markdown(f"<div style='background-color:{ral_hex}; height:192px; margin:0;'></div>", unsafe_allow_html=True)
    
    # Display the hex and RAL codes below each swatch
    cols = st.columns(num_matches)
    for i, (diff, ral_name) in enumerate(closest_colors):
        ral_hex = ral_palette[ral_name]
        with cols[i]:
            st.markdown(f"<div style='text-align:center; padding:10px; font-size:18px;'>{ral_name} - {ral_hex}</div>", unsafe_allow_html=True)

# Custom CSS to remove gaps and make the app fullscreen
st.markdown(
    """
    <style>
    .css-18e3th9 {padding-top: 1rem; padding-bottom: 1rem;}
    .css-1d391kg {padding-top: 1rem; padding-bottom: 1rem;}
    .stTextInput div {text-align: center;}
    .stSelectbox div {text-align: center;}
    .stButton div {text-align: center;}
    .stButton button {margin: 0 auto;}
    .css-1outpf7 {padding: 0;}
    .css-12oz5g7 {padding: 0;}
    </style>
    """,
    unsafe_allow_html=True
)
