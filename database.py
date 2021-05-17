import motor.motor_asyncio
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_DETAILS =  os.environ.get("MONGO_DETAILS")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

database = client.oneDB

users_collection = database.get_collection("users")
evaluate_collection = database.get_collection("evaluate")

# helpers

def user_helper(identity_id):
    return {
       identity_id:{
           "identity_id": identity_id,
           "full_name": None,
           "birth_date":None,
           "hashed_password":None,
           "disabled":False
       },
       'evaluate_datetime': None,
       'create_datetime': datetime.utcnow()+ timedelta(hours=7)
    }

def evaluate_helper(identity_id):
    return {
         "identity_id": identity_id,
         "score": 0,
         "datetime": datetime.utcnow()+ timedelta(hours=7)
    }

def evaluate_score_detail(name, score):
    return{
        "name": name,
        "position": "Employee",
        "score": score
    } 

def evaluate_detail(identity_id,name):
    return{
        "identity_id": identity_id,
        "name": name
    } 


# Retrieve all students present in the database
async def retrieve_users():
    users = []
    async for user in users_collection.find({},{'_id': 0}):
        users.append(user)
    return users



async def get_admin_hashed_password():
    admin = None
    async for user in users_collection.find({},{'_id': 0}):
        for id in user:
            if str(id).startswith("A"):
                return user[id]['hashed_password']
    return admin


async def create_new_user(identity_id):
    insert_data = user_helper(identity_id)
    if str(identity_id).startswith("B"):
        await users_collection.insert_one(insert_data)
        new_student = await users_collection.find_one({ identity_id : { '$exists' : True }} )
    else:
        await users_collection.insert_one(insert_data)
        new_student = await users_collection.find_one({ identity_id : { '$exists' : True }})
    return new_student[identity_id]['identity_id']


async def register_new_user(full_name, identity_id ,password, birth_date):
    is_user_exits = await users_collection.find_one({ identity_id : { '$exists' : True }} )
    if not is_user_exits:
        return None
    if is_user_exits[identity_id]['full_name'] is not None:
        return None
    if is_user_exits:
        new_user = user_helper(identity_id)
        new_user[identity_id]['full_name'] = full_name
        new_user[identity_id]['hashed_password'] = password
        new_user[identity_id]['birth_date'] = birth_date
        result = await users_collection.update_one({"_id": is_user_exits["_id"]},{"$set": new_user})
        if str(identity_id).startswith("E"):
            await evaluate_collection.insert_one(evaluate_helper(identity_id))
        return result

async def evaluate_score_list(identity_id):
    evaluate_list_result = []
    is_user_exits = await users_collection.find_one({ identity_id : { '$exists' : True }})
    if is_user_exits:
        if str(identity_id).startswith("E") :
            result = await evaluate_collection.find_one({"identity_id":identity_id})
            user_data = await users_collection.find_one({identity_id: { '$exists' : True }})
            full_name = user_data[identity_id]['full_name']
            data = evaluate_score_detail(full_name,result['score'])
            evaluate_list_result.append(data)
            return evaluate_list_result
        else:
            object_id = is_user_exits["_id"]
            result = evaluate_collection.find({"_id":{"$ne":object_id} })
            async for user in result:
                user_identity_id = user['identity_id']
                if str(user_identity_id).startswith("E"):
                    user_data = await users_collection.find_one({user_identity_id: { '$exists' : True }})
                    full_name = user_data[user_identity_id]['full_name']
                    data = evaluate_score_detail(full_name,user['score'])
                    evaluate_list_result.append(data)
            return evaluate_list_result


async def evaluate_list(identity_id):
    evaluate_list_result = []
    is_user_exits = await users_collection.find_one({ identity_id : { '$exists' : True }})
    if is_user_exits:
        object_id = is_user_exits["_id"]
        result = evaluate_collection.find({"_id":{"$ne":object_id} })
        async for user in result:
            user_identity_id = user['identity_id']
            if str(user_identity_id).startswith("E"):
                user_data = await users_collection.find_one({user_identity_id: { '$exists' : True }})
                full_name = user_data[user_identity_id]['full_name']
                data = evaluate_detail(user_identity_id,full_name)
                evaluate_list_result.append(data)
        return evaluate_list_result

async def calculate_evaluate_score(idenntity_id, evaluate_list):
    user_data = await users_collection.find_one({idenntity_id: { '$exists' : True }})
    evaluater_obj_id = user_data['_id']
    for evaluated_user in evaluate_list:
        evaluated_id = evaluated_user['identity_id']
        score =  evaluated_user['score']
        evaluated_data = await evaluate_collection.find_one({"identity_id" : evaluated_id}, {"score": 1})
        current_score = evaluated_data['score']
        if current_score == 0:
            await evaluate_collection.update_one(
                {"identity_id" : evaluated_id}, 
                {"$set": {"score": score}})
        else:
            calculated_score = (score + current_score)/2
            await evaluate_collection.update_one(
                {"identity_id" : evaluated_id}, 
                {"$set": {"score": calculated_score}})
    update_result = await users_collection.update_one(
                {"_id" : evaluater_obj_id}, 
                {"$set": {"evaluate_datetime": datetime.utcnow()+ timedelta(hours=7)}})
    if update_result:
        return True
    return False
