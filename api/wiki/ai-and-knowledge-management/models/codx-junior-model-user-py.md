# Models

This document describes the data models used within the codx-api project.

## User Model

The `CodxUser` model represents a user in the system.

### Attributes

*   `username` (str): The unique username of the user. Defaults to an empty string.
*   `email` (Optional[str]): The email address of the user. Defaults to `None`.
*   `full_name` (Optional[str]): The full name of the user. Defaults to an empty string.
*   `is_active` (bool): Indicates if the user account is active. Defaults to `True`.
*   `is_superuser` (bool): Indicates if the user has superuser privileges. Defaults to `False`.

### Methods

*   `activate()`: Sets `is_active` to `True`.
*   `deactivate()`: Sets `is_active` to `False`.

```python /codx/junior/model/user.py
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
```

## Login Model

The `Login` model is used for user authentication.

### Attributes

*   `token` (Optional[str]): The authentication token for the user session. Defaults to `None`.
*   `identifier` (Optional[str]): A unique identifier, such as a username or email, for login. Defaults to `None`.
*   `password` (Optional[str]): The password for user authentication. Defaults to `None`.

```python /codx/junior/model/user.py
# New Login model for authentication
class Login(BaseModel):
    token: Optional[str] = Field(default=None, description="Authentication token for the user session")
    identifier: Optional[str] = Field(default=None, description="Unique identifier, like username or email, for login")
    password: Optional[str] = Field(default=None, description="Password for user authentication")
```