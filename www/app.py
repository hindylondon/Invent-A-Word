from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
import requests as url_reqs
from google.auth.transport import requests
from pymongo import MongoClient
import app_oauth
from google.auth.transport.requests import Request

client = MongoClient('mongodb://localhost:27017/')
db = client['myapp']

# Initialize OAuth flow using client secrets file
flow = Flow.from_client_secrets_file(
    'googleOAuth.json',
    scopes=['openid', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/userinfo.email'],
    redirect_uri='https://localhost:5000/oauth2callback'
)


app = Flask(__name__)
app.secret_key = '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'

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["user_dictionaries"]
collection = db["dictionaries"]

# OAuth related routes

def credentials_to_dict(credentials):
    # Convert credentials to a dictionary
    return {'token': credentials.token, 'refresh_token': credentials.refresh_token, 'token_uri': credentials.token_uri, 'client_id': credentials.client_id, 'client_secret': credentials.client_secret, 'scopes': credentials.scopes}


# Route for the starting page
@app.route('/')
def starting_page():
    # Render the starting page template
    return render_template('starting_page.html')

# Route for initiating the login process
@app.route('/login')
    
def login():
    # Initiate the authorization URL
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    # Redirect user to Google for authentication
    return redirect(authorization_url)


# Route for handling OAuth callback
@app.route('/oauth2callback')
def callback():
    # Fetch token using the callback URL
    flow.fetch_token(authorization_response=request.url)

    # Check state to prevent CSRF attacks
    if not session['state'] == request.args['state']:
        return 'State mismatch', 500


    # Extract user credentials
    credentials = flow.credentials
    
    session['credentials'] = credentials_to_dict(credentials)
    request_session = requests.Request()

    # Verify the ID token
    id_info = id_token.verify_oauth2_token(
        credentials.id_token, request_session, flow.client_config['client_id']
    )

    session['google_id'] = id_info['sub']
    session['name'] = id_info.get('name', '')

    # Use it as needed (e.g., create a user in your database)
    users_collection = db['users']

    user_info = {
        'google_id':id_info['sub'],
        'email': id_info['email'],
        'name': id_info['name']
        
    }

    result = users_collection.update_one(
        {'google_id': user_info['google_id']},  # Filter
        {'$set': user_info},  # Update
        upsert=True  # Insert if the document does not exist
    )


    # Redirect user to the home page after successful login
    return redirect(url_for('home'))
    #return redirect('/')


# Route for the home page
@app.route('/home')
def home():
    if 'google_id' in session:
        # User is signed in, render home page with user email
        name = session.get('name', 'Guest')
        return render_template('home_logged_in.html', name=name)
    else:
        # User is not signed in, redirect to login
        return redirect(url_for('login'))


@app.route('/new_word')
def new_word():
    return render_template('new_word.html')


@app.route('/submit_word', methods=['POST'])
def submit_word():
    if request.method == 'POST':
        # Get user ID from the session
        user_id = session.get("google_id")

        # Process form data
        word_name = request.form.get("wordName")
        definitions = request.form.get("definitions")
        pronunciations = request.form.get("pronunciations")
        synonyms = request.form.get("synonyms", "")
        antonyms = request.form.get("antonyms", "")

        # Check if required fields are filled
        if not word_name or not definitions or not pronunciations:
            return render_template('submitted_word.html', message="Please fill out all required fields."), 400

        # Check if the word exists in the personal dictionary
        user_dictionary = collection.find_one({"user_id": user_id})
        if user_dictionary and word_name in user_dictionary.get("words", []):
            return render_template('submitted_word.html', message="This word is already in your personal dictionary, so it cannot be validated."), 400

        # Check if the word exists in the dictionary
        api_key = '79cdece0-3124-4718-ad26-013d3b0003e3'
        api_url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word_name}?key={api_key}'

        try:
            response = url_reqs.get(api_url)
            data = response.json()

            # Check if the word exists in the dictionary
            if isinstance(data, list):
                # Iterate through the list of entries
                for entry in data:
                    # Check if the entry is a dictionary and if it has 'meta' and 'hwi' keys
                    if isinstance(entry, dict) and 'meta' in entry and 'hwi' in entry:
                        # Get the headword information
                        headword_info = entry['hwi']
                        # Check if the headword matches the queried word
                        if 'hw' in headword_info and headword_info['hw'].lower() == word_name.lower():
                            # If the word already exists in the dictionary, inform the user
                            message = "This word already exists in the dictionary. Please try another word."
                            break
                else:
                    # If the word is not found in the dictionary, save it to the personal dictionary
                    message = "This word is successfully validated and will be added to your personal dictionary."
                    save_word_to_database(user_id, word_name, definitions, pronunciations, synonyms, antonyms)
            else:
                # If the API response is not a list, it might indicate an error or invalid word
                message = "Invalid response from the dictionary API. Please try again later."

            return render_template('submitted_word.html', message=message)

        except Exception as e:
            # If an error occurs while validating the word, inform the user
            error_message = f"Error occurred while validating the word: {e}"
            print(error_message)
            return render_template('submitted_word.html', message=error_message), 500

    return render_template('submitted_word.html', message="Invalid request method."), 405

def save_word_to_database(user_id, word_name, definitions, pronunciations, synonyms, antonyms):
    # Save word to user's dictionary in MongoDB
    user_dictionary = collection.find_one({"user_id": user_id})
    if user_dictionary:
        words = user_dictionary.get("words", [])
        # Check if the word already exists in the dictionary
        existing_word = next((word for word in words if word['word_name'] == word_name), None)
        if existing_word:
            return {"message": "This word is already in your personal dictionary, so it cannot be validated.", "status": "error"}
        else:
            # If the word does not exist, add it to the dictionary
            words.append({
                "word_name": word_name,
                "definitions": definitions,
                "pronunciations": pronunciations,
                "synonyms": synonyms,
                "antonyms": antonyms
            })
            collection.update_one({"user_id": user_id}, {"$set": {"words": words}})
    else:
        # If the user does not have a dictionary yet, create a new one and add the word
        collection.insert_one({"user_id": user_id, "words": [{
            "word_name": word_name,
            "definitions": definitions,
            "pronunciations": pronunciations,
            "synonyms": synonyms,
            "antonyms": antonyms
        }]})
    return {"message": "Word saved successfully.", "status": "success"}


@app.route('/view_dictionary')
def view_dictionary():
    # Get the user's email from the session (you'll replace this with your actual authentication mechanism)
    user_email = session.get("google_id")

    # Retrieve the user's personal dictionary from the database
    user_dictionary = collection.find_one({"user_id": user_email})

    if user_dictionary:
        # Extract the words from the user's dictionary
        words = user_dictionary.get("words", [])
        return render_template('personal_dictionary.html', words=words)
    else:
        # If the user's dictionary is not found, return a message
        return render_template('personal_dictionary.html', message="No words found in your personal dictionary.")

@app.route('/sign_out', methods=['POST'])
def sign_out():
    # Clear session data
    session.pop('google_id', None)
    session.pop('name', None)
    # Redirect user to the starting page or sign-in page
    return redirect(url_for('starting_page'))


if __name__ == '__main__':
    # Run the application in debug mode
    app.run(debug=True)



