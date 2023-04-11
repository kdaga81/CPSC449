import re
from flask import Flask, abort, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from werkzeug.utils import secure_filename
import pymysql

# Configure the Flask application
app = Flask(__name__)
# Change this to a secret key of your choice
app.config['JWT_SECRET_KEY'] = 'super-secret'  
# Set a maximum file size limit of 16 megabytes
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
jwt = JWTManager(app)

# Create a connection to the database
conn = pymysql.connect(
    host='localhost',
    user='username',
    password='password',
    db='movie_reviews',
    cursorclass= pymysql.cursors.DictCursor
)


# Define an error handler for 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({'error': 'Not found'}), 404

# Define a public API endpoint for getting a list of movies
@app.route('/movies', methods=['GET'])
def get_movies():
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM movie_reviews')
    movies = cursor.fetchall()
    return jsonify(movies)

# Define a private API endpoint for adding a movie
@app.route('/movies', methods=['POST'])
@jwt_required()
def add_movie():
    title = request.form['title']
    review = request.form['review']
    rating = request.form['rating']
    image = request.files['image']

    if image.content_length > app.config['MAX_CONTENT_LENGTH']:
        return jsonify({'error': 'File size exceeds maximum allowed'}), 413
       

    if not all([title, review, rating]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if the file is allowed
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    if not allowed_file(image.filename, allowed_extensions):
        return jsonify({'error': 'Only png, jpg and jpeg allowed! '})
    
    cursor = conn.cursor()
    cursor.execute('INSERT INTO movie_reviews (title, review, rating, image) VALUES (%s, %s, %s, %s)',
                   (title, review, rating, image))
    conn.commit()

    return jsonify({'success': 'Movie added successfully'}), 201

# Define method to handle allowed files extension
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Define an API endpoint for authenticating users
@app.route('/auth', methods=['POST'])
def authenticate():
    username = request.form['username']
    password = request.form['password']

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users where username = %s and password = %s',(username, password))
    users = cursor.fetchone()
    if not users:
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=username)
    return jsonify({'access_token': access_token}), 200

# Define an API endpoint for registering the users
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users where username = %s and password = %s',(username, password))
    user = cursor.fetchone()

    cursor.execute('SELECT * FROM users where username = %s',(username))
    curr_user = cursor.fetchone()
    if not all([username, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if curr_user: 
        return jsonify({'error': 'User already registered'}), 403
    elif not re.match(r'^[a-zA-Z]{6,20}$', username):
        return jsonify({'error': 'Invalid name. It must have atleast 6 characters long and should contain only alphabets.'}), 401
    elif not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{6,}$', password):
        return jsonify({'error': 'Invalid password. Password must be atleast 6 characters long, must contain atleast one upper and lowercase letter, must have one number, must have one special symbol'}), 403
    else:
        cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)',
                   (username, password))
        conn.commit()

    return jsonify({'success': 'User added successfully'}), 201
    

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
