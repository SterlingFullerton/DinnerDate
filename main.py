#Imports
import json
import sqlite3
import random
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def createDatabaseTables(cursor):
  #user
  cursor.execute("""CREATE TABLE users 
                      (username TEXT NOT NULL PRIMARY KEY, 
                      password TEXT,
                      first_name TEXT, 
                      last_name TEXT, 
                      email TEXT,
                      UNIQUE(email))""")
  
  #friends
  cursor.execute("""CREATE TABLE friends 
                      (username TEXT,
                      friend TEXT,
                      FOREIGN KEY (username) 
                        REFERENCES users (username) 
                        ON DELETE CASCADE,
                      FOREIGN KEY (username) 
                        REFERENCES users (friend) 
                        ON DELETE CASCADE)""")
  
  #friend_requests
  cursor.execute("""CREATE TABLE friend_requests
                      (username TEXT,
                      other TEXT,
                      FOREIGN KEY (username) 
                        REFERENCES users (username) 
                        ON DELETE CASCADE,
                      FOREIGN KEY (username) 
                        REFERENCES users (other) 
                        ON DELETE CASCADE)""")

  #group
  cursor.execute("""CREATE TABLE groups 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      name TEXT, admin TEXT, latitude REAL, longitude REAL,
                      FOREIGN KEY (admin) 
                        REFERENCES users (username) 
                        ON DELETE CASCADE)""")
  
  #group_members
  cursor.execute("""CREATE TABLE group_members 
                      (id INTEGER, 
                      username TEXT, 
                      FOREIGN KEY (id) 
                        REFERENCES groups (id) 
                        ON DELETE CASCADE, 
                      FOREIGN KEY (username) 
                        REFERENCES users (username) 
                        ON DELETE CASCADE)""")
  
  #restaurants 
  cursor.execute("""CREATE TABLE restaurants
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT, photo_ref TEXT, lat REAL, lon REAL,
                    price_level INTEGER, rating INTEGER, 
                    group_id INTEGER,
                    FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE)""")
  
  #restaurants_choice
  cursor.execute("""CREATE TABLE restaurants_choice
                    (group_id INTEGER, 
                    restaurant_id INTEGER,
                    member TEXT,
                    choice INTEGER,
                    FOREIGN kEY (group_id)
                      REFERENCES groups (id)
                      ON DELETE CASCADE, 
                    FOREIGN KEY (restaurant_id)
                      REFERENCES restaurants (id)
                      ON DELETE CASCADE,
                    FOREIGN KEY (member)
                      REFERENCES users (username)
                      ON DELETE CASCADE)""")

def fillUsers(cursor):

  email_hosts = ["gmail", "yahoo", "me", "outlook", "hotmail"]
  email_endings = ["ca", "com"]

  with open("usernames.txt", "r") as fp:
    line = fp.readline().strip()
    while line != "":
      email = f"{line}@{random.choice(email_hosts)}.{random.choice(email_endings)}"

      password = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for i in range(random.randint(6, 23)))
      password += random.choice(["!", "@", "#", "$", "%", "^", "&", "*", "-", "_", "+", "="])
      password += str(random.randint(0, 9))

      first_name = line[:len(line)//2]
      last_name = line[len(line)//2:]

      cursor.execute(f"""INSERT INTO users(username, password, first_name, last_name, email) 
                          values(?, ?, ?, ?, ?)""",
                          (line, password, first_name, last_name, email))

      line = fp.readline().strip()

def createDatabase():
  connection = sqlite3.connect("dinnerdate.db")
  cursor = connection.cursor()
  createDatabaseTables(cursor)
  fillUsers(cursor)
  connection.commit()
  connection.close()

class dinnerDate:
  def __init__(self):
    self.connection = sqlite3.connect("dinnerdate.db")
    self.cursor = self.connection.cursor()
    try:
      self.API_KEY = os.getenv("API_KEY")
    except:
      print("Could not aquire api key from .env file")

  def createUser(self, username: str, password: str, first_name: str, last_name: str, email: str):
    #Validate Username
    if username is None or username == '':
      return "username invalid"

    #Validate Password
    if password is None:
      return "no password given"
    if len(password) < 8 or len(password) > 25: 
      return "password not within 8-25 characters"

    hasDigit = False
    hasUpper = False
    hasSymbol = False
    symbols = ["!", "@", "#", "$", "%", "^", "&", "*", "-", "_", "+", "="]
    for char in password:
      if char.isupper(): hasUpper = True
      if char.isdigit(): hasDigit = True
      if char in symbols: hasSymbol = True
      
    if not hasUpper:
      return "Password requires an uppercase character"
    if not hasDigit:
      return "Password requires a numerical value"
    if not hasSymbol:
      return f"Password requires one of these symbols [{''.join(symbols)}]"
    
    #first_name and last_name will not be validated

    #Username and Email must be checked for existing columns on db

    request = self.cursor.execute(f"""
    SELECT username, email
    FROM users
    WHERE 
    username=? OR email=?
    """, (username, email)).fetchall()
    
    for r in request:
      if r[0] == username:
        return "Username already exists"
      if r[1] == email:
        return "Email already exists"
    
    #If we get to this point, we are valid

    self.cursor.execute(f"""INSERT INTO 
                users(username, password, first_name, last_name, email) 
                values(?, ?, ?, ?, ?)""", 
                (username, password, first_name, last_name, email))

    self.connection.commit()

    validate_check = self.cursor.execute(f"SELECT username FROM users WHERE username= ?", (username,))

    if not validate_check:
      return "unknown error occured while trying to create user"
    return "User Created Successfully"

  def deleteUser(self, username: str, password: str):

    #Check if username and password exist
    request = self.cursor.execute(f'SELECT username FROM users WHERE username = ? AND password = ?', (username, password)).fetchall()

    #If it does not exist
    if len(request) == 0:
      return "Username or Password was not correct, user not deleted"

    self.cursor.execute(f'DELETE FROM users WHERE username = ? AND password = ?', (username, password))
    self.connection.commit()

    request_2 = self.cursor.execute(f'SELECT username FROM users WHERE username = ? AND password = ?', (username, password)).fetchall()

    if len(request_2) > 0:
      return "User was not removed"

    return f"User {request[0][0]} Removed"
  
  def addFriend(self, username: str, other: str):
    #Confirm Users Exist
    users = self.cursor.execute("SELECT username FROM users WHERE username = ? OR username = ?", (username, other)).fetchall()
    username_exists = False
    other_exists = False

    for user in users:
      if user[0] == username:
        username_exists = True
      elif user[0] == other:
        other_exists = True
      
    if not username_exists:
      return "Requester Not Found"
    
    if not other_exists:
      return "Username does not exist"

    #Confirm You are not already Friends
    request = self.cursor.execute("""SELECT * FROM friends WHERE (username = ? AND friend = ?) or (username = ? AND friend = ?)""",
                        (username, other, other, username)).fetchall()
    if len(request) > 0:
      return "You are already Friends with that user"

    #Add Friend Request
    self.cursor.execute("""INSERT INTO
                friend_requests(username, other)
                values(?, ?)""",
                (username, other))
    
    self.connection.commit()

    #Confirm Friend Request Add
    users_2 = self.cursor.execute("""
                SELECT * 
                FROM friend_requests
                WHERE username = ? AND other = ?""", 
                (username, other)).fetchall()
    
    #Expected Value for true is 1 eg users_2 returns [('user_1', 'user_2')]

    if len(users_2[0]) == 0: 
      return "Unkown Error Occured"

    return "Friend Request Sent"

  def getFriendRequests(self, username: str):

    request = self.cursor.execute("""SELECT username
                          FROM friend_requests
                          WHERE other = ?""",
                          (username,)).fetchall()
    friend_requests = []
    for user in request:
      friend_requests.append(user[0])

    return friend_requests

  def acceptFriendRequest(self, username: str, other: str):
    #username is the user making the request
    #other is the user who made the friend request

    #Confirm this request exists
    request = self.cursor.execute("""
    SELECT * 
    FROM friend_requests
    WHERE username = ? and other = ?""",
    (other, username)).fetchall()

    if len(request) == 0:
      return "Friend Request does not exist"
    #Request Exists

    #Remove Request
    self.cursor.execute("""DELETE FROM friend_requests WHERE username = ? and other = ?""",
                        (other, username))

    #Confirm You are not already Friends
    request = self.cursor.execute("""SELECT * FROM friends WHERE (username = ? AND friend = ?) or (username = ? AND friend = ?)""",
                        (username, other, other, username)).fetchall()
    if len(request) > 0:
      return "You are already Friends with that user"

    #Add Friend
    self.cursor.execute("""INSERT INTO 
                friends(username, friend) 
                values(?, ?)""",
                (username, other))

    self.connection.commit()

    #Confirm Add Friend
    request = self.cursor.execute("""
    SELECT *
    FROM friends
    WHERE (username = ? AND friend = ?) OR (username = ? AND friend = ?)""",
    (username, other, other, username)).fetchall()

    if len(request) == 0:
      return "Unknown Error While Adding Friend"

    return f"You are now friends with {other}"

  def removeFriend(self, username: str, other: str):
    #Confirm you are friends
    request = self.cursor.execute("""SELECT * FROM friends WHERE (username = ? AND friend = ?) or (username = ? AND friend = ?)""",
                        (username, other, other, username)).fetchall()
    if len(request) == 0:
      return "You are not friends with that user!"

    #Remove Friend
    self.cursor.execute("""DELETE FROM friends WHERE (username = ? AND friend = ?) or (username = ? AND friend = ?)""",
                        (username, other, other, username))
    self.connection.commit()

    #Confirm you removed friend
    request = self.cursor.execute("""SELECT * FROM friends WHERE (username = ? AND friend = ?) or (username = ? AND friend = ?)""",
                        (username, other, other, username)).fetchall()

    if len(request) > 0:
      return "Friend not removed"
    
    return "Friend Removed"

  def createGroup(self, username: str, group_invites: list, latitute: int, longitude: int):
    #group_invites is a list of usernames (strings)

    if len(group_invites) == 0:
      return "You must add someone to create a group"

    #Figure out which group_invites are friends
    query = "SELECT username FROM friends WHERE (username = ? AND friend = ?) OR (username = ? AND friend = ?)"

    for i in range(len(group_invites)-1):
      query += " OR (username = ? AND friend = ?) OR (username = ? AND friend = ?)"
    
    l = [username, group_invites[0], group_invites[0], username]

    for member in group_invites[1:]:
      l.append(username)
      l.append(member)
      l.append(member)
      l.append(username)

    request = self.cursor.execute(query, tuple(l)).fetchall()

    if len(request) == 0:
      return "You have no friends!"

    friends = []
    for friend in request:
      friends.append(friend[0])

    group_name = ", ".join([username, ", ".join(friends)])
    
    self.cursor.execute("""INSERT INTO groups (name, latitude, longitude, admin) values (?, ?, ?, ?)""", 
                        (group_name, latitute, longitude, username))
    self.connection.commit()

    group_id = self.cursor.execute("""SELECT id FROM groups WHERE name = ?""", (group_name,)).fetchall()
    
    if len(group_id) == 0:
      return "Unknown error occured when creating group"

    group_id = group_id[0][0]

    self.cursor.execute("""INSERT INTO group_members (id, username) values(?, ?)""",
                        (group_id, username))

    for friend in friends:
      self.cursor.execute("""INSERT INTO group_members (id, username) values(?, ?)""",
                        (group_id, friend))
    self.connection.commit()

    return group_id
    
  def deleteGroup(self, requesting_user: str, group_id: int):

    #Confirm user is group admin
    request = self.cursor.execute("""SELECT admin FROM groups WHERE id = ?""", (group_id,)).fetchall()

    #Confirm Group Exists
    if len(request) > 0:
      #Confirm User is group admin
      if (request[0][0] != requesting_user):
        return "User is not group admin!"
    
    self.cursor.execute("""DELETE FROM groups WHERE id = ?""", (group_id,))
    self.cursor.execute("""DELETE FROM group_members WHERE id = ?""", (group_id,))
    self.connection.commit()

    #Confirm Group Deleted
    request = self.cursor.execute("""SELECT admin, name FROM groups WHERE id = ?""", (group_id,)).fetchall()

    if len(request) != 0:
      return "Group Not Deleted"
    
    return f"Group Deleted"

  def getLocalRestaurants(self, group_id: int, lat: float, lon: float, radius: int = 5000):
    """
      This function has been modified to act like it is querying the google 
        place api as I will not put my private API key on github publicly
        and do not want you to have to set one up for it to run properly
    """

    keyword = "restaurant"
    keyword = f"&keyword={keyword}"
    #keyword = ''

    #Price level can be implemented in this request

    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat}%2C{lon}&radius={radius}&type=restaurant{keyword}&opennow&key={self.API_KEY}"

    #response = requests.request("GET", url, headers={}, data={})
    
    #record response
    """
    with open("getLocalRestaurants_output.json", "w", encoding='UTF-8') as fp:
      fp.write(response.text)
    """


    with open("getLocalRestaurants_output.json", "r", encoding='UTF-8') as fp: #, encoding='UTF-8'
      #fp.write(response.text)
      response = json.load(fp)
    
    #response = json.loads(response.content)

    if response["status"] != "OK":
      return f"Error {response['status']}"

    #response["results"]
    """List of dictionary
        --business_status expected OPERATIONAL
        -geometry->location->lat, lng
        -name
        --opening_hours->open_now required true
        -photos->photo_reference
        -place_id (for future queries)
        -price_level
        -rating
    """

    for b in response["results"]:
      try:
        if len(b["photos"]) == 0:
          print("restaurant has no photos, skipping")
          continue

        photo = b["photos"][0]["photo_reference"]
        
        if "price_level" in b.keys():
          price_level = b["price_level"]
        else:
          price_level = 0

        #Is restaurant already in database?
        result = self.cursor.execute("""SELECT id FROM restaurants WHERE name = ? AND lat = ? 
        AND lon = ? AND price_level = ? AND rating = ?""", 
        (b["name"], b["geometry"]["location"]["lat"], b["geometry"]["location"]["lng"], 
        price_level, b["rating"])).fetchall()

        if len(result) > 0:
          #Skip
          continue

        #Insert Restaurant
        self.cursor.execute("""
        INSERT INTO restaurants (name, photo_ref, lat, lon, price_level, rating) 
        values (?, ?, ?, ?, ?, ?)""",
        (b["name"], photo, 
        b["geometry"]["location"]["lat"], b["geometry"]["location"]["lng"], 
        price_level, b["rating"]))

        self.connection.commit()

        #Confirm Insert
        result = self.cursor.execute("""SELECT id FROM restaurants WHERE name = ? AND lat = ? 
        AND lon = ? AND price_level = ? AND rating = ?""", 
        (b["name"], b["geometry"]["location"]["lat"], b["geometry"]["location"]["lng"], 
        price_level, b["rating"])).fetchall()

        if len(result) == 0:
          continue

        print(f"{result[0][0]:4} Restaurant {b['name']} Added")
      except Exception as e:
        print(f"Error: {e}")

#createDatabase()

def example_flow():
  try:
    print("Creating Database")
    createDatabase()
  except:
    print("Database Already Created")

  d = dinnerDate()
  #Friends create accounts
  print(d.createUser("JackFrost", "dfhwIof7*", "Jack", "Frost", "JackFrost@hotmail.com"))
  print(d.createUser("Highlary", "fheuiwF$8", "High", "Lary", "Highlary@gmail.com"))

  #JackFrost sends friend request to Highlary
  print(d.addFriend("JackFrost", "Highlary"))

  #Highlary logs in and checks friend requests
  print(d.getFriendRequests("Highlary"))

  #Highlary accepts friend request
  print(d.acceptFriendRequest("Highlary", "JackFrost"))

  #Adding more friends
  print(d.addFriend("JackFrost", "LivingMyBestLife"))
  print(d.acceptFriendRequest("LivingMyBestLife", "JackFrost"))
  print(d.addFriend("JackFrost", "LadyInRed"))
  print(d.acceptFriendRequest("LadyInRed", "JackFrost"))
  print(d.addFriend("JackFrost", "LoneWolf"))
  print(d.acceptFriendRequest("LoneWolf", "JackFrost"))

  #group id will be hidden in the front end for querying
  group_id = d.createGroup("JackFrost", ["Highlary", "LivingMyBestLife", "LadyInRed", "LoneWolf"], 43.47371058300456, -80.52798807621002)

  d.getLocalRestaurants(group_id = group_id, lat = 43.47371058300456, lon = -80.52798807621002)

  d.connection.close()

example_flow()
