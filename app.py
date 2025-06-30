from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USERS_FILE = 'users.txt'
BLOGS_DIR = 'blogs'


@app.context_processor
def inject_now():
    from datetime import datetime
    return {'current_year': datetime.utcnow().year}



@app.template_filter('format_dt')
def format_dt(value):
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%H-%M %d-%m-%Y")
    except Exception:
        return value



# Ensure blogs directory exists
os.makedirs(BLOGS_DIR, exist_ok=True)

# Helper to load users
def load_users():
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    username, password = line.split(':', 1)
                    users[username] = password
    return users

# Helper to save new user
def save_user(username, password):
    with open(USERS_FILE, 'a') as f:
        f.write(f"{username}:{password}\n")

# Helper to load all blogs
def load_all_blogs():
    all_blogs = []
    if not os.path.exists(BLOGS_DIR):
        return all_blogs

    for user in os.listdir(BLOGS_DIR):
        user_folder = os.path.join(BLOGS_DIR, user)
        if os.path.isdir(user_folder):
            for blog_file in os.listdir(user_folder):
                file_path = os.path.join(user_folder, blog_file)
                with open(file_path, 'r') as f:
                    title = f.readline().strip()
                    published = f.readline().strip()
                    edited = f.readline().strip()
                    content = f.read().strip()
                    all_blogs.append({
                        'author': user,
                        'title': title,
                        'published': published,
                        'edited': edited,
                        'content': content,
                        'filename': blog_file
                    })
    all_blogs.sort(key=lambda x: x['published'], reverse=True)
    return all_blogs


@app.route('/')
def home():
    blogs = load_all_blogs()
    return render_template('home.html', blogs=blogs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username] == password:
            session['username'] = username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()

        if username in users:
            flash('Username already taken.', 'warning')
        elif not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            flash('Password must contain letters and numbers.', 'warning')
        else:
            save_user(username, password)
            flash('Registered successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        flash('Please log in to upload blogs.', 'info')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        if not title or not content:
            flash('Title and content cannot be empty.', 'warning')
        else:
            user = session['username']
            user_folder = os.path.join(BLOGS_DIR, user)
            os.makedirs(user_folder, exist_ok=True)
            timestamp = datetime.utcnow().isoformat()
            filename = f"{uuid.uuid4().hex}.txt"
            file_path = os.path.join(user_folder, filename)
            with open(file_path, 'w') as f:
                f.write(f"{title}\n")
                f.write(f"{timestamp}\n")
                f.write("None\n")  # No edits yet
                f.write(content)
            flash('Blog uploaded successfully!', 'success')
            return redirect(url_for('home'))

    return render_template('upload.html')


@app.route('/profile')
def profile():
    if 'username' not in session:
        flash('Please log in to view your profile.', 'info')
        return redirect(url_for('login'))
    
    username = session['username']
    # Load only this user's blogs
    user_folder = os.path.join(BLOGS_DIR, username)
    blogs = []
    if os.path.isdir(user_folder):
        for blog_file in os.listdir(user_folder):
            file_path = os.path.join(user_folder, blog_file)
            with open(file_path, 'r') as f:
                title = f.readline().strip()
                published = f.readline().strip()
                edited = f.readline().strip()
                content = f.read().strip()
                blogs.append({
                    'title': title,
                    'published': published,
                    'edited': edited,
                    'content': content,
                    'filename': blog_file
                })
        blogs.sort(key=lambda x: x['published'], reverse=True)
    
    return render_template('profile.html', username=username, blogs=blogs)


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    results = []
    blogs = load_all_blogs()
    if query:
        results = [b for b in blogs if query.lower() in b['title'].lower() or query.lower() in b['content'].lower()]
    return render_template('search.html', results=results)



@app.route('/edit/<filename>', methods=['GET', 'POST'])
def edit_blog(filename):
    if 'username' not in session:
        flash('Please log in.', 'info')
        return redirect(url_for('login'))
    
    user = session['username']
    file_path = os.path.join(BLOGS_DIR, user, filename)
    if not os.path.exists(file_path):
        flash('Blog not found.', 'danger')
        return redirect(url_for('profile'))
    
    # Load current data
    with open(file_path, 'r') as f:
        title = f.readline().strip()
        published = f.readline().strip()
        edited = f.readline().strip()
        content = f.read().strip()
    
    if request.method == 'POST':
        new_title = request.form['title'].strip()
        new_content = request.form['content'].strip()
        if not new_title or not new_content:
            flash('Title and content cannot be empty.', 'warning')
        else:
            edited_timestamp = datetime.utcnow().isoformat()
            with open(file_path, 'w') as f:
                f.write(f"{new_title}\n")
                f.write(f"{published}\n")
                f.write(f"{edited_timestamp}\n")
                f.write(new_content)
            flash('Blog updated successfully!', 'success')
            return redirect(url_for('profile'))
    
    return render_template('edit.html', title=title, content=content, filename=filename)

@app.route('/delete/<filename>', methods=['POST'])
def delete_blog(filename):
    if 'username' not in session:
        flash('Please log in.', 'info')
        return redirect(url_for('login'))

    user = session['username']
    file_path = os.path.join(BLOGS_DIR, user, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash('Blog deleted.', 'info')
    else:
        flash('Blog not found.', 'danger')
    return redirect(url_for('profile'))



if __name__ == '__main__':
    app.run(debug=True)
