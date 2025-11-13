"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional

# Example schemas (you can keep these as references)

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# PAYLOT app schemas

class Lead(BaseModel):
    """
    Leads collected from landing page
    Collection name: "lead"
    """
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    broker: Optional[str] = Field(None, max_length=120)
    expected_monthly_volume: Optional[float] = Field(None, ge=0, description="Expected monthly trading volume in lots")
    message: Optional[str] = Field(None, max_length=1000)
    consent: bool = Field(True, description="User consent to be contacted")
