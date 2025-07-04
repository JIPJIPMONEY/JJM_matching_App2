"""
Database-based Keyword Manager - Replaces JSON-based keyword loading with database queries
"""

from models import Base, Brand, Model, ModelSize, ModelMaterial, BrandColor, BrandHardware, get_session
from sqlalchemy.orm import joinedload

class DatabaseKeywordManager:
    """
    Database-based keyword manager that replaces JSON file loading
    Provides the same interface as the original KeywordManager but reads from PostgreSQL
    """
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.session = None
        self.engine = None
        self.global_data = {}
        self.brands_cache = {}
        self.connect_to_database()
        self.load_all_keywords()
    
    def connect_to_database(self):
        """Establish database connection"""
        try:
            self.session, self.engine = get_session(self.db_config)
            return True
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return False
    
    def load_all_keywords(self):
        """Load all brand keywords from database and cache them"""
        try:
            if not self.session:
                return
            
            # Load all brands with their related data
            brands = self.session.query(Brand).options(
                joinedload(Brand.models).joinedload(Model.sizes),
                joinedload(Brand.models).joinedload(Model.materials),
                joinedload(Brand.colors),
                joinedload(Brand.hardwares)
            ).all()
            
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
            
        except Exception as e:
            print(f"❌ Error loading keywords from database: {e}")
    
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
        """Refresh the cache by reloading data from database"""
        self.brands_cache = {}
        self.global_data = {}
        self.load_all_keywords()
    
    def add_brand(self, brand_name):
        """Add a new brand to the database"""
        try:
            existing_brand = self.session.query(Brand).filter_by(name=brand_name).first()
            if existing_brand:
                return False, f"Brand '{brand_name}' already exists"
            
            brand = Brand(name=brand_name)
            self.session.add(brand)
            self.session.commit()
            self.refresh_cache()
            return True, f"Brand '{brand_name}' added successfully"
        except Exception as e:
            self.session.rollback()
            return False, f"Error adding brand: {e}"
    
    def add_model(self, brand_name, collection, model_name, sizes=None, materials=None):
        """Add a new model to a brand"""
        try:
            brand = self.session.query(Brand).filter_by(name=brand_name).first()
            if not brand:
                return False, f"Brand '{brand_name}' not found"
            
            model = Model(
                brand_id=brand.id,
                collection=collection,
                model_name=model_name
            )
            self.session.add(model)
            self.session.flush()
            
            # Add sizes
            if sizes:
                for size in sizes:
                    model_size = ModelSize(model_id=model.id, size=size)
                    self.session.add(model_size)
            
            # Add materials
            if materials:
                for material in materials:
                    model_material = ModelMaterial(model_id=model.id, material=material)
                    self.session.add(model_material)
            
            self.session.commit()
            self.refresh_cache()
            return True, f"Model '{model_name}' added to '{brand_name}'"
        except Exception as e:
            self.session.rollback()
            return False, f"Error adding model: {e}"
    
    def add_brand_color(self, brand_name, color):
        """Add a color to a brand"""
        try:
            brand = self.session.query(Brand).filter_by(name=brand_name).first()
            if not brand:
                return False, f"Brand '{brand_name}' not found"
            
            # Check if color already exists for this brand
            existing_color = self.session.query(BrandColor).filter_by(
                brand_id=brand.id, color=color
            ).first()
            if existing_color:
                return False, f"Color '{color}' already exists for '{brand_name}'"
            
            brand_color = BrandColor(brand_id=brand.id, color=color)
            self.session.add(brand_color)
            self.session.commit()
            self.refresh_cache()
            return True, f"Color '{color}' added to '{brand_name}'"
        except Exception as e:
            self.session.rollback()
            return False, f"Error adding color: {e}"
    
    def add_brand_hardware(self, brand_name, hardware):
        """Add a hardware to a brand"""
        try:
            brand = self.session.query(Brand).filter_by(name=brand_name).first()
            if not brand:
                return False, f"Brand '{brand_name}' not found"
            
            # Check if hardware already exists for this brand
            existing_hardware = self.session.query(BrandHardware).filter_by(
                brand_id=brand.id, hardware=hardware
            ).first()
            if existing_hardware:
                return False, f"Hardware '{hardware}' already exists for '{brand_name}'"
            
            brand_hardware = BrandHardware(brand_id=brand.id, hardware=hardware)
            self.session.add(brand_hardware)
            self.session.commit()
            self.refresh_cache()
            return True, f"Hardware '{hardware}' added to '{brand_name}'"
        except Exception as e:
            self.session.rollback()
            return False, f"Error adding hardware: {e}"
    
    def get_database_stats(self):
        """Get statistics about the keyword database"""
        try:
            stats = {
                'brands': self.session.query(Brand).count(),
                'models': self.session.query(Model).count(),
                'colors': self.session.query(BrandColor).count(),
                'hardwares': self.session.query(BrandHardware).count(),
                'sizes': self.session.query(ModelSize).count(),
                'materials': self.session.query(ModelMaterial).count()
            }
            return stats
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}
    
    def __del__(self):
        """Clean up database connection"""
        if self.session:
            self.session.close()
