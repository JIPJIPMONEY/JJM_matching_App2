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
import os

# Configure page - adjust based on authentication state
if 'authenticated' not in st.session_state or not st.session_state.get('authenticated', False):
    st.set_page_config(
        page_title="Login - Model Request System",
        page_icon="🔐",
        layout="centered"
    )
else:
    st.set_page_config(
        page_title="Model Request System",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded"
    )

# Database configuration for request_model database
REQUEST_DB_CONFIG = {
    'user': 'postgres',
    'password': '8558',
    'host': '192.168.1.111',
    'port': '5432',
    'database': 'request_model'
}

# Database configuration for jipjipmoney database (for fetching existing brands)
MAIN_DB_CONFIG = {
    'user': 'postgres',
    'password': '8558',
    'host': '192.168.1.111',
    'port': '5432',
    'database': 'jipjipmoney'
}

# User credentials
USER_CREDENTIALS = {
    "admin": "admin8558",
    "Build@CS": "NRJ24017", 
    "Pin@SCL": "NRJ23006",
    "Knight@SCL": "NRJ23004",
    "Gun@SCL": "NRJ24027"
}

# SQLAlchemy Base
Base = declarative_base()

def authenticate_user():
    """Handle user authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
    
    if not st.session_state.authenticated:
        show_login_page()
        return False
    
    return True

def show_login_page():
    """Display login page"""
    st.title("🔐 Login Required")
    st.subheader("Model Request System v2.0")
    
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
                    st.success(f"✅ Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

def check_credentials(username, password):
    """Check if username and password are valid"""
    return username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password

def logout_user():
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.rerun()

class ModelRequest(Base):
    """Model for storing model requests"""
    __tablename__ = 'model_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    requested_by = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    submodel = Column(String(100), nullable=False)
    sizes = Column(Text, nullable=False)  # Store as comma-separated values
    materials = Column(Text, nullable=True)  # Store as comma-separated values
    notes = Column(Text, nullable=True)
    status = Column(String(20), default='pending')  # pending, approved, rejected
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_by = Column(String(100), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)

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
            model=request_data['model'],
            submodel=request_data['submodel'],
            sizes=request_data['sizes'] or '',  # Handle None case
            materials=request_data['materials'],
            notes=request_data['notes']
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

def load_processed_requests():
    """Load processed requests from database"""
    try:
        engine = get_request_db_engine()
        if not engine:
            return []
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        requests = session.query(ModelRequest).filter(ModelRequest.status.in_(['approved', 'rejected'])).order_by(ModelRequest.processed_at.desc()).all()
        
        session.close()
        return requests
    except Exception as e:
        st.error(f"❌ Failed to load processed requests: {e}")
        return []

def update_request_status(request_id, status, processed_by, admin_notes=None):
    """Update request status"""
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
            
            session.commit()
            
            # If approved, insert into main database
            if status == 'approved':
                insert_approved_request_to_main_db(request)
        
        session.close()
        return True
    except Exception as e:
        st.error(f"❌ Failed to update request: {e}")
        return False

def insert_approved_request_to_main_db(request):
    """Insert approved request into jipjipmoney database"""
    try:
        engine = get_main_db_engine()
        if not engine:
            st.error("❌ Cannot connect to main database")
            return False
        
        with engine.begin() as conn:
            # Get or create brand
            brand_result = conn.execute(
                text("SELECT id FROM brands WHERE UPPER(name) = UPPER(:brand_name)"),
                {"brand_name": request.brand}
            ).fetchone()
            
            if brand_result:
                brand_id = brand_result[0]
            else:
                # Create new brand
                brand_result = conn.execute(
                    text("INSERT INTO brands (name) VALUES (:brand_name) RETURNING id"),
                    {"brand_name": request.brand}
                )
                brand_id = brand_result.fetchone()[0]
            
            # Get or create model
            model_result = conn.execute(
                text("SELECT id FROM models WHERE brand_id = :brand_id AND UPPER(model_name) = UPPER(:model_name)"),
                {"brand_id": brand_id, "model_name": request.model}
            ).fetchone()
            
            if model_result:
                model_id = model_result[0]
            else:
                # Create new model
                model_result = conn.execute(
                    text("INSERT INTO models (brand_id, model_name, collection) VALUES (:brand_id, :model_name, :collection) RETURNING id"),
                    {"brand_id": brand_id, "model_name": request.model, "collection": request.submodel}
                )
                model_id = model_result.fetchone()[0]
            
            # Process sizes
            if request.sizes:
                sizes_list = [size.strip() for size in request.sizes.split(',')]
                for size in sizes_list:
                    if size:
                        # Check if size already exists
                        size_result = conn.execute(
                            text("SELECT id FROM model_sizes WHERE model_id = :model_id AND UPPER(size) = UPPER(:size)"),
                            {"model_id": model_id, "size": size}
                        ).fetchone()
                        
                        if not size_result:
                            conn.execute(
                                text("INSERT INTO model_sizes (model_id, size) VALUES (:model_id, :size)"),
                                {"model_id": model_id, "size": size}
                            )
            
            # Process materials
            if request.materials:
                materials_list = [material.strip() for material in request.materials.split(',')]
                for material in materials_list:
                    if material:
                        # Check if material already exists
                        material_result = conn.execute(
                            text("SELECT id FROM model_materials WHERE model_id = :model_id AND UPPER(material) = UPPER(:material)"),
                            {"model_id": model_id, "material": material}
                        ).fetchone()
                        
                        if not material_result:
                            conn.execute(
                                text("INSERT INTO model_materials (model_id, material) VALUES (:model_id, :material)"),
                                {"model_id": model_id, "material": material}
                            )
        
        return True
        
    except Exception as e:
        st.error(f"❌ Failed to insert into main database: {e}")
        return False

def create_model_request_form():
    """Create the model request form"""
    st.subheader("📝 Submit New Model Request")
    existing_brands = get_existing_brands()
    brands_options = [''] + sorted(existing_brands) if existing_brands else ['']
    
    selected_brand = st.selectbox(
        "Brand *",
        brands_options
    )
    
    with st.form("model_request_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Submodel input
            submodel_name = st.text_input(
                "Collection Name *",
                placeholder="Enter collection name (e.g., Classic, 19, Reissue)"
            )
            # Model input (can be new or existing)
            size_input = st.text_input(
                "Sizes",
                placeholder="Enter sizes (e.g., 7,8,9,10 or just 25) - Optional if adding materials only"
            )
            
        
        with col2:
            model_name = st.text_input(
                "Model Name *",
                placeholder="Enter model name (e.g., Neverfull, Speedy)"
            )
            # Size input - support both single and multiple sizes
            material_input = st.text_input(
            "Materials",
            placeholder="Enter materials (e.g., Canvas, Leather) - Optional if adding sizes only"
            )
            
        # Additional notes
        notes = st.text_area(
            "Additional Notes",
            placeholder="Any additional information or special requests..."
        )
        
        # Submit button
        submitted = st.form_submit_button("📤 Submit Request", type="primary")
        
        if submitted:
            # Validate required fields
            if not selected_brand:
                st.error("❌ Please select a brand")
                return
            
            if not model_name.strip():
                st.error("❌ Please enter a model name")
                return
                
            if not submodel_name.strip():
                st.error("❌ Please enter a collection name")
                return
            
            # At least one of sizes or materials must be provided
            if not size_input.strip() and not material_input.strip():
                st.error("❌ Please enter at least sizes or materials (or both)")
                return
            
            # Prepare request data using logged-in username
            request_data = {
                'requested_by': st.session_state.username,
                'brand': selected_brand.strip(),
                'model': model_name.strip(),
                'submodel': submodel_name.strip(),
                'sizes': size_input.strip() if size_input.strip() else None,
                'materials': material_input.strip() if material_input.strip() else None,
                'notes': notes.strip() if notes.strip() else None
            }
            
            # Save request
            if save_model_request(request_data):
                st.success("✅ Request submitted successfully!")
                st.info(" Your request will be reviewed by an administrator.")
                # Clear the form by rerunning the app
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Failed to submit request. Please try again.")
            status_filter = st.selectbox("Filter by status:", ["All", "Approved", "Rejected"], key="processed_filter")
            
            # Filter processed requests
    processed_requests = load_processed_requests()
    # Sort by processed_at descending and limit to 20 rows
    processed_requests = sorted(processed_requests, key=lambda r: r.processed_at or datetime.min, reverse=True)[:20]
    # Create table data for processed requests
    table_data = []
    for request in processed_requests:
        status_icon = "✅" if request.status == "approved" else "❌"
        table_data.append({
        'ID': request.id,
        'Status': f"{status_icon} {request.status.title()}",
        'Requested By': request.requested_by,
        'Brand': request.brand,
        'Model': request.model,
        'Collection': request.submodel,
        'Sizes': request.sizes,
        'Materials': request.materials or 'N/A',
        'Submitted': request.submitted_at.strftime('%Y-%m-%d %H:%M'),
        'Processed By': request.processed_by,
        'Processed At': request.processed_at.strftime('%Y-%m-%d %H:%M'),
        'Admin Notes': request.admin_notes or 'N/A'
        })
    
    # Display table
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)
def create_admin_panel():
    """Create admin panel for approving/rejecting requests"""
    st.subheader("👑 Admin: Model Request Management")
    
    # Check if user is admin
    if st.session_state.username != "admin":
        st.error("🚫 Access Denied: Admin privileges required!")
        return
    
    # Tabs for pending and processed requests
    pending_tab, processed_tab = st.tabs(["📋 Pending Requests", "📊 Processed Requests"])
    
    with pending_tab:
        st.subheader("📋 Pending Requests")
        
        pending_requests = load_pending_requests()
        
        if pending_requests:
            for request in pending_requests:
                with st.expander(f"Request #{request.id}: {request.brand} - {request.model} - {request.submodel}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**👤 Requested by:** {request.requested_by}")
                        st.write(f"**🏷️ Brand:** {request.brand}")
                        st.write(f"**📦 Model:** {request.model}")
                        st.write(f"**🔸 Collection:** {request.submodel}")
                        st.write(f"**📏 Sizes:** {request.sizes}")
                        if request.materials:
                            st.write(f"**🧵 Materials:** {request.materials}")
                        if request.notes:
                            st.write(f"**📝 Notes:** {request.notes}")
                        st.write(f"**📅 Submitted:** {request.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
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
                                if update_request_status(request.id, 'approved', 'admin', admin_notes):
                                    st.success("✅ Request approved!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to approve request")
                        
                        with col_reject:
                            if st.button("❌ Reject", key=f"reject_{request.id}", type="secondary"):
                                if not admin_notes.strip():
                                    st.error("❌ Please provide a reason for rejection")
                                else:
                                    if update_request_status(request.id, 'rejected', 'admin', admin_notes):
                                        st.success("❌ Request rejected")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to reject request")
        else:
            st.info("📭 No pending requests at the moment.")
    
    with processed_tab:
        st.subheader("📊 Processed Requests")
        
        processed_requests = load_processed_requests()
        
        if processed_requests:
            # Filter options
            status_filter = st.selectbox("Filter by status:", ["All", "Approved", "Rejected"], key="processed_filter")
            
            # Filter processed requests
            filtered_requests = processed_requests
            if status_filter != "All":
                filtered_requests = [req for req in processed_requests if req.status.title() == status_filter]
            
            if filtered_requests:
                # Create table data for processed requests
                table_data = []
                for request in filtered_requests:
                    status_icon = "✅" if request.status == "approved" else "❌"
                    table_data.append({
                        'ID': request.id,
                        'Status': f"{status_icon} {request.status.title()}",
                        'Requested By': request.requested_by,
                        'Brand': request.brand,
                        'Model': request.model,
                        'Collection': request.submodel,
                        'Sizes': request.sizes,
                        'Materials': request.materials or 'N/A',
                        'Submitted': request.submitted_at.strftime('%Y-%m-%d %H:%M'),
                        'Processed By': request.processed_by,
                        'Processed At': request.processed_at.strftime('%Y-%m-%d %H:%M'),
                        'Admin Notes': request.admin_notes or 'N/A'
                    })
                
                # Display table
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info(f"📭 No {status_filter.lower()} requests found.")
        else:
            st.info("📭 No processed requests yet.")

def main():
    """Main application"""
    # Check authentication first
    if not authenticate_user():
        return
    
    st.title("📝 Model Request System")
    st.markdown("---")
    
    # Initialize database
    if not init_request_database():
        st.error("❌ Failed to initialize database. Please check your database connection.")
        return
    
    # Sidebar
    with st.sidebar:
        # User info and logout
        st.subheader(f"👤 {st.session_state.username}")
        if st.session_state.username == "admin":
            st.success("👑 Admin")
        
        if st.button("🚪 Logout", type="secondary"):
            logout_user()
        
        st.markdown("---")
        
        # Navigation
        if st.session_state.username == "admin":
            page = st.radio("Navigation:", ["📝 Submit Request", "👑 Admin Panel"])
        else:
            page = st.radio("Navigation:", ["📝 Submit Request"])
        
        st.markdown("---")
        st.caption("Model Request System v2.0")
        with st.expander("🔍 Database Status", expanded=False):
        # Test request database
          req_engine = get_request_db_engine()
          main_engine = get_main_db_engine()
          if req_engine and main_engine:
              st.success("✅ database: Connected")
          else:
              st.error("❌ database: Failed")
    # Main content
    if page == "📝 Submit Request":
        create_model_request_form()
    elif page == "👑 Admin Panel":
        create_admin_panel()

if __name__ == "__main__":
    main()
