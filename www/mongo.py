from pymongo import MongoClient

class PersonalDictionary:
    def __init__(self, connection_string, database_name):
        self.client = MongoClient(connection_string)
        self.db = self.client[database_name]
        self.collection = self.db['personal_dictionaries']

    def add_word(self, user_id, word):
        dictionary = self.collection.find_one({'user_id': user_id})
        if dictionary:
            words = dictionary.get('words', [])
            if word not in words:
                words.append(word)
            self.collection.update_one({'user_id': user_id}, {'$set': {'words': words}})
        else:
            self.collection.insert_one({'user_id': user_id, 'words': [word]})

    def get_dictionary(self, user_id):
        dictionary = self.collection.find_one({'user_id': user_id})
        if dictionary:
            return dictionary.get('words', [])
        else:
            return []

    def delete_word(self, user_id, word):
        dictionary = self.collection.find_one({'user_id': user_id})
        if dictionary:
            words = dictionary.get('words', [])
            if word in words:
                words.remove(word)
                self.collection.update_one({'user_id': user_id}, {'$set': {'words': words}})

    def delete_dictionary(self, user_id):
        self.collection.delete_one({'user_id': user_id})

# Example usage:
# Initialize PersonalDictionary with MongoDB connection string and database name
mongo = PersonalDictionary('mongodb://localhost:27017/', 'my_database')

# Add word to user's dictionary
mongo.add_word('user123', 'hello')

# Get user's dictionary
print(mongo.get_dictionary('user123'))  # Output: ['hello']

# Add another word
mongo.add_word('user123', 'world')

# Get updated dictionary
print(mongo.get_dictionary('user123'))  # Output: ['hello', 'world']

# Delete a word
mongo.delete_word('user123', 'hello')

# Get updated dictionary
print(mongo.get_dictionary('user123'))  # Output: ['world']

# Delete user's dictionary
mongo.delete_dictionary('user123')

# Get dictionary after deletion
print(mongo.get_dictionary('user123'))  # Output: []
