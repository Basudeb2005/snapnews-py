
import sys
import os
import subprocess
import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import nltk

# First download NLTK data to ensure it's available
try:
    print("Running NLTK download script...")
    subprocess.run(["python", "download_nltk_data.py"], check=True)
    print("NLTK download complete")
except Exception as e:
    print(f"Error downloading NLTK data: {e}")

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

st.set_page_config(page_title='SnapNews🇸🇬: News Anytime, Anywhere', page_icon='snap.png')

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'orbitals-d866e-b32d6b61b17c.json'))
    firebase_admin.initialize_app(cred)

def login():
    st.title('Welcome to SnapNews')

    choice = st.selectbox('Login/Sign Up', ['Login', 'Sign Up'])

    if choice == 'Login':
        email = st.text_input('Email Address')
        password = st.text_input('Password', type='password')

        if st.button('Login'):
            try:
                user = auth.get_user_by_email(email)
                st.success(f'Login Successful for {user.email}. Press again to continue')
                st.session_state['logged_in'] = True
                st.session_state['username'] = user.display_name if user.display_name else user.email
                st.session_state['current_page'] = 'page1'
            except firebase_admin.auth.UserNotFoundError:
                st.warning('Login Failed: User not found.')
            except Exception as e:
                st.error(f'Error: {str(e)}')

    elif choice == 'Sign Up':
        email = st.text_input('Email Address')
        password = st.text_input('Password', type='password')
        username = st.text_input('Enter your unique username')

        if st.button('Create my account'):
            try:
                user = auth.create_user(
                    email=email,
                    password=password,
                    display_name=username
                )
                st.success('Account created successfully!')
                st.markdown('Please login using your email and password')
                st.balloons()
            except Exception as e:
                st.error(f'Error: {str(e)}')

def pa():
    import page1
    page1.main(st.session_state['username'])
    if st.button("Log out"):
        st.session_state['logged_in'] = False
        st.session_state['current_page'] = 'login'

def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'login'

    if st.session_state['current_page'] == 'login':
        login()
    elif st.session_state['current_page'] == 'page1' and st.session_state['logged_in']:
        pa()

if __name__ == "__main__":
    main()
