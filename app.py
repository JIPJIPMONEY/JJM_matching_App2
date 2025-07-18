"""
Customer Loan Management App - Production Version v2.0 (PostgreSQL)
Docker-ready Streamlit application for managing customer loan records with PostgreSQL database
"""

import streamlit as st
import pandas as pd
import os
import json
from sqlalchemy import create_engine, text
from urllib.parse import urlparse
import requests
from PIL import Image
import hashlib

# Authentication configuration
USER_CREDENTIALS = {
    "admin": "admin8558",
    "Build@CS": "NRJ24017", 
    "Pin@SCL": "NRJ23006",
    "Knight@SCL": "NRJ23004",
    "Gun@SCL":"NRJ24027"
}

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a password against its hash"""
    return stored_password == provided_password

def authenticate_user(username, password):
    """Authenticate user credentials"""
    if username in USER_CREDENTIALS:
        return verify_password(USER_CREDENTIALS[username], password)
    return False

def show_login_page():
    """Display login page"""
    st.title("🔐 Login Required")
    st.subheader("Back Office Matching v2.0")
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        
        with st.form("login_form"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            login_button = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if login_button:
                if authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"✅ Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

def logout():
    """Logout function"""
    st.session_state.authenticated = False
    st.session_state.username = None
    if 'data_manager' in st.session_state:
        del st.session_state.data_manager
    if 'keyword_manager' in st.session_state:
        del st.session_state.keyword_manager
    st.rerun()

# Import database models and managers
from models import Base, Brand, Model, ModelSize, ModelMaterial, BrandColor, BrandHardware, create_tables
from database_keyword_manager import DatabaseKeywordManager

# Configure page
if not st.session_state.get('authenticated', False):
    st.set_page_config(
        page_title="Login - Back Office Matching v2.0",
        page_icon="🔐",
        layout="centered"
    )
else:
    st.set_page_config(
        page_title="Back office matching v2.0",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

# Database configuration
db_config = {
    'user': 'postgres',
    'password': '8558',
    'host': '192.168.1.76',
    'port': '5432',
    'database': 'jjm_database'
}

# Data paths - check both local and mounted data directory (for keywords only now)
DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."

class DataManager:
    """
    Data Manager for PostgreSQL operations using SQLAlchemy only
    - All database operations use SQLAlchemy engine for consistency
    - Eliminates pandas warnings and provides unified database interface
    """
    def __init__(self, db_config=db_config):
        self.db_config = db_config
        self.data_cache = None
        self.fixed_records = set()
        self.unfixed_records = set()
        self.table_name = "jjm_customer_loan"  # Your existing table name
        self.engine = None
        
    # ...existing code...
    def get_engine(self):
        """Create SQLAlchemy engine with connection pooling for better performance"""
        if self.engine is None:
            try:
                connection_string = (
                    f"postgresql://{self.db_config['user']}:{self.db_config['password']}"
                    f"@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                )
                # Add connection pooling and performance optimizations
                self.engine = create_engine(
                    connection_string,
                    pool_size=10,          # Number of connections to maintain
                    max_overflow=20,       # Additional connections when needed
                    pool_pre_ping=True,    # Verify connections before use
                    pool_recycle=3600,     # Recycle connections every hour
                    echo=False             # Set to True for debugging SQL queries
                )
            except Exception as e:
                st.error(f"❌ SQLAlchemy engine creation failed: {str(e)}")
                return None
        return self.engine
    # ...existing code...
    
    #def test_connections(self):
        #"""Test SQLAlchemy connection"""
        #test_results = {
            #'sqlalchemy': False,
            #'errors': []
        #}
        
        ## Test SQLAlchemy engine
        #try:
            #engine = self.get_engine()
            #if engine:
                # Test with a simple query using text()
                #pd.read_sql_query(text("SELECT 1 as test"), engine)
                #test_results['sqlalchemy'] = True
        #except Exception as e:
            #test_results['errors'].append(f"SQLAlchemy test failed: {str(e)}")
        
        #return test_results
    
    def load_data(self):
        """Load data from PostgreSQL database using SQLAlchemy with optimizations"""
        try:
            if self.data_cache is None:
                # Add progress indicator
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Connecting to database...")
                progress_bar.progress(0.1)
                
                engine = self.get_engine()
                if engine is None:
                    progress_bar.empty()
                    status_text.empty()
                    return None
                
                status_text.text("Executing query...")
                progress_bar.progress(0.3)
                
                # Load data in chunks for better performance
                query = text(f"SELECT * FROM {self.table_name} ORDER BY form_id")
                
                chunk_size = 10000
                chunks = []
                
                with engine.connect() as conn:
                    result = conn.execute(query)
                    while True:
                        chunk = result.fetchmany(chunk_size)
                        if not chunk:
                            break
                        chunks.append(pd.DataFrame(chunk))
                        status_text.text(f"Loading data... {len(chunks)} chunks processed")
                        progress_bar.progress(min(0.7, 0.3 + (len(chunks) * 0.1)))
                
                status_text.text("Processing data...")
                progress_bar.progress(0.8)
                
                # Combine all chunks
                if chunks:
                    self.data_cache = pd.concat(chunks, ignore_index=True)
                else:
                    self.data_cache = pd.DataFrame()
                
                # Map your database columns to the app's expected column names
                column_mapping = {
                    'form_id': 'Form_ids',
                    'contract_num': 'Contract_Numbers', 
                    'type': 'Types',
                    'brand': 'Brands',
                    'model': 'Models',
                    'sub_model': 'Sub-Models',
                    'size': 'Sizes',
                    'color': 'Colors',
                    'hardware': 'Hardwares',
                    'material': 'Materials',
                    'picture_url': 'Picture_url',
                    'status': 'Status',
                    'editor': 'Editor',
                    'updated_at': 'Updated_at'
                }
                
                # Rename columns efficiently
                self.data_cache = self.data_cache.rename(columns=column_mapping)
                
                # Handle missing columns and null values efficiently
                self._prepare_data_columns()
                
                progress_bar.progress(0.9)
                
                # Load tracking data from Status column
                self.load_tracking_from_status()
                
                progress_bar.progress(1.0)
                status_text.text("Data loaded successfully!")
                
                # Clean up progress indicators
                import time
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                        
            return self.data_cache
        except Exception as e:
            st.error(f"❌ Error loading data from database: {str(e)}")
            return None
    
    def _prepare_data_columns(self):
        """Prepare data columns efficiently"""
        # Handle Status column
        if 'Status' not in self.data_cache.columns:
            self.data_cache['Status'] = 0
        else:
            self.data_cache['Status'] = self.data_cache['Status'].fillna(0).astype(int)
        
        # Handle Editor column
        if 'Editor' not in self.data_cache.columns:
            self.data_cache['Editor'] = ''
        else:
            self.data_cache['Editor'] = self.data_cache['Editor'].fillna('')
        
        # Handle Updated_at column
        if 'Updated_at' not in self.data_cache.columns:
            self.data_cache['Updated_at'] = pd.NaT
        else:
            self.data_cache['Updated_at'] = pd.to_datetime(self.data_cache['Updated_at'], errors='coerce')
    # ...existing code...
    
    def load_tracking_from_status(self):
        """Load tracking data from the Status column"""
        if self.data_cache is not None and 'Status' in self.data_cache.columns:
            self.fixed_records = set(self.data_cache[self.data_cache['Status'] == 1].index)
            self.unfixed_records = set(self.data_cache[self.data_cache['Status'] == 0].index)
        else:
            self.unfixed_records = set(self.data_cache.index) if self.data_cache is not None else set()
            self.fixed_records = set()
    
    def save_single_record(self, index):
        """Update only one specific record in the database - OPTIMIZED for single changes"""
        if self.data_cache is not None and index in self.data_cache.index:
            try:
                engine = self.get_engine()
                if engine is None:
                    return False
                
                # Get the specific record to update
                row = self.data_cache.iloc[index]
                form_id = row.get('Form_ids', row.get('form_id'))
                
                # Update only this specific record using SQLAlchemy
                with engine.begin() as conn:
                    update_sql = text(f"""
                    UPDATE {self.table_name} 
                    SET contract_num = :contract_num, type = :type, brand = :brand, model = :model, 
                        sub_model = :sub_model, size = :size, color = :color, hardware = :hardware, 
                        material = :material, picture_url = :picture_url, status = :status, editor = :editor
                    WHERE form_id = :form_id
                    """)
                    
                    result = conn.execute(update_sql, {
                        'contract_num': row.get('Contract_Numbers'),
                        'type': row.get('Types'),
                        'brand': row.get('Brands'),
                        'model': row.get('Models'),
                        'sub_model': row.get('Sub-Models'),
                        'size': row.get('Sizes'),
                        'color': row.get('Colors'),
                        'hardware': row.get('Hardwares'),
                        'material': row.get('Materials'),
                        'picture_url': row.get('Picture_url'),
                        'status': int(row.get('Status', 0)),
                        'editor': row.get('Editor', ''),
                        'form_id': int(form_id)
                    })
                    
                    if result.rowcount == 0:
                        st.warning(f"⚠️ No record found with form_id {form_id}")
                        return False
                
                # After successful database update, refresh the local cache with the updated record
                # This ensures the trigger-updated timestamp is reflected in our local data
                self.refresh_single_record(int(form_id), index)
                
                return True
                
            except Exception as e:
                st.error(f"❌ Error updating single record: {e}")
                return False
        return False
    
    def get_record(self, index):
        if self.data_cache is not None and index in self.data_cache.index:
            return self.data_cache.iloc[index].to_dict()
        return None
    
    def update_record(self, index, updated_data, keep_as_fixed=True):
        if self.data_cache is not None:
            # Add current user as editor
            current_user = st.session_state.get('username', 'Unknown')
            updated_data['Editor'] = current_user
            
            for column, value in updated_data.items():
                if column in self.data_cache.columns:
                    self.data_cache.loc[index, column] = value
            
            # Update tracking in memory based on keep_as_fixed parameter
            if keep_as_fixed:
                # Keep as fixed (default behavior)
                if index in self.unfixed_records:
                    self.unfixed_records.remove(index)
                self.fixed_records.add(index)
                self.data_cache.loc[index, 'Status'] = 1
            else:
                # Mark as unfixed (when editing from fixed records and choosing to unfix)
                if index in self.fixed_records:
                    self.fixed_records.remove(index)
                self.unfixed_records.add(index)
                self.data_cache.loc[index, 'Status'] = 0
            
            # Save only this specific record to database
            return self.save_single_record(index)
        return False
    
    def delete_record(self, index):
        """Delete a record from the dataframe and database using SQLAlchemy"""
        if self.data_cache is not None and index in self.data_cache.index:
            try:
                # Get the form_id of the record to delete
                form_id = self.data_cache.loc[index, 'Form_ids']
                
                # Delete from database first using SQLAlchemy
                engine = self.get_engine()
                if engine:
                    with engine.begin() as conn:  # Use begin() for automatic transaction management
                        delete_sql = text(f"DELETE FROM {self.table_name} WHERE form_id = :form_id")
                        result = conn.execute(delete_sql, {'form_id': int(form_id)})  # Ensure form_id is int
                        
                        if result.rowcount == 0:
                            st.warning(f"⚠️ No record found with form_id {form_id}")
                            return False
                
                # Remove from tracking sets
                if index in self.fixed_records:
                    self.fixed_records.remove(index)
                if index in self.unfixed_records:
                    self.unfixed_records.remove(index)
                
                # Drop the record from dataframe
                self.data_cache = self.data_cache.drop(index)
                
                # Reset index to avoid gaps
                self.data_cache = self.data_cache.reset_index(drop=True)
                
                # Update tracking sets with new indices
                self.load_tracking_from_status()
                
                return True
            except Exception as e:
                st.error(f"❌ Error deleting record: {str(e)}")
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
                
                # Keep the editor information - don't clear it
                # User progress tracking will filter by status = 1 instead
                
                # Save only this specific record to database
                return self.save_single_record(index)
                
            except Exception as e:
                st.error(f"❌ Error unfixing record: {str(e)}")
                return False
        return False
    
    def refresh_single_record(self, form_id, index):
        """Refresh a single record from database to get the latest data including trigger-updated fields"""
        try:
            engine = self.get_engine()
            if engine is None:
                return False
            
            # Fetch the updated record from database
            with engine.begin() as conn:
                fetch_sql = text(f"""
                SELECT * FROM {self.table_name} WHERE form_id = :form_id
                """)
                result = conn.execute(fetch_sql, {'form_id': form_id})
                row = result.fetchone()
                
                if row:
                    # Convert row to dict and map column names
                    row_dict = dict(row._mapping)
                    
                    # Map database columns to app columns
                    column_mapping = {
                        'form_id': 'Form_ids',
                        'contract_num': 'Contract_Numbers', 
                        'type': 'Types',
                        'brand': 'Brands',
                        'model': 'Models',
                        'sub_model': 'Sub-Models',
                        'size': 'Sizes',
                        'color': 'Colors',
                        'hardware': 'Hardwares',
                        'material': 'Materials',
                        'picture_url': 'Picture_url',
                        'status': 'Status',
                        'editor': 'Editor',
                        'updated_at': 'Updated_at'
                    }
                    
                    # Update the specific row in data_cache with fresh database values
                    for db_col, app_col in column_mapping.items():
                        if db_col in row_dict and app_col in self.data_cache.columns:
                            self.data_cache.loc[index, app_col] = row_dict[db_col]
                    
                    return True
                    
        except Exception as e:
            st.error(f"❌ Error refreshing record {form_id}: {e}")
            
        return False
    
    def get_tracking_stats(self):
        return {
            'total': len(self.data_cache) if self.data_cache is not None else 0,
            'fixed': len(self.fixed_records),
            'unfixed': len(self.unfixed_records)
        }
    
    def get_user_daily_progress(self, target_date=None):
        """Get daily progress for all users"""
        if self.data_cache is None:
            return {}
        
        # Use today if no date specified
        if target_date is None:
            target_date = pd.Timestamp.now().date()
        else:
            target_date = pd.to_datetime(target_date).date()
        
        progress_data = {}
        
        # Check if Updated_at column exists
        if 'Updated_at' in self.data_cache.columns and 'Editor' in self.data_cache.columns:
            # Convert Updated_at to datetime if it's not already
            df_copy = self.data_cache.copy()
            
            # Handle different datetime formats and NULL values
            try:
                # Convert to datetime, coercing errors (NULL/invalid values become NaT)
                df_copy['Updated_at'] = pd.to_datetime(df_copy['Updated_at'], errors='coerce')
                
                # Filter out records with NULL/NaT Updated_at values before date comparison
                df_with_dates = df_copy.dropna(subset=['Updated_at'])
                
                # Filter records for the target date AND status = 1 (fixed)
                if len(df_with_dates) > 0:
                    df_today = df_with_dates[
                        (df_with_dates['Updated_at'].dt.date == target_date) & 
                        (df_with_dates['Status'] == 1)
                    ]
                    
                    # Count records per user for today (only fixed records)
                    user_counts = df_today.groupby('Editor').size().to_dict()
                else:
                    user_counts = {}
                
                # Get all unique users (including those who haven't worked today)
                # Include users from all records, not just today's
                all_users = df_copy['Editor'].dropna().unique()
                
                # Create progress data for all users
                for user in all_users:
                    if user and user != "admin":  # Skip empty usernames
                        count = user_counts.get(user, 0)
                        progress_data[user] = {
                            'count': count,
                            'target': 50,
                            'percentage': min(100, (count / 50) * 100)
                        }
                        
            except Exception as e:
                st.error(f"Error calculating user progress: {e}")
                # Return empty progress for all known users
                try:
                    all_users = self.data_cache['Editor'].dropna().unique()
                    for user in all_users:
                        if user and user.strip() and user != "admin":
                            progress_data[user] = {
                                'count': 0,
                                'target': 50,
                                'percentage': 0
                            }
                except:
                    pass
                return progress_data
        
        return progress_data
    
    #def export_to_excel(self, filename=None):
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

class KeywordManager:
    """
    Database-based keyword manager that reads brand data from PostgreSQL database
    Provides the same interface as the original JSON-based KeywordManager
    """
    
    def __init__(self, db_config=db_config):
        self.db_config = db_config
        self.session = None
        self.engine = None
        self.global_data = {}
        self.brands_cache = {}
        self.keywords_loaded = False  # Flag to track if keywords are loaded
        self.connect_to_database()
        self.load_all_keywords()
    
    def connect_to_database(self):
        """Establish database connection"""
        try:
            from models import get_session
            self.session, self.engine = get_session(self.db_config)
            return True
        except Exception as e:
            st.error(f"❌ Failed to connect to keyword database: {e}")
            return False
    
    def load_all_keywords(self, force_reload=False):
        """Load all brand keywords from database and cache them"""
        # Only load if not already loaded or force reload is requested
        if self.keywords_loaded and not force_reload:
            return
            
        try:
            if not self.session:
                return
            
            from models import Brand, Model, ModelSize, ModelMaterial, BrandColor, BrandHardware
            from sqlalchemy.orm import joinedload
            from sqlalchemy.orm import selectinload
            # Clear cache before reloading
            self.brands_cache = {}
            self.global_data = {}
            
            # Load all brands with their related data
            # ...existing code...
            brands = self.session.query(Brand).options(
                selectinload(Brand.models).selectinload(Model.sizes),
                selectinload(Brand.models).selectinload(Model.materials),
                selectinload(Brand.colors),
                selectinload(Brand.hardwares)
            ).all()
            # ...existing code...
            
            # Cache brand data in the same format as JSON-based system
            for brand in brands:
                brand_data = {}
                
                # Group models by collection
                collections = {}
                for model in brand.models:
                    collection = model.collection or "default"
                    if collection not in collections:
                        collections[collection] = {}
                    
                    # Add model with sizes and materials
                    model_data = {}
                    if model.sizes:
                        model_data['sizes'] = [size.size for size in model.sizes]
                    if model.materials:
                        model_data['materials'] = [material.material for material in model.materials]
                    
                    collections[collection][model.model_name] = model_data
                
                # Add collections to brand data
                brand_data.update(collections)
                
                # Add global colors and hardwares
                if brand.colors:
                    brand_data['colors'] = [color.color for color in brand.colors]
                if brand.hardwares:
                    brand_data['hardwares'] = [hardware.hardware for hardware in brand.hardwares]
                
                # Cache the brand data
                self.brands_cache[brand.name.upper()] = brand_data
            
            # Extract global data
            self.extract_global_data()
            
            # Mark as loaded
            self.keywords_loaded = True
            
        except Exception as e:
            st.error(f"❌ Error loading keywords from database: {e}")
            self.keywords_loaded = False
    
    def extract_global_data(self):
        """Extract colors and materials organized by brand and globally"""
        all_colors = set()
        all_hardwares = set()
        brand_colors = {}
        brand_hardwares = {}
        
        for brand_name, brand_data in self.brands_cache.items():
            brand_colors[brand_name] = set()
            brand_hardwares[brand_name] = set()
            
            # Check for top-level colors and hardwares
            if 'colors' in brand_data:
                brand_colors[brand_name].update(brand_data['colors'])
                all_colors.update(brand_data['colors'])
            
            if 'hardwares' in brand_data:
                brand_hardwares[brand_name].update(brand_data['hardwares'])
                all_hardwares.update(brand_data['hardwares'])
        
        self.global_data = {
            'colors': sorted(list(all_colors)),
            'hardwares': sorted(list(all_hardwares)),
            'brand_colors': {brand: sorted(list(colors)) for brand, colors in brand_colors.items()},
            'brand_hardwares': {brand: sorted(list(hardwares)) for brand, hardwares in brand_hardwares.items()}
        }
    
    def get_available_brands(self):
        """Get list of available brands"""
        return list(self.brands_cache.keys())
    
    def get_brand_data(self, brand):
        """Get data for a specific brand"""
        return self.brands_cache.get(brand.upper(), {})
    
    def get_global_colors(self):
        """Get all colors across all brands"""
        return self.global_data.get('colors', [])
    
    def get_global_materials(self):
        """Get all hardwares/materials across all brands"""
        return self.global_data.get('hardwares', [])
    
    def get_brand_colors(self, brand):
        """Get colors specific to a brand"""
        if brand:
            return self.global_data.get('brand_colors', {}).get(brand.upper(), [])
        return self.get_global_colors()
    
    def get_brand_hardwares(self, brand):
        """Get hardwares specific to a brand"""
        if brand:
            return self.global_data.get('brand_hardwares', {}).get(brand.upper(), [])
        return self.get_global_materials()
    
    def refresh_cache(self):
        """Refresh the cache by reloading data from database - Manual refresh only"""
        self.keywords_loaded = False  # Reset the flag to allow reload
        self.brands_cache = {}
        self.global_data = {}
        self.load_all_keywords(force_reload=True)
    
    def __del__(self):
        """Clean up database connection"""
        if self.session:
            self.session.close()

def create_filters(df):
    """Create filter widgets with dependent dropdowns"""
    st.subheader("🔍 Filters")
    
    # First row: Status filter and Form ID Search
    col_status, col_search = st.columns([1, 1])
    filters = {}
    
    with col_status:
        status_options = ["All", "✅ Fixed", "❌ Unfixed"]
        filters['status'] = st.selectbox("📊 Status", status_options, key="filter_status")
    
    with col_search:
        # Form ID Search
        if 'Form_ids' in df.columns:
            filters['form_id_search'] = st.text_input(
                "🔍 Search Form ID", 
                placeholder="Enter exact Form ID to search...",
                key="form_id_search",
                help="Search for records with exact Form ID match (case-insensitive)"
            )
        else:
            filters['form_id_search'] = ""
    
    # Second row: Other filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'Contract_Numbers' in df.columns:
            filters['contract'] = st.selectbox("Contract Number", ["All", "Not Empty", "Empty"])
        else:
            filters['contract'] = "All"
    
    with col2:
        if 'Types' in df.columns:
            # Filter by status, form_id_search, and contract first, then get unique types
            status_filtered_df = df.copy()
            if filters['status'] == "✅ Fixed" and 'Status' in df.columns:
                status_filtered_df = status_filtered_df[status_filtered_df['Status'] == 1]
            elif filters['status'] == "❌ Unfixed" and 'Status' in df.columns:
                status_filtered_df = status_filtered_df[status_filtered_df['Status'] == 0]
            
            # Apply form ID search if provided
            if filters.get('form_id_search', '').strip() and 'Form_ids' in df.columns:
                search_term = filters['form_id_search'].strip()
                status_filtered_df = status_filtered_df[
                    status_filtered_df['Form_ids'].astype(str).str.lower() == search_term.lower()
                ]
            
            # Apply contract filter
            if filters.get('contract') == "Not Empty" and 'Contract_Numbers' in df.columns:
                status_filtered_df = status_filtered_df[status_filtered_df['Contract_Numbers'].notna()]
            elif filters.get('contract') == "Empty" and 'Contract_Numbers' in df.columns:
                status_filtered_df = status_filtered_df[status_filtered_df['Contract_Numbers'].isna()]
            
            unique_types = ['All'] + sorted([str(x) for x in status_filtered_df['Types'].dropna().unique() if str(x) != 'nan'])
            filters['type'] = st.selectbox("Type", unique_types, key="filter_type")
        else:
            filters['type'] = "All"
    
    with col3:
        if 'Brands' in df.columns and 'Types' in df.columns:
            # Filter by status, form_id_search, contract, then by type
            brand_filtered_df = df.copy()
            if filters['status'] == "✅ Fixed" and 'Status' in df.columns:
                brand_filtered_df = brand_filtered_df[brand_filtered_df['Status'] == 1]
            elif filters['status'] == "❌ Unfixed" and 'Status' in df.columns:
                brand_filtered_df = brand_filtered_df[brand_filtered_df['Status'] == 0]
            
            # Apply form ID search if provided
            if filters.get('form_id_search', '').strip() and 'Form_ids' in df.columns:
                search_term = filters['form_id_search'].strip()
                brand_filtered_df = brand_filtered_df[
                    brand_filtered_df['Form_ids'].astype(str).str.lower() == search_term.lower()
                ]
            
            # Apply contract filter
            if filters.get('contract') == "Not Empty" and 'Contract_Numbers' in df.columns:
                brand_filtered_df = brand_filtered_df[brand_filtered_df['Contract_Numbers'].notna()]
            elif filters.get('contract') == "Empty" and 'Contract_Numbers' in df.columns:
                brand_filtered_df = brand_filtered_df[brand_filtered_df['Contract_Numbers'].isna()]
            
            if filters['type'] != "All":
                brand_filtered_df = brand_filtered_df[brand_filtered_df['Types'].astype(str) == filters['type']]
            
            unique_brands = ['All'] + sorted([str(x) for x in brand_filtered_df['Brands'].dropna().unique() if str(x) != 'nan'])
            filters['brand'] = st.selectbox("Brand", unique_brands, key="filter_brand")
        else:
            filters['brand'] = "All"
    
    with col4:
        if 'Sub-Models' in df.columns and 'Types' in df.columns and 'Brands' in df.columns:
            # Filter by status, form_id_search, contract, then by type, then by brand
            filtered_for_submodel = df.copy()
            
            if filters['status'] == "✅ Fixed" and 'Status' in df.columns:
                filtered_for_submodel = filtered_for_submodel[filtered_for_submodel['Status'] == 1]
            elif filters['status'] == "❌ Unfixed" and 'Status' in df.columns:
                filtered_for_submodel = filtered_for_submodel[filtered_for_submodel['Status'] == 0]
            
            # Apply form ID search if provided
            if filters.get('form_id_search', '').strip() and 'Form_ids' in df.columns:
                search_term = filters['form_id_search'].strip()
                filtered_for_submodel = filtered_for_submodel[
                    filtered_for_submodel['Form_ids'].astype(str).str.lower() == search_term.lower()
                ]
            
            # Apply contract filter
            if filters.get('contract') == "Not Empty" and 'Contract_Numbers' in df.columns:
                filtered_for_submodel = filtered_for_submodel[filtered_for_submodel['Contract_Numbers'].notna()]
            elif filters.get('contract') == "Empty" and 'Contract_Numbers' in df.columns:
                filtered_for_submodel = filtered_for_submodel[filtered_for_submodel['Contract_Numbers'].isna()]
            
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
    if filters.get('form_id_search', '').strip():
        active_filters.append(f"Form ID='{filters['form_id_search']}'")
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
    
    # Form ID search filter
    if filters.get('form_id_search', '').strip() and 'Form_ids' in df.columns:
        search_term = filters['form_id_search'].strip()
        # Exact match (case-insensitive)
        filtered_df = filtered_df[
            filtered_df['Form_ids'].astype(str).str.lower() == search_term.lower()
        ]
    
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


def create_edit_form(selected_row, keyword_manager, data_manager, context="main"):
    """Create edit form with dependent dropdowns - compact version for right column"""
    
    # Initialize form state
    if 'form_state' not in st.session_state:
        st.session_state.form_state = {
            'type': selected_row.get('Types', ''),
            'brand': selected_row.get('Brands', ''),
            'model': selected_row.get('Models', ''),
            'submodel': selected_row.get('Sub-Models', ''),
            'size': selected_row.get('Sizes', ''),
            'color': selected_row.get('Colors', ''),
            'hardware': selected_row.get('Hardwares', ''),
            'material': selected_row.get('Materials', '')
        }
    
    # Types dropdown - add this first
    types_options = ['', 'Bag', 'Jewelry', 'Watch']
    type_idx = 0
    if st.session_state.form_state['type'] in types_options:
        type_idx = types_options.index(st.session_state.form_state['type'])
    
    selected_type = st.selectbox(
        "Type",
        types_options,
        index=type_idx,
        key=f"edit_type_{context}"
    )
    
    if selected_type != st.session_state.form_state['type']:
        st.session_state.form_state['type'] = selected_type
    
    # Brand dropdown
    brands = [''] + sorted(keyword_manager.get_available_brands())
    brand_idx = 0
    if st.session_state.form_state['brand'] in brands:
        brand_idx = brands.index(st.session_state.form_state['brand'])
    
    selected_brand = st.selectbox(
        "Brand", 
        brands, 
        index=brand_idx,
        key=f"edit_brand_{context}"
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
            models.extend(sorted([key for key in brand_data.keys() if key not in ['colors', 'hardwares']]))
    
    model_idx = 0
    if st.session_state.form_state['model'] in models:
        model_idx = models.index(st.session_state.form_state['model'])
    
    selected_model = st.selectbox(
        "Model", 
        models, 
        index=model_idx,
        key=f"edit_model_{context}"
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
                submodels.extend(sorted(list(model_data.keys())))
    
    submodel_idx = 0
    if st.session_state.form_state['submodel'] in submodels:
        submodel_idx = submodels.index(st.session_state.form_state['submodel'])
    
    selected_submodel = st.selectbox(
        "Sub-Model", 
        submodels, 
        index=submodel_idx,
        key=f"edit_submodel_{context}"
    )
    
    if selected_submodel != st.session_state.form_state['submodel']:
        st.session_state.form_state['submodel'] = selected_submodel
        st.session_state.form_state['size'] = ''
        st.session_state.form_state['material'] = ''
    
    # Size input - with option to use dropdown or manual entry
    st.write("**Size:**")
    
    # Initialize size input mode if not exists
    if f'size_input_mode_{context}' not in st.session_state:
        st.session_state[f'size_input_mode_{context}'] = 'dropdown'
    
    # Option selector for size input method
    size_input_mode = st.radio(
        "Size input method:",
        options=['dropdown', 'manual'],
        index=0 if st.session_state[f'size_input_mode_{context}'] == 'dropdown' else 1,
        format_func=lambda x: 'Use Dropdown' if x == 'dropdown' else 'Manual Entry',
        key=f"size_mode_{context}",
        horizontal=True
    )
    
    # Update session state
    st.session_state[f'size_input_mode_{context}'] = size_input_mode
    
    if size_input_mode == 'dropdown':
        # Dropdown mode
        sizes = ['']
        if selected_brand and selected_model and selected_submodel:
            brand_data = keyword_manager.get_brand_data(selected_brand)
            if (brand_data and 
                selected_model in brand_data and
                selected_submodel in brand_data[selected_model]):
                
                submodel_data = brand_data[selected_model][selected_submodel]
                if isinstance(submodel_data, dict) and 'sizes' in submodel_data:
                    sizes.extend(sorted(submodel_data['sizes']))
        
        size_idx = 0
        if st.session_state.form_state['size'] in sizes:
            size_idx = sizes.index(st.session_state.form_state['size'])
        
        selected_size = st.selectbox(
            "Select size:", 
            sizes, 
            index=size_idx,
            key=f"edit_size_dropdown_{context}"
        )
    else:
        # Manual entry mode
        selected_size = st.text_input(
            "Enter size manually:",
            value=st.session_state.form_state['size'],
            key=f"edit_size_manual_{context}"
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
                materials.extend(sorted(submodel_data['materials']))
    
    material_idx = 0
    if st.session_state.form_state['material'] in materials:
        material_idx = materials.index(st.session_state.form_state['material'])
    
    selected_material = st.selectbox(
        "Material", 
        materials, 
        index=material_idx,
        key=f"edit_material_{context}"
    )
    
    if selected_material != st.session_state.form_state['material']:
        st.session_state.form_state['material'] = selected_material
    
    # Color dropdown
    colors = [''] + sorted(keyword_manager.get_brand_colors(selected_brand))
    color_idx = 0
    if st.session_state.form_state['color'] in colors:
        color_idx = colors.index(st.session_state.form_state['color'])
    
    selected_color = st.selectbox(
        "Color", 
        colors, 
        index=color_idx,
        key=f"edit_color_{context}"
    )
    
    if selected_color != st.session_state.form_state['color']:
        st.session_state.form_state['color'] = selected_color
    
    # Hardware dropdown
    hardwares = [''] + sorted(keyword_manager.get_brand_hardwares(selected_brand))
    hardware_idx = 0
    if st.session_state.form_state['hardware'] in hardwares:
        hardware_idx = hardwares.index(st.session_state.form_state['hardware'])
    
    selected_hardware = st.selectbox(
        "Hardware", 
        hardwares, 
        index=hardware_idx,
        key=f"edit_hardware_{context}"
    )
    
    if selected_hardware != st.session_state.form_state['hardware']:
        st.session_state.form_state['hardware'] = selected_hardware
    
    # Update form state
    st.session_state.form_state.update({
        'type': selected_type,
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
    
    # Main edit form is now only used for Data Management tab, always keep as fixed
    keep_as_fixed = True
    
    if st.button("💾 Save Changes", type="primary", use_container_width=True, key=f"save_btn_{context}"):
        # Prepare updated data
        updated_data = {
            'Types': selected_type,
            'Brands': selected_brand,
            'Models': selected_model,
            'Sub-Models': selected_submodel,
            'Sizes': selected_size,
            'Colors': selected_color,
            'Hardwares': selected_hardware,
            'Materials': selected_material
        }
        
        # Update the record with the status choice
        success = data_manager.update_record(selected_row['_index'], updated_data, keep_as_fixed)
        
        if success:
            st.success("✅ Record updated successfully!")
            st.session_state.selected_row = None
            st.session_state.show_edit_form = False
            if 'form_state' in st.session_state:
                del st.session_state.form_state
            st.rerun()
        else:
            st.error("❌ Failed to save changes")
    
    if st.button("🗑️ Delete Record", type="secondary", use_container_width=True, key=f"delete_btn_{context}"):
        st.session_state.show_delete_popup = True
    
    if st.button("❌ Cancel", use_container_width=True, key=f"cancel_btn_{context}"):
        st.session_state.selected_row = None
        st.session_state.show_edit_form = False
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

def create_fixed_edit_form(selected_row, keyword_manager, data_manager):
    """Independent edit form for Fixed Records tab - uses separate state"""
    
    # Initialize SEPARATE form state for fixed records
    if 'fixed_form_state' not in st.session_state:
        st.session_state.fixed_form_state = {
            'type': selected_row.get('Types', ''),
            'brand': selected_row.get('Brands', ''),
            'model': selected_row.get('Models', ''),
            'submodel': selected_row.get('Sub-Models', ''),
            'size': selected_row.get('Sizes', ''),
            'color': selected_row.get('Colors', ''),
            'hardware': selected_row.get('Hardwares', ''),
            'material': selected_row.get('Materials', '')
        }
    
    # Types dropdown
    types_options = ['', 'Bag', 'Jewelry', 'Watch']
    type_idx = 0
    if st.session_state.fixed_form_state['type'] in types_options:
        type_idx = types_options.index(st.session_state.fixed_form_state['type'])
    
    selected_type = st.selectbox(
        "Type",
        types_options,
        index=type_idx,
        key="fixed_edit_type"
    )
    
    if selected_type != st.session_state.fixed_form_state['type']:
        st.session_state.fixed_form_state['type'] = selected_type
    
    # Brand dropdown
    brands = [''] + sorted(keyword_manager.get_available_brands())
    brand_idx = 0
    if st.session_state.fixed_form_state['brand'] in brands:
        brand_idx = brands.index(st.session_state.fixed_form_state['brand'])
    
    selected_brand = st.selectbox(
        "Brand", 
        brands, 
        index=brand_idx,
        key="fixed_edit_brand"
    )
    
    if selected_brand != st.session_state.fixed_form_state['brand']:
        st.session_state.fixed_form_state['brand'] = selected_brand
        st.session_state.fixed_form_state['model'] = ''
        st.session_state.fixed_form_state['submodel'] = ''
        st.session_state.fixed_form_state['size'] = ''
        st.session_state.fixed_form_state['material'] = ''
    
    # Model dropdown
    models = ['']
    if selected_brand:
        brand_data = keyword_manager.get_brand_data(selected_brand)
        if brand_data:
            models.extend(sorted([key for key in brand_data.keys() if key not in ['colors', 'hardwares']]))
    
    model_idx = 0
    if st.session_state.fixed_form_state['model'] in models:
        model_idx = models.index(st.session_state.fixed_form_state['model'])
    
    selected_model = st.selectbox(
        "Model", 
        models, 
        index=model_idx,
        key="fixed_edit_model"
    )
    
    if selected_model != st.session_state.fixed_form_state['model']:
        st.session_state.fixed_form_state['model'] = selected_model
        st.session_state.fixed_form_state['submodel'] = ''
        st.session_state.fixed_form_state['size'] = ''
        st.session_state.fixed_form_state['material'] = ''
    
    # Sub-Model dropdown
    submodels = ['']
    if selected_brand and selected_model:
        brand_data = keyword_manager.get_brand_data(selected_brand)
        if brand_data and selected_model in brand_data:
            model_data = brand_data[selected_model]
            if isinstance(model_data, dict):
                submodels.extend(sorted(list(model_data.keys())))
    
    submodel_idx = 0
    if st.session_state.fixed_form_state['submodel'] in submodels:
        submodel_idx = submodels.index(st.session_state.fixed_form_state['submodel'])
    
    selected_submodel = st.selectbox(
        "Sub-Model", 
        submodels, 
        index=submodel_idx,
        key="fixed_edit_submodel"
    )
    
    if selected_submodel != st.session_state.fixed_form_state['submodel']:
        st.session_state.fixed_form_state['submodel'] = selected_submodel
        st.session_state.fixed_form_state['size'] = ''
        st.session_state.fixed_form_state['material'] = ''
    
    # Size input - with option to use dropdown or manual entry
    st.write("**Size:**")
    
    # Initialize size input mode if not exists
    if 'fixed_size_input_mode' not in st.session_state:
        st.session_state['fixed_size_input_mode'] = 'dropdown'
    
    # Option selector for size input method
    size_input_mode = st.radio(
        "Size input method:",
        options=['dropdown', 'manual'],
        index=0 if st.session_state['fixed_size_input_mode'] == 'dropdown' else 1,
        format_func=lambda x: 'Use Dropdown' if x == 'dropdown' else 'Manual Entry',
        key="fixed_size_mode",
        horizontal=True
    )
    
    # Update session state
    st.session_state['fixed_size_input_mode'] = size_input_mode
    
    if size_input_mode == 'dropdown':
        # Dropdown mode
        sizes = ['']
        if selected_brand and selected_model and selected_submodel:
            brand_data = keyword_manager.get_brand_data(selected_brand)
            if (brand_data and 
                selected_model in brand_data and
                selected_submodel in brand_data[selected_model]):
                
                submodel_data = brand_data[selected_model][selected_submodel]
                if isinstance(submodel_data, dict) and 'sizes' in submodel_data:
                    sizes.extend(sorted(submodel_data['sizes']))
        
        size_idx = 0
        if st.session_state.fixed_form_state['size'] in sizes:
            size_idx = sizes.index(st.session_state.fixed_form_state['size'])
        
        selected_size = st.selectbox(
            "Select size:", 
            sizes, 
            index=size_idx,
            key="fixed_edit_size_dropdown"
        )
    else:
        # Manual entry mode
        selected_size = st.text_input(
            "Enter size manually:",
            value=st.session_state.fixed_form_state['size'],
            key="fixed_edit_size_manual"
        )
    
    if selected_size != st.session_state.fixed_form_state['size']:
        st.session_state.fixed_form_state['size'] = selected_size
    
    # Material dropdown
    materials = ['']
    if selected_brand and selected_model and selected_submodel:
        brand_data = keyword_manager.get_brand_data(selected_brand)
        if (brand_data and 
            selected_model in brand_data and
            selected_submodel in brand_data[selected_model]):
            
            submodel_data = brand_data[selected_model][selected_submodel]
            if isinstance(submodel_data, dict) and 'materials' in submodel_data:
                materials.extend(sorted(submodel_data['materials']))
    
    material_idx = 0
    if st.session_state.fixed_form_state['material'] in materials:
        material_idx = materials.index(st.session_state.fixed_form_state['material'])
    
    selected_material = st.selectbox(
        "Material", 
        materials, 
        index=material_idx,
        key="fixed_edit_material"
    )
    
    if selected_material != st.session_state.fixed_form_state['material']:
        st.session_state.fixed_form_state['material'] = selected_material
    
    # Color dropdown
    colors = [''] + sorted(keyword_manager.get_brand_colors(selected_brand))
    color_idx = 0
    if st.session_state.fixed_form_state['color'] in colors:
        color_idx = colors.index(st.session_state.fixed_form_state['color'])
    
    selected_color = st.selectbox(
        "Color", 
        colors, 
        index=color_idx,
        key="fixed_edit_color"
    )
    
    if selected_color != st.session_state.fixed_form_state['color']:
        st.session_state.fixed_form_state['color'] = selected_color
    
    # Hardware dropdown
    hardwares = [''] + sorted(keyword_manager.get_brand_hardwares(selected_brand))
    hardware_idx = 0
    if st.session_state.fixed_form_state['hardware'] in hardwares:
        hardware_idx = hardwares.index(st.session_state.fixed_form_state['hardware'])
    
    selected_hardware = st.selectbox(
        "Hardware", 
        hardwares, 
        index=hardware_idx,
        key="fixed_edit_hardware"
    )
    
    if selected_hardware != st.session_state.fixed_form_state['hardware']:
        st.session_state.fixed_form_state['hardware'] = selected_hardware
    
    # Update form state
    st.session_state.fixed_form_state.update({
        'type': selected_type,
        'brand': selected_brand,
        'model': selected_model,
        'submodel': selected_submodel,
        'size': selected_size,
        'color': selected_color,
        'hardware': selected_hardware,
        'material': selected_material
    })
    
    # Action buttons
    if st.button("💾 Save Changes", type="primary", use_container_width=True, key="fixed_save_btn"):
        # Prepare updated data
        updated_data = {
            'Types': selected_type,
            'Brands': selected_brand,
            'Models': selected_model,
            'Sub-Models': selected_submodel,
            'Sizes': selected_size,
            'Colors': selected_color,
            'Hardwares': selected_hardware,
            'Materials': selected_material
        }
        
        # Update the record - always keep as fixed since this is the Fixed Records tab
        success = data_manager.update_record(selected_row['_index'], updated_data, keep_as_fixed=True)
        
        if success:
            st.success("✅ Record updated successfully!")
            # Clear the fixed records selection state
            st.session_state.fixed_selected_row = None
            if 'fixed_form_state' in st.session_state:
                del st.session_state.fixed_form_state
            st.rerun()
        else:
            st.error("❌ Failed to save changes")
    
    if st.button("❌ Cancel", use_container_width=True, key="fixed_cancel_btn"):
        st.session_state.fixed_selected_row = None
        if 'fixed_form_state' in st.session_state:
            del st.session_state.fixed_form_state
        st.rerun()
    
# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'username' not in st.session_state:
    st.session_state.username = None

# if 'data_manager' not in st.session_state:
#     st.session_state.data_manager = DataManager()

# if 'keyword_manager' not in st.session_state:
#     # Initialize keyword manager only once
#     st.session_state.keyword_manager = KeywordManager()

if 'selected_row' not in st.session_state:
    st.session_state.selected_row = None

if 'fixed_selected_row' not in st.session_state:
    st.session_state.fixed_selected_row = None

if 'show_edit_form' not in st.session_state:
    st.session_state.show_edit_form = False

if 'show_delete_popup' not in st.session_state:
    st.session_state.show_delete_popup = False

if 'show_fixed_delete_popup' not in st.session_state:
    st.session_state.show_fixed_delete_popup = False

# Main app
def main():
    # Check authentication first
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()

    if 'keyword_manager' not in st.session_state:
        # Initialize keyword manager only once
        st.session_state.keyword_manager = KeywordManager()
    if not st.session_state.get('authenticated', False):
        show_login_page()
        return
    
    st.title("Back Office Matching v2.0 (PostgreSQL)")
    
    # Add logout button in sidebar
    with st.sidebar:
        current_user = st.session_state.get('username', 'Unknown')
        st.write(f"👤 Logged in as: **{current_user}**")
        
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            logout()
        
        st.markdown("---")
        
        st.subheader("📊 Dashboard")
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
        
        # User Daily Progress Dashboard
        st.subheader("📈 Daily Progress")
        
        # Get user progress data
        user_progress = st.session_state.data_manager.get_user_daily_progress()
        
        if user_progress:
            # Sort users alphabetically for consistent display
            sorted_users = sorted(user_progress.keys())
            
            for user in sorted_users:
                data = user_progress[user]
                count = data['count']
                percentage = data['percentage']
                
                # Display user name and progress
                st.write(f"**{user}**")
                
                # Progress bar with color coding
                if percentage >= 100:
                    progress_color = "🟢"  # Green for completed
                elif percentage >= 75:
                    progress_color = "🟡"  # Yellow for almost there
                elif percentage >= 50:
                    progress_color = "🟠"  # Orange for halfway
                else:
                    progress_color = "🔴"  # Red for needs work
                
                # Show progress bar
                st.progress(min(1.0, percentage / 100))
                
                # Show detailed stats
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"{progress_color} {count}/50")
                with col2:
                    st.caption(f"{percentage:.1f}%")
                
                if count == 50:
                    st.caption("✅ Target achieved!")
        else:
            st.info("No user activity data available for today.")
        
        # Export controls
        st.subheader("🔧 Option")
        # Keywords refresh
        if st.button("🔄 Refresh Keywords", type="primary"):
            try:
                with st.spinner("Refreshing keywords from database..."):
                    # Refresh the keyword manager cache
                    st.session_state.keyword_manager.refresh_cache()
                    
                    # Get updated stats
                    brands = st.session_state.keyword_manager.get_available_brands()
                    
                    if brands:
                        st.success(f"✅ Keywords refreshed!")
                    else:
                        st.warning("⚠️ No keywords found in database")
                        #st.info("💡 Run load_keywords_to_db.py to add keywords to database")
                        
            except Exception as e:
                st.error(f"❌ Failed to refresh keywords: {e}")

        #if st.button("📁 Export to Excel", type="secondary"):
            #filename = st.session_state.data_manager.export_to_excel()
            #if filename:
                #st.success(f"✅ Exported: {os.path.basename(filename)}")
            #else:
                #st.error("❌ Export failed")
        
            # Connection test
        #if st.button("🔧 Test DB Connection",type="primary"):
            #test_results = st.session_state.data_manager.test_connections()
            
            #if test_results['sqlalchemy']:
                #st.success("✅ Database connection working!")
            #else:
                #st.error("❌ Database connection failed!")
            
            #for error in test_results['errors']:
                #st.error(f"🔍 {error}")
        
        
        
        # System info
        st.markdown("---")
        st.caption("🐳 Using PostgreSQL Database (SQLAlchemy)")
        st.caption(f"🗄️ Database: {db_config['host']}:{db_config['port']}")
        
        # Keywords database info
        brands = st.session_state.keyword_manager.get_available_brands()
        if brands:
            st.caption(f"🏷️ Brands in Database: {len(brands)}")
            # Show brand list in an expandable section
            with st.expander("View Brand Names", expanded=False):
                for brand in sorted(brands):
                    st.caption(f"• {brand}")
            
    
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
                st.subheader("🖼️ Image Preview")
                
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
                        height=400,  # Fixed height to save space
                        key="main_data_table"
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
                else:
                    st.info("No records match the current filters.")
            
            # Right Column: Edit Form
            with col3:
                st.subheader("✏️ Edit Record")
                if st.session_state.show_edit_form and st.session_state.selected_row:
                    create_edit_form(
                        st.session_state.selected_row,
                        st.session_state.keyword_manager,
                        st.session_state.data_manager,
                        context="main"
                    )
                else:
                    st.info("Select a record to edit")
        
        else:
            st.error("❌ Could not load data from database")
            st.info("💡 Please check database connection and ensure table exists")
    
    with tab2:
        col1, col2 = st.columns([2, 1])

        stats = st.session_state.data_manager.get_tracking_stats()
        
        if stats['fixed'] > 0:
            df = st.session_state.data_manager.load_data()
            if df is not None:
                fixed_df = df[df['Status'] == 1].copy()
                
                
                # Create two-column layout: Data Table | Edit Form
                #col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("✅ Fixed Records")   
                    st.subheader(f"Total Fixed Records: {len(fixed_df)}")
                     
                    # Display interactive dataframe for fixed records
                    display_fixed_df = fixed_df.copy()
                    
                    # Add visual Status column
                    if 'Status' in display_fixed_df.columns:
                        display_fixed_df['Status_Display'] = display_fixed_df['Status'].map({
                            0: '❌ Unfixed',
                            1: '✅ Fixed'
                        })
                        cols = ['Status_Display'] + [col for col in display_fixed_df.columns if col not in ['Status_Display', 'Status']]
                        display_fixed_df = display_fixed_df[cols]
                    
                    display_fixed_df_reset = display_fixed_df.reset_index(drop=False)
                    
                    # Configure columns
                    column_config = {
                        "Picture_url": st.column_config.LinkColumn(
                            "Picture URL",
                            help="Click to view image",
                            display_text="View Image"
                        ) if 'Picture_url' in display_fixed_df_reset.columns else None,
                        "Status_Display": st.column_config.TextColumn(
                            "Status",
                            help="Record status",
                            width="small"
                        ) if 'Status_Display' in display_fixed_df_reset.columns else None,
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
                        selection_mode="single-row",  # Change to single-row like Data Management
                        height=400,
                        key="fixed_records_table"
                    )
                    
                    # Handle selection for fixed records - similar to Data Management tab
                    if fixed_event.selection.rows:
                        try:
                            selected_idx = fixed_event.selection.rows[0]
                            
                            # Get the original index from the filtered dataframe
                            if 'index' in display_fixed_df_reset.columns:
                                original_idx = display_fixed_df_reset.iloc[selected_idx]['index']
                            else:
                                original_idx = fixed_df.iloc[selected_idx].name
                            
                            # Always update if selection changed or no selection exists
                            current_fixed_selected_row = st.session_state.get('fixed_selected_row', None)
                            current_selection = current_fixed_selected_row.get('_index', None) if current_fixed_selected_row else None
                            
                            if current_selection != original_idx:
                                selected_data = df.loc[original_idx].to_dict()
                                selected_data['_index'] = original_idx
                                
                                st.session_state.fixed_selected_row = selected_data
                                
                                # Clear form state when switching records
                                if 'fixed_form_state' in st.session_state:
                                    del st.session_state.fixed_form_state
                                
                                st.success(f"✅ Selected: Contract {selected_data.get('Contract_Numbers', 'N/A')} | Index: {original_idx}")
                                
                                # Force rerun to update edit form
                                st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ Error selecting row: {str(e)}")
                            st.error(f"Debug info - Selected idx: {selected_idx}, Available rows: {len(display_fixed_df_reset)}")
                    else:
                        # Clear selection when no rows are selected
                        if st.session_state.get('fixed_selected_row') is not None:
                            st.session_state.fixed_selected_row = None
                            if 'fixed_form_state' in st.session_state:
                                del st.session_state.fixed_form_state
                    
                    # Additional action buttons (only show if record is selected)
                    if st.session_state.get('fixed_selected_row'):
                        st.markdown("---")
                        if st.button("🔄 Unfix This Record", type="secondary", use_container_width=True, key="fixed_unfix_single_btn"):
                            success = st.session_state.data_manager.unfix_record(st.session_state.fixed_selected_row['_index'])
                            if success:
                                st.success("✅ Record moved back to unfixed!")
                                st.session_state.fixed_selected_row = None
                                st.rerun()
                            else:
                                st.error("❌ Failed to unfix record")
                
                with col2:
                    # Edit Form for Fixed Records - ALWAYS SHOW IF WE HAVE SELECTED ROW
                    st.subheader("✏️ Edit Fixed Record")
                    
                    # Show edit form if we have a fixed record selected
                    if st.session_state.fixed_selected_row:
                        create_fixed_edit_form(
                            st.session_state.fixed_selected_row,
                            st.session_state.keyword_manager,
                            st.session_state.data_manager
                        )
                    else:
                        st.info("Click on a row in the table to edit the record")
        else:
            st.info("No records have been fixed yet.")
    
    with tab3:
        st.subheader("❌ Unfixed Records")
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
                
                st.dataframe(page_df, use_container_width=True, key="unfixed_records_table")
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
            st.info("🔄 **คืนค่าขก่อนแก้ไข**\nสามารถกดคืนค่าข้อมูลที่แก้ไขผิดได้")
        
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
            st.write("• **Single Record:** คืนค่าได้ทีละแถว")
            
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

        with col2:
            st.write("**📝 บันทึกข้อมูล**")
            st.write("• บันทึกสิ่งที่เกิดขึ้น")
            st.write("• ถ่ายภาพหน้าจอ (Screenshot)")
        with col3:
            st.write("**📞 แจ้งผู้ดูแลระบบ**")
            st.write("• แจ้งข้อมูลที่บันทึกไว้")
            st.write("• ระบุหมายเลขแถวที่มีปัญหา")
            st.write("• **096-982-2813 (อู๋)**")
        
        st.success("🎉 เสร็จสิ้น! คุณพร้อมใช้งานระบบ Back Office Matching v2.0 (PostgreSQL) แล้ว!")

if __name__ == "__main__":
    main()
