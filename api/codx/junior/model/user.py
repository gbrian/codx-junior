from pydantic import BaseModel, Field
from typing import Optional

# Existing CodxUser model
class CodxUser(BaseModel):
    username: str = Field(default="", description="Unique username of the user")
    email: Optional[str] = Field(default=None, description="Email address of the user")
    full_name: Optional[str] = Field(default="", description="Full name of the user")
    is_active: bool = Field(default=True, description="Indicates if the user account is active")
    is_superuser: bool = Field(default=False, description="Indicates if the user has superuser privileges")
    
    def activate(self):
        self.is_active = True
    
    def deactivate(self):
        self.is_active = False

# New Login model for authentication
class Login(BaseModel):
    token: Optional[str] = Field(default=None, description="Authentication token for the user session")
    identifier: Optional[str] = Field(default=None, description="Unique identifier, like username or email, for login")
    password: Optional[str] = Field(default=None, description="Password for user authentication")