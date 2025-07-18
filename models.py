"""
Database models for keyword management system using SQLAlchemy ORM
"""

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import QueuePool

Base = declarative_base()

class Brand(Base):
    __tablename__ = 'brands'
    
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False, index=True)  # เพิ่ม index
    
    # Relationships
    models = relationship("Model", back_populates="brand", cascade="all, delete-orphan", lazy="select")
    colors = relationship("BrandColor", back_populates="brand", cascade="all, delete-orphan", lazy="select")
    hardwares = relationship("BrandHardware", back_populates="brand", cascade="all, delete-orphan", lazy="select")
    
    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}')>"

class Model(Base):
    __tablename__ = 'models'
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False, index=True)  # เพิ่ม index
    collection = Column(Text, index=True)  # เพิ่ม index สำหรับการค้นหา
    model_name = Column(Text, index=True)  # เพิ่ม index สำหรับการค้นหา
    
    # Relationships
    brand = relationship("Brand", back_populates="models")
    sizes = relationship("ModelSize", back_populates="model", cascade="all, delete-orphan", lazy="select")
    materials = relationship("ModelMaterial", back_populates="model", cascade="all, delete-orphan", lazy="select")
    
    # เพิ่ม composite index สำหรับการค้นหาที่ใช้บ่อย
    __table_args__ = (
        Index('idx_brand_collection_model', 'brand_id', 'collection', 'model_name'),
    )
    
    def __repr__(self):
        return f"<Model(id={self.id}, brand_id={self.brand_id}, collection='{self.collection}', model_name='{self.model_name}')>"

class ModelSize(Base):
    __tablename__ = 'model_sizes'
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False, index=True)  # เพิ่ม index
    size = Column(Text, index=True)  # เพิ่ม index สำหรับการค้นหา
    
    # Relationships
    model = relationship("Model", back_populates="sizes")
    
    def __repr__(self):
        return f"<ModelSize(id={self.id}, model_id={self.model_id}, size='{self.size}')>"

class ModelMaterial(Base):
    __tablename__ = 'model_materials'
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False, index=True)  # เพิ่ม index
    material = Column(Text, index=True)  # เพิ่ม index สำหรับการค้นหา
    
    # Relationships
    model = relationship("Model", back_populates="materials")
    
    def __repr__(self):
        return f"<ModelMaterial(id={self.id}, model_id={self.model_id}, material='{self.material}')>"

class BrandColor(Base):
    __tablename__ = 'brand_colors'
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False, index=True)  # เพิ่ม index
    color = Column(Text, index=True)  # เพิ่ม index สำหรับการค้นหา
    
    # Relationships
    brand = relationship("Brand", back_populates="colors")
    
    def __repr__(self):
        return f"<BrandColor(id={self.id}, brand_id={self.brand_id}, color='{self.color}')>"

class BrandHardware(Base):
    __tablename__ = 'brand_hardwares'
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False, index=True)  # เพิ่ม index
    hardware = Column(Text, index=True)  # เพิ่ม index สำหรับการค้นหา
    
    # Relationships
    brand = relationship("Brand", back_populates="hardwares")
    
    def __repr__(self):
        return f"<BrandHardware(id={self.id}, brand_id={self.brand_id}, hardware='{self.hardware}')>"

def create_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(engine)

def get_session(db_config):
    """Create a database session with connection pooling"""
    connection_string = (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    
    # เพิ่ม connection pooling และ performance optimizations
    engine = create_engine(
        connection_string,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False  # เปลี่ยนเป็น True เพื่อดู SQL queries สำหรับ debugging
    )
    
    Session = sessionmaker(bind=engine)
    return Session(), engine

# เพิ่มฟังก์ชันสำหรับสร้าง indexes เพิ่มเติม
def create_additional_indexes(engine):
    """Create additional indexes for better performance"""
    with engine.connect() as conn:
        # สร้าง indexes เพิ่มเติมที่ไม่ได้ define ใน model
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_brands_name_lower ON brands(LOWER(name))")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_models_collection_lower ON models(LOWER(collection))")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_models_name_lower ON models(LOWER(model_name))")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_brand_colors_color_lower ON brand_colors(LOWER(color))")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_brand_hardwares_hardware_lower ON brand_hardwares(LOWER(hardware))")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model_sizes_size_lower ON model_sizes(LOWER(size))")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model_materials_material_lower ON model_materials(LOWER(material))")
            conn.commit()
        except Exception as e:
            print(f"Warning: Could not create additional indexes: {e}")