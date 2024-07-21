import streamlit as st
from PIL import Image
from bs4 import BeautifulSoup as soup
from urllib.request import urlopen, Request
from newspaper import Article
import io
import nltk
from gtts import gTTS
import base64
import random
import requests
import re

nltk.download('punkt')

st.set_page_config(page_title='SnapNews🇸🇬: News Anytime, Anywhere', page_icon='snap.png')

if 'saved_articles' not in st.session_state:
    st.session_state['saved_articles'] = []

if 'saved_status' not in st.session_state:
    st.session_state['saved_status'] = {}

if 'page_number' not in st.session_state:
    st.session_state['page_number'] = 0

NEWS_API_KEY = 'ec48b2493593467a8947d0253d2786a2'

def fetch_news_search_topic(topic):
    try:
        site = f'https://news.google.com/rss/search?q={topic}'
        op = urlopen(Request(site, headers={'User-Agent': 'Mozilla/5.0'}))
        rd = op.read()
        op.close()
        sp_page = soup(rd, 'xml')
        news_list = sp_page.find_all('item')
        return news_list
    except Exception as e:
        st.error(f"Error fetching news for topic {topic}: {e}")
        return []

def fetch_top_news():
    try:
        site = 'https://news.google.com/news/rss'
        op = urlopen(Request(site, headers={'User-Agent': 'Mozilla/5.0'}))
        rd = op.read()
        op.close()
        sp_page = soup(rd, 'xml')
        news_list = sp_page.find_all('item')
        return news_list
    except Exception as e:
        st.error(f"Error fetching top news: {e}")
        return []

def fetch_category_news(topic):
    try:
        site = f'https://news.google.com/news/rss/headlines/section/topic/{topic.upper()}'
        op = urlopen(Request(site, headers={'User-Agent': 'Mozilla/5.0'}))
        rd = op.read()
        op.close()
        sp_page = soup(rd, 'xml')
        news_list = sp_page.find_all('item')
        return news_list
    except Exception as e:
        st.error(f"Error fetching category news for {topic}: {e}")
        return []

def fetch_news_poster(poster_link):
    try:
        u = urlopen(Request(poster_link, headers={'User-Agent': 'Mozilla/5.0'}))
        raw_data = u.read()
        image = Image.open(io.BytesIO(raw_data))
        st.image(image, use_column_width=True)
    except Exception as e:
        st.error(f"Error fetching image: {e}")
        image = Image.open('snap.png')
        st.image(image, use_column_width=True)

def save_article(index, title, link, summary):
    st.session_state['saved_articles'].append({'title': title, 'link': link, 'summary': summary})
    st.session_state['saved_status'][index] = True
    st.success(f'Article "{title}" saved!')

def unsave_article(index, title):
    st.session_state['saved_articles'] = [article for article in st.session_state['saved_articles'] if article['title'] != title]
    st.session_state['saved_status'][index] = False
    st.success(f'Article "{title}" removed!')

def load_saved_articles():
    st.subheader("Saved Articles")
    for index, article in enumerate(st.session_state['saved_articles']):
        st.write(f"**{article['title']}**")
        st.write(f"[Read more...]({article['link']})")
        st.write(f"{article['summary']}")
        if st.button("Unsave", key=f"unsave_{index}_saved"):
            unsave_article(index, article['title'])
        st.write("---")

def text_to_speech(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    audio_file = f"audio_{text[:10].replace(' ', '_')}.mp3"
    tts.save(audio_file)
    audio_data = open(audio_file, "rb").read()
    b64 = base64.b64encode(audio_data).decode()
    audio_html = f"""
    <audio controls>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        Your browser does not support the audio element.
    </audio>
    """
    return audio_html

def display_news(list_of_news, page_number, language):
    from googletrans import Translator
    translator = Translator()
    items_per_page = 5
    start_index = page_number * items_per_page
    end_index = start_index + items_per_page
    news_to_display = list_of_news[start_index:end_index]

    for i, news in enumerate(news_to_display):
        index = start_index + i
        st.write(f'**({index + 1}) {news.title.text}**')
        if not news.link or not news.link.text.startswith('http'):
            st.warning(f"Skipping article with invalid URL: {news.link.text}")
            continue
        news_data = Article(news.link.text)
        try:
            news_data.download()
            news_data.parse()
            news_data.nlp()
        except Exception as e:
            st.error(f"Error processing article {news.link.text}: {e}")
            continue 

        image_url = news_data.top_image if news_data.top_image else 'snap.png'
        fetch_news_poster(image_url)

        with st.expander(news.title.text):
            try:
                summary = news_data.summary if news_data.summary else "No summary available."
                summary_translated = translator.translate(summary, dest=language).text
            except Exception as e:
                summary_translated = f"Error in translation: {e}"
            st.markdown(f"<h6 style='text-align: justify;'>{summary_translated}</h6>", unsafe_allow_html=True)
            source_url = news_data.source_url if news_data.source_url else news.link.text
            st.markdown(f"[Read more at source]({source_url})")
            audio_html = text_to_speech(summary_translated)
            st.markdown(audio_html, unsafe_allow_html=True)

            if st.session_state['saved_status'].get(index, False):
                if st.button("Unsave", key=f"unsave_{index}"):
                    unsave_article(index, news.title.text)
            else:
                if st.button("Save", key=f"save_{index}"):
                    save_article(index, news.title.text, news.link.text, summary_translated)

            st.write("---")
            st.write("Share on:")
            st.markdown(
                f"""
                <a href="https://www.facebook.com/sharer/sharer.php?u={news.link.text}" target="_blank">
                <img src="https://img.icons8.com/fluent/48/000000/facebook-new.png"/>
                </a>
                <a href="https://twitter.com/intent/tweet?url={news.link.text}&text={news.title.text}" target="_blank">
                <img src="https://img.icons8.com/fluent/48/000000/twitter.png"/>
                </a>
                <a href="https://www.linkedin.com/shareArticle?mini=true&url={news.link.text}&title={news.title.text}" target="_blank">
                <img src="https://img.icons8.com/fluent/48/000000/linkedin.png"/>
                </a>
                """,
                unsafe_allow_html=True
            )
        st.success("Published Date: " + news.pubDate.text)

def fetch_real_breaking_news():
    url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'ok' and data['totalResults'] > 0:
            return random.choice(data['articles'])['title']
    return "No breaking news available at the moment."

def simulate_notifications():
    notification = fetch_real_breaking_news()
    st.sidebar.info(notification)

def remove_emojis(input_string):
    return re.sub(r'[^\w\s,]', '', input_string)

def run():
    st.markdown("<h1 style='text-align: center;'>SnapNews🇸🇬: News Anytime, Anywhere 🌍🕒</h1>", unsafe_allow_html=True)
    image = Image.open('snap.png')

    col1, col2, col3 = st.columns([3, 5, 3])

    with col1:
        st.write("")

    with col2:
        st.image(image, use_column_width=False)

    with col3:
        st.write("")

    if st.sidebar.button("Simulate Notification"):
        simulate_notifications()

    category = ['--Select--', '🔥 Hot News', '💙 Top Picks', '🔍 Explore']
    cat_op = st.selectbox('Choose Your News', category)

    language_options = ['English', 'Malay', 'Tamil', 'Chinese']
    language = st.selectbox('Select Language', language_options)
    language_code = {'English': 'en', 'Malay': 'ms', 'Tamil': 'ta', 'Chinese': 'zh-cn'}

    news_list = []

    if cat_op == category[0]:
        st.warning('Please select a category!')
    elif cat_op == category[1]:
        st.subheader("🔥 Hot News")
        news_list = fetch_top_news()
        display_news(news_list, st.session_state['page_number'], language_code[language])
    elif cat_op == category[2]:
        av_topics = ['Choose Topic', '🌐 World', '🏛️ Nation', '💼 Business', '💻 Tech', '🎭 Entertainment', '⚽ Sports', '🔬 Science', '🩺 Health']
        st.subheader("💙 Top Picks")
        chosen_topic = st.selectbox("Choose your favourite topic", av_topics)
        if chosen_topic == av_topics[0]:
            st.warning("Please choose a topic")
        else:
            chosen_topic_keyword = chosen_topic.split()[-1]  
            news_list = fetch_category_news(chosen_topic_keyword)
            if news_list:
                st.subheader(f"💙 Here are some {chosen_topic_keyword} news for you")
                display_news(news_list, st.session_state['page_number'], language_code[language])
            else:
                st.error(f"No news found for {chosen_topic}")

    elif cat_op == category[3]:
        user_topic = st.text_input("Enter Your Topic🔍")

        if st.button("Search") and user_topic != '':
            user_topic_pr = remove_emojis(user_topic.replace(' ', ''))
            news_list = fetch_news_search_topic(topic=user_topic_pr)
            if news_list:
                st.subheader(f"🔍 Here are some {user_topic.capitalize()} news for you")
                display_news(news_list, st.session_state['page_number'], language_code[language])
            else:
                st.error(f"No news found for {user_topic}")
        else:
            st.warning("Please enter a topic name to search🔍")

    if news_list:
        if st.session_state['page_number'] > 0:
            if st.button("Previous", key="prev"):
                st.session_state['page_number'] -= 1
                st.experimental_rerun()

        if st.session_state['page_number'] < (len(news_list) // 5):
            if st.button("Next", key="next"):
                st.session_state['page_number'] += 1
                st.experimental_rerun()

    load_saved_articles()

run()

def display_news(list_of_news, page_number, language):
    translator = Translator()
    items_per_page = 5
    start_index = page_number * items_per_page
    end_index = start_index + items_per_page
    news_to_display = list_of_news[start_index:end_index]

    for i, news in enumerate(news_to_display):
        index = start_index + i
        st.write(f'**({index + 1}) {news.title.text}**')

        if not news.link or not news.link.text.startswith('http'):
            st.warning(f"Skipping article with invalid URL: {news.link.text}")
            continue
        
        try:
            article = Article(news.link.text)
            article.download()
            article.parse()

            # Perform NLP and summarize the article
            article.nlp()
            summary = article.summary if article.summary else "No summary available."
            
            # Translate summary to the selected language
            summary_translated = translator.translate(summary, dest=language).text
            
            # Display news poster image
            image_url = article.top_image if article.top_image else 'snap.png'
            fetch_news_poster(image_url)
            
            # Display summary and link to full article
            with st.expander(news.title.text):
                st.markdown(f"<h6 style='text-align: justify;'>{summary_translated}</h6>", unsafe_allow_html=True)
                st.markdown(f"[Read more at source]({article.source_url})", unsafe_allow_html=True)
                
                # Text to speech functionality
                audio_html = text_to_speech(summary_translated)
                st.markdown(audio_html, unsafe_allow_html=True)

                # Save/Unsave buttons
                if st.session_state['saved_status'].get(index, False):
                    if st.button("Unsave", key=f"unsave_{index}"):
                        unsave_article(index, news.title.text)
                else:
                    if st.button("Save", key=f"save_{index}"):
                        save_article(index, news.title.text, news.link.text, summary_translated)

                st.write("---")
                st.write("Share on:")
                # Share buttons
                st.markdown(
                    f"""
                    <a href="https://www.facebook.com/sharer/sharer.php?u={news.link.text}" target="_blank">
                    <img src="https://img.icons8.com/fluent/48/000000/facebook-new.png"/>
                    </a>
                    <a href="https://twitter.com/intent/tweet?url={news.link.text}&text={news.title.text}" target="_blank">
                    <img src="https://img.icons8.com/fluent/48/000000/twitter.png"/>
                    </a>
                    <a href="https://www.linkedin.com/shareArticle?mini=true&url={news.link.text}&title={news.title.text}" target="_blank">
                    <img src="https://img.icons8.com/fluent/48/000000/linkedin.png"/>
                    </a>
                    """,
                    unsafe_allow_html=True
                )
            st.success("Published Date: " + news.pubDate.text)

        except Exception as e:
            st.error(f"Error processing article {news.link.text}: {e}")
