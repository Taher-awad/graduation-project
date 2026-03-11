from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import User, UserRole
from shared.models import User, UserRole
from shared.schemas import UserCreate, Token, UserResponse
from shared.auth_utils import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    # Role is now passed from Pydantic model
    new_user = User(username=user.username, password_hash=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@router.post("/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Store role in metadata or just token
    access_token = create_access_token(data={"sub": db_user.username, "role": db_user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "role": db_user.role}
