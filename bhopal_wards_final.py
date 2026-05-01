#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 11:00:57 2026

@author: neeravsharma
"""

import streamlit as st
import folium
import geopandas as gpd
import pandas as pd
import numpy as np
from streamlit_folium import st_folium

# ==============================
# PAGE CONFIG (optional but good)
# ==============================
st.set_page_config(layout="wide")

# ==============================
# LOAD DATA (RELATIVE PATH)
# ==============================
shp_path = "wards_with_pop.shp"

gdf = gpd.read_file(shp_path)
gdf = gdf.to_crs("EPSG:4326")

# Ensure ward name exists
if "ward_name" not in gdf.columns:
    gdf["ward_name"] = "Ward " + gdf["code"].astype(str)

# ==============================
# POPULATION DENSITY
# ==============================
gdf["population"] = gdf["wards_70po"]

proj = gdf.to_crs("EPSG:32644")
gdf["area"] = proj.geometry.area

gdf["density"] = gdf["population"] / (gdf["area"] / 1e6)

gdf["density_norm"] = (gdf["density"] - gdf["density"].min()) / (
    gdf["density"].max() - gdf["density"].min()
)

# ==============================
# SYNTHETIC RISK (TEMPORARY)
# ==============================
np.random.seed(42)

gdf["risk"] = (
    0.6 * gdf["density_norm"] +
    0.4 * np.random.rand(len(gdf))
)

gdf["risk_norm"] = (gdf["risk"] - gdf["risk"].min()) / (
    gdf["risk"].max() - gdf["risk"].min()
)

# ==============================
# PRIORITY SCORE
# ==============================
gdf["priority_score"] = (
    0.6 * gdf["risk_norm"] +
    0.4 * gdf["density_norm"]
)

gdf["priority_rank"] = gdf["priority_score"].rank(ascending=False)

# 🔥 Top 10 selection
top_wards = gdf.sort_values("priority_score", ascending=False).head(10)

# ==============================
# CLASSIFICATION
# ==============================
gdf["density_class"] = pd.qcut(
    gdf["density_norm"],
    4,
    labels=["Low", "Moderate", "High", "Very High"],
    duplicates="drop"
)

gdf["risk_class"] = pd.qcut(
    gdf["risk_norm"],
    4,
    labels=["Low", "Moderate", "High", "Very High"],
    duplicates="drop"
)

# ==============================
# SIDEBAR CONTROLS
# ==============================
st.sidebar.title("Layer Control")

show_density = st.sidebar.checkbox("Population Density", True)
show_risk = st.sidebar.checkbox("Dengue Risk", False)
show_priority = st.sidebar.checkbox("🔥 Top 10 Priority Wards", True)

# ==============================
# COLOR FUNCTIONS
# ==============================
def density_color(x):
    return {
        "Low": "#2ecc71",
        "Moderate": "#f1c40f",
        "High": "#e67e22",
        "Very High": "#e31a1c"
    }.get(str(x), "#cccccc")

def risk_color(x):
    return {
        "Low": "#fff7bc",
        "Moderate": "#fec44f",
        "High": "#fe9929",
        "Very High": "#e31a1c"
    }.get(str(x), "#cccccc")

# ==============================
# TOOLTIP (HOVER INFO)
# ==============================
tooltip = folium.GeoJsonTooltip(
    fields=["code", "ward_name", "population", "density", "risk_norm", "priority_score"],
    aliases=[
        "Ward No:",
        "Ward Name:",
        "Population:",
        "Density:",
        "Risk:",
        "Priority Score:"
    ],
    localize=True
)

# ==============================
# MAP
# ==============================
m = folium.Map(location=[23.25, 77.41], zoom_start=11)

# Always show boundaries
folium.GeoJson(
    gdf,
    style_function=lambda x: {
        "fillOpacity": 0,
        "color": "black",
        "weight": 1
    }
).add_to(m)

# Density layer
if show_density:
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            "fillColor": density_color(x["properties"].get("density_class")),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.6
        },
        tooltip=tooltip
    ).add_to(m)

# Risk layer
if show_risk:
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            "fillColor": risk_color(x["properties"].get("risk_class")),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.6
        },
        tooltip=tooltip
    ).add_to(m)

# 🔥 Top 10 priority layer
if show_priority:
    folium.GeoJson(
        top_wards,
        style_function=lambda x: {
            "fillColor": "#8e44ad",
            "color": "black",
            "weight": 2,
            "fillOpacity": 0.85
        },
        tooltip=tooltip
    ).add_to(m)

# ==============================
# DISPLAY MAP
# ==============================
st.title("🦟 Dengue Risk Decision Dashboard")

st_folium(m, width=1200, height=700)

# ==============================
# METRICS
# ==============================
st.subheader("📊 Key Metrics")

col1, col2 = st.columns(2)
col1.metric("Total Wards", len(gdf))
col2.metric("Top Priority Wards", len(top_wards))

# ==============================
# TABLE
# ==============================
st.subheader("🔥 Top 10 Priority Wards")

top_wards_display = top_wards[[
    "code", "ward_name", "risk_norm"
]].rename(columns={
    "code": "Ward Number",
    "ward_name": "Ward Name",
    "risk_norm": "Risk"
})

st.dataframe(top_wards_display)

# ==============================
# DOWNLOAD
# ==============================
csv = gdf.to_csv(index=False)

st.download_button(
    "Download Ward Priority Data",
    csv,
    "ward_priority.csv",
    "text/csv"
)