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

def parse_ral_design_name(ral_name):
    parts = ral_name.split()
    h = int(parts[1])
    c = int(parts[2])
    l = int(parts[3])
    return h, c, l

def delta_e_cie2000(lab1, lab2):
    # Implementation of the CIEDE2000 formula
    L1, a1, b1 = lab1.lab_l, lab1.lab_a, lab1.lab_b
    L2, a2, b2 = lab2.lab_l, lab2.lab_a, lab2.lab_b

    kL, kC, kH = 1, 1, 1

    delta_L_prime = L2 - L1
    L_bar = (L1 + L2) / 2

    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    C_bar = (C1 + C2) / 2
    C_bar7 = C_bar**7

    G = 0.5 * (1 - np.sqrt(C_bar7 / (C_bar7 + 25**7)))

    a1_prime = a1 * (1 + G)
    a2_prime = a2 * (1 + G)
    C1_prime = np.sqrt(a1_prime**2 + b1**2)
    C2_prime = np.sqrt(a2_prime**2 + b2**2)
    C_bar_prime = (C1_prime + C2_prime) / 2

    h1_prime = np.degrees(np.arctan2(b1, a1_prime)) % 360
    h2_prime = np.degrees(np.arctan2(b2, a2_prime)) % 360

    H_bar_prime = (h1_prime + h2_prime) / 2 if abs(h1_prime - h2_prime) <= 180 else \
                  (h1_prime + h2_prime + 360) / 2 if h1_prime + h2_prime < 360 else \
                  (h1_prime + h2_prime - 360) / 2

    T = 1 - 0.17 * np.cos(np.radians(H_bar_prime - 30)) + 0.24 * np.cos(np.radians(2 * H_bar_prime)) + \
        0.32 * np.cos(np.radians(3 * H_bar_prime + 6)) - 0.20 * np.cos(np.radians(4 * H_bar_prime - 63))

    delta_h_prime = h2_prime - h1_prime if abs(h2_prime - h1_prime) <= 180 else \
                    h2_prime - h1_prime + 360 if h2_prime <= h1_prime else \
                    h2_prime - h1_prime - 360

    delta_C_prime = C2_prime - C1_prime
    delta_H_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(delta_h_prime / 2))

    S_L = 1 + ((0.015 * (L_bar - 50)**2) / np.sqrt(20 + (L_bar - 50)**2))
    S_C = 1 + 0.045 * C_bar_prime
    S_H = 1 + 0.015 * C_bar_prime * T

    delta_theta = 30 * np.exp(-(((H_bar_prime - 275) / 25)**2))
    R_C = 2 * np.sqrt(C_bar_prime**7 / (C_bar_prime**7 + 25**7))
    R_T = -R_C * np.sin(2 * np.radians(delta_theta))

    delta_E = np.sqrt(
        (delta_L_prime / (kL * S_L))**2 +
        (delta_C_prime / (kC * S_C))**2 +
        (delta_H_prime / (kH * S_H))**2 +
        R_T * (delta_C_prime / (kC * S_C)) * (delta_H_prime / (kH * S_H))
    )

    return delta_E

def find_closest_ral_colors(input_lab, ral_lab, num_matches, hue_range=None, lightness_range=None, chroma_range=None):
    differences = []
    for ral_name, ral_lab_values in ral_lab.items():
        if hue_range or lightness_range or chroma_range:
            h, c, l = parse_ral_design_name(ral_name)
            if hue_range and not (hue_range[0] <= h <= hue_range[1]):
                continue
            if lightness_range and not (lightness_range[0] <= l <= lightness_range[1]):
                continue
            if chroma_range and not (chroma_range[0] <= c <= chroma_range[1]):
                continue
        diff = delta_e_cie2000(input_lab, ral_lab_values)
        differences.append((diff, ral_name))
    
    differences.sort(key=lambda x: x[0])
    return differences[:num_matches]

st.title('Hex to RAL Color Matcher')

hex_color = st.text_input('Enter a HEX color (e.g., #2e2f33):', '#2e2f33')
palette_type = st.selectbox('Select RAL Palette', ['RAL Classic', 'RAL Design'])
num_matches = st.selectbox('Number of matches', list(range(1, 10)), index=8)

if palette_type == 'RAL Design':
    hue_range = st.slider('Hue range', 0, 360, (0, 360))
    lightness_range = st.slider('Lightness range', 0, 100, (0, 100))
    chroma_range = st.slider('Chroma range', 0, 100, (0, 100))
else:
    hue_range = lightness_range = chroma_range = None

if palette_type == 'RAL Classic':
    ral_palette = ral_classic_colors
    ral_lab = precomputed_lab['classic']
else:
    ral_palette = ral_design_colors
    ral_lab = precomputed_lab['design']

if hex_color:
    input_lab = hex_to_lab(hex_color)
    closest_colors = find_closest_ral_colors(input_lab, ral_lab, num_matches, hue_range, lightness_range, chroma_range)
    
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
