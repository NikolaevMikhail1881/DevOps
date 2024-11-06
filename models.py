from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    city = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, city='{self.city}')>"
