from datetime import datetime, timedelta
from typing import Optional
from random import randint
# Fastapi
from fastapi import Depends, Request , FastAPI, HTTPException, status, Form
from fastapi.param_functions import Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# jwt / hash
from jose import JWTError, jwt
from passlib.context import CryptContext

import os
from dotenv import load_dotenv

# Database and Model
from database import (
    retrieve_users,
    get_admin_hashed_password,
    create_new_user,
    register_new_user,
    evaluate_score_list,
    evaluate_list,
    calculate_evaluate_score
)

# Import model
from model.user import (
    ResponseModel,
    User,
    UserInDB,
    UserRole
)
from model.auth import (
    Token,
    TokenData
)

from model.evaluate import Evaluate


load_dotenv()
# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY =  os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)

async def is_admin(plain_password):
    hashed = await get_admin_hashed_password()
    return verify_password(plain_password, hashed)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user(identity_id: str):
    db = await retrieve_users()
    for user in db:
        if identity_id in user:
            user_dict = user[identity_id]
            if isinstance(user['evaluate_datetime'], datetime):
                user_dict['evaluate_datetime'] =  user['evaluate_datetime']
            if isinstance(user['create_datetime'], datetime):    
                user_dict['create_datetime'] =  user['create_datetime']
            return UserInDB(**user_dict)

async def authenticate_user(identity_id: str, password: str):
    user = await get_user(identity_id)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identity_id: str = payload.get("sub")
        if identity_id is None:
            raise credentials_exception
        token_data = TokenData(identity_id=identity_id)
    except JWTError:
        raise credentials_exception

    user = await get_user(identity_id=token_data.identity_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/generate/new/user", response_description="Admin generate user")
async def generate_user(User = Depends(get_current_active_user), admin_password: str = Form(...), user_role: UserRole = Form(...)):
    if await is_admin(plain_password= admin_password):
        if user_role == UserRole.boss:
            identity_id = "{}{}".format("B",random_with_N_digits(13))
            respond = await create_new_user(identity_id)
        else:
            identity_id = "{}{}".format("E",random_with_N_digits(13))
            respond = await create_new_user(identity_id)
    return {"identity_id": respond}


@app.post("/register", response_description="Registered user")
async def register(identity_id: str = Form(..., min_length=14, max_length=14), birth_date: str = Form(...), full_name: str = Form(...), password: str = Form(...)):
    password = get_password_hash(password)
    result = await register_new_user(full_name, identity_id,password, birth_date)
    if result is not None:
        return {"Success": "Created user {}".format(identity_id)}
    return JSONResponse(status_code=409, content={"message": "Item not found or already exist"})


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    print("Form data = {} {}".format(form_data.username, form_data.password))
    user = await authenticate_user(form_data.username, form_data.password)
    print("User =",user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect identity_id or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.identity_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.post("/users/all", response_description="Users retrieved")
async def get_all_users(User = Depends(get_current_active_user), admin_password: str = Form(...)):
    users = []
    if await is_admin(plain_password= admin_password):
        users = await retrieve_users()
    if users:
        return ResponseModel(users, "Users data retrieved successfully")
    return ResponseModel(users, "Empty list returned")


@app.get("/evaluate/score/list", response_description="Evaluation list retrieved")
async def get_evaluate_score_list(current_user: User = Depends(get_current_active_user)):
    result = await evaluate_score_list(current_user.identity_id)
    return JSONResponse(result)

@app.get("/evaluate/list", response_description="Evaluation list retrieved")
async def get_evaluate_list(current_user: User = Depends(get_current_active_user)):
    result = await evaluate_list(current_user.identity_id)
    return JSONResponse(result)

@app.post("/send/evaluate/score", response_description="Submited evaluate score")
async def submit_evaluate_score(current_user: User = Depends(get_current_active_user), payload: Evaluate = Body(...)):
    evaluate_list = []
    try:
        for payload_list in payload:
            evaluate_list = payload_list[1]
        if len(evaluate_list) != 0:
            result = await calculate_evaluate_score(current_user.identity_id, evaluate_list)
            if result:
                return JSONResponse(status_code=200, content={"message": "Success Evaluated!"})
        else:
            return JSONResponse(status_code=422, content={"message": "List is empty"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": e})

