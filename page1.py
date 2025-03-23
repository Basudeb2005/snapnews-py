import streamlit as st
from PIL import Image
import nltk
from bs4 import BeautifulSoup as soup
from urllib.request import urlopen, Request
from newspaper import Article
import io
from gtts import gTTS
import base64
import random
import requests
import re
import os
import pandas as pd
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import hashlib
import csv

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

if 'saved_articles' not in st.session_state:
    st.session_state['saved_articles'] = []

if 'saved_status' not in st.session_state:
    st.session_state['saved_status'] = {}

if 'page_number' not in st.session_state:
    st.session_state['page_number'] = 0

NEWS_API_KEY = 'ec48b2493593467a8947d0253d2786a2'
COMMENTS_CSV = 'comments.csv'
USERS_CSV = 'users.csv'


def fetch_rss_feed(url):
    try:
        op = urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}))
        rd = op.read()
        op.close()
        sp_page = soup(rd, 'xml')
        news_list = sp_page.find_all('item')
        return news_list
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []


def fetch_news_poster(poster_link):
    try:
        u = urlopen(Request(poster_link, headers={'User-Agent':
                                                  'Mozilla/5.0'}))
        raw_data = u.read()
        image = Image.open(io.BytesIO(raw_data))
        st.image(image, use_container_width=True)
    except Exception as e:
        st.error(f"Error fetching image: {e}")
        image = Image.open('snap.png')
        st.image(image, use_container_width=True)


def save_article(index, title, link, summary):
    st.session_state['saved_articles'].append({
        'title': title,
        'link': link,
        'summary': summary
    })
    st.session_state['saved_status'][index] = True
    st.success(f'Article "{title}" saved!')


def unsave_article(index, title):
    st.session_state['saved_articles'] = [
        article for article in st.session_state['saved_articles']
        if article['title'] != title
    ]
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


def summarize_text(text):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 2)  # Summarize to 2 sentences
    return " ".join([str(sentence) for sentence in summary])


def extract_article_text(url):
    try:
        # Using newspaper3k library with timeout
        import socket
        default_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(10)  # Set timeout to 10 seconds

        article = Article(url)
        article.download()
        article.parse()

        # Reset timeout to default
        socket.setdefaulttimeout(default_timeout)

        if article.text:
            return article.text, article.top_image or 'snap.png'
        else:
            # If no text was extracted, try the fallback method
            raise Exception("No text extracted by newspaper3k")
    except Exception as e:
        st.error(f"Newspaper library failed to extract article: {e}")
        try:
            # Fallback method using BeautifulSoup
            headers = {
                'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            req = Request(url, headers=headers)

            # Set timeout for urlopen
            page = urlopen(req, timeout=10).read()
            page_soup = soup(page, 'html.parser')

            # Extract paragraphs
            paragraphs = page_soup.find_all('p')
            text = ' '.join([
                para.text for para in paragraphs if len(para.text) > 20
            ])  # Filter out short paragraphs

            # Look for image
            img_url = 'snap.png'
            try:
                top_image = page_soup.find('meta', property='og:image')
                if not top_image:
                    top_image = page_soup.find('meta',
                                               attrs={'name': 'og:image'})

                # Check if it's a valid Tag element with content
                if top_image and hasattr(top_image, 'attrs'):
                    try:
                        if 'content' in top_image.attrs:
                            img_url = top_image['content']
                    except (AttributeError, KeyError):
                        pass
            except Exception:
                pass  # Keep using the default image

            if text:
                return text, img_url
            else:
                st.warning(f"Could not extract meaningful text from {url}")
                return "No content could be extracted from this article.", 'snap.png'
        except Exception as e:
            st.error(f"BeautifulSoup failed to extract article: {e}")
            return "Unable to access this article content. The website might be blocking access or the article might no longer be available.", 'snap.png'


def display_news(list_of_news, page_number, language, s):
    from googletrans import Translator
    items_per_page = 5
    start_index = page_number * items_per_page
    end_index = start_index + items_per_page
    news_to_display = list_of_news[start_index:end_index]

    for i, news in enumerate(news_to_display):
        index = start_index + i
        title = news.title.text if news.title else "No title"
        link = news.link.text if news.link else "No link"

        st.write(f'**({index + 1}) {title}**')
        if not link or not link.startswith('http'):
            st.warning(f"Skipping article with invalid URL: {link}")
            continue

        # Initialize default values to avoid possibly unbound variables
        summary_translated = "Error retrieving article content."
        top_image = 'snap.png'

        try:
            # Extract article text and image
            article_text, top_image = extract_article_text(link)

            # Summarize if we have text
            if article_text:
                summary = summarize_text(article_text)

                # Translate summary based on selected language
                if language != 'en':  # Only translate if not English
                    try:
                        # Create a new translator instance each time to avoid session issues
                        translator = Translator()

                        # Add retry logic for translation
                        max_retries = 3
                        translation_successful = False

                        for retry in range(max_retries):
                            try:
                                translated = translator.translate(
                                    summary, dest=language)
                                summary_translated = translated.text
                                translation_successful = True
                                break
                            except Exception as translate_error:
                                if retry == max_retries - 1:  # If last retry
                                    st.warning(
                                        f"Translation failed. Showing original content: {translate_error}"
                                    )
                                    summary_translated = summary  # Use original summary if translation fails
                                else:
                                    # Wait before retrying (increasing delay)
                                    import time
                                    time.sleep(1 * (retry + 1))

                        # If all retries failed and we didn't set summary_translated yet
                        if not translation_successful and 'summary_translated' not in locals(
                        ):
                            summary_translated = summary

                    except Exception as e:
                        st.warning(
                            f"Translation error: {str(e)}. Showing original content."
                        )
                        summary_translated = summary  # Fallback to original language
                else:
                    # No translation needed for English
                    summary_translated = summary
            else:
                summary_translated = "No content available for summarization."
        except Exception as e:
            st.error(f"Error processing article {link}: {e}")

        fetch_news_poster(top_image)

        with st.expander(title):
            st.markdown(
                f"<h6 style='text-align: justify;'>{summary_translated}</h6>",
                unsafe_allow_html=True)
            source_url = link
            st.markdown(f"[Read more at source]({source_url})")
            audio_html = text_to_speech(summary_translated)
            st.markdown(audio_html, unsafe_allow_html=True)

            if st.session_state['saved_status'].get(index, False):
                if st.button("Unsave", key=f"unsave_{index}"):
                    unsave_article(index, title)
            else:
                if st.button("Save", key=f"save_{index}"):
                    save_article(index, title, link, summary_translated)

            st.write("---")
            st.write("Share on:")
            st.markdown(f"""
                <a href="https://www.facebook.com/sharer/sharer.php?u={link}" target="_blank">
                <img src="https://img.icons8.com/fluent/48/000000/facebook-new.png"/>
                </a>
                <a href="https://twitter.com/intent/tweet?url={link}&text={title}" target="_blank">
                <img src="https://img.icons8.com/fluent/48/000000/twitter.png"/>
                </a>
                <a href="https://www.linkedin.com/shareArticle?mini=true&url={link}&title={title}" target="_blank">
                <img src="https://img.icons8.com/fluent/48/000000/linkedin.png"/>
                </a>
                """,
                        unsafe_allow_html=True)
            st.success("Published Date: " + news.pubDate.text)

            # Display and add comments
            st.write("Comments:")
            comments = load_comments(link)
            for comment in comments:
                st.write(f"{comment['username']}: {comment['comment']}")
            new_comment = st.text_area(
                f"Add a comment for article {index + 1}",
                key=f"comment_{index}")
            if st.button("Submit", key=f"submit_{index}"):
                add_comment(link, new_comment, s)
                st.success("Comment added!")
                st.rerun()


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


import csv


def add_comment(article_url, comment, username="Anonymous"):
    try:
        if comment.strip() == "":
            st.error("Comment cannot be empty")
            return

        new_comment = {
            "article_url": article_url,
            "comment": comment,
            "username": username
        }

        # Read existing comments
        if os.path.exists(COMMENTS_CSV):
            with open(COMMENTS_CSV, mode='r', newline='',
                      encoding='utf-8') as file:
                reader = csv.DictReader(file)
                comments = list(reader)
        else:
            comments = []

        # Add new comment
        comments.append(new_comment)

        # Write updated comments back to the CSV
        with open(COMMENTS_CSV, mode='w', newline='',
                  encoding='utf-8') as file:
            fieldnames = ["article_url", "comment", "username"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comments)

        st.success("Comment added successfully!")

    except Exception as e:
        st.error(f"Error saving comment: {e}")


def load_comments(article_url):
    try:
        if os.path.exists(COMMENTS_CSV):
            comments_df = pd.read_csv(COMMENTS_CSV)
            article_comments = comments_df[comments_df['article_url'] ==
                                           article_url]
            return article_comments.to_dict('records')
        else:
            return []
    except Exception as e:
        st.error(f"Error loading comments: {e}")
        return []
        st.error(f"Error saving comment: {e}")


def main(s):

    if 'saved_articles' not in st.session_state:
        st.session_state['saved_articles'] = []

    if 'saved_status' not in st.session_state:
        st.session_state['saved_status'] = {}

    if 'page_number' not in st.session_state:
        st.session_state['page_number'] = 0
    st.markdown(
        "<h1 style='text-align: center;'>SnapNews🇸🇬: News Anytime, Anywhere 🌍🕒</h1>",
        unsafe_allow_html=True)
    image = Image.open('snap.png')

    col1, col2, col3 = st.columns([3, 5, 3])

    with col1:
        st.write("")

    with col2:
        st.image(image)

    with col3:
        st.write("")

    if st.sidebar.button("Simulate Notification"):
        simulate_notifications()

    category = ['--Select--', '🔥 Hot News', '💙 Top Picks', '🔍 Explore']
    cat_op = st.selectbox('Choose Your News', category)

    language_options = ['English', 'Malay', 'Tamil', 'Chinese']
    language = st.selectbox('Select Language', language_options)
    language_code = {
        'English': 'en',
        'Malay': 'ms',
        'Tamil': 'ta',
        'Chinese': 'zh-cn'
    }

    news_list = []

    if cat_op == category[0]:
        st.warning('Please select a category!')
    elif cat_op == category[1]:
        st.subheader("🔥 Hot News")
        news_list = fetch_rss_feed('https://www.yahoo.com/news/rss')
        display_news(news_list, st.session_state['page_number'],
                     language_code[language], s)
    elif cat_op == category[2]:
        av_topics = [
            'Choose Topic', '💼 Business', '💻 Tech', '⚖️ Politics', '🌍 World',
            '⚽ Sports'
        ]
        st.subheader("💙 Top Picks")
        chosen_topic = st.selectbox("Choose your favourite topic", av_topics)
        if chosen_topic == av_topics[0]:
            st.warning("Please choose a topic")
        else:
            if chosen_topic == '💼 Business':
                news_list = fetch_rss_feed('https://finance.yahoo.com/rss/')
            elif chosen_topic == '💻 Tech':
                news_list = fetch_rss_feed(
                    'https://www.yahoo.com/news/tech/rss')
            elif chosen_topic == '⚖️ Politics':
                news_list = fetch_rss_feed(
                    'https://news.yahoo.com/rss/politics')
            elif chosen_topic == '🌍 World':
                news_list = fetch_rss_feed('https://news.yahoo.com/rss/world')
            elif chosen_topic == '⚽ Sports':
                news_list = fetch_rss_feed('https://sports.yahoo.com/rss/')

            if news_list:
                st.subheader(
                    f"💙 Here are some {chosen_topic.split()[-1]} news for you")
                display_news(news_list, st.session_state['page_number'],
                             language_code[language], s)
            else:
                st.error(f"No news found for {chosen_topic}")

    elif cat_op == category[3]:
        user_topic = st.text_input("Enter Your Topic🔍")

        if st.button("Search") and user_topic != '':
            user_topic_pr = remove_emojis(user_topic.replace(' ', ''))
            news_list = fetch_rss_feed(
                f"https://news.google.com/rss/search?q={user_topic_pr}&hl=en-IN&gl=IN&ceid=IN:en"
            )
            if news_list:
                st.subheader(
                    f"🔍 Here are some {user_topic.capitalize()} news for you")
                display_news(news_list, st.session_state['page_number'],
                             language_code[language], s)
            else:
                st.error(f"No news found for {user_topic}")
        else:
            st.warning("Please enter a topic name to search🔍")

    if news_list:
        if st.session_state['page_number'] > 0:
            if st.button("Previous", key="prev"):
                st.session_state['page_number'] -= 1
                st.rerun()

        if st.session_state['page_number'] < (len(news_list) // 5):
            if st.button("Next", key="next"):
                st.session_state['page_number'] += 1
                st.rerun()

    load_saved_articles()


if __name__ == "__main__":
    main("Anonymous")  # Default username when run directly
