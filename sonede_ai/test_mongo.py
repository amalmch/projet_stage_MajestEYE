from db import is_available, get_db

print("Mongo available:", is_available())

db = get_db()

print("Database:", db.name)

print("Collections:", db.list_collection_names())