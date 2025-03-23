
import sys
import os
import subprocess
import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import nltk
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download required NLTK data
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('maxent_ne_chunker', quiet=True)
nltk.download('words', quiet=True)

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
