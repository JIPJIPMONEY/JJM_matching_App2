"""
Customer Loan Management App - Production Version v1.0
Docker-ready Streamlit application for managing customer loan records
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import json
from urllib.parse import urlparse
import requests
from PIL import Image

# Configure page
st.set_page_config(
    page_title="Back office matching v1.3",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Data paths - check both local and mounted data directory
DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."
EXCEL_FILE = os.path.join(DATA_DIR, "Customer_Loan_2025_06_07.xlsx")

# BRAND_KEYWORDS directory - check multiple possible locations
if os.path.exists("/app/BRAND_KEYWORDS"):
    # Running in Docker, keywords are in /app/BRAND_KEYWORDS
    KEYWORDS_DIR = "/app/BRAND_KEYWORDS"
elif os.path.exists(os.path.join(DATA_DIR, "BRAND_KEYWORDS")):
    # Running locally or keywords mounted in data directory
    KEYWORDS_DIR = os.path.join(DATA_DIR, "BRAND_KEYWORDS")
else:
    # Fallback to current directory
    KEYWORDS_DIR = "BRAND_KEYWORDS"

class DataManager:
    def __init__(self, excel_file=EXCEL_FILE):
        self.excel_file = excel_file
        self.data_cache = None
        self.modified_data = {}
        self.fixed_records = set()
        self.unfixed_records = set()
        
    def load_data(self):
        try:
            if self.data_cache is None:
                if not os.path.exists(self.excel_file):
                    st.error(f"❌ Excel file not found: {self.excel_file}")
                    st.info("💡 Please ensure your Excel file is in the data directory")
                    return None
                    
                self.data_cache = pd.read_excel(self.excel_file)
                
                # Check if Status column exists, if not create it
                if 'Status' not in self.data_cache.columns:
                    self.data_cache['Status'] = 0
                    st.success("📋 Added Status column (0=unfixed, 1=fixed)")
                    self.save_to_excel()
                
                # Load tracking data from Status column
                self.load_tracking_from_status()
                        
            return self.data_cache
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return None
    
    def load_tracking_from_status(self):
        """Load tracking data from the Status column"""
        if self.data_cache is not None and 'Status' in self.data_cache.columns:
            self.fixed_records = set(self.data_cache[self.data_cache['Status'] == 1].index)
            self.unfixed_records = set(self.data_cache[self.data_cache['Status'] == 0].index)
        else:
            self.unfixed_records = set(self.data_cache.index) if self.data_cache is not None else set()
            self.fixed_records = set()
    
    def save_to_excel(self, filename=None):
        """Save current data back to Excel file"""
        if self.data_cache is not None:
            if filename is None:
                filename = self.excel_file
            
            try:
                self.data_cache.to_excel(filename, index=False)
                return True
            except Exception as e:
                st.error(f"❌ Error saving to Excel: {e}")
                return False
        return False
    
    def get_record(self, index):
        if self.data_cache is not None and index in self.data_cache.index:
            return self.data_cache.iloc[index].to_dict()
        return None
    
    def update_record(self, index, updated_data):
        if self.data_cache is not None:
            for column, value in updated_data.items():
                if column in self.data_cache.columns:
                    self.data_cache.loc[index, column] = value
            
            self.modified_data[index] = updated_data
            
            # Update tracking in memory
            if index in self.unfixed_records:
                self.unfixed_records.remove(index)
            self.fixed_records.add(index)
            
            # Update Status column in the dataframe
            self.data_cache.loc[index, 'Status'] = 1
            
            # Save to Excel file immediately
            self.save_to_excel()
            
            return True
        return False
    
    def delete_record(self, index):
        """Delete a record from the dataframe"""
        if self.data_cache is not None and index in self.data_cache.index:
            try:
                # Remove from tracking sets
                if index in self.fixed_records:
                    self.fixed_records.remove(index)
                if index in self.unfixed_records:
                    self.unfixed_records.remove(index)
                
                # Remove from modified data if exists
                if index in self.modified_data:
                    del self.modified_data[index]
                
                # Drop the record from dataframe
                self.data_cache = self.data_cache.drop(index)
                
                # Reset index to avoid gaps
                self.data_cache = self.data_cache.reset_index(drop=True)
                
                # Update tracking sets with new indices
                self.load_tracking_from_status()
                
                # Save to Excel file immediately
                self.save_to_excel()
                
                return True
            except Exception as e:
                return False
        return False
    
    def unfix_record(self, index):
        """Change a record status from fixed back to unfixed"""
        if self.data_cache is not None and index in self.data_cache.index:
            try:
                # Update tracking in memory
                if index in self.fixed_records:
                    self.fixed_records.remove(index)
                self.unfixed_records.add(index)
                
                # Update Status column in the dataframe
                self.data_cache.loc[index, 'Status'] = 0
                
                # Save to Excel file immediately
                self.save_to_excel()
                
                return True
            except Exception as e:
                return False
        return False
    
    def bulk_unfix_records(self, indices):
        """Change multiple records status from fixed back to unfixed"""
        if self.data_cache is not None:
            try:
                success_count = 0
                for index in indices:
                    if index in self.data_cache.index:
                        # Update tracking in memory
                        if index in self.fixed_records:
                            self.fixed_records.remove(index)
                        self.unfixed_records.add(index)
                        
                        # Update Status column in the dataframe
                        self.data_cache.loc[index, 'Status'] = 0
                        success_count += 1
                
                # Save to Excel file once
                if success_count > 0:
                    self.save_to_excel()
                
                return success_count
            except Exception as e:
                return 0
        return 0
    
    def get_tracking_stats(self):
        return {
            'total': len(self.data_cache) if self.data_cache is not None else 0,
            'fixed': len(self.fixed_records),
            'unfixed': len(self.unfixed_records)
        }
    
    def export_to_excel(self, filename=None):
        """Export current data to Excel file"""
        if self.data_cache is not None:
            if filename is None:
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(DATA_DIR, f"Customer_Loan_Updated_{timestamp}.xlsx")
            
            try:
                self.data_cache.to_excel(filename, index=False)
                return filename
            except Exception as e:
                st.error(f"❌ Error exporting to Excel: {e}")
                return None
        return None
    
    def reset_tracking(self):
        """Reset all tracking data"""
        if self.data_cache is not None:
            self.fixed_records = set()
            self.unfixed_records = set(self.data_cache.index)
            self.data_cache['Status'] = 0
            self.save_to_excel()
            return True
        return False

class KeywordManager:
    def __init__(self, keywords_dir=KEYWORDS_DIR):
        self.keywords_dir = keywords_dir
        self.keywords_cache = {}
        self.global_data = {}
        self.load_all_keywords()
    
    def load_all_keywords(self):
        """Load brand keywords from JSON files listed in brands_list.txt"""
        try:
            if not os.path.exists(self.keywords_dir):
                return
                
            brands_list_file = os.path.join(self.keywords_dir, "brands_list.txt")
            
            if os.path.exists(brands_list_file):
                # Load brands from the brands_list.txt file
                with open(brands_list_file, 'r', encoding='utf-8') as f:
                    brand_files = [line.strip() for line in f 
                                 if line.strip() and not line.strip().startswith('#')]
                
                for brand_file in brand_files:
                    # Handle both old format (BRAND/file.json) and new format (file.json)
                    if '/' in brand_file:
                        # Old format: CHANEL/chanel_keywords.json
                        brand_name = brand_file.split('/')[0]
                        filename = brand_file.split('/')[1]
                    else:
                        # New format: chanel_keywords.json
                        filename = brand_file
                        brand_name = brand_file.replace('_keywords.json', '').replace('.json', '')
                    
                    # Try to find the file directly in keywords_dir
                    brand_path = os.path.join(self.keywords_dir, filename)
                    if os.path.exists(brand_path):
                        self.load_brand_keywords(brand_path, brand_name)
            else:
                # Fallback: auto-discover JSON files in the directory
                for item in os.listdir(self.keywords_dir):
                    if item.endswith('.json') and 'keywords' in item.lower():
                        brand_path = os.path.join(self.keywords_dir, item)
                        brand_name = item.replace('_keywords.json', '').replace('.json', '')
                        self.load_brand_keywords(brand_path, brand_name)
                            
            self.extract_global_data()
                            
        except Exception as e:
            pass
    
    def load_brand_keywords(self, json_path, brand_name):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.keywords_cache[brand_name.upper()] = data
        except Exception as e:
            pass
    
    def extract_global_data(self):
        """Extract global colors and materials from all brands"""
        all_colors = set()
        all_hardwares = set()
        
        for brand_data in self.keywords_cache.values():
            # Check for top-level colors first
            if 'colors' in brand_data:
                all_colors.update(brand_data['colors'])
            
            if 'hardwares' in brand_data:
                all_hardwares.update(brand_data['hardwares'])
            # Navigate through the nested structure: brand -> model -> submodel

        
        self.global_data = {
            'colors': sorted(list(all_colors)),
            'hardwares': sorted(list(all_hardwares))
        }
    
    def get_available_brands(self):
        return list(self.keywords_cache.keys())
    
    def get_brand_data(self, brand):
        return self.keywords_cache.get(brand.upper(), {})
    
    def get_global_colors(self):
        return self.global_data.get('colors', [])
    
    def get_global_materials(self):
        return self.global_data.get('hardwares', [])

def create_filters(df):
    """Create filter widgets with dependent dropdowns"""
    st.subheader("🔍 Filters")
    
    # First row: Status filter
    col_status = st.columns(1)[0]
    with col_status:
        status_options = ["All", "✅ Fixed", "❌ Unfixed"]
        filters = {}
        filters['status'] = st.selectbox("📊 Status", status_options, key="filter_status")
    
    # Second row: Other filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'Contract_Numbers' in df.columns:
            filters['contract'] = st.selectbox("Contract Number", ["All", "Not Empty", "Empty"])
        else:
            filters['contract'] = "All"
    
    with col2:
        if 'Types' in df.columns:
            unique_types = ['All'] + sorted([str(x) for x in df['Types'].dropna().unique() if str(x) != 'nan'])
            filters['type'] = st.selectbox("Type", unique_types, key="filter_type")
        else:
            filters['type'] = "All"
    
    with col3:
        if 'Brands' in df.columns and 'Types' in df.columns:
            if filters['type'] == "All":
                unique_brands = ['All'] + sorted([str(x) for x in df['Brands'].dropna().unique() if str(x) != 'nan'])
            else:
                type_filtered_df = df[df['Types'].astype(str) == filters['type']]
                unique_brands = ['All'] + sorted([str(x) for x in type_filtered_df['Brands'].dropna().unique() if str(x) != 'nan'])
            
            filters['brand'] = st.selectbox("Brand", unique_brands, key="filter_brand")
        else:
            filters['brand'] = "All"
    
    with col4:
        if 'Sub-Models' in df.columns and 'Types' in df.columns and 'Brands' in df.columns:
            filtered_for_submodel = df.copy()
            
            if filters['type'] != "All":
                filtered_for_submodel = filtered_for_submodel[filtered_for_submodel['Types'].astype(str) == filters['type']]
            
            if filters['brand'] != "All":
                filtered_for_submodel = filtered_for_submodel[filtered_for_submodel['Brands'].astype(str) == filters['brand']]
            
            unique_submodels = ['All'] + sorted([str(x) for x in filtered_for_submodel['Sub-Models'].dropna().unique() if str(x) != 'nan'])
            filters['submodel'] = st.selectbox("Sub-Model", unique_submodels, key="filter_submodel")
        else:
            filters['submodel'] = "All"
    
    # Show active filters
    active_filters = []
    if filters['status'] != "All":
        active_filters.append(f"Status='{filters['status']}'")
    if filters['type'] != "All":
        active_filters.append(f"Type='{filters['type']}'")
    if filters['brand'] != "All":
        active_filters.append(f"Brand='{filters['brand']}'")
    if filters['submodel'] != "All":
        active_filters.append(f"Sub-Model='{filters['submodel']}'")
    
    if active_filters:
        st.info(f"🔍 Active filters: {', '.join(active_filters)}")
    
    return filters

def apply_filters(df, filters):
    """Apply filters to dataframe"""
    filtered_df = df.copy()
    
    # Status filter
    if filters.get('status') == "✅ Fixed" and 'Status' in df.columns:
        filtered_df = filtered_df[filtered_df['Status'] == 1]
    elif filters.get('status') == "❌ Unfixed" and 'Status' in df.columns:
        filtered_df = filtered_df[filtered_df['Status'] == 0]
    
    # Contract filter
    if filters.get('contract') == "Not Empty" and 'Contract_Numbers' in df.columns:
        filtered_df = filtered_df[filtered_df['Contract_Numbers'].notna()]
    elif filters.get('contract') == "Empty" and 'Contract_Numbers' in df.columns:
        filtered_df = filtered_df[filtered_df['Contract_Numbers'].isna()]
    
    # Other filters
    if filters.get('type') != "All" and 'Types' in df.columns:
        filtered_df = filtered_df[filtered_df['Types'].astype(str) == filters['type']]
    
    if filters.get('brand') != "All" and 'Brands' in df.columns:
        filtered_df = filtered_df[filtered_df['Brands'].astype(str) == filters['brand']]
    
    if filters.get('submodel') != "All" and 'Sub-Models' in df.columns:
        filtered_df = filtered_df[filtered_df['Sub-Models'].astype(str) == filters['submodel']]
    
    return filtered_df

def create_edit_form(selected_row, keyword_manager, data_manager):
    """Create edit form with dependent dropdowns - compact version for right column"""
    
    # Initialize form state
    if 'form_state' not in st.session_state:
        st.session_state.form_state = {
            'brand': selected_row.get('Brands', ''),
            'model': selected_row.get('Models', ''),
            'submodel': selected_row.get('Sub-Models', ''),
            'size': selected_row.get('Sizes', ''),
            'color': selected_row.get('Colors', ''),
            'hardware': selected_row.get('Hardwares', ''),
            'material': selected_row.get('Materials', '')
        }
    
    # Brand dropdown
    brands = [''] + keyword_manager.get_available_brands()
    brand_idx = 0
    if st.session_state.form_state['brand'] in brands:
        brand_idx = brands.index(st.session_state.form_state['brand'])
    
    selected_brand = st.selectbox(
        "Brand", 
        brands, 
        index=brand_idx,
        key="edit_brand"
    )
    
    if selected_brand != st.session_state.form_state['brand']:
        st.session_state.form_state['brand'] = selected_brand
        st.session_state.form_state['model'] = ''
        st.session_state.form_state['submodel'] = ''
        st.session_state.form_state['size'] = ''
        st.session_state.form_state['material'] = ''
    
    # Model dropdown
    models = ['']
    if selected_brand:
        brand_data = keyword_manager.get_brand_data(selected_brand)
        if brand_data:
            models.extend(list(brand_data.keys()))
    
    model_idx = 0
    if st.session_state.form_state['model'] in models:
        model_idx = models.index(st.session_state.form_state['model'])
    
    selected_model = st.selectbox(
        "Model", 
        models, 
        index=model_idx,
        key="edit_model"
    )
    
    if selected_model != st.session_state.form_state['model']:
        st.session_state.form_state['model'] = selected_model
        st.session_state.form_state['submodel'] = ''
        st.session_state.form_state['size'] = ''
        st.session_state.form_state['material'] = ''
    
    # Sub-Model dropdown
    submodels = ['']
    if selected_brand and selected_model:
        brand_data = keyword_manager.get_brand_data(selected_brand)
        if brand_data and selected_model in brand_data:
            model_data = brand_data[selected_model]
            if isinstance(model_data, dict):
                submodels.extend(list(model_data.keys()))
    
    submodel_idx = 0
    if st.session_state.form_state['submodel'] in submodels:
        submodel_idx = submodels.index(st.session_state.form_state['submodel'])
    
    selected_submodel = st.selectbox(
        "Sub-Model", 
        submodels, 
        index=submodel_idx,
        key="edit_submodel"
    )
    
    if selected_submodel != st.session_state.form_state['submodel']:
        st.session_state.form_state['submodel'] = selected_submodel
        st.session_state.form_state['size'] = ''
        st.session_state.form_state['material'] = ''
    
    # Size dropdown
    sizes = ['']
    if selected_brand and selected_model and selected_submodel:
        brand_data = keyword_manager.get_brand_data(selected_brand)
        if (brand_data and 
            selected_model in brand_data and
            selected_submodel in brand_data[selected_model]):
            
            submodel_data = brand_data[selected_model][selected_submodel]
            if isinstance(submodel_data, dict) and 'sizes' in submodel_data:
                sizes.extend(submodel_data['sizes'])
    
    size_idx = 0
    if st.session_state.form_state['size'] in sizes:
        size_idx = sizes.index(st.session_state.form_state['size'])
    
    selected_size = st.selectbox(
        "Size", 
        sizes, 
        index=size_idx,
        key="edit_size"
    )
    
    if selected_size != st.session_state.form_state['size']:
        st.session_state.form_state['size'] = selected_size
    
    # Material dropdown
    materials = ['']
    if selected_brand and selected_model and selected_submodel:
        brand_data = keyword_manager.get_brand_data(selected_brand)
        if (brand_data and 
            selected_model in brand_data and
            selected_submodel in brand_data[selected_model]):
            
            submodel_data = brand_data[selected_model][selected_submodel]
            if isinstance(submodel_data, dict) and 'materials' in submodel_data:
                materials.extend(submodel_data['materials'])
    
    material_idx = 0
    if st.session_state.form_state['material'] in materials:
        material_idx = materials.index(st.session_state.form_state['material'])
    
    selected_material = st.selectbox(
        "Material", 
        materials, 
        index=material_idx,
        key="edit_material"
    )
    
    if selected_material != st.session_state.form_state['material']:
        st.session_state.form_state['material'] = selected_material
    
    # Color dropdown
    colors = [''] + keyword_manager.get_global_colors()
    color_idx = 0
    if st.session_state.form_state['color'] in colors:
        color_idx = colors.index(st.session_state.form_state['color'])
    
    selected_color = st.selectbox(
        "Color", 
        colors, 
        index=color_idx,
        key="edit_color"
    )
    
    if selected_color != st.session_state.form_state['color']:
        st.session_state.form_state['color'] = selected_color
    
    # Hardware dropdown
    hardwares = [''] + keyword_manager.get_global_materials()
    hardware_idx = 0
    if st.session_state.form_state['hardware'] in hardwares:
        hardware_idx = hardwares.index(st.session_state.form_state['hardware'])
    
    selected_hardware = st.selectbox(
        "Hardware", 
        hardwares, 
        index=hardware_idx,
        key="edit_hardware"
    )
    
    if selected_hardware != st.session_state.form_state['hardware']:
        st.session_state.form_state['hardware'] = selected_hardware
    
    # Update form state
    st.session_state.form_state.update({
        'brand': selected_brand,
        'model': selected_model,
        'submodel': selected_submodel,
        'size': selected_size,
        'color': selected_color,
        'hardware': selected_hardware,
        'material': selected_material
    })
    
    # Action buttons - stacked vertically for narrow column
    #st.markdown("---")
    
    if st.button("💾 Save Changes", type="primary", use_container_width=True):
        # Prepare updated data
        updated_data = {
            'Brands': selected_brand,
            'Models': selected_model,
            'Sub-Models': selected_submodel,
            'Sizes': selected_size,
            'Colors': selected_color,
            'Hardwares': selected_hardware,
            'Materials': selected_material
        }
        
        # Update the record
        success = data_manager.update_record(selected_row['_index'], updated_data)
        
        if success:
            st.success("✅ Record updated successfully!")
            st.session_state.selected_row = None
            st.session_state.show_edit_form = False
            st.session_state.edit_from_fixed = False  # Clear the flag
            if 'form_state' in st.session_state:
                del st.session_state.form_state
            st.rerun()
        else:
            st.error("❌ Failed to save changes")
    
    if st.button("🗑️ Delete Record", type="secondary", use_container_width=True):
        st.session_state.show_delete_popup = True
    
    if st.button("❌ Cancel", use_container_width=True):
        st.session_state.selected_row = None
        st.session_state.show_edit_form = False
        st.session_state.edit_from_fixed = False  # Clear the flag
        if 'form_state' in st.session_state:
            del st.session_state.form_state
        st.rerun()
    
    # Delete confirmation popup
    if st.session_state.get('show_delete_popup', False):
        @st.dialog("Delete Record")
        def delete_confirmation():
            st.error("⚠️ Are you sure you want to delete this record?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Yes, Delete", type="primary", use_container_width=True, key="confirm_delete_btn"):
                    success = data_manager.delete_record(selected_row['_index'])
                    
                    if success:
                        st.session_state.selected_row = None
                        st.session_state.show_edit_form = False
                        st.session_state.show_delete_popup = False
                        if 'form_state' in st.session_state:
                            del st.session_state.form_state
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete record")
            
            with col2:
                if st.button("❌ Cancel", use_container_width=True, key="cancel_delete_btn"):
                    st.session_state.show_delete_popup = False
                    st.rerun()
        
        delete_confirmation()

# Initialize session state
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()

if 'keyword_manager' not in st.session_state:
    st.session_state.keyword_manager = KeywordManager()

if 'selected_row' not in st.session_state:
    st.session_state.selected_row = None

if 'show_edit_form' not in st.session_state:
    st.session_state.show_edit_form = False

if 'show_delete_popup' not in st.session_state:
    st.session_state.show_delete_popup = False

if 'edit_from_fixed' not in st.session_state:
    st.session_state.edit_from_fixed = False

# Main app
def main():
    st.title("Back Office Matching v1.3")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        stats = st.session_state.data_manager.get_tracking_stats()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", stats['total'])
            st.metric("Fixed", stats['fixed'])
        with col2:
            st.metric("Unfixed", stats['unfixed'])
            if stats['total'] > 0:
                progress = stats['fixed'] / stats['total']
                st.metric("Progress", f"{progress:.1%}")
        
        if stats['total'] > 0:
            st.progress(stats['fixed'] / stats['total'])
        
        st.markdown("---")
        
        # Export controls
        st.subheader("💾 Data Export")
        
        if st.button("📁 Export to Excel", type="primary"):
            filename = st.session_state.data_manager.export_to_excel()
            if filename:
                st.success(f"✅ Exported: {os.path.basename(filename)}")
            else:
                st.error("❌ Export failed")
        
        # Reset option
        with st.expander("⚠️ Advanced Options"):
            if st.button("🔄 Reset All Status", type="secondary"):
                if st.session_state.data_manager.reset_tracking():
                    st.success("✅ All records reset to unfixed")
                    st.rerun()
                else:
                    st.error("❌ Reset failed")
        
        # System info
        st.markdown("---")
        st.caption("🐳 Running in Docker")
        st.caption(f"📁 Data: {DATA_DIR}")
        
        # Keywords info
        brands = st.session_state.keyword_manager.get_available_brands()
        if brands:
            st.caption(f"🏷️ Brands: {len(brands)}")
        else:
            st.caption("⚠️ No keyword files loaded")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Data Management", "✅ Fixed Records", "❌ Unfixed Records", "📖 User Manual"])
    
    with tab1:
        # Load data
        df = st.session_state.data_manager.load_data()
        
        if df is not None:
            st.success(f"✅ Loaded {len(df)} records successfully!")
            
            # Create three-column layout: Image Preview | Data Management | Edit Form
            col1, col2, col3 = st.columns([1, 2, 1])
            
            # Left Column: Image Preview
            with col1:
                st.header("🖼️ Image Preview")
                
                # Get current selection data
                current_selection = st.session_state.get('selected_row', None)
                
                if current_selection and 'Picture_url' in current_selection:
                    image_url = current_selection['Picture_url']
                    record_index = current_selection.get('_index', 'Unknown')
                    
                    if image_url and str(image_url) != 'nan' and str(image_url).strip():
                        try:
                            # Display the image
                            st.image(
                                image_url, 
                                caption=f"Product Image (Row {record_index})", 
                                use_container_width=True
                            )
                            
                            
                        except Exception as e:
                            st.error("Could not load image")
                            st.error(f"Error details: {str(e)}")
                            st.write(f"Image URL: {image_url}")

                    else:
                        st.info("No valid image URL available")
                        # Show record info even without image
                else:
                    st.info("Select a row to view image")
                    if current_selection:
                        st.write(f"Debug: Selected row exists but missing Picture_url field")
                        st.write(f"Available fields: {list(current_selection.keys())}")
            
            # Middle Column: Filters and Data Table
            with col2:
                # Filters
                filters = create_filters(df)
                filtered_df = apply_filters(df, filters)
                
                # Data table
                st.subheader(f"📋 Data Table ({len(filtered_df)} records)")
                
                if not filtered_df.empty:
                    display_df = filtered_df.copy()
                    
                    # Add visual Status column
                    if 'Status' in display_df.columns:
                        display_df['Status_Display'] = display_df['Status'].map({
                            0: '❌ Unfixed',
                            1: '✅ Fixed'
                        })
                        cols = ['Status_Display'] + [col for col in display_df.columns if col not in ['Status_Display', 'Status']]
                        display_df = display_df[cols]
                    
                    display_df_reset = display_df.reset_index(drop=False)
                    
                    # Configure columns
                    column_config = {
                        "Picture_url": st.column_config.LinkColumn(
                            "Picture URL",
                            help="Click to view image",
                            display_text="View Image"
                        ) if 'Picture_url' in display_df_reset.columns else None,
                        "Status_Display": st.column_config.TextColumn(
                            "Status",
                            help="Record status",
                            width="small"
                        ) if 'Status_Display' in display_df_reset.columns else None,
                    }
                    
                    if 'index' in display_df_reset.columns:
                        column_config["index"] = None
                    
                    # Display dataframe
                    event = st.dataframe(
                        display_df_reset,
                        use_container_width=True,
                        hide_index=True,
                        column_config=column_config,
                        on_select="rerun",
                        selection_mode="single-row",
                        height=400  # Fixed height to save space
                    )
                    
                    # Handle row selection
                    if event.selection.rows:
                        try:
                            selected_idx = event.selection.rows[0]
                            
                            # Get the original index from the filtered dataframe
                            if 'index' in display_df_reset.columns:
                                original_idx = display_df_reset.iloc[selected_idx]['index']
                            else:
                                # If no 'index' column, get from the filtered_df original index
                                original_idx = filtered_df.iloc[selected_idx].name
                            
                            # Always update if selection changed or no selection exists
                            current_selected_row = st.session_state.get('selected_row', None)
                            current_selection = current_selected_row.get('_index', None) if current_selected_row else None
                            
                            if current_selection != original_idx:
                                selected_data = df.loc[original_idx].to_dict()
                                selected_data['_index'] = original_idx
                                
                                st.session_state.selected_row = selected_data
                                st.session_state.show_edit_form = True
                                
                                # Clear form state when switching records
                                if 'form_state' in st.session_state:
                                    del st.session_state.form_state
                                
                                st.success(f"✅ Selected: Contract {selected_data.get('Contract_Numbers', 'N/A')} | Index: {original_idx}")
                                
                                # Force rerun to update image display
                                st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ Error selecting row: {str(e)}")
                            st.error(f"Debug info - Selected idx: {selected_idx}, Available rows: {len(display_df_reset)}")
                    else:
                        # Clear selection when no rows are selected
                        if st.session_state.get('selected_row') is not None:
                            st.session_state.selected_row = None
                            st.session_state.show_edit_form = False
                            if 'form_state' in st.session_state:
                                del st.session_state.form_state
                    
                    # Clear selection button
                    if st.session_state.selected_row is not None:
                        if st.button("🔄 Clear Selection", use_container_width=True):
                            st.session_state.selected_row = None
                            st.session_state.show_edit_form = False
                            if 'form_state' in st.session_state:
                                del st.session_state.form_state
                            st.rerun()
                else:
                    st.info("No records match the current filters.")
            
            # Right Column: Edit Form
            with col3:
                # Check if editing from Fixed Records tab
                if st.session_state.get('edit_from_fixed', False):
                    st.warning("⚠️ **Editing Fixed Record** - This record was previously marked as complete")
                
                st.header("✏️ Edit Record")
                if st.session_state.show_edit_form and st.session_state.selected_row:
                    create_edit_form(
                        st.session_state.selected_row,
                        st.session_state.keyword_manager,
                        st.session_state.data_manager
                    )
                else:
                    st.info("Select a record to edit")
        
        else:
            st.error("❌ Could not load Excel file")
            st.info("💡 Ensure your Excel file is mounted in the data directory")
    
    with tab2:
        st.header("✅ Fixed Records")
        stats = st.session_state.data_manager.get_tracking_stats()
        
        if stats['fixed'] > 0:
            df = st.session_state.data_manager.load_data()
            if df is not None:
                fixed_df = df[df['Status'] == 1].copy()
                
                st.subheader(f"Total Fixed Records: {len(fixed_df)}")
                
                # Display interactive dataframe for fixed records
                display_fixed_df = fixed_df.copy()
                display_fixed_df_reset = display_fixed_df.reset_index(drop=False)
                
                # Configure columns
                column_config = {
                    "Picture_url": st.column_config.LinkColumn(
                        "Picture URL",
                        help="Click to view image",
                        display_text="View Image"
                    ) if 'Picture_url' in display_fixed_df_reset.columns else None,
                }
                
                if 'index' in display_fixed_df_reset.columns:
                    column_config["index"] = None
                
                # Interactive dataframe for fixed records
                fixed_event = st.dataframe(
                    display_fixed_df_reset,
                    use_container_width=True,
                    hide_index=True,
                    column_config=column_config,
                    on_select="rerun",
                    selection_mode="multi-row"
                )
                
                # Handle selection for fixed records
                if fixed_event.selection.rows:
                    selected_indices = []
                    for selected_idx in fixed_event.selection.rows:
                        if 'index' in display_fixed_df_reset.columns:
                            original_idx = display_fixed_df_reset.iloc[selected_idx]['index']
                        else:
                            original_idx = fixed_df.iloc[selected_idx].name
                        selected_indices.append(original_idx)
                    
                    st.info(f"✅ Selected {len(selected_indices)} fixed record(s)")
                    
                    # Only Unfix Selected button
                    if st.button("🔄 Unfix Selected", type="primary", use_container_width=True):
                        success_count = st.session_state.data_manager.bulk_unfix_records(selected_indices)
                        if success_count > 0:
                            st.success(f"✅ {success_count} record(s) moved back to unfixed!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to unfix records")
                else:
                    st.info("Select one or more records to unfix them")
        else:
            st.info("No records have been fixed yet.")
    
    with tab3:
        st.header("❌ Unfixed Records")
        stats = st.session_state.data_manager.get_tracking_stats()
        
        if stats['unfixed'] > 0:
            df = st.session_state.data_manager.load_data()
            if df is not None:
                unfixed_df = df[df['Status'] == 0].copy()
                
                st.subheader(f"Total Unfixed Records: {len(unfixed_df)}")
                
                # Pagination
                page_size = 100
                total_pages = (len(unfixed_df) + page_size - 1) // page_size
                
                if total_pages > 1:
                    page = st.selectbox("Page", range(1, total_pages + 1))
                    start_idx = (page - 1) * page_size
                    end_idx = min(start_idx + page_size, len(unfixed_df))
                    page_df = unfixed_df.iloc[start_idx:end_idx]
                    st.info(f"Showing {start_idx + 1} to {end_idx} of {len(unfixed_df)} unfixed records")
                else:
                    page_df = unfixed_df
                
                st.dataframe(page_df, use_container_width=True)
        else:
            st.success("🎉 All records have been fixed!")
    
    with tab4:
        st.header("📖 User Manual - คู่มือการใช้งาน")
        
        # Overview Section
        st.subheader("🎯 เกี่ยวกับระบบ")
        st.write("ระบบ Back Office Matching เป็นเครื่องมือสำหรับการจัดการและแก้ไขข้อมูลสินค้าลูกค้า")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("🖼️ **แสดงรูปภาพสินค้า**\nดูรูปสินค้าขณะแก้ไขข้อมูล")
            st.info("🔍 **กรองข้อมูล**\nหาข้อมูลที่ต้องการได้อย่างรวดเร็ว")
        with col2:
            st.info("✏️ **แก้ไขข้อมูล**\nใช้ระบบ Dropdown ที่เชื่อมโยงกันอัตโนมัติ")
            st.info("🗑️ **ลบข้อมูล**\nลบข้อมูลที่ไม่ต้องการพร้อมระบบยืนยัน")
        with col3:
            st.info("📊 **ติดตามสถานะ**\nแยกข้อมูลที่แก้ไขแล้วและยังไม่แก้ไข")
            st.info("🔄 **คืนค่าก่อนแก้ไข**\nสามารถกดคืนค่าข้อมูลที่แก้ไขผิดได้")
        
        st.markdown("---")
        
        # How to Use Section
        st.subheader("วิธีการใช้งาน")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("** ขั้นตอนที่ 1: กรองข้อมูล**")
            st.write("• **Status:** ทั้งหมด / แก้ไขแล้ว / ยังไม่แก้ไข")
            st.write("• **Contract:** ทั้งหมด / มีข้อมูล / ไม่มีข้อมูล")
            st.write("• **Type, Brand, Sub-Model:** เลือกตามประเภทสินค้า")
            
            st.write("**📋 ขั้นตอนที่ 2: เลือกข้อมูล**")
            st.write("• คลิกที่แถวข้อมูลที่ต้องการแก้ไข")
            st.write("• รูปภาพจะแสดงทันทีทางด้านซ้าย")
            st.write("• ฟอร์มแก้ไขจะเปิดทางด้านขวา")
            
            st.write("**✏️ ขั้นตอนที่ 3: แก้ไขข้อมูล**")
            st.write("• เลือกตามลำดับ: Brand → Model → Sub-Model → Size → Material")
            st.write("• Color & Hardware เลือกได้อิสระ")
            st.write("• ตรวจสอบรูปภาพให้ตรงกับข้อมูล")
        
        with col2:
            st.write("**💾 ขั้นตอนที่ 4: บันทึกหรือลบ**")
            st.write("• **Save Changes:** บันทึกการแก้ไข")
            st.write("• **Delete Record:** ลบข้อมูล")
            st.write("• **Cancel:** ยกเลิกการแก้ไข")
            
            st.write("**🔄 ขั้นตอนที่ 5: คืนค่าการแก้ไข**")
            st.write("• **Unfixed Selected:** คืนค่าการแก้ไขข้อมูล")
            st.write("• **Multiple Select:** คืนค่าได้หลายแถวพร้อมกัน")
            
            st.write("**⚠️ ข้อควรระวัง**")
            st.warning("• **การลบข้อมูล:** ไม่สามารถกู้คืนได้")
            st.warning("• **การบันทึก:** ข้อมูลจะบันทึกลงไฟล์ Excel ทันที")
            st.warning("• **การปิดโปรแกรม:** บันทึกข้อมูลก่อนปิดเสมอ")
        
        st.markdown("---")
        
        # Troubleshooting
        st.subheader("🔧 การแก้ปัญหาเบื้องต้น")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**❌ รูปภาพไม่แสดง**")
            st.write("**วิธีแก้ไข:**")
            st.write("• ลองเลือกข้อมูลใหม่อีกครั้ง")
            st.write("• ตรวจสอบ Debug Info → Image URL")
            st.write("• ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต")
        
        with col2:
            st.write("**❌ Dropdown ไม่มีข้อมูล**")
            st.write("**วิธีแก้ไข:**")
            st.write("• เลือก Brand ใหม่อีกครั้ง")
            st.write("• ตรวจสอบว่าเลือก Brand ที่มีข้อมูล")
            st.write("• Refresh หน้าเว็บ (กด F5)")
        
        with col3:
            st.write("**❌ บันทึกไม่ได้**")
            st.write("**วิธีแก้ไข:**")
            st.write("• ตรวจสอบว่าปิดไฟล์ Excel แล้ว")
            st.write("• ลองเปลี่ยนข้อมูลอื่นแล้วบันทึกใหม่")
            st.write("• ติดต่อผู้ดูแลระบบ")
        
        st.markdown("---")
        
        # Contact
        st.subheader("📞 ติดต่อขอความช่วยเหลือ")
        st.info("**เมื่อพบปัญหา:** ทำตามขั้นตอนนี้ก่อนติดต่อผู้ดูแลระบบ")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**🔄 ลองแก้ไขเบื้องต้น**")
            st.write("• Refresh หน้าเว็บ (F5)")
            st.write("• Clear Selection และเลือกใหม่")
        with col2:
            st.write("**📝 บันทึกข้อมูล**")
            st.write("• บันทึกสิ่งที่เกิดขึ้น")
            st.write("• ถ่ายภาพหน้าจอ (Screenshot)")
        with col3:
            st.write("**📞 แจ้งผู้ดูแลระบบ**")
            st.write("• แจ้งข้อมูลที่บันทึกไว้")
            st.write("• ระบุหมายเลขแถวที่มีปัญหา")
            st.write("• **096-982-2813 (อู๋)**")
        
        st.success("🎉 เสร็จสิ้น! คุณพร้อมใช้งานระบบ Back Office Matching v1.1 แล้ว!")

if __name__ == "__main__":
    main()
