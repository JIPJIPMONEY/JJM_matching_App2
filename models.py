"""
Database models for keyword management system using SQLAlchemy ORM
"""

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class Brand(Base):
    __tablename__ = 'brands'
    
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    
    # Relationships
    models = relationship("Model", back_populates="brand", cascade="all, delete-orphan")
    colors = relationship("BrandColor", back_populates="brand", cascade="all, delete-orphan")
    hardwares = relationship("BrandHardware", back_populates="brand", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}')>"

class Model(Base):
    __tablename__ = 'models'
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False)
    collection = Column(Text)
    model_name = Column(Text)
    
    # Relationships
    brand = relationship("Brand", back_populates="models")
    sizes = relationship("ModelSize", back_populates="model", cascade="all, delete-orphan")
    materials = relationship("ModelMaterial", back_populates="model", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Model(id={self.id}, brand_id={self.brand_id}, collection='{self.collection}', model_name='{self.model_name}')>"

class ModelSize(Base):
    __tablename__ = 'model_sizes'
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    size = Column(Text)
    
    # Relationships
    model = relationship("Model", back_populates="sizes")
    
    def __repr__(self):
        return f"<ModelSize(id={self.id}, model_id={self.model_id}, size='{self.size}')>"

class ModelMaterial(Base):
    __tablename__ = 'model_materials'
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    material = Column(Text)
    
    # Relationships
    model = relationship("Model", back_populates="materials")
    
    def __repr__(self):
        return f"<ModelMaterial(id={self.id}, model_id={self.model_id}, material='{self.material}')>"

class BrandColor(Base):
    __tablename__ = 'brand_colors'
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False)
    color = Column(Text)
    
    # Relationships
    brand = relationship("Brand", back_populates="colors")
    
    def __repr__(self):
        return f"<BrandColor(id={self.id}, brand_id={self.brand_id}, color='{self.color}')>"

class BrandHardware(Base):
    __tablename__ = 'brand_hardwares'
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False)
    hardware = Column(Text)
    
    # Relationships
    brand = relationship("Brand", back_populates="hardwares")
    
    def __repr__(self):
        return f"<BrandHardware(id={self.id}, brand_id={self.brand_id}, hardware='{self.hardware}')>"

def create_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(engine)

def get_session(db_config):
    """Create a database session"""
    connection_string = (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    engine = create_engine(connection_string)
    Session = sessionmaker(bind=engine)
    return Session(), engine
