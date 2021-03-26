# FastAPI
from fastapi import APIRouter, HTTPException, status, Request, Depends, BackgroundTasks

# SQLAlchemy
from sqlalchemy.orm import Session

# Types
from typing import List, Optional

# Custom Modules
from .. import schemas, crud
from ..core import security
from ..core.config import settings
from ..dependencies import get_db, get_current_user
from .. import background_functions

router = APIRouter(prefix="/users", tags=['users'])

@router.get("/", response_model=List[schemas.UserResponse])
def get_all_users(userId: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Return a list of all users in the database
    """
    if userId:
        users = [crud.get_user_by_id(db, userId)]
    else:
        users = crud.get_users(db, skip=skip, limit=limit)
    
    # TODO perhaps there is a better way of returning this model.
    # It seems like its trying to immidate graphql
    return [
        schemas.UserResponse(  
        id=user.id,
        email=user.email,
        username=user.username,
        bio=user.bio,
        birthdate=user.birthdate
    ) for user in users]


@router.get("/me", response_model=schemas.User)
def get_authenticated_user(db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    """Get the currently logged in user if there is one (testing purposes only)
    """
    return current_user


@router.post("/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Create a new user record in the database
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    print("Sending registration email")
    bg_tasks.add_task(background_functions.send_registration_confirmation_email, email=user.email)
    return crud.create_user(db=db, user=user)


@router.put('/', response_model=schemas.UserUpdateResponseBody)
def update_user(request_body:schemas.UserUpdateRequestBody,
                 db: Session = Depends(get_db),
                 current_user: schemas.UserWithPassword = Depends(get_current_user)):
    
    # Check that password is correct
    if not security.verify_password(request_body.password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not authorized to update that user")
    
    # Update user attributes
    user = crud.update_user(db, current_user.id, request_body)
    return user


@router.delete('/', response_model=schemas.EmptyResponse)
def delete_user(request_body:schemas.UserDeleteRequestBody,
                 db: Session = Depends(get_db),
                 current_user: schemas.UserWithPassword = Depends(get_current_user)):
    if not security.verify_password(request_body.password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not authorized to delete that user")
    delete_successful = crud.delete_user(db, current_user.id)
    
    return schemas.EmptyResponse()
