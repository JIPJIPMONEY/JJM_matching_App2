"""
Model Request Application
Separate Streamlit app for requesting new model data
Saves requests to request_model database
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import json
import os

# Configure page - adjust based on authentication state
if 'authenticated' not in st.session_state or not st.session_state.get('authenticated', False):
    st.set_page_config(
        page_title="Login - Keywords Manager v2.0",
        page_icon="🔐",
        layout="centered"
    )
else:
    st.set_page_config(
        page_title="Keywords Manager v2.0",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded"
    )

# Database configuration for request_model database
REQUEST_DB_CONFIG = {
    'user': 'datateam',
    'password': 'jipjipmoneydata',
    'host': '192.168.1.111',
    'port': '5432',
    'database': 'request_model'
}

# Database configuration for jipjipmoney database (for fetching existing brands)
MAIN_DB_CONFIG = {
    'user': 'datateam',
    'password': 'jipjipmoneydata',
    'host': '192.168.1.111',
    'port': '5432',
    'database': 'jipjipmoney'
}

# User credentials with roles
USER_CREDENTIALS = {
    "admin": {"password": "admin8558", "role": "admin"},  # Can approve/reject and execute requests
    "Build@CS": {"password": "NRJ24017", "role": "user"}, 
    "Pin@SCL": {"password": "NRJ23006", "role": "admin"},# Can approve/reject and execute requests
    "Knight@SCL": {"password": "NRJ23004", "role": "user"},
    "Gun@SCL": {"password": "NRJ24027", "role": "user"}
}

# SQLAlchemy Base
Base = declarative_base()

def authenticate_user():
    """Handle user authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None
    
    if not st.session_state.authenticated:
        show_login_page()
        return False
    
    return True

def show_login_page():
    """Display login page"""
    st.title("🔐 Login Required")
    st.subheader("Keywords Manager V.2")
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if login_button:
                if check_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_role = USER_CREDENTIALS[username]["role"]
                    st.success(f"✅ Welcome, {username}! ({USER_CREDENTIALS[username]['role'].title()})")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

def check_credentials(username, password):
    """Check if username and password are valid"""
    return username in USER_CREDENTIALS and USER_CREDENTIALS[username]["password"] == password

def logout_user():
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.rerun()

class ModelRequest(Base):
    """Model for storing model requests"""
    __tablename__ = 'model_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    requested_by = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    submodel = Column(String(100), nullable=False)
    sizes = Column(Text, nullable=True)  # Store as comma-separated values
    materials = Column(Text, nullable=True)  # Store as comma-separated values
    notes = Column(Text, nullable=True)
    status = Column(String(20), default='pending')  # pending, approved, rejected
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_by = Column(String(100), nullable=True)  # Admin who approved/rejected
    processed_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Simplified fields for the workflow
    category = Column(String(20), nullable=True, default='add')  # add, edit, delete
    edit_status = Column(String(20), nullable=True, default='pending')  # pending, done (for approved requests)

class AuditLog(Base):
    """Model for storing audit logs"""
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    submodel = Column(String(100), nullable=True)
    user_id = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def get_request_db_engine():
    """Create engine for request_model database"""
    try:
        connection_string = f"postgresql://{REQUEST_DB_CONFIG['user']}:{REQUEST_DB_CONFIG['password']}@{REQUEST_DB_CONFIG['host']}:{REQUEST_DB_CONFIG['port']}/{REQUEST_DB_CONFIG['database']}"
        engine = create_engine(connection_string, pool_pre_ping=True)
        return engine
    except Exception as e:
        st.error(f"❌ Failed to connect to request database: {e}")
        return None

def get_main_db_engine():
    """Create engine for jipjipmoney database"""
    try:
        connection_string = f"postgresql://{MAIN_DB_CONFIG['user']}:{MAIN_DB_CONFIG['password']}@{MAIN_DB_CONFIG['host']}:{MAIN_DB_CONFIG['port']}/{MAIN_DB_CONFIG['database']}"
        engine = create_engine(connection_string, pool_pre_ping=True)
        return engine
    except Exception as e:
        st.error(f"❌ Failed to connect to main database: {e}")
        return None

def init_request_database():
    """Initialize the request_model database and create tables"""
    try:
        engine = get_request_db_engine()
        if engine:
            # Create all tables
            Base.metadata.create_all(engine)
            return True
    except Exception as e:
        st.error(f"❌ Failed to initialize request database: {e}")
        return False

def log_audit_action(category, action, brand=None, model=None, submodel=None, user_id=None, old_value=None, new_value=None):
    """Log an action to the audit_log table"""
    try:
        engine = get_request_db_engine()
        if not engine:
            st.error("❌ Cannot connect to request database for audit logging")
            return False
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Convert new_value to JSON string if it's a dict/list
        new_value_str = None
        if new_value is not None:
            if isinstance(new_value, (dict, list)):
                new_value_str = json.dumps(new_value)
            else:
                new_value_str = str(new_value)
        
        # Convert old_value to JSON string if it's a dict/list
        old_value_str = None
        if old_value is not None:
            if isinstance(old_value, (dict, list)):
                old_value_str = json.dumps(old_value)
            else:
                old_value_str = str(old_value)
        
        audit_entry = AuditLog(
            category=category,
            action=action,
            brand=brand,
            model=model,
            submodel=submodel,
            user_id=user_id or (st.session_state.username if 'username' in st.session_state else 'unknown'),
            old_value=old_value_str,
            new_value=new_value_str
        )
        
        session.add(audit_entry)
        session.commit()
        session.close()
        
        return True
    except Exception as e:
        st.error(f"❌ Failed to log audit action: {e}")
        return False

def get_model_details_by_id(model_id):
    """Get model details (brand, model, submodel) by model ID"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return None
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT b.name, m.collection, m.model_name 
                        FROM models m 
                        JOIN brands b ON m.brand_id = b.id 
                        WHERE m.id = :model_id"""),
                {"model_id": model_id}
            ).fetchone()
            
            if result:
                return (result[0], result[1], result[2])  # brand, model, submodel
            return None
    except Exception as e:
        st.error(f"❌ Failed to get model details: {e}")
        return None

def get_existing_brands():
    """Fetch existing brands from the main database"""
    try:
        engine = get_main_db_engine()
        if engine:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT DISTINCT name FROM brands ORDER BY name"))
                brands = [row[0] for row in result.fetchall()]
                return brands
    except Exception as e:
        st.error(f"❌ Failed to fetch brands: {e}")
        return []

def save_model_request(request_data):
    """Save model request to database"""
    try:
        engine = get_request_db_engine()
        if not engine:
            st.error("❌ Cannot connect to request database")
            return False
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        new_request = ModelRequest(
            requested_by=request_data['requested_by'],
            brand=request_data['brand'],
            model=request_data.get('model', ''),
            submodel=request_data.get('submodel', ''),
            sizes=request_data.get('sizes', ''),
            materials=request_data.get('materials', ''),
            notes=request_data.get('notes', ''),
            category=request_data.get('category', 'add')
        )
        
        session.add(new_request)
        session.commit()
        session.close()
        
        return True
    except Exception as e:
        st.error(f"❌ Failed to save request: {e}")
        return False

def load_pending_requests():
    """Load pending requests from database"""
    try:
        engine = get_request_db_engine()
        if not engine:
            return []
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        requests = session.query(ModelRequest).filter(ModelRequest.status == 'pending').order_by(ModelRequest.submitted_at.desc()).all()
        
        session.close()
        return requests
    except Exception as e:
        st.error(f"❌ Failed to load requests: {e}")
        return []

def update_request_status(request_id, status, processed_by, admin_notes=None):
    """Update request status (supervisor approval/rejection)"""
    try:
        engine = get_request_db_engine()
        if not engine:
            return False
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        request = session.query(ModelRequest).filter(ModelRequest.id == request_id).first()
        if request:
            request.status = status
            request.processed_by = processed_by
            request.processed_at = datetime.now(timezone.utc)
            if admin_notes:
                request.admin_notes = admin_notes
            
            # If approved, set edit_status to pending (waiting for superuser execution)
            if status == 'approved':
                request.edit_status = 'pending'
            
            session.commit()
        
        session.close()
        return True
    except Exception as e:
        st.error(f"❌ Failed to update request: {e}")
        return False

def update_edit_status(request_id, edit_status, executed_by):
    """Update edit status (superuser execution)"""
    try:
        engine = get_request_db_engine()
        if not engine:
            return False
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        request = session.query(ModelRequest).filter(ModelRequest.id == request_id).first()
        if request:
            request.edit_status = edit_status
            request.executed_by = executed_by
            request.executed_at = datetime.now(timezone.utc)
            session.commit()
        
        session.close()
        return True
    except Exception as e:
        st.error(f"❌ Failed to update edit status: {e}")
        return False

def load_approved_pending_requests():
    """Load approved requests that are pending execution"""
    try:
        engine = get_request_db_engine()
        if not engine:
            return []
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        requests = session.query(ModelRequest).filter(
            ModelRequest.status == 'approved',
            ModelRequest.edit_status == 'pending'
        ).order_by(ModelRequest.processed_at.desc()).all()
        
        session.close()
        return requests
    except Exception as e:
        st.error(f"❌ Failed to load approved pending requests: {e}")
        return []

def create_model_request_form():
    """Create the comprehensive model request form with add/edit/delete categories"""
    st.subheader("📝 Submit Request")
    
    # Category selection
    category = st.selectbox(
        "Request category *",
        ["add", "edit", "delete"],
        format_func=lambda x: {"add": "➕ Add", "edit": "✏️ Edit", "delete": "🗑️ Delete"}[x]
    )
    
    existing_brands = get_existing_brands()
    brands_options = [''] + sorted(existing_brands) if existing_brands else ['']

    selected_brand = st.selectbox(
        "Brand *",
        brands_options,
        key="brand_select"
    )

    if category == "add":
        create_add_request_form(selected_brand)
    elif category == "edit":
        create_edit_request_form(selected_brand)
    elif category == "delete":
        create_delete_request_form(selected_brand)

def create_add_request_form(selected_brand):
    """Create form for adding new items"""
    st.markdown("#### ➕ Add New Item")
    
    with st.form("add_request_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            model_name = st.text_input("Model *", placeholder="e.g., Vintage, Chevron")
            size_input = st.text_input("Sizes", placeholder="e.g., 7,8,9,10 (separate with commas)")
        with col2:
            submodel_name = st.text_input("Submodel *", placeholder="e.g., Kelly, Diana")
            material_input = st.text_input("Materials", placeholder="e.g., Canvas, Leather (separate with commas)")
        
        notes = st.text_area("Additional Notes", placeholder="Any additional information...")
        submitted = st.form_submit_button("📤 Submit Add Request", type="primary")
        
        if submitted:
            if not selected_brand:
                st.error("❌ Please select a brand")
                return
            
            if not model_name.strip() or not submodel_name.strip():
                st.error("❌ Please enter both model and submodel names")
                return
                
            request_data = {
                'requested_by': st.session_state.username,
                'brand': selected_brand,
                'category': 'add',
                'model': model_name.strip(),
                'submodel': submodel_name.strip(),
                'sizes': size_input.strip() or None,
                'materials': material_input.strip() or None,
                'notes': notes.strip() or None
            }
            
            if save_model_request(request_data):
                st.success("✅ Add request submitted successfully!")
                st.rerun()

def create_edit_request_form(selected_brand):
    """Create form for editing existing items"""
    st.markdown("#### ✏️ Edit Existing Item")
    st.info("💡 **Edit Format**: Use 'Old Value → New Value' format for edits")
    
    with st.form("edit_request_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            model_name = st.text_input("Model Edit", placeholder="e.g., Vintage → Classic")
            size_input = st.text_input("Size Edit", placeholder="e.g., 7 → Size 7 (optional)")
        with col2:
            submodel_name = st.text_input("Submodel Edit", placeholder="e.g., Kelly → Kelly 25")
            material_input = st.text_input("Material Edit", placeholder="e.g., Canvas → Leather (optional)")
        
        st.markdown("**Examples:**")
        st.markdown("- Model: `Vintage → Classic` (changes all Vintage to Classic)")
        st.markdown("- Submodel: `Kelly → Kelly 25` (changes all Kelly to Kelly 25)")
        st.markdown("- Size: `7 → Size 7` (changes size '7' to 'Size 7')")
        st.markdown("- Material: `Canvas → Leather` (changes Canvas to Leather)")
        
        notes = st.text_area("Reason for Edit", placeholder="Why is this edit needed?")
        submitted = st.form_submit_button("📤 Submit Edit Request", type="primary")
        
        if submitted:
            if not selected_brand:
                st.error("❌ Please select a brand")
                return
            
            if not model_name.strip() and not submodel_name.strip() and not size_input.strip() and not material_input.strip():
                st.error("❌ Please specify at least one edit (model, submodel, size, or material)")
                return
            
            if model_name.strip() and "→" not in model_name:
                st.error("❌ Model edit must use format: 'Old Value → New Value'")
                return
            if submodel_name.strip() and "→" not in submodel_name:
                st.error("❌ Submodel edit must use format: 'Old Value → New Value'")
                return
            if size_input.strip() and "→" not in size_input:
                st.error("❌ Size edit must use format: 'Old Value → New Value'")
                return
            if material_input.strip() and "→" not in material_input:
                st.error("❌ Material edit must use format: 'Old Value → New Value'")
                return
                
            request_data = {
                'requested_by': st.session_state.username,
                'brand': selected_brand,
                'category': 'edit',
                'model': model_name.strip() or 'No Change',
                'submodel': submodel_name.strip() or 'No Change',
                'sizes': size_input.strip() or None,
                'materials': material_input.strip() or None,
                'notes': notes.strip() or None
            }
            
            if save_model_request(request_data):
                st.success("✅ Edit request submitted successfully!")
                st.rerun()

def create_delete_request_form(selected_brand):
    """Create form for deleting existing items"""
    st.markdown("#### 🗑️ Delete Existing Item")
    
    with st.form("delete_request_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            model_name = st.text_input("Model to Delete *", placeholder="e.g., Vintage, Chevron")
            size_input = st.text_input("Sizes to Delete", placeholder="e.g., 7,8,9,10 (separate with commas)")
        with col2:
            submodel_name = st.text_input("Submodel to Delete *", placeholder="e.g., Kelly, Diana")
            material_input = st.text_input("Materials to Delete", placeholder="e.g., Canvas, Leather (separate with commas)")
        
        st.warning("⚠️ **Deletion Warning**: This request will be reviewed by admin before any data is removed.")
        notes = st.text_area("Reason for Deletion *", placeholder="Why should this be deleted? (Required)")
        submitted = st.form_submit_button("📤 Submit Delete Request", type="primary")
        
        if submitted:
            if not selected_brand:
                st.error("❌ Please select a brand")
                return
            
            if not model_name.strip() or not submodel_name.strip():
                st.error("❌ Please enter model and submodel names to delete")
                return
                
            if not notes.strip():
                st.error("❌ Please provide a reason for deletion")
                return
                
            request_data = {
                'requested_by': st.session_state.username,
                'brand': selected_brand,
                'category': 'delete',
                'model': model_name.strip(),
                'submodel': submodel_name.strip(),
                'sizes': size_input.strip() or None,
                'materials': material_input.strip() or None,
                'notes': notes.strip()
            }
            
            if save_model_request(request_data):
                st.success("✅ Delete request submitted successfully!")
                st.rerun()

def show_user_requests():
    """Show all requests with filtering options including by editor name"""
    st.subheader("📋 All Requests")
    
    # Get all requests from database
    all_requests = []
    try:
        engine = get_request_db_engine()
        if engine:
            Session = sessionmaker(bind=engine)
            session = Session()
            # Get ALL requests, not just current user's
            all_requests = session.query(ModelRequest).order_by(ModelRequest.submitted_at.desc()).all()
            session.close()
    except Exception as e:
        st.error(f"❌ Failed to load requests: {e}")
        return

    if all_requests:
        # Get unique requesters for the filter
        unique_requesters = sorted(list(set([r.requested_by for r in all_requests])))
        
        # Filters - editor filter first, then the rest
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            editor_filter = st.selectbox("Filter by Editor:", ["All"] + unique_requesters)
        with col2:
            category_filter = st.selectbox("Filter by Category:", ["All", "Add", "Edit", "Delete"])
        with col3:
            status_filter = st.selectbox("Filter by Status:", ["All", "Pending", "Approved", "Rejected"])
        with col4:
            edit_status_filter = st.selectbox("Filter by Execution:", ["All", "Pending", "Done"])
        
        # Apply filters
        filtered_requests = all_requests
        if category_filter != "All":
            filtered_requests = [r for r in filtered_requests if (r.category or 'add').strip() == category_filter.lower()]
        if status_filter != "All":
            filtered_requests = [r for r in filtered_requests if r.status == status_filter.lower()]
        if edit_status_filter != "All":
            filtered_requests = [r for r in filtered_requests if (r.edit_status or 'pending') == edit_status_filter.lower()]
        if editor_filter != "All":
            filtered_requests = [r for r in filtered_requests if r.requested_by == editor_filter]
        
        if filtered_requests:
            # Create table data
            table_data = []
            for request in filtered_requests:
                category = (request.category or 'add').strip()
                category_icon = {"add": "➕", "edit": "✏️", "delete": "🗑️"}[category]
                status_icon = "✅" if request.status == "approved" else ("❌" if request.status == "rejected" else "⏳")
                # Get the actual edit status and handle case sensitivity
                actual_edit_status = (request.edit_status or 'pending').lower().strip()
                edit_status_icon = "✅" if actual_edit_status == "done" else "⏳"
                
                table_data.append({
                    'ID': request.id,
                    'Category': f"{category_icon} {category.title()}",
                    'Requested By': request.requested_by,
                    'Brand': request.brand,
                    'Model': request.model,
                    'Submodel': request.submodel,
                    'Status': f"{status_icon} {request.status.title()}",
                    'Execution': f"{edit_status_icon} {actual_edit_status.title()}" if request.status == "approved" else "N/A",
                    'Submitted': request.submitted_at.strftime('%Y-%m-%d %H:%M')
                })

            # Display table
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("📭 No requests match the selected filters.")
    else:
        st.info("📭 No requests found.")

def show_model_size_material_table():
    """Show table of all models with sizes and materials, filterable by brand"""
    st.subheader("Brand Keywords")
    brands = get_existing_brands()
    if not brands:
        st.info("No brands found in main database.")
        return
    selected_brand = st.selectbox("Filter by Brand", ['All'] + brands, key="table_brand_filter")
    engine = get_main_db_engine()
    if not engine:
        st.error("❌ Cannot connect to main database")
        return
    with engine.connect() as conn:
        if selected_brand == 'All':
            models = conn.execute(text("SELECT m.id, b.name, m.model_name, m.collection FROM models m JOIN brands b ON m.brand_id = b.id ORDER BY b.name, m.model_name")).fetchall()
        else:
            models = conn.execute(text("SELECT m.id, b.name, m.model_name, m.collection FROM models m JOIN brands b ON m.brand_id = b.id WHERE b.name = :brand ORDER BY m.model_name"), {"brand": selected_brand}).fetchall()
        if not models:
            st.info("No models found for this brand.")
            return
        table_data = []
        for m in models:
            model_id = m[0]
            brand = m[1]
            model_name = m[2]
            collection = m[3]
            sizes = conn.execute(text("SELECT size FROM model_sizes WHERE model_id = :model_id ORDER BY size"), {"model_id": model_id}).fetchall()
            materials = conn.execute(text("SELECT material FROM model_materials WHERE model_id = :model_id ORDER BY material"), {"model_id": model_id}).fetchall()
            sizes_str = ", ".join([s[0] for s in sizes]) if sizes else ""
            materials_str = ", ".join([mat[0] for mat in materials]) if materials else ""
            table_data.append({
                "Brand": brand,
                "Model": collection,    # Collection field from DB is now Model
                "Submodel": model_name, # Model_name field from DB is now Submodel
                "Sizes": sizes_str,
                "Materials": materials_str
            })
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

def create_admin_panel():
    """Create unified admin panel for approving and executing requests"""
    st.subheader("👑 Admin Panel")
    
    # Create tabs for different admin functions
    tab1, tab2, tab3 = st.tabs(["🔍 Pending Requests", "✅ Approved Requests", "📋 All Requests"])
    
    with tab1:
        st.markdown("#### 🔍 Pending Requests (Awaiting Approval)")
        pending_requests = load_pending_requests()
        
        if pending_requests:
            for request in pending_requests:
                category_display = (request.category or 'add').strip().upper()
                with st.expander(f"🔍 {category_display} Request #{request.id}: {request.brand} - {request.model} - {request.submodel}", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"👤 **Requested by:** {request.requested_by}")
                        st.write(f"🏷️ **Brand:** {request.brand}")
                        st.write(f"� **Model:** {request.model}")
                        st.write(f"� **Submodel:** {request.submodel}")
                        
                        if request.sizes:
                            st.write(f"� **Sizes:** {request.sizes}")
                        if request.materials:
                            st.write(f"🧵 **Materials:** {request.materials}")
                        if request.notes:
                            st.write(f"� **Notes:** {request.notes}")
                            
                        st.write(f"📅 **Submitted:** {request.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                    with col2:
                        st.write("**Actions:**")
                        
                        # Admin notes for approval/rejection
                        admin_notes = st.text_area(
                            "Admin Notes:",
                            key=f"admin_notes_{request.id}",
                            placeholder="Enter notes (required for rejection)...",
                            height=100
                        )
                        
                        col_approve, col_reject = st.columns(2)
                        
                        with col_approve:
                            if st.button("✅ Approve", key=f"approve_{request.id}", type="primary"):
                                # For approval, admin notes can be empty
                                notes_to_save = admin_notes.strip() if admin_notes.strip() else None
                                if update_request_status(request.id, 'approved', st.session_state.username, notes_to_save):
                                    st.success("✅ Request approved!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to approve request")
                        
                        with col_reject:
                            if st.button("❌ Reject", key=f"reject_{request.id}", type="secondary"):
                                if not admin_notes.strip():
                                    st.error("❌ Please provide a reason for rejection")
                                else:
                                    if update_request_status(request.id, 'rejected', st.session_state.username, admin_notes.strip()):
                                        st.success("❌ Request rejected")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to reject request")

        else:
            st.info("No pending requests")
    
    with tab2:
        st.markdown("#### ✅ Approved Requests (Ready for Manual Work)")
        approved_requests = load_approved_pending_requests()
        
        if approved_requests:
            # Add filters for approved requests
            col1, col2 = st.columns(2)
            with col1:
                category_filter = st.selectbox("Filter by Category:", ["All", "Add", "Edit", "Delete"], key="approved_category_filter")
            with col2:
                # Get unique approval dates
                approval_dates = list(set([req.processed_at.date() for req in approved_requests if req.processed_at]))
                approval_dates.sort(reverse=True)  # Most recent first
                date_options = ["All"] + [date.strftime('%Y-%m-%d') for date in approval_dates]
                date_filter = st.selectbox("Filter by Approval Date:", date_options, key="approved_date_filter")
            
            # Apply filters
            filtered_requests = approved_requests
            if category_filter != "All":
                filtered_requests = [r for r in filtered_requests if (r.category or 'add').strip() == category_filter.lower()]
            if date_filter != "All":
                selected_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                filtered_requests = [r for r in filtered_requests if r.processed_at and r.processed_at.date() == selected_date]
            
            if filtered_requests:
                for request in filtered_requests:
                    category_display = (request.category or 'add').strip().upper()
                    exec_status = request.edit_status or 'pending'
                    
                    # Status indicators
                    if exec_status == 'done':
                        status_indicator = "✅ COMPLETED"
                    else:
                        status_indicator = "⏳ NEEDS MANUAL WORK"
                    
                    with st.expander(f"{status_indicator} - {category_display} Request #{request.id}: {request.brand} - {request.model} - {request.submodel}", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"👤 **Requested by:** {request.requested_by}")
                            st.write(f"👑 **Approved by:** {request.processed_by}")
                            st.write(f"📅 **Approved:** {request.processed_at.strftime('%Y-%m-%d %H:%M')}")
                            st.write(f"🏷️ **Brand:** {request.brand}")
                            st.write(f"📦 **Model:** {request.model}")
                            st.write(f"🔸 **Submodel:** {request.submodel}")
                            
                            if request.sizes:
                                st.write(f"� **Sizes:** {request.sizes}")
                            if request.materials:
                                st.write(f"🧵 **Materials:** {request.materials}")
                            if request.notes:
                                st.write(f"📝 **Notes:** {request.notes}")
                            if request.admin_notes:
                                st.write(f"💬 **Admin Notes:** {request.admin_notes}")
                        
                        with col2:
                            # Show current execution status
                            exec_status = request.edit_status or 'pending'
                            if exec_status == 'done':
                                st.success("✅ Completed")
                            else:
                                if st.button(f"✅ Mark as Done #{request.id}", key=f"mark_done_{request.id}", type="primary"):
                                    if update_edit_status(request.id, 'done', st.session_state.username):
                                        st.success(f"✅ Request #{request.id} marked as DONE!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to update status")
            else:
                st.info("📭 No approved requests match the selected filters")
        else:
            st.info("No approved requests pending manual work")
    
    with tab3:
        st.markdown("#### 📋 All Requests")
        
        # Get all requests from database
        all_requests = []
        try:
            engine = get_request_db_engine()
            if engine:
                Session = sessionmaker(bind=engine)
                session = Session()
                # Get ALL requests, not just processed ones
                all_requests = session.query(ModelRequest).order_by(ModelRequest.submitted_at.desc()).all()
                session.close()
        except Exception as e:
            st.error(f"❌ Failed to load requests: {e}")
            return

        if all_requests:
            # Add filters
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                status_filter = st.selectbox("Filter by Status:", ["All", "Pending", "Approved", "Rejected"], key="all_status_filter")
            
            with col2:
                execution_filter = st.selectbox("Filter by Execution:", ["All", "Pending", "Done"], key="all_execution_filter")
            
            with col3:
                category_filter = st.selectbox("Filter by Category:", ["All", "Add", "Edit", "Delete"], key="all_category_filter")
            
            with col4:
                # Get unique submission dates
                submission_dates = list(set([req.submitted_at.date() for req in all_requests if req.submitted_at]))
                submission_dates.sort(reverse=True)  # Most recent first
                date_options = ["All"] + [date.strftime('%Y-%m-%d') for date in submission_dates]
                date_filter = st.selectbox("Filter by Date:", date_options, key="all_date_filter")
            
            # Apply filters
            filtered_requests = all_requests
            
            if status_filter != "All":
                filtered_requests = [r for r in filtered_requests if r.status == status_filter.lower()]
            
            if execution_filter != "All":
                filtered_requests = [r for r in filtered_requests if (r.edit_status or 'pending').lower() == execution_filter.lower()]
            
            if category_filter != "All":
                filtered_requests = [r for r in filtered_requests if (r.category or 'add').strip() == category_filter.lower()]
            
            if date_filter != "All":
                selected_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                filtered_requests = [r for r in filtered_requests if r.submitted_at and r.submitted_at.date() == selected_date]

            if filtered_requests:
                # Create table data
                table_data = []
                for request in filtered_requests:
                    category = (request.category or 'add').strip()
                    category_icon = {"add": "➕", "edit": "✏️", "delete": "🗑️"}[category]
                    status_icon = "✅" if request.status == "approved" else ("❌" if request.status == "rejected" else "⏳")
                    
                    # Get execution status for approved requests
                    execution_status = ""
                    if request.status == "approved":
                        actual_edit_status = (request.edit_status or 'pending').lower().strip()
                        exec_icon = "✅" if actual_edit_status == "done" else "⏳"
                        execution_status = f"{exec_icon} {actual_edit_status.title()}"
                    else:
                        execution_status = "N/A"
                    
                    table_data.append({
                        'ID': request.id,
                        'Category': f"{category_icon} {category.title()}",
                        'Status': f"{status_icon} {request.status.title()}",
                        'Execution': execution_status,
                        'Requested By': request.requested_by,
                        'Brand': request.brand,
                        'Model': request.model,
                        'Submodel': request.submodel,
                        'Sizes': request.sizes or 'N/A',
                        'Materials': request.materials or 'N/A',
                        'Submitted': request.submitted_at.strftime('%Y-%m-%d %H:%M'),
                        'Processed By': request.processed_by or 'N/A',
                        'Notes': request.notes or 'N/A',
                        'Admin Notes': request.admin_notes or 'N/A'
                    })

                # Display table
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, height=600)
            else:
                st.info("📭 No requests match the selected filters.")
        else:
            st.info("📭 No requests found.")

def create_keyword_manager():
    """Create keyword manager interface for manual size/material management"""
    st.subheader("🔧 Keyword Manager")
    
    # Get existing brands
    brands = get_existing_brands()
    if not brands:
        st.info("No brands found in main database.")
        return
    
    # Brand selection
    selected_brand = st.selectbox("Select Brand:", brands, key="km_brand_select")
    
    if selected_brand:
        # Operation tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "🆕 Add Model/Submodel", 
            "📋 Manage Size/Material", 
            " Edit Submodel Name",
            "❌ Delete Submodel"
        ])
        
        with tab1:
            show_add_model_interface(selected_brand)
        
        with tab2:
            show_manage_size_material_interface(selected_brand)
        
        with tab3:
            show_edit_submodel_interface(selected_brand)
        
        with tab4:
            show_delete_submodel_interface(selected_brand)

def show_add_model_interface(brand):
    """Show interface for adding new models and submodels"""
    
    with st.form("add_model_submodel_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Model Information:**")
            model_name = st.text_input("Model (Collection) *", placeholder="e.g., Vintage, Chevron, Speedy")
            submodel_name = st.text_input("Submodel (Model Name) *", placeholder="e.g., Kelly, Diana, 25")
        
        with col2:
            st.markdown("**Optional Initial Data:**")
            initial_sizes = st.text_input("Initial Sizes", placeholder="e.g., 7,8,9,10 (separate with commas)")
            initial_materials = st.text_input("Initial Materials", placeholder="e.g., Canvas, Leather (separate with commas)")
        
        st.markdown("**Note:** This will create a new model entry in the database for the selected brand.")
        
        submitted = st.form_submit_button("🆕 Add Model/Submodel", type="primary")
        
        if submitted:
            if not model_name.strip() or not submodel_name.strip():
                st.error("❌ Both Model and Submodel names are required")
                return
            
            # Check if this model/submodel combination already exists
            if check_model_exists(brand, model_name.strip(), submodel_name.strip()):
                st.error(f"❌ Model '{model_name.strip()}' with Submodel '{submodel_name.strip()}' already exists for {brand}")
                return
            
            # Add the new model/submodel
            if add_new_model(brand, model_name.strip(), submodel_name.strip(), initial_sizes.strip(), initial_materials.strip()):
                st.success(f"✅ Successfully added Model '{model_name.strip()}' with Submodel '{submodel_name.strip()}' to {brand}")
                st.rerun()
            else:
                st.error("❌ Failed to add new model/submodel")

def show_manage_size_material_interface(brand):
    """Unified interface for managing sizes and materials - Add, Edit, Delete all in one"""
    st.markdown("#### 📋 Manage Sizes & Materials")
    st.info("💡 **Note:** To add a completely new model/submodel, use the 'Add Model/Submodel' tab instead.")
    
    # Get models for the brand
    models = get_models_for_brand(brand)
    if not models:
        st.warning(f"No models found for {brand}. Please add a model first using the 'Add Model/Submodel' tab.")
        return
    
    # Model selection
    unique_collections = sorted(list(set([m[2] for m in models])))
    selected_collection = st.selectbox("Model (Collection):", [""] + unique_collections, key="manage_collection_select")
    
    # Submodel dropdown
    if selected_collection:
        submodels_for_collection = [m for m in models if m[2] == selected_collection]
        submodel_options = [m[1] for m in submodels_for_collection]
        selected_submodel = st.selectbox("Submodel:", [""] + submodel_options, key="manage_submodel_select")
    else:
        selected_submodel = st.selectbox("Submodel:", [""], key="manage_submodel_select_empty")
    
    if selected_collection and selected_submodel:
        # Find the model ID
        model_id = None
        for m in models:
            if m[2] == selected_collection and m[1] == selected_submodel:
                model_id = m[0]
                break
    
        if model_id:
            st.markdown("---")
            
            # Add New Size/Material Section at the top
            st.markdown("### ➕ Add New Size or Material")
            
            col_add1, col_add2 = st.columns(2)
            
            with col_add1:
                st.markdown("##### 📏 Add Size")
                with st.form("add_size_form"):
                    new_size = st.text_input("New Size:", placeholder="Enter new size")
                    submitted_size = st.form_submit_button("➕ Add Size", type="primary")
                    
                    if submitted_size and new_size.strip():
                        if add_size_or_material(model_id, "size", new_size.strip()):
                            st.success(f"✅ Added size '{new_size.strip()}' to {selected_collection} - {selected_submodel}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add size")
            
            with col_add2:
                st.markdown("##### 🧵 Add Material")
                with st.form("add_material_form"):
                    new_material = st.text_input("New Material:", placeholder="Enter new material")
                    submitted_material = st.form_submit_button("➕ Add Material", type="primary")
                    
                    if submitted_material and new_material.strip():
                        if add_size_or_material(model_id, "material", new_material.strip()):
                            st.success(f"✅ Added material '{new_material.strip()}' to {selected_collection} - {selected_submodel}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add material")
            
            st.markdown("---")
            
            # Current Sizes and Materials Section with Edit/Delete
            st.markdown("### 📋 Current Sizes & Materials")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📏 Sizes**")
                sizes = get_sizes_for_model(model_id)
                if sizes:
                    for size in sizes:
                        with st.container():
                            size_col1, size_col2 = st.columns([3, 2])
                            
                            with size_col1:
                                # Editable text input for size
                                new_size_value = st.text_input(
                                    "Size:",
                                    value=size[1],
                                    key=f"edit_size_{size[0]}",
                                    label_visibility="collapsed"
                                )
                            
                            with size_col2:
                                # Save and Delete buttons side by side
                                btn_col1, btn_col2 = st.columns(2)
                                with btn_col1:
                                    if st.button("💾 Save", key=f"save_size_{size[0]}", type="secondary"):
                                        if new_size_value.strip() and new_size_value.strip() != size[1]:
                                            if update_size(size[0], new_size_value.strip()):
                                                st.success(f"✅ Updated size to '{new_size_value.strip()}'")
                                                st.rerun()
                                            else:
                                                st.error("❌ Failed to update size")
                                        elif new_size_value.strip() == size[1]:
                                            st.info("💡 No changes to save")
                                        else:
                                            st.error("❌ Size cannot be empty")
                                with btn_col2:
                                    if st.button("🗑️ Delete", key=f"delete_size_{size[0]}", type="secondary"):
                                        if delete_size(size[0]):
                                            st.success(f"✅ Deleted size '{size[1]}'")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to delete size")
                else:
                    st.info("No sizes found for this model")
            
            with col2:
                st.markdown("**🧵 Materials**")
                materials = get_materials_for_model(model_id)
                if materials:
                    for material in materials:
                        with st.container():
                            mat_col1, mat_col2 = st.columns([3, 2])
                            
                            with mat_col1:
                                # Editable text input for material
                                new_material_value = st.text_input(
                                    "Material:",
                                    value=material[1],
                                    key=f"edit_material_{material[0]}",
                                    label_visibility="collapsed"
                                )
                            
                            with mat_col2:
                                # Save and Delete buttons side by side
                                btn_col1, btn_col2 = st.columns(2)
                                with btn_col1:
                                    if st.button("💾 Save", key=f"save_material_{material[0]}", type="secondary"):
                                        if new_material_value.strip() and new_material_value.strip() != material[1]:
                                            if update_material(material[0], new_material_value.strip()):
                                                st.success(f"✅ Updated material to '{new_material_value.strip()}'")
                                                st.rerun()
                                            else:
                                                st.error("❌ Failed to update material")
                                        elif new_material_value.strip() == material[1]:
                                            st.info("💡 No changes to save")
                                        else:
                                            st.error("❌ Material cannot be empty")
                                with btn_col2:
                                    if st.button("🗑️ Delete", key=f"delete_material_{material[0]}", type="secondary"):
                                        if delete_material(material[0]):
                                            st.success(f"✅ Deleted material '{material[1]}'")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to delete material")
                else:
                    st.info("No materials found for this model")

def show_edit_submodel_interface(brand):
    """Show interface for editing submodel names"""
    st.markdown("#### 📝 Edit Submodel Name")
    st.info("💡 **Note:** This will change the submodel name in the database.")
    
    # Get models for the brand
    models = get_models_for_brand(brand)
    if not models:
        st.info(f"No models found for {brand}")
        return
    
    # Model selection
    unique_collections = sorted(list(set([m[2] for m in models])))
    selected_collection = st.selectbox(
        "Model (Collection):", 
        [""] + unique_collections, 
        key="edit_submodel_collection_select"
    )
    
    if selected_collection:
        # Get submodels for the selected collection
        submodels_for_collection = [m for m in models if m[2] == selected_collection]
        submodel_options = [(m[0], m[1]) for m in submodels_for_collection]  # (id, name)
        
        if submodel_options:
            selected_submodel_data = st.selectbox(
                "Submodel to Edit:", 
                [("", "")] + submodel_options, 
                format_func=lambda x: x[1] if x[1] else "Select a submodel...",
                key="edit_submodel_select"
            )
            
            if selected_submodel_data[0]:  # If a submodel is selected
                model_id, current_name = selected_submodel_data
                
                with st.form("edit_submodel_form"):
                    st.write(f"**Current Name:** {current_name}")
                    new_name = st.text_input(
                        "New Submodel Name:", 
                        value=current_name,
                        placeholder="Enter new submodel name"
                    )
                    
                    submitted = st.form_submit_button("📝 Update Submodel Name", type="primary")
                    
                    if submitted:
                        if not new_name.strip():
                            st.error("❌ Submodel name cannot be empty")
                        elif new_name.strip() == current_name:
                            st.warning("⚠️ New name is the same as current name")
                        else:
                            if update_submodel_name(model_id, new_name.strip()):
                                st.success(f"✅ Successfully updated submodel name from '{current_name}' to '{new_name.strip()}'")
                                st.rerun()
                            else:
                                st.error("❌ Failed to update submodel name")
        else:
            st.info("No submodels found for this model")
    else:
        st.info("Please select a model first")

def show_delete_submodel_interface(brand):
    """Show interface for deleting entire submodels"""
    st.markdown("#### ❌ Delete Submodel")
    st.warning("⚠️ **Warning:** This will permanently delete the entire submodel and all its associated sizes and materials!")
    
    # Get models for the brand
    models = get_models_for_brand(brand)
    if not models:
        st.info(f"No models found for {brand}")
        return
    
    # Model selection
    unique_collections = sorted(list(set([m[2] for m in models])))
    selected_collection = st.selectbox(
        "Model (Collection):", 
        [""] + unique_collections, 
        key="delete_submodel_collection_select"
    )
    
    if selected_collection:
        # Get submodels for the selected collection
        submodels_for_collection = [m for m in models if m[2] == selected_collection]
        submodel_options = [(m[0], m[1], m[2]) for m in submodels_for_collection]  # (id, name, collection)
        
        if submodel_options:
            selected_submodel_data = st.selectbox(
                "Submodel to Delete:", 
                [("", "", "")] + submodel_options, 
                format_func=lambda x: x[1] if x[1] else "Select a submodel to delete...",
                key="delete_submodel_select"
            )
            
            if selected_submodel_data[0]:  # If a submodel is selected
                model_id, submodel_name, collection_name = selected_submodel_data
                
                # Show details about what will be deleted
                st.markdown("**Will be deleted:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Model:** {collection_name}")
                    st.write(f"**Submodel:** {submodel_name}")
                    
                    # Show sizes that will be deleted
                    sizes = get_sizes_for_model(model_id)
                    if sizes:
                        st.write(f"**Sizes ({len(sizes)}):** {', '.join([s[1] for s in sizes])}")
                    else:
                        st.write("**Sizes:** None")
                
                with col2:
                    # Show materials that will be deleted
                    materials = get_materials_for_model(model_id)
                    if materials:
                        st.write(f"**Materials ({len(materials)}):** {', '.join([m[1] for m in materials])}")
                    else:
                        st.write("**Materials:** None")
                
                # Confirmation section
                st.markdown("---")
                st.error("⚠️ **This action cannot be undone!**")
                
                confirmation_text = st.text_input(
                    f"Type '{submodel_name}' to confirm deletion:",
                    placeholder=f"Type {submodel_name} here..."
                )
                
                if st.button("❌ DELETE SUBMODEL", type="primary", disabled=(confirmation_text != submodel_name)):
                    if confirmation_text == submodel_name:
                        if delete_submodel(model_id):
                            st.success(f"✅ Successfully deleted submodel '{submodel_name}' and all its data")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete submodel")
                    else:
                        st.error("❌ Confirmation text doesn't match")
        else:
            st.info("No submodels found for this model")
    else:
        st.info("Please select a model first")

def get_complete_model_state(model_id, engine):
    """Get complete state of a model including all sizes and materials"""
    try:
        with engine.connect() as conn:
            # Get model details
            model_result = conn.execute(
                text("""SELECT b.name as brand, m.collection, m.model_name 
                        FROM models m 
                        JOIN brands b ON m.brand_id = b.id 
                        WHERE m.id = :model_id"""),
                {"model_id": model_id}
            ).fetchone()
            
            if not model_result:
                return None
            
            brand, model_name, submodel_name = model_result
            
            # Get all sizes
            sizes_result = conn.execute(
                text("SELECT size FROM model_sizes WHERE model_id = :model_id ORDER BY size"),
                {"model_id": model_id}
            ).fetchall()
            sizes = [size[0] for size in sizes_result]
            
            # Get all materials
            materials_result = conn.execute(
                text("SELECT material FROM model_materials WHERE model_id = :model_id ORDER BY material"),
                {"model_id": model_id}
            ).fetchall()
            materials = [material[0] for material in materials_result]
            
            return {
                "brand": brand,
                "model": model_name,
                "submodel": submodel_name,
                "sizes": sizes,
                "materials": materials
            }
    except Exception as e:
        return None

def get_models_for_brand(brand):
    """Get all models for a specific brand"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return []
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT m.id, m.model_name, m.collection 
                        FROM models m 
                        JOIN brands b ON m.brand_id = b.id 
                        WHERE b.name = :brand_name 
                        ORDER BY m.collection, m.model_name"""),
                {"brand_name": brand}
            )
            return result.fetchall()
    except Exception as e:
        st.error(f"❌ Failed to fetch models: {e}")
        return []

def get_sizes_for_model(model_id):
    """Get all sizes for a specific model"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return []
        
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, size FROM model_sizes WHERE model_id = :model_id ORDER BY size"),
                {"model_id": model_id}
            )
            return result.fetchall()
    except Exception as e:
        st.error(f"❌ Failed to fetch sizes: {e}")
        return []

def get_materials_for_model(model_id):
    """Get all materials for a specific model"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return []
        
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, material FROM model_materials WHERE model_id = :model_id ORDER BY material"),
                {"model_id": model_id}
            )
            return result.fetchall()
    except Exception as e:
        st.error(f"❌ Failed to fetch materials: {e}")
        return []

def add_size_or_material(model_id, type_name, value):
    """Add a new size or material to a model"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        # Get model details for audit logging
        model_details = get_model_details_by_id(model_id)
        if not model_details:
            st.error("❌ Model not found")
            return False
        
        brand, model_name, submodel_name = model_details
        
        # Get current list BEFORE adding
        if type_name == "size":
            current_items = get_sizes_for_model(model_id)
            old_list = [item[1] for item in current_items]  # Get size values
        else:  # material
            current_items = get_materials_for_model(model_id)
            old_list = [item[1] for item in current_items]  # Get material values
        
        with engine.begin() as conn:
            if type_name == "size":
                # Check if size already exists
                existing = conn.execute(
                    text("SELECT id FROM model_sizes WHERE model_id = :model_id AND UPPER(size) = UPPER(:size)"),
                    {"model_id": model_id, "size": value}
                ).fetchone()
                
                if existing:
                    st.warning(f"Size '{value}' already exists for this model")
                    return False
                
                conn.execute(
                    text("INSERT INTO model_sizes (model_id, size) VALUES (:model_id, :size)"),
                    {"model_id": model_id, "size": value}
                )
            else:  # material
                # Check if material already exists
                existing = conn.execute(
                    text("SELECT id FROM model_materials WHERE model_id = :model_id AND UPPER(material) = UPPER(:material)"),
                    {"model_id": model_id, "material": value}
                ).fetchone()
                
                if existing:
                    st.warning(f"Material '{value}' already exists for this model")
                    return False
                
                conn.execute(
                    text("INSERT INTO model_materials (model_id, material) VALUES (:model_id, :material)"),
                    {"model_id": model_id, "material": value}
                )
        
        # Get updated list AFTER adding
        if type_name == "size":
            updated_items = get_sizes_for_model(model_id)
            new_list = [item[1] for item in updated_items]  # Get size values
        else:  # material
            updated_items = get_materials_for_model(model_id)
            new_list = [item[1] for item in updated_items]  # Get material values
        
        # Log the audit action with before/after lists
        log_audit_action(
            category="size_material",
            action="add",
            brand=brand,
            model=model_name,
            submodel=submodel_name,
            user_id=st.session_state.username,
            old_value={type_name: ",".join(old_list) if old_list else ""},
            new_value={type_name: ",".join(new_list)}
        )
        
        return True
    except Exception as e:
        st.error(f"❌ Failed to add {type_name}: {e}")
        return False

def check_model_exists(brand, model_name, submodel_name):
    """Check if a model/submodel combination already exists for a brand"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT m.id FROM models m 
                        JOIN brands b ON m.brand_id = b.id 
                        WHERE b.name = :brand_name 
                        AND UPPER(m.collection) = UPPER(:model_name) 
                        AND UPPER(m.model_name) = UPPER(:submodel_name)"""),
                {"brand_name": brand, "model_name": model_name, "submodel_name": submodel_name}
            ).fetchone()
            
            return result is not None
    except Exception as e:
        st.error(f"❌ Failed to check if model exists: {e}")
        return False

def add_new_model(brand, model_name, submodel_name, initial_sizes=None, initial_materials=None):
    """Add a new model/submodel combination to the database"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        with engine.begin() as conn:
            # Get brand ID
            brand_result = conn.execute(
                text("SELECT id FROM brands WHERE UPPER(name) = UPPER(:brand_name)"),
                {"brand_name": brand}
            ).fetchone()
            
            if not brand_result:
                st.error(f"❌ Brand '{brand}' not found")
                return False
            
            brand_id = brand_result[0]
            
            # Insert new model
            result = conn.execute(
                text("INSERT INTO models (brand_id, collection, model_name) VALUES (:brand_id, :collection, :model_name) RETURNING id"),
                {"brand_id": brand_id, "collection": model_name, "model_name": submodel_name}
            )
            
            model_id = result.fetchone()[0]
            
            # Add initial sizes if provided
            sizes_list = []
            if initial_sizes:
                sizes_list = [size.strip() for size in initial_sizes.split(',') if size.strip()]
                for size in sizes_list:
                    conn.execute(
                        text("INSERT INTO model_sizes (model_id, size) VALUES (:model_id, :size)"),
                        {"model_id": model_id, "size": size}
                    )
            
            # Add initial materials if provided
            materials_list = []
            if initial_materials:
                materials_list = [material.strip() for material in initial_materials.split(',') if material.strip()]
                for material in materials_list:
                    conn.execute(
                        text("INSERT INTO model_materials (model_id, material) VALUES (:model_id, :material)"),
                        {"model_id": model_id, "material": material}
                    )
        
        # Create the new model data for audit
        new_model_data = {
            "model": model_name,
            "submodel": submodel_name
        }
        if sizes_list:
            new_model_data["sizes"] = sizes_list
        if materials_list:
            new_model_data["materials"] = materials_list
        
        # Log the audit action with focused data
        log_audit_action(
            category="model_submodel",
            action="add",
            brand=brand,
            model=model_name,
            submodel=submodel_name,
            user_id=st.session_state.username,
            old_value=None,
            new_value=new_model_data
        )
        
        return True
    except Exception as e:
        st.error(f"❌ Failed to add new model: {e}")
        return False

def update_size(size_id, new_value):
    """Update a size"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        # Get current size value and model details for audit logging
        with engine.connect() as conn:
            size_result = conn.execute(
                text("SELECT size, model_id FROM model_sizes WHERE id = :id"),
                {"id": size_id}
            ).fetchone()
            
            if not size_result:
                st.error("❌ Size not found")
                return False
            
            old_size_value = size_result[0]
            model_id = size_result[1]
        
        model_details = get_model_details_by_id(model_id)
        if not model_details:
            st.error("❌ Model not found")
            return False
        
        brand, model_name, submodel_name = model_details
        
        # Get current sizes list BEFORE update
        current_sizes = get_sizes_for_model(model_id)
        old_sizes_list = [size[1] for size in current_sizes]
        
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE model_sizes SET size = :size WHERE id = :id"),
                {"size": new_value, "id": size_id}
            )
        
        # Get updated sizes list AFTER update
        updated_sizes = get_sizes_for_model(model_id)
        new_sizes_list = [size[1] for size in updated_sizes]
        
        # Log the audit action with before/after size lists
        log_audit_action(
            category="size_material",
            action="edit",
            brand=brand,
            model=model_name,
            submodel=submodel_name,
            user_id=st.session_state.username,
            old_value={"size": ",".join(old_sizes_list)},
            new_value={"size": ",".join(new_sizes_list)}
        )
        
        return True
    except Exception as e:
        st.error(f"❌ Failed to update size: {e}")
        return False

def update_material(material_id, new_value):
    """Update a material"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        # Get current material value and model details for audit logging
        with engine.connect() as conn:
            material_result = conn.execute(
                text("SELECT material, model_id FROM model_materials WHERE id = :id"),
                {"id": material_id}
            ).fetchone()
            
            if not material_result:
                st.error("❌ Material not found")
                return False
            
            old_material_value = material_result[0]
            model_id = material_result[1]
        
        model_details = get_model_details_by_id(model_id)
        if not model_details:
            st.error("❌ Model not found")
            return False
        
        brand, model_name, submodel_name = model_details
        
        # Get current materials list BEFORE update
        current_materials = get_materials_for_model(model_id)
        old_materials_list = [material[1] for material in current_materials]
        
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE model_materials SET material = :material WHERE id = :id"),
                {"material": new_value, "id": material_id}
            )
        
        # Get updated materials list AFTER update
        updated_materials = get_materials_for_model(model_id)
        new_materials_list = [material[1] for material in updated_materials]
        
        # Log the audit action with before/after material lists
        log_audit_action(
            category="size_material",
            action="edit",
            brand=brand,
            model=model_name,
            submodel=submodel_name,
            user_id=st.session_state.username,
            old_value={"material": ",".join(old_materials_list)},
            new_value={"material": ",".join(new_materials_list)}
        )
        
        return True
    except Exception as e:
        st.error(f"❌ Failed to update material: {e}")
        return False

def delete_size(size_id):
    """Delete a size"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        # Get size value and model details for audit logging before deletion
        with engine.connect() as conn:
            size_result = conn.execute(
                text("SELECT size, model_id FROM model_sizes WHERE id = :id"),
                {"id": size_id}
            ).fetchone()
            
            if not size_result:
                st.error("❌ Size not found")
                return False
            
            old_size_value = size_result[0]
            model_id = size_result[1]
        
        model_details = get_model_details_by_id(model_id)
        if not model_details:
            st.error("❌ Model not found")
            return False
        
        brand, model_name, submodel_name = model_details
        
        # Get current sizes list BEFORE deletion
        current_sizes = get_sizes_for_model(model_id)
        old_sizes_list = [size[1] for size in current_sizes]
        
        with engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM model_sizes WHERE id = :id"),
                {"id": size_id}
            )
            
            if result.rowcount > 0:
                # Get updated sizes list AFTER deletion within the same transaction
                updated_sizes_result = conn.execute(
                    text("SELECT size FROM model_sizes WHERE model_id = :model_id ORDER BY size"),
                    {"model_id": model_id}
                ).fetchall()
                new_sizes_list = [size[0] for size in updated_sizes_result]
                
                # Log the audit action with before/after size lists
                log_audit_action(
                    category="size_material",
                    action="delete",
                    brand=brand,
                    model=model_name,
                    submodel=submodel_name,
                    user_id=st.session_state.username,
                    old_value={"size": ",".join(old_sizes_list)},
                    new_value={"size": ",".join(new_sizes_list) if new_sizes_list else ""}
                )
                return True
            else:
                st.error("❌ Size not found or already deleted")
                return False
    
    except Exception as e:
        st.error(f"❌ Failed to delete size: {e}")
        return False

def delete_material(material_id):
    """Delete a material"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        # Get material value and model details for audit logging before deletion
        with engine.connect() as conn:
            material_result = conn.execute(
                text("SELECT material, model_id FROM model_materials WHERE id = :id"),
                {"id": material_id}
            ).fetchone()
            
            if not material_result:
                st.error("❌ Material not found")
                return False
            
            old_material_value = material_result[0]
            model_id = material_result[1]
        
        model_details = get_model_details_by_id(model_id)
        if not model_details:
            st.error("❌ Model not found")
            return False
        
        brand, model_name, submodel_name = model_details
        
        # Get current materials list BEFORE deletion
        current_materials = get_materials_for_model(model_id)
        old_materials_list = [material[1] for material in current_materials]
        
        with engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM model_materials WHERE id = :id"),
                {"id": material_id}
            )
            
            if result.rowcount > 0:
                # Get updated materials list AFTER deletion within the same transaction
                updated_materials_result = conn.execute(
                    text("SELECT material FROM model_materials WHERE model_id = :model_id ORDER BY material"),
                    {"model_id": model_id}
                ).fetchall()
                new_materials_list = [material[0] for material in updated_materials_result]
                
                # Log the audit action with before/after material lists
                log_audit_action(
                    category="size_material",
                    action="delete",
                    brand=brand,
                    model=model_name,
                    submodel=submodel_name,
                    user_id=st.session_state.username,
                    old_value={"material": ",".join(old_materials_list)},
                    new_value={"material": ",".join(new_materials_list) if new_materials_list else ""}
                )
                return True
            else:
                st.error("❌ Material not found or already deleted")
                return False
    
    except Exception as e:
        st.error(f"❌ Failed to delete material: {e}")
        return False

def update_submodel_name(model_id, new_name):
    """Update a submodel name"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        # Get current submodel name and model details for audit logging
        model_details = get_model_details_by_id(model_id)
        if not model_details:
            st.error("❌ Model not found")
            return False
        
        brand, model_name, old_submodel_name = model_details
        
        with engine.begin() as conn:
            result = conn.execute(
                text("UPDATE models SET model_name = :new_name WHERE id = :id"),
                {"new_name": new_name, "id": model_id}
            )
            
            if result.rowcount > 0:
                # Log the audit action with only the submodel name change
                log_audit_action(
                    category="model_submodel",
                    action="edit",
                    brand=brand,
                    model=model_name,
                    submodel=new_name,  # Use new name for current submodel
                    user_id=st.session_state.username,
                    old_value={"submodel": old_submodel_name},
                    new_value={"submodel": new_name}
                )
                return True
            
            return False
        
    except Exception as e:
        st.error(f"❌ Failed to update submodel name: {e}")
        return False

def delete_submodel(model_id):
    """Delete a submodel and all its associated sizes and materials"""
    try:
        engine = get_main_db_engine()
        if not engine:
            return False
        
        # Get model details and associated data for audit logging before deletion
        model_details = get_model_details_by_id(model_id)
        if not model_details:
            st.error("❌ Model not found")
            return False
        
        brand, model_name, submodel_name = model_details
        
        # Get sizes and materials that will be deleted for audit
        sizes = get_sizes_for_model(model_id)
        materials = get_materials_for_model(model_id)
        
        deleted_data = {
            "model": model_name,
            "submodel": submodel_name,
            "sizes": [size[1] for size in sizes],
            "materials": [material[1] for material in materials]
        }
        
        with engine.begin() as conn:
            # Delete associated sizes first
            conn.execute(
                text("DELETE FROM model_sizes WHERE model_id = :model_id"),
                {"model_id": model_id}
            )
            
            # Delete associated materials
            conn.execute(
                text("DELETE FROM model_materials WHERE model_id = :model_id"),
                {"model_id": model_id}
            )
            
            # Finally delete the model itself
            result = conn.execute(
                text("DELETE FROM models WHERE id = :id"),
                {"id": model_id}
            )
            
            if result.rowcount > 0:
                # Log the audit action with focused deletion data
                log_audit_action(
                    category="model_submodel",
                    action="delete",
                    brand=brand,
                    model=model_name,
                    submodel=submodel_name,
                    user_id=st.session_state.username,
                    old_value=deleted_data,
                    new_value=None
                )
                return True
            
            return False
        
    except Exception as e:
        st.error(f"❌ Failed to delete submodel: {e}")
        return False

def main():
    """Main application"""
    # Check authentication first
    if not authenticate_user():
        return
    
    st.title("📝 Keywords Manager v2.0")
    st.markdown("---")
    
    # Initialize database
    if not init_request_database():
        st.error("❌ Failed to initialize database. Please check your database connection.")
        return
    
    # Sidebar
    with st.sidebar:
        # User info and logout
        st.subheader(f"👤 {st.session_state.username}")
        user_role = st.session_state.get('user_role', 'user')
        role_icons = {"user": "👤", "admin": "👑"}
        st.success(f"{role_icons.get(user_role, '�')} {user_role.title()}")
        
        if st.button("🚪 Logout", type="secondary"):
            logout_user()
        st.markdown("---")
        
        # Navigation based on role
        if user_role == "admin":
            page = st.radio("Menu:", [
                "📝 Submit Request", 
                "📋 All Requests",
                "📊 Brand Keywords", 
                "👑 Admin Panel",
                "🔧 Keyword Manager"
            ])
        else:  # user
            page = st.radio("Navigation:", [
                "📝 Submit Request", 
                "📋 All Requests",
                "📊 Brand Keywords"
            ])
        
        st.markdown("---")
        st.caption("Keywords Manager v2.0")
        with st.expander("🔍 Database Status", expanded=False):
            req_engine = get_request_db_engine()
            main_engine = get_main_db_engine()
            if req_engine and main_engine:
                st.success("✅ database: Connected")
            else:
                st.error("❌ database: Failed")
    
    # Main content
    if page == "📝 Submit Request":
        create_model_request_form()
    elif page == "📋 All Requests":
        show_user_requests()
    elif page == "📊 Brand Keywords":
        show_model_size_material_table()
    elif page == "👑 Admin Panel":
        create_admin_panel()
    elif page == "🔧 Keyword Manager":
        create_keyword_manager()

if __name__ == "__main__":
    main()
