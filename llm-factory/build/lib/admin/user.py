from fastapi import FastAPI, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app import models, crud, schemas
from app.database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserCreate(BaseModel):
    username: str
    email: str

class ApiKeyBase(BaseModel):
    key: str

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKey(ApiKeyBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

class UserPermissionBase(BaseModel):
    permission_name: str

class UserPermissionCreate(UserPermissionBase):
    pass

class UserPermission(UserPermissionBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

@app.post("/users/", response_model=schemas.User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/users/{user_id}/api_keys/", response_model=schemas.ApiKey)
def create_api_key_for_user(user_id: int, api_key: ApiKeyCreate, db: Session = Depends(get_db)):
    return crud.create_api_key(db=db, api_key=api_key, user_id=user_id)

@app.post("/users/{user_id}/permissions/", response_model=schemas.UserPermission)
def create_permission_for_user(user_id: int, permission: UserPermissionCreate, db: Session = Depends(get_db)):
    return crud.create_user_permission(db=db, user_permission=permission, user_id=user_id)